"""B-02 LIF engine: the B-01 Shiu-standard spike-driven engine
(`lif_b01.py`, byte-identical copy of B-01's frozen `lif.py`) extended
with THREE DISTINCT drive APIs, each named for what it physically is.

  API 1  `inject(ids, dv)`
      Current injection: a calibrated depolarization added directly to
      the target cells' membrane potential (no delay, no reset, no
      refractory interaction beyond the threshold test). This is the
      "declared 15 mV" semantics the B-01 pre-registration intended but
      never actually delivered (B-01 README deviation 5).

  API 2  `events(ids, counts, w)`
      External synaptic events ONTO a target population: each event adds
      the DECLARED per-event weight `w` (mV, default `drive_w`) to the
      target's conductance `g`, delivered with the same fixed synaptic
      delay as internal spikes, and integrated by the membrane exactly
      like a synaptic input. Note: B-01's `ext_spikes` delivery was
      NOT this — it forced DRIVE neurons to spike and let their own
      measured outgoing weights do the work (see API 3). B-02 names
      the two apart; both are kept.

  API 3  `force(ids)`
      Forced spikes: the named cells are made to spike on this step
      (reset + refractory + their measured outgoing edges enqueued).
      This is what B-01's "drive" actually did at the circuit level.

The core step is byte-for-byte the B-01 one (same operation order:
expire queue -> g decay -> refractory -> exact-exponential membrane
update -> threshold -> reset/queue), so results remain comparable with
B-01; only the drive path changed.
"""
import torch

from lif_b01 import LIFNet as LIFNetB01


class LIFNet(LIFNetB01):
    def __init__(self, src, dst, w, n, *, drive_w=3.0, **kw):
        super().__init__(src, dst, w, n, **kw)
        self.drive_w = float(drive_w)
        # second delay queue for declared-weight external events
        self.wqueue = [None] * self.delay_steps

    def _deliver(self, spike_ids):
        """B-01 delivery, guarded for edgeless test networks."""
        if len(self.u_src) == 0:
            return
        super()._deliver(spike_ids)

    # ---------------- API 1: current injection ----------------
    def inject(self, ids, dv):
        """Add dv (mV) directly to the membrane potential of `ids`.
        Calibrated semantics: dv is the declared depolarization itself;
        a cell at v0=-52 mV with v_th=-45 mV needs dv > 7 mV to cross
        threshold (strict inequality; see test_drives.py calibration)."""
        if len(ids) == 0:
            return
        self.v[ids] = self.v[ids] + dv

    # ---------------- API 2: external synaptic events ------------
    def events(self, ids, counts, w=None):
        """Queue `counts` external events onto target cells `ids`, each
        adding `w` mV (default drive_w) to g after the synaptic delay."""
        ids = torch.as_tensor(ids, dtype=torch.int64)
        counts = torch.as_tensor(counts, dtype=torch.int64)
        keep = counts > 0
        if not keep.any():
            return
        entry = (ids[keep], counts[keep].clone(),
                 float(w) if w is not None else self.drive_w)
        self.wqueue.append(entry)

    # ---------------- API 3: forced spikes -----------------------
    def force(self, ids):
        """Make `ids` spike on this step (their outgoing edges are
        enqueued like any spike; this is B-01's actual drive behavior)."""
        ids = torch.as_tensor(ids, dtype=torch.int64)
        if len(ids) == 0:
            return
        self.v[ids] = self.v_rst
        self.g[ids] = 0.0
        self.rf[ids] = self.rfc
        self.queue.append(ids)

    # ---------------- step --------------------------------------
    def step(self, ext_spikes=None, ext_events=None, injects=None,
             forces=None):
        """One dt step.
        ext_spikes  (src_ids, counts): B-01 semantics — external spikes
                    of source neurons delivered through their own
                    measured outgoing weights (deprecated in B-02, kept
                    for comparison runs).
        ext_events  (dst_ids, counts, w or None): API 2 events.
        injects     (ids, dv): API 1.
        forces      ids: API 3.
        """
        self.t += self.dt
        # 1. deliver expired internal-spikes queue
        due = self.queue.pop(0)
        self._deliver(due)
        # 1b. deliver expired declared-weight external events
        wdue = self.wqueue.pop(0)
        if wdue is not None:
            ids, cnt, w = wdue
            self.g.scatter_add_(0, ids, w * cnt.to(torch.float32))
        # 2. synaptic current decay
        self.g = self.g * self.exp_tau
        # 3. refractory bookkeeping
        self.rf = torch.maximum(self.rf - self.dt, torch.zeros(1))
        # 4. membrane (exact exponential integration of g between steps)
        self.v = self.v0v + (self.v - self.v0v) * self.exp_tm + \
            self.g * self.one_minus_exp_tm
        # 5. API 1: current injection (before the threshold test)
        if injects is not None:
            ids, dv = injects
            self.v[ids] = self.v[ids] + dv
        # 6. threshold (API 3 forced spikes override the test)
        spiked = (self.v > self.v_th) & (self.rf <= 0)
        if forces is not None and len(forces) > 0:
            f = torch.as_tensor(forces, dtype=torch.int64)
            spiked = spiked | torch.zeros(self.n, dtype=torch.bool)
            spiked[f] = True
        if spiked.any():
            idx = spiked.nonzero().flatten()
        else:
            idx = torch.zeros(0, dtype=torch.int64)
        # 7. reset / refractory / queue (identical to B-01)
        if len(idx) > 0:
            self.v[idx] = self.v_rst
            self.g[idx] = 0.0
            self.rf[idx] = self.rfc
        self.total_spikes += len(idx)
        if ext_spikes is not None and len(ext_spikes[0]) > 0:
            ids, cnt = ext_spikes
            ids, cnt = torch.as_tensor(ids, dtype=torch.int64), \
                torch.as_tensor(cnt, dtype=torch.int64)
            keep = cnt > 0
            ext = torch.repeat_interleave(ids[keep], cnt[keep])
        else:
            ext = torch.zeros(0, dtype=torch.int64)
        self.queue.append(torch.cat([idx, ext]))
        self.wqueue.append(None)
        return idx if len(idx) > 0 else None

    def reset(self):
        """B-02-local reset. The pinned B-01 reset() (inherited here)
        is LATENT-BROKEN per the A-03 lane (2026-10-12): it calls
        fill_ with a value whose dimensionality follows the v0 argument
        on state fields that are multi-dim when v0 is — B-01 never
        called it, so it never surfaced. IDIOM: never call reset() to
        re-run a network — the sanctioned reset is FRESH LIFNet
        construction (constructor state == B-01's initial state; A-03
        pinned and verified a byte-identical copy). This override
        exists so the class does not expose the broken inherited
        primitive; it rebuilds the initial state directly."""
        self.v = torch.full((self.n,), self.v0)
        self.g = torch.zeros(self.n)
        self.rf = torch.zeros(self.n)
        self.queue = [torch.zeros(0, dtype=torch.int64)
                      for _ in range(self.delay_steps)]
        self.wqueue = [None] * self.delay_steps
        self.t = 0.0
        self.total_spikes = 0
