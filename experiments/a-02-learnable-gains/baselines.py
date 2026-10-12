"""Conventional baseline architectures for A-02.

Copied verbatim (code unchanged) from
../a-01-connectome-advantage/baselines.py. Same input/output interface
as the circuit arms: 16-d input -> K-way head. No circuit, no fixed
wiring — the "does the wiring beat plain MLP/GRU muscle of comparable
size?" comparison. As in A-01 the MLP/GRU arms have no circuit
counterpart to train; they are re-run here (same seeds) so the
trainable-fly vs baseline comparison stands on identical data, noise
realizations and training protocol in both experiments.
"""
from __future__ import annotations

import torch
from torch import nn


def _head(n_in: int, n_out: int) -> nn.Linear:
    h = nn.Linear(n_in, n_out)
    nn.init.orthogonal_(h.weight, 0.01)
    nn.init.zeros_(h.bias)
    return h


class MLP(nn.Module):
    """16 -> 512 ReLU -> 512 ReLU -> K."""

    def __init__(self, n_classes: int, state_dim: int = 16, hidden: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
        )
        self.head = _head(hidden, n_classes)

    def forward(self, x):
        return self.head(self.net(x))

    def trainable(self):
        return list(self.parameters())


class GRU(nn.Module):
    """One GRU(16 -> 256) time step -> 256-d state -> K."""

    def __init__(self, n_classes: int, state_dim: int = 16, hidden: int = 256):
        super().__init__()
        self.rnn = nn.GRU(state_dim, hidden, batch_first=True)
        self.head = _head(hidden, n_classes)

    def forward(self, x):
        h, _ = self.rnn(x.unsqueeze(1))
        return self.head(h[:, -1])

    def trainable(self):
        return list(self.parameters())


def param_budget(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
