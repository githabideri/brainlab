"""The recurrent circuit — A-03 dynamics, sequential variant.

Dynamics reused from ../a-02-learnable-gains/circuit.py (which reuses
A-01's tanh-rate core): tanh hidden state, per-node leak, signed per-edge
gain, internal propagation steps per input. The A-02 treatment is kept
verbatim: zero-init edge gains (-> gain 1.0), per-node leak (-> 0.5),
per-node bias (-> 0), all trainable in every circuit arm.

A-03 changes vs A-02: (1) TEMPORAL — `step_persistent` takes the hidden
state from the previous input step instead of re-initializing it, so a
trial is processed as a sequence with BPTT (T input steps per trial);
`initial()` resets per trial. (2) n_prop = 2 internal propagations per
input step instead of A-02's 4 — a declared sizing revision (measured:
one propagation on this 42,921-edge circuit costs ~95 ms at batch 64,
4 propagations per step put the pre-registered grid ~5x over budget;
2 propagations per 100 ms step is still a deep settling per step, and
T x 2 propagations per trial is more total depth than A-02's 4 per
decision, distributed over time). See the README "Sizing outcome".

The Δw accessor (mandatory per the A-02 review) exposes the effective
edge weight w_eff = base_magnitude * sign * 2*sigmoid(gain) so a run can
record the pre/post difference per edge.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn


class SeqCircuit(nn.Module):
    STEPS = 4  # internal propagation steps per input step (A-01/A-02 core)

    def __init__(self, doc: dict, src, tgt, w, enabled: bool = True,
                 n_prop: int = 4):
        super().__init__()
        self.STEPS = n_prop  # per-instance: A-03 runs with 2 (sizing)
        self.n = len(doc["neurons"])
        self.enabled = enabled
        src = np.asarray(src, dtype=np.int64)
        tgt = np.asarray(tgt, dtype=np.int64)
        w = np.asarray(w, dtype=np.float32)
        if enabled:
            assert src.shape == tgt.shape == w.shape
            assert (src >= 0).all() and (tgt >= 0).all() and src.max() < self.n
            assert not (src == tgt).any(), "self-loop in wiring"
        else:
            assert len(src) == 0, "disconnected circuit must have no edges"
        self.register_buffer("source", torch.tensor(src, dtype=torch.long))
        self.register_buffer("target", torch.tensor(tgt, dtype=torch.long))
        # magnitude: log1p(|w|), normalized per target incoming sum (clamped >= 1)
        mag = torch.tensor(w, dtype=torch.float32).abs().log1p()
        incoming = torch.zeros(self.n).index_add_(0, self.target, mag).clamp_min(1)
        self.register_buffer("edge_sign", torch.tensor(w, dtype=torch.float32).sign())
        self.register_buffer("initial_weight", mag / incoming[self.target])
        self.edge_gain = nn.Parameter(torch.zeros(len(src)))  # -> gain 1.0
        self.leak = nn.Parameter(torch.zeros(self.n))         # -> leak 0.5
        self.bias = nn.Parameter(torch.zeros(self.n))
        # group masks (atlas group ids: 6 = food olfactory receptor neurons;
        # 19/23 = mushroom-body output + lateral horn appositions)
        sensory = [i for i, n in enumerate(doc["neurons"]) if n["group"] == 6]
        outputs = [i for i, n in enumerate(doc["neurons"]) if n["group"] in (19, 23)]
        assert len(sensory) == 256, f"expected 256 drive-channel nodes, got {len(sensory)}"
        assert len(outputs) == 384, f"expected 384 output nodes, got {len(outputs)}"
        self.register_buffer("sensory", torch.tensor(sensory, dtype=torch.long))
        self.register_buffer("outputs", torch.tensor(outputs, dtype=torch.long))

    def trainable(self):
        """A-02 treatment: the zero-init circuit parameters join the optimizer."""
        return [self.edge_gain, self.leak, self.bias]

    @property
    def weight(self) -> torch.Tensor:
        return self.initial_weight * self.edge_sign * (2.0 * torch.sigmoid(self.edge_gain))

    def initial(self, batch: int = 1, device=None) -> torch.Tensor:
        return torch.zeros(batch, self.n, device=device)

    def step_persistent(self, hidden: torch.Tensor, drive: torch.Tensor) -> torch.Tensor:
        """One input step with a PERSISTENT hidden state (the A-03 change
        vs A-02's per-decision re-init): apply the drive, run the 4
        internal propagations, return the new state."""
        leak = torch.sigmoid(self.leak) * 0.9 + 0.05
        for _ in range(self.STEPS):
            message = hidden.new_zeros(hidden.shape)
            if self.enabled:
                message = message.index_add_(1, self.target,
                                             hidden[:, self.source] * self.weight)
            hidden = leak * hidden + (1.0 - leak) * torch.tanh(message + drive + self.bias)
        return hidden

    # ------------------------------------------------------------ Δw
    def w_eff_init(self) -> torch.Tensor:
        return self.initial_weight * self.edge_sign  # gain 1.0 at zero init

    def dw_record(self) -> dict:
        """Pre/post learning change, per edge / per node (float64 numpy).
        dw_eff = w_eff(final) - w_eff(initial); the initial state is the
        zero-init convention, so this is a pure function of the current
        parameters."""
        rec = {
            "dw_eff": (self.weight - self.w_eff_init()).detach().cpu().numpy().astype(np.float64),
            "w_eff_init": self.w_eff_init().detach().cpu().numpy().astype(np.float64),
            "w_eff_final": self.weight.detach().cpu().numpy().astype(np.float64),
            "dw_leak": self.leak.detach().cpu().numpy().astype(np.float64),
            "dw_bias": self.bias.detach().cpu().numpy().astype(np.float64),
        }
        return rec


def dw_stats(rec: dict) -> dict:
    """Compact summary of a dw_record (goes into the run JSON; the raw
    arrays go to results/dw/ as an npz)."""
    dw = rec["dw_eff"]
    w0 = rec["w_eff_init"]
    scale = float(np.mean(np.abs(w0))) if len(w0) else 1.0
    return {
        "n_edges": int(len(dw)),
        "mean_dw": round(float(dw.mean()), 8),
        "std_dw": round(float(dw.std()), 8),
        "mean_abs_dw": round(float(np.abs(dw).mean()), 8),
        "max_abs_dw": round(float(np.abs(dw).max()), 8),
        "frac_abs_gt_1e-3": round(float((np.abs(dw) > 1e-3).mean()), 6),
        "frac_abs_gt_1e-2": round(float((np.abs(dw) > 1e-2).mean()), 6),
        "abs_dw_over_abs_w0": (round(float(np.abs(dw).mean() / scale), 6) if scale else 0.0),
        "corr_abs_dw_base": round(float(np.corrcoef(np.abs(dw), np.abs(w0))[0, 1]), 6)
        if len(dw) > 1 else 0.0,
        "mean_abs_dw_leak": round(float(np.abs(rec["dw_leak"]).mean()), 8),
        "mean_abs_dw_bias": round(float(np.abs(rec["dw_bias"]).mean()), 8),
    }
