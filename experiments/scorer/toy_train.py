#!/usr/bin/env python3
"""Toy training smoke: can a head learn a 3-class task through the frozen
circuit wiring?

State = 16-d vector (one-hot class in the first 3 dims + noise). The
state encoder + sensory drive + readout + head train; the circuit wiring
is frozen at zero-init (gain 1.0, leak 0.5, bias 0). Pass: train accuracy
>= 0.95 and validation accuracy >= 0.90 within the epoch budget — i.e.
the fixed wiring does not bury the class signal under the readout.
"""
from __future__ import annotations

import argparse
import json
import time

import torch
from torch import nn

from scorer.circuit import load_circuit
from scorer.model import Scorer


def make_states(dim: int, n: int, seed: int):
    g = torch.Generator().manual_seed(seed)
    y = torch.randint(0, 3, (n,), generator=g)
    x = torch.randn(n, dim, generator=g)
    x[:, :3] = 0.0
    one = torch.zeros(n, 3)
    one[torch.arange(n), y] = 1.0
    x[:, :3] = one
    return x, y


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--state-dim", type=int, default=16)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    doc = load_circuit(args.circuit)
    model = Scorer(doc, state_dim=args.state_dim, tasks={"toy3": 3})
    model.freeze_circuit()
    opt = torch.optim.Adam(model.trainable(), lr=2.5e-3)
    lossf = nn.CrossEntropyLoss()

    xtr, ytr = make_states(args.state_dim, 4096, args.seed + 1)
    xval, yval = make_states(args.state_dim, 2048, args.seed + 2)

    history = []
    t0 = time.time()
    for epoch in range(args.epochs):
        model.train()
        for i in range(0, len(xtr), args.batch):
            b = slice(i, i + args.batch)
            scores, _, _, _ = model.score(xtr[b], "toy3")
            opt.zero_grad()
            lossf(scores, ytr[b]).backward()
            opt.step()
        if (epoch + 1) % 25 == 0 or epoch == args.epochs - 1:
            model.eval()
            with torch.no_grad():
                _, c, _, _ = model.score(xtr, "toy3")
                _, cv, _, _ = model.score(xval, "toy3")
            tr = (c == ytr).float().mean().item()
            va = (cv == yval).float().mean().item()
            history.append({"epoch": epoch + 1, "train": round(tr, 4), "val": round(va, 4)})
            print(history[-1], flush=True)
            if va >= 0.90 and tr >= 0.95:
                break
    wall = time.time() - t0
    result = {"history": history, "wall_s": round(wall, 1),
              "pass": history and history[-1]["train"] >= 0.95 and history[-1]["val"] >= 0.90}
    print(json.dumps(result, indent=2))
    with open(f"toy{args.seed}.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
