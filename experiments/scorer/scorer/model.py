"""The scorer: learned state -> sensory drive -> frozen circuit -> readout -> heads.

Candidate-only contract: each head scores a FIXED candidate list for a
task; the decision is argmax, and a small top-1/top-2 margin triggers
abstention (escalation) instead of a choice. The model never generates
actions.
"""
from __future__ import annotations

import torch
from torch import nn

from .circuit import Circuit

HIDDEN = 128


def _head(n_in: int, n_out: int) -> nn.Linear:
    h = nn.Linear(n_in, n_out)
    nn.init.orthogonal_(h.weight, 0.01)
    nn.init.zeros_(h.bias)
    return h


class Scorer(nn.Module):
    def __init__(self, circuit_doc: dict, state_dim: int, tasks: dict,
                 variant: str = "fly"):
        """tasks: {task_name: n_candidates}"""
        super().__init__()
        self.circuit = Circuit(circuit_doc, variant=variant)
        n_sensory = len(self.circuit.sensory)
        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, 256), nn.ELU(),
            nn.Linear(256, 256), nn.ELU(),
            nn.LayerNorm(256),
        )
        self.sensory_drive = nn.Linear(256, n_sensory)
        self.readout = nn.Sequential(
            nn.LayerNorm(len(self.circuit.outputs), eps=1e-6),
            nn.Linear(len(self.circuit.outputs), HIDDEN), nn.Tanh(),
        )
        self.heads = nn.ModuleDict({t: _head(HIDDEN, k) for t, k in tasks.items()})

    def features(self, state: torch.Tensor):
        """state (B, state_dim) -> (features (B, HIDDEN), hidden (B, n))"""
        enc = self.state_encoder(state)
        drive_values = self.sensory_drive(enc)
        drive = self.circuit.initial(state.shape[0], state.device)
        drive.index_copy_(1, self.circuit.sensory, drive_values)
        hidden = self.circuit.step(self.circuit.initial(state.shape[0], state.device), drive)
        return self.readout(hidden[:, self.circuit.outputs]), hidden

    def forward(self, state: torch.Tensor):
        """Full pass: state -> (features, hidden)."""
        return self.features(state)

    def score(self, state: torch.Tensor, task: str, abstain_margin: float = 0.25):
        """(scores (B,K), chosen (B,), margin (B,), abstained (B,))"""
        features, _ = self.features(state)
        scores = self.heads[task](features)
        top2 = torch.topk(scores, 2, dim=-1).values
        margin = (top2[:, 0] - top2[:, 1]).clamp_min(0.0)
        chosen = scores.argmax(-1)
        abstained = margin < abstain_margin
        return scores, chosen, margin, abstained

    def trainable(self):
        return list(self.state_encoder.parameters()) + list(self.sensory_drive.parameters()) \
            + list(self.readout.parameters()) + [p for h in self.heads.values() for p in h.parameters()]

    def freeze_circuit(self):
        for p in self.circuit.parameters():
            p.requires_grad_(False)
