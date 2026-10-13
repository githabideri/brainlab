"""A-03 paired-sensory-RNG evidence (2026-10-13 fix, review P0).

The spike arm's external Poisson drive must be a pure function of
(task id, trial master-order index) — never of the wiring — so that
all wiring arms see identical sensory spike trains for a given trial
and the fly-vs-shuffle contrast is a clean comparison. This script
replays ONE trial's external drive events (neuron id, time in ms) for
the biological wiring (fly) and one shuffled wiring arm (degree —
independent permutations of source and target, seed 20261013), asserts
the two event lists are identical, and commits the dump as evidence.

Usage:
  python paired_rng_evidence.py --circuit <staged atlas>
                                [--task T-del] [--trial <master row>]
                                [--out <json path>]

No default paths in the repo (public boundary): the staged circuit is
passed as an argument; the dump is written to <out> (default:
data/a03-paired-spike-rng.json in the repo root).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import controls
import model
import tasks
import run as runner


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--task", default="T-del",
                    choices=[s["key"] for s in tasks.TASKS])
    ap.add_argument("--trial", type=int, default=None,
                    help="master-order trial row (default: first held-out "
                         "test trial of the task)")
    ap.add_argument("--out", default=str(HERE.parent.parent / "data" /
                                         "a03-paired-spike-rng.json"))
    args = ap.parse_args()
    torch.set_num_threads(1)  # the LIF/Poisson loop is declared single-threaded

    staged = Path(args.circuit)
    assert runner.sha256_file(staged) == runner.CIRCUIT_SHA256, \
        "staged circuit hash mismatch"
    doc = json.loads(staged.read_text())

    task = tasks.generate_task(args.task)
    row = args.trial if args.trial is not None else int(task["test_idx"][0])

    groups = np.array([n["group"] for n in doc["neurons"]])
    n = len(doc["neurons"])
    wirings = {
        "fly": controls.from_doc(doc)[:3],
        "degree": controls.make_degree(doc, n)[:3],
    }
    dump = {
        "what": "A-03 paired sensory-RNG evidence: external Poisson "
                "drive events (neuron id, time ms) for ONE trial, "
                "replayed for two wiring arms with the per-trial seed "
                "protocol. Identical event lists = the sensory train is "
                "a pure function of (task id, trial index), independent "
                "of the wiring.",
        "fix_date": "2026-10-13",
        "task": args.task,
        "task_kind": task["kind"],
        "trial_master_row": row,
        "trial_is_held_out": bool(row in set(map(int, task["test_idx"]))),
        "seed_recipe": "torch.manual_seed = sha256("
                       "'a03-spike-drive:{task}:{row}')[:4] & 0x7FFFFFFF, "
                       "set once before the trial's step loop",
        "circuit_sha256": runner.CIRCUIT_SHA256,
        "n_neurons": n,
        "sensory_population": {
            "group": 6,
            "n": int((groups == 6).sum()),
            "indices": [int(i) for i in np.where(groups == 6)[0]],
            "is_identity_0_to_255": bool(
                np.array_equal(np.where(groups == 6)[0],
                               np.arange((groups == 6).sum()))),
        },
        "arms": {},
    }
    events = {}
    for arm in ("fly", "degree"):
        src, tgt, w = wirings[arm]
        a = model.SpikeArm(doc, (src, tgt, w), task, task["x"],
                           task["train_idx"])
        t0 = time.time()
        ev = a.drive_events(task["x"][row], row)
        events[arm] = ev
        dump["arms"][arm] = {
            "n_external_events": len(ev),
            "unique_sensory_neurons_driven": int(
                len({e[0] for e in ev})),
            "replay_wall_s": round(time.time() - t0, 2),
            "events": ev,
        }
    same = events["fly"] == events["degree"]
    dump["arms_equal"] = bool(same)
    dump["fly_sha256"] = hashlib.sha256(
        json.dumps(events["fly"]).encode()).hexdigest()
    dump["degree_sha256"] = hashlib.sha256(
        json.dumps(events["degree"]).encode()).hexdigest()
    assert same, "paired RNG VIOLATION: sensory drives differ between " \
                 "wiring arms for the same (task, trial)"
    assert len(events["fly"]) > 0, "no external events — drive is dead"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dump, indent=2))
    print(f"OK: {len(events['fly'])} external events identical across "
          f"fly vs degree for {args.task} trial row {row}")
    print(f"    dump: {out}")
    print(f"    sha256(fly events)    {dump['fly_sha256']}")
    print(f"    sha256(degree events) {dump['degree_sha256']}")


if __name__ == "__main__":
    main()
