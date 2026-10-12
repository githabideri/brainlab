"""Custom torch LIF spiking network (no external toolkit).

Implements the model as published by Shiu et al. (2024) and implemented by
the fly-brain toolkit (code/paper-phil-drosophila/model.py): single-
exponential synaptic current (g += w on delivery; exponential decay),
voltage reset to v_rst with g cleared, absolute refractory period, constant
synaptic delay. Defaults match that file: v0=-52 mV, v_th=-45 mV,
v_rst=-52 mV, tau_m=20 ms, tau=5 ms, delay=1.8 ms, refractory=2.2 ms.

Spike-driven: the membrane integrates the exact exponential between steps;
synaptic updates are O(delivered spikes x fan-out), not O(edges).
"""
import torch


class LIFNet:
    def __init__(self, src, dst, w, n, *, v0=-52.0, v_th=-45.0, v_rst=-52.0,
                 tau_m=20.0, tau=5.0, delay_ms=1.8, refractory_ms=2.2, dt=1.0,
                 tonic=None):
        dev = torch.device("cpu")
        self.n = int(n)
        self.v0, self.v_th, self.v_rst = v0, v_th, v_rst
        self.dt = dt
        self.rfc = refractory_ms
        src = torch.as_tensor(src, dtype=torch.int64)
        dst = torch.as_tensor(dst, dtype=torch.int64)
        w = torch.as_tensor(w, dtype=torch.float32)
        o = src.argsort(stable=True)
        src, dst, w = src[o], dst[o], w[o]
        self.src = src.to(dev)
        self.dst = dst.to(dev)
        self.w = w.to(dev)
        # block boundaries per presynaptic neuron
        self.u_src, c = torch.unique(self.src, return_counts=True)
        self.u_start = torch.cat([torch.zeros(1, dtype=torch.int64), c.cumsum(0)])
        self.exp_tau = torch.exp(torch.tensor(-dt / tau))
        self.exp_tm = torch.exp(torch.tensor(-dt / tau_m))
        self.one_minus_exp_tm = 1.0 - self.exp_tm
        # per-neuron tonic offset (declared background drive, mV steady-state)
        self.v0v = torch.full((self.n,), v0)
        if tonic is not None:
            self.v0v = self.v0v + torch.as_tensor(tonic, dtype=torch.float32)
        self.v = torch.full((self.n,), v0)
        self.g = torch.zeros(self.n)
        self.rf = torch.zeros(self.n)          # refractory remaining, ms
        self.delay_steps = max(1, int(round(delay_ms / dt)))
        self.queue = [torch.zeros(0, dtype=torch.int64)
                      for _ in range(self.delay_steps)]
        self.t = 0.0
        self.total_spikes = 0

    def _deliver(self, spike_ids):
        """spike_ids: int64 tensor, one entry per spike (duplicates allowed
        within a step, e.g. Poisson counts). Adds w to g of every
        postsynaptic neuron of each spiking source."""
        if len(spike_ids) == 0:
            return
        uniq, cnt = torch.unique(spike_ids, return_counts=True)
        j = torch.searchsorted(self.u_src, uniq)
        jchk = j.clamp(max=len(self.u_src) - 1)
        keep = (j < len(self.u_src)) & (self.u_src[jchk] == uniq)
        j, cnt = j[keep], cnt[keep]
        if len(j) == 0:
            return
        s = self.u_start[j]
        e = self.u_start[j + 1]
        sizes = e - s
        total = int(sizes.sum())
        base = torch.repeat_interleave(s, sizes)
        block_starts = torch.cat([torch.zeros(1, dtype=torch.int64),
                                  sizes.cumsum(0)[:-1]])
        inner = torch.arange(total, dtype=torch.int64) - \
            torch.repeat_interleave(block_starts, sizes)
        pos = base + inner
        self.g.scatter_add_(0, self.dst[pos],
                            self.w[pos] * torch.repeat_interleave(
                                cnt.to(torch.float32), sizes))

    def step(self, ext_spikes=None):
        """One timestep (dt ms). ext_spikes: (src_ids, counts) of external
        Poisson drive spikes this step, aggregated per source; delivered
        with the same constant delay as internal spikes.
        The delay queue holds exactly delay_steps entries; internal and
        external events of a step are merged into one queue slot so the
        queue length stays fixed and the delay is a true constant.
        Returns the ids of neurons that spiked this step (or None)."""
        self.t += self.dt
        # 1. deliver spikes whose delay expired
        due = self.queue.pop(0)
        self._deliver(due)
        # 2. synaptic current decay
        self.g = self.g * self.exp_tau
        # 3. refractory bookkeeping
        self.rf = torch.maximum(self.rf - self.dt, torch.zeros(1))
        # 4. membrane (exact exponential integration of g between steps)
        self.v = self.v0v + (self.v - self.v0v) * self.exp_tm + \
            self.g * self.one_minus_exp_tm
        # 5. threshold
        spiked = (self.v > self.v_th) & (self.rf <= 0)
        if spiked.any():
            idx = spiked.nonzero().flatten()
            self.v[idx] = self.v_rst
            self.g[idx] = 0.0
            self.rf[idx] = self.rfc
            self.total_spikes += len(idx)
        else:
            idx = torch.zeros(0, dtype=torch.int64)
        # 6. queue this step's events (internal + external) as one entry
        if ext_spikes is not None and len(ext_spikes[0]) > 0:
            ids, cnt = ext_spikes
            ids, cnt = torch.as_tensor(ids, dtype=torch.int64), \
                torch.as_tensor(cnt, dtype=torch.int64)
            keep = cnt > 0
            ext = torch.repeat_interleave(ids[keep], cnt[keep])
        else:
            ext = torch.zeros(0, dtype=torch.int64)
        self.queue.append(torch.cat([idx, ext]))
        return idx if len(idx) > 0 else None

    def reset(self):
        self.v.fill_(self.v0v)
        self.g.zero_()
        self.rf.zero_()
        self.queue = [torch.zeros(0, dtype=torch.int64)
                      for _ in range(self.delay_steps)]
        self.t = 0.0
