"""The frozen-wiring recurrent circuit — A-01 dynamics.

Reused verbatim in dynamics from ../scorer/scorer/circuit.py (tanh
hidden state, per-node leak, signed per-edge gain, 4 internal
propagation steps per input). One difference: the edge arrays are
injected, so the same class serves the fly wiring and every control
wiring (controls.py). The A-01 run freezes all circuit parameters at
zero-init (edge gain -> 1.0, leak -> 0.5, bias -> 0): the pure-wiring
passthrough, the strictest test of the wiring.

Topology + base edge magnitudes are the substrate; everything else is
an assumption declared in the experiment README.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
from torch import nn


def load_circuit(path: str | Path) -> dict:
    """Parse a circuit atlas: neurons (id/group/nt/p), signed edges."""
    doc = json.loads(Path(path).read_text())
    assert "neurons" in doc and "edges" in doc, "not a circuit atlas"
    return doc


class Circuit(nn.Module):
    STEPS = 4  # internal propagation steps per input (FlyBridge core)

    def __init__(self, doc: dict, src, tgt, w, enabled: bool = True):
        super().__init__()
        import numpy as np

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

    @property
    def weight(self) -> torch.Tensor:
        return self.initial_weight * self.edge_sign * (2.0 * torch.sigmoid(self.edge_gain))

    def initial(self, batch: int = 1, device=None) -> torch.Tensor:
        return torch.zeros(batch, self.n, device=device)

    def step(self, hidden: torch.Tensor, drive: torch.Tensor) -> torch.Tensor:
        """One decision: apply the drive, run the internal propagation."""
        leak = torch.sigmoid(self.leak) * 0.9 + 0.05
        for _ in range(self.STEPS):
            message = hidden.new_zeros(hidden.shape)
            if self.enabled:
                message = message.index_add_(1, self.target, hidden[:, self.source] * self.weight)
            hidden = leak * hidden + (1.0 - leak) * torch.tanh(message + drive + self.bias)
        return hidden

    def freeze(self):
        for p in self.parameters():
            p.requires_grad_(False)
