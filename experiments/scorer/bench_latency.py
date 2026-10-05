#!/usr/bin/env python3
"""Latency benchmark: one decision (encode -> drive -> 4-step recurrence ->
readout -> head) on a plain CPU.

Usage:
    python3 bench_latency.py --circuit circuit.json [--threads 1,2,4,8]
                             [--iters 200] [--label <role-string>]

Writes <label>.latency.json. Machine identity is never recorded; pass a
role label (e.g. "4-core-cpu-testbed") or leave the default.
"""
from __future__ import annotations

import argparse
import json
import time

import torch

from scorer.circuit import load_circuit
from scorer.model import Scorer


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--threads", default="1,2,4,8")
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--state-dim", type=int, default=16)
    ap.add_argument("--tasks", default="taskA:8")  # name:n_candidates[,name2:n2]
    ap.add_argument("--label", default="cpu-testbed")
    ap.add_argument("--encoder-hidden", type=int, default=256)
    ap.add_argument("--readout-hidden", type=int, default=128)
    args = ap.parse_args()

    torch.manual_seed(0)
    doc = load_circuit(args.circuit)
    tasks = dict(t.split(":") for t in args.tasks.split(","))
    tasks = {t: int(n) for t, n in tasks.items()}
    model = Scorer(doc, state_dim=args.state_dim, tasks=tasks,
                   encoder_hidden=args.encoder_hidden, readout_hidden=args.readout_hidden)
    n_params = sum(p.numel() for p in model.parameters())
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)

    x = torch.randn(1, args.state_dim)
    report = {
        "label": args.label,
        "circuit": str(args.circuit),
        "neurons": model.circuit.n,
        "edges": int(model.circuit.source.numel()),
        "sensory": int(model.circuit.sensory.numel()),
        "outputs": int(model.circuit.outputs.numel()),
        "params_total": n_params,
        "params_trainable": n_trainable,
        "threads": {},
    }
    for t in (int(v) for v in args.threads.split(",")):
        torch.set_num_threads(t)
        with torch.no_grad():
            for _ in range(50):
                model(x)  # warmup
            samples = []
            for _ in range(args.iters):
                t0 = time.perf_counter()
                model(x)
                samples.append((time.perf_counter() - t0) * 1000)
        samples.sort()
        report["threads"][t] = {
            "p50_ms": round(samples[len(samples) // 2], 3),
            "p95_ms": round(samples[int(len(samples) * 0.95)], 3),
            "mean_ms": round(sum(samples) / len(samples), 3),
        }
    print(json.dumps(report, indent=2))
    out = f"{args.label}.latency.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
