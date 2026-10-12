"""Independent plain-numpy LIF, written from the Shiu et al. 2024
equations (Nature 634:210-219, Methods — `text/Shiu2024.txt` in the
research pack), NOT from `lif_b01.py`. Used only for the Stage 1
differential test (max spike-time difference vs the torch engine on
identical seeded inputs).

Model, as published:
  dv/dt = ( g_i - (v_i - V_rest) ) / T_m          (mV/ms; g is the
                                                  effective conductance
                                                  in mV, i.e. w already
                                                  scaled)
  dg/dt = -g / tau
  g_i += w_j,i  when presynaptic neuron j fires (after a fixed delay
  T_dly = 1.8 ms); g starts at 0
  v is reset to V_reset and frozen for T_refr after a spike; a spike
  occurs when v crosses V_threshold (strict >)

Parameters (all published values): V_rest = V_reset = -52 mV,
V_threshold = -45 mV, T_m = C_m*R_m = 2*10 ms = 20 ms, tau = 5 ms,
T_dly = 1.8 ms (2 steps at dt = 1 ms), T_refr = 2.2 ms,
W_syn = 0.275 mV per PSD unit.

Discretization (derived independently here): the standard exact
integration of the two ODEs with g held at its end-of-decay value over
each step:
  g(t+dt) = g(t) * exp(-dt/tau)
  v(t+dt) = V_rest + (v(t) - V_rest)*exp(-dt/T_m) + g(t+dt)*(1 - exp(-dt/T_m))
This is the unique scheme that is exact when g is piecewise constant
between spikes, which is what the published model's single-exponential
form implies; it is also what the torch engine does, and that identity
is what the differential test is trying to establish.
"""
import numpy as np


class NumpyLIF:
    def __init__(self, src, dst, w, n, *, v0=-52.0, v_th=-45.0,
                 v_rst=-52.0, tau_m=20.0, tau=5.0, delay_ms=1.8,
                 refractory_ms=2.2, dt=1.0, tonic=None,
                 dtype=np.float64):
        self.n = int(n)
        self.dt = dt
        self.t = 0.0
        src = np.asarray(src, dtype=np.int64)
        dst = np.asarray(dst, dtype=np.int64)
        w = np.asarray(w, dtype=np.float64)
        o = np.argsort(src, kind="stable")
        self.src, self.dst, self.w = src[o], dst[o], w[o]
        # per-source block bounds (mirror of the torch reference's
        # u_src/u_start unique+cumsum structure)
        if len(self.src):
            u, c = np.unique(self.src, return_counts=True)
            u_start = np.concatenate([np.zeros(1, dtype=np.int64),
                                      np.cumsum(c)])
            size = int(self.src.max()) + 1
            bs = np.zeros(size, dtype=np.int64)
            be = np.zeros(size, dtype=np.int64)
            bs[u] = u_start[:-1]
            be[u] = u_start[1:]
            self.block_start, self.block_end = bs, be
            self.block_start_map = {int(j) for j in u}
        else:
            self.block_start = self.block_end = np.zeros(1, dtype=np.int64)
            self.block_start_map = set()
        self.v_th = -45.0
        self.v_rst = v_rst
        self.exp_tau = float(np.exp(-dt / tau))
        self.exp_tm = float(np.exp(-dt / tau_m))
        self.om_exp_tm = 1.0 - self.exp_tm
        v0v = np.full(self.n, v0, dtype=dtype)
        if tonic is not None:
            v0v = v0v + np.asarray(tonic, dtype=dtype)
        self.v0v = v0v
        self.v = v0v.copy()
        self.g = np.zeros(self.n, dtype=dtype)
        self.rf = np.zeros(self.n, dtype=np.float64)
        self.rfc = refractory_ms
        self.delay_steps = max(1, int(round(delay_ms / dt)))
        self.queue = [[] for _ in range(self.delay_steps)]
        self.total_spikes = 0

    def _deliver(self, ids):
        if len(np.asarray(ids)) == 0 or not len(self.src):
            return
        for j in set(ids.tolist() if hasattr(ids, "tolist") else ids):
            if j not in self.block_start_map:
                continue
            s, e = self.block_start[j], self.block_end[j]
            # np.add.at: duplicates in dst must accumulate (the torch
            # reference uses scatter_add_; plain fancy-index += would
            # drop them)
            np.add.at(self.g, self.dst[s:e], self.w[s:e])

    def step(self, ext_spikes=None, injects=None, forces=None):
        self.t += self.dt
        due = self.queue.pop(0)
        self._deliver(due)
        self.g *= self.exp_tau
        self.rf = np.maximum(self.rf - self.dt, 0.0)
        self.v = (self.v0v + (self.v - self.v0v) * self.exp_tm +
                  self.g * self.om_exp_tm)
        if injects is not None:
            ids, dv = injects
            self.v[ids] = self.v[ids] + dv
        spiked = (self.v > self.v_th) & (self.rf <= 0)
        if forces is not None and len(forces) > 0:
            spiked[forces] = True
        idx = np.flatnonzero(spiked)
        if len(idx):
            self.v[idx] = self.v_rst  # V_reset = -52 (published)
            self.g[idx] = 0.0
            self.rf[idx] = self.rfc
            self.total_spikes += len(idx)
        if ext_spikes is not None and len(ext_spikes[0]) > 0:
            ids, cnt = ext_spikes
            ext = np.repeat(ids, cnt)
        else:
            ext = np.zeros(0, dtype=np.int64)
        self.queue.append(np.concatenate([idx, ext]) if len(idx) else ext)
        return idx if len(idx) > 0 else None

    def spike_train(self, steps, **per_step_kwargs):
        """Run `steps` steps; per_step_kwargs maps step -> kwargs dict
        for step(). Returns list of (t_ms, ids) spike events."""
        out = []
        for k in range(steps):
            kw = per_step_kwargs.get(k, {})
            idx = self.step(**kw)
            if idx is not None:
                out.append((self.t, idx))
        return out
