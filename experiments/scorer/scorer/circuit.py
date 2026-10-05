"""The frozen-wiring recurrent circuit.

Topology + base edge magnitudes come from the circuit atlas (frozen).
Learnable: per-edge gain (zero-init -> 1.0), per-node leak (zero-init ->
0.5), per-node bias (zero-init -> 0). Hidden state is tanh-bounded; one
`step` applies the input drive and runs the fixed number of internal
propagation steps. This mirrors the dynamics of the FlyBridge "small
brain" (topology-constrained, signed recurrence; their engine is an
image-driven variant of the same core).
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
from torch import nn

DT_FILE = "circuit.json"


def load_circuit(path: str | Path):
    """Parse a circuit atlas: neurons (id/group/nt/pos), signed edges."""
    doc = json.loads(Path(path).read_text())
    assert "neurons" in doc and "edges" in doc, "not a circuit atlas"
    return doc


class Circuit(nn.Module):
    STEPS = 4  # internal propagation steps per input (FlyBridge core)

    def __init__(self, doc: dict, variant: str = "fly", generator_seed: int = 8001):
        super().__init__()
        if variant not in ("fly", "shuffled", "disconnected"):
            raise ValueError(f"unknown variant {variant}")
        self.variant = variant
        self.n = len(doc["neurons"])
        edges = torch.tensor(doc["edges"], dtype=torch.float32)
        source, target = edges[:, 0].long(), edges[:, 1].long()
        if variant == "shuffled":
            target = target[torch.randperm(len(target), generator=torch.Generator().manual_seed(generator_seed))]
        # magnitude: log1p(|w|), normalized per target incoming sum (clamped >= 1)
        magnitude = edges[:, 2].abs().log1p()
        incoming = torch.zeros(self.n).index_add_(0, target, magnitude).clamp_min(1)
        self.register_buffer("source", source)
        self.register_buffer("target", target)
        self.register_buffer("edge_sign", edges[:, 2].sign())
        self.register_buffer("initial_weight", magnitude / incoming[target])
        self.edge_gain = nn.Parameter(torch.zeros(len(source)))  # -> gain 1.0
        self.leak = nn.Parameter(torch.zeros(self.n))            # -> leak 0.5
        self.bias = nn.Parameter(torch.zeros(self.n))
        # group masks (atlas group ids: 6 = food olfactory receptor neurons;
        # 19/23 = mushroom-body output + lateral horn appositions)
        sensory = [i for i, n in enumerate(doc["neurons"]) if n["group"] == 6]
        outputs = [i for i, n in enumerate(doc["neurons"]) if n["group"] in (19, 23)]
        self.register_buffer("sensory", torch.tensor(sensory))
        self.register_buffer("outputs", torch.tensor(outputs))

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
            if self.variant != "disconnected":
                message = message.index_add_(1, self.target, hidden[:, self.source] * self.weight)
            hidden = leak * hidden + (1.0 - leak) * torch.tanh(message + drive + self.bias)
        return hidden
