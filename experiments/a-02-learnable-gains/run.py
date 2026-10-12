#!/usr/bin/env python3
"""A-02 grid driver: the A-01 battery re-run with the FlyBridge
full-curriculum treatment — the circuit's 42,921 edge gains (plus
per-node leaks and biases) are TRAINABLE instead of frozen; topology
and base edge magnitudes stay frozen.

Phases:
  --benchmark   one 50-epoch fly/T1 run (sizing the grid to the wall budget;
                the pre-registered 4x-slower rule for the 5->3 seed shrink)
  --phase main  wirings x tasks x seeds (disconnected: T1 only), 100% data
  --phase deff  data-efficiency sub-grid: fly @10% + fly @50% + degree @50%,
                per the pre-registered grid (both tasks unless shrunk)
  --phase summary   per-cell mean/sd over seeds; embeds the comparable
                    A-01 frozen numbers (read from a-01's summary.json)
  --phase manifest  provenance: circuit sha256, control seeds + edge hashes,
                    treatment, seeds, versions, hardware role

Every run writes one JSON to results/. The held-out test set is touched
exactly once per model (final evaluation); selection uses a 10% internal
val split of the training fold. See README.md for the pre-registered
protocol and pass criteria.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

import baselines
import controls
import tasks
from circuit import Circuit, load_circuit
from baselines import GRU, MLP, param_budget

HERE = Path(__file__).parent
CIRCUIT_SHA256 = "ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227"
MASTER_SEED = tasks.MASTER_SEED
SEEDS = [100, 101, 102, 103, 104]
WIRINGS = ["fly", "degree", "sign", "weight", "population", "disconnected"]
TASKS = {"T1": 3, "T2": 6}
HARDWARE_ROLE = "4-core CPU host, 12 GB RAM"
EPOCH_CAP = 300
PATIENCE = 30
BATCH = 256
LR = 2.5e-3
FRACTIONS = (1.0, 0.5, 0.1)
DEFF_ARMS = [("fly", 0.1), ("fly", 0.5), ("degree", 0.5)]
TREATMENT = ("trainable edge gains + per-node leaks + biases (zero-init: "
             "gain 1.0, leak 0.5, bias 0), topology + base magnitudes frozen")
A01_SUMMARY = HERE.parent / "a-01-connectome-advantage" / "results" / "summary.json"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def weights_sha256(model: nn.Module) -> str:
    h = hashlib.sha256()
    for k in sorted(model.state_dict()):
        h.update(k.encode())
        h.update(model.state_dict()[k].numpy().tobytes())
    return h.hexdigest()


class A02Model(nn.Module):
    """The A-02 architecture: the A-01 model with the circuit un-frozen.

    16-d state -> encoder (256) -> sensory drive (256 drive-channel nodes)
    -> circuit (4 tanh steps, edge gains + leaks + biases TRAINABLE,
    zero-init) -> LN readout over the 384 output nodes -> linear head.
    Only the connectivity varies between circuit arms; the treatment
    (which parameters train) is identical for every arm.
    """

    def __init__(self, doc: dict, src, tgt, w, n_classes: int):
        super().__init__()
        self.circuit = Circuit(doc, src, tgt, w, enabled=len(src) > 0)
        n_sens = len(self.circuit.sensory)
        n_out = len(self.circuit.outputs)
        self.encoder = nn.Sequential(
            nn.Linear(16, 256), nn.ELU(),
            nn.Linear(256, 256), nn.ELU(),
            nn.LayerNorm(256),
        )
        self.drive = nn.Linear(256, n_sens)
        self.readout = nn.LayerNorm(n_out, eps=1e-6)
        self.head = baselines._head(n_out, n_classes)

    def features(self, x):
        e = self.encoder(x)
        d = self.circuit.initial(x.shape[0], x.device)
        d.index_copy_(1, self.circuit.sensory, self.drive(e))
        h = self.circuit.step(self.circuit.initial(x.shape[0], x.device), d)
        return self.readout(h[:, self.circuit.outputs])

    def forward(self, x):
        return self.head(self.features(x))

    def trainable(self):
        return ([p for m in (self.encoder, self.drive, self.readout, self.head)
                 for p in m.parameters()]
                + self.circuit.trainable())


def make_model(arm: str, doc: dict, wirings: dict, n_classes: int):
    if arm in ("mlp", "gru"):
        return MLP(n_classes) if arm == "mlp" else GRU(n_classes)
    src, tgt, w = wirings[arm]
    return A02Model(doc, src, tgt, w, n_classes)


def train_eval(arm: str, model, task_key: str, task: dict, frac: float, seed: int,
               epochs: int, bench: bool = False) -> dict:
    train_idx, test_idx = tasks.split(task, frac)
    g = torch.Generator().manual_seed(seed)
    order = torch.randperm(len(train_idx), generator=g).numpy()
    train_idx = train_idx[order]
    n_val = max(1, len(train_idx) // 10)
    val_idx, tr_idx = train_idx[:n_val], train_idx[n_val:]

    xtr = torch.tensor(task["x"][tr_idx], dtype=torch.float32)
    ytr = torch.tensor(task["y"][tr_idx], dtype=torch.long)
    xval = torch.tensor(task["x"][val_idx], dtype=torch.float32)
    yval = torch.tensor(task["y"][val_idx], dtype=torch.long)

    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.trainable(), lr=LR)
    lossf = nn.CrossEntropyLoss()
    batch = min(BATCH, len(xtr))
    per_epoch_g = torch.Generator().manual_seed(seed)
    best_val, bad, best_state, epochs_run = -1.0, 0, None, 0
    t0 = time.time()
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(len(xtr), generator=per_epoch_g)
        for i in range(0, len(xtr), batch):
            b = perm[i:i + batch]
            opt.zero_grad()
            lossf(model(xtr[b]), ytr[b]).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            val_acc = (model(xval).argmax(-1) == yval).float().mean().item()
        epochs_run = epoch + 1
        if val_acc > best_val + 1e-9:
            best_val, bad, best_state = val_acc, 0, copy.deepcopy(model.state_dict())
        else:
            bad += 1
            if not bench and bad >= PATIENCE:
                break
        if bench and (epoch + 1) % 10 == 0:
            print(f"  epoch {epoch + 1}: {time.time() - t0:.1f}s elapsed, val {val_acc:.3f}",
                  flush=True)
    model.load_state_dict(best_state)
    wall = time.time() - t0

    # the held-out test set: touched exactly once, at all three noise levels
    model.eval()
    held = {}
    with torch.no_grad():
        for lvl in task["noise_levels"]:
            xte = torch.tensor(tasks.eval_inputs(task, lvl), dtype=torch.float32)
            yte = torch.tensor(task["y"][test_idx], dtype=torch.long)
            held[f"sigma_{int(lvl * 100):03d}"] = (model(xte).argmax(-1) == yte).float().mean().item()
    with torch.no_grad():
        tr_acc = (model(xtr).argmax(-1) == ytr).float().mean().item()
    return {
        "arm": arm, "task": task_key, "seed": seed, "data_fraction": frac,
        "n_classes": task["n_classes"],
        "n_train": int(len(xtr)), "n_internal_val": int(n_val), "n_test": int(len(test_idx)),
        "params_trained": int(param_budget(model)),
        "per_epoch_s": round(wall / max(1, epochs_run), 3),
        "treatment": TREATMENT if arm not in ("mlp", "gru") else "no circuit (baseline)",
        "held_out": held,
        "train_acc": round(tr_acc, 4), "internal_val_best": round(best_val, 4),
        "epochs_run": int(epochs_run), "early_stopped": (epochs_run < epochs and not bench),
        "wall_s": round(wall, 1),
        "peak_rss_mb": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024),
        "weights_sha256": weights_sha256(model),
        "torch_version": torch.__version__, "hardware_role": HARDWARE_ROLE,
        "experiment": "a-02-learnable-gains",
    }


def write_result(res: dict, outdir: Path):
    p = outdir / f"{res['arm']}_{res['task']}_s{res['seed']}_f{int(res['data_fraction'] * 100)}.json"
    p.write_text(json.dumps(res, indent=2))
    print(f"  -> {p.name}: held-out " +
          " ".join(f"{k}={v:.3f}" for k, v in res["held_out"].items()) +
          f" (train {res['train_acc']:.3f}, {res['wall_s']}s)", flush=True)
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--phase", choices=["benchmark", "main", "deff", "summary", "manifest", "all"],
                    default="all")
    ap.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    ap.add_argument("--tasks", default="T1,T2")
    ap.add_argument("--arms", default=",".join(WIRINGS + ["mlp", "gru"]))
    ap.add_argument("--epochs", type=int, default=EPOCH_CAP)
    ap.add_argument("--benchmark-epochs", type=int, default=50)
    args = ap.parse_args()
    torch.set_num_threads(4)
    seeds = [int(s) for s in args.seeds.split(",")]
    task_keys = [t.strip() for t in args.tasks.split(",")]
    arms = [a.strip() for a in args.arms.split(",")]
    assert set(task_keys) <= set(TASKS), f"unknown tasks {task_keys}"
    assert set(arms) <= set(WIRINGS + ["mlp", "gru"]), f"unknown arms {arms}"
    outdir = HERE / "results"
    outdir.mkdir(exist_ok=True)

    staged = Path(args.circuit)
    got = sha256_file(staged)
    assert got == CIRCUIT_SHA256, f"staged circuit hash mismatch: {got}"
    doc = load_circuit(staged)
    n = len(doc["neurons"])
    groups = np.array([ne["group"] for ne in doc["neurons"]], dtype=np.int64)
    print(f"circuit sha256 verified: {got}", flush=True)
    wirings = {"fly": controls.from_doc(doc)}
    for name, (src, tgt, w, _rec) in controls.build_controls(doc, groups, n).items():
        wirings[name] = (src, tgt, w)

    task_gen = {k: tasks.generate_task(kc) for k, kc in TASKS.items()}
    tasks_all = {"T1": task_gen["T1"], "T2": task_gen["T2"]}

    if args.phase == "benchmark":
        print("benchmark: fly / T1 / seed 100 / 50 epochs (trainable circuit)", flush=True)
        t0 = time.time()
        res = train_eval("fly", make_model("fly", doc, wirings, 3), "T1",
                         tasks_all["T1"], 1.0, 100, args.benchmark_epochs, bench=True)
        print(json.dumps({k: res[k] for k in ("wall_s", "epochs_run", "per_epoch_s",
                                              "internal_val_best", "held_out")
                          if k in res}, indent=2))
        return

    runs_done = set(p.name for p in outdir.glob("*.json") if p.name not in
                    ("summary.json", "manifest.json"))

    if args.phase in ("main", "all"):
        for arm in arms:
            if arm in WIRINGS:
                for task_key in task_keys:
                    if arm == "disconnected" and task_key != "T1":
                        continue  # pre-registered: the null floor is T1-only
                    for seed in seeds:
                        name = f"{arm}_{task_key}_s{seed}_f100.json"
                        if name in runs_done:
                            continue
                        model = make_model(arm, doc, wirings, TASKS[task_key])
                        res = train_eval(arm, model, task_key, tasks_all[task_key],
                                         1.0, seed, args.epochs)
                        write_result(res, outdir)
            else:  # conventional baselines: no circuit, no wiring to treat
                for task_key in task_keys:
                    for seed in seeds:
                        name = f"{arm}_{task_key}_s{seed}_f100.json"
                        if name in runs_done:
                            continue
                        model = make_model(arm, doc, wirings, TASKS[task_key])
                        res = train_eval(arm, model, task_key, tasks_all[task_key],
                                         1.0, seed, args.epochs)
                        write_result(res, outdir)

    if args.phase in ("deff", "all"):
        for arm, frac in DEFF_ARMS:
            for task_key in task_keys:
                for seed in seeds:
                    name = f"{arm}_{task_key}_s{seed}_f{int(frac * 100)}.json"
                    if name in runs_done:
                        continue
                    model = make_model(arm, doc, wirings, TASKS[task_key])
                    res = train_eval(arm, model, task_key, tasks_all[task_key],
                                     frac, seed, args.epochs)
                    write_result(res, outdir)

    if args.phase in ("summary", "all"):
        runs = [json.loads(p.read_text()) for p in sorted(outdir.glob("*.json"))
                if p.name not in ("summary.json", "manifest.json")]
        cells = {}
        for r in runs:
            cells.setdefault((r["arm"], r["task"], r["data_fraction"]), []).append(r)

        def cell_stats(rs):
            def stat(vals):
                vals = list(vals)
                return {"mean": round(float(np.mean(vals)), 4),
                        "std": round(float(np.std(vals)), 4),
                        "per_seed": [round(v, 4) for v in vals]}
            return {
                "seeds": [r["seed"] for r in rs],
                "held_out": {k: stat([r["held_out"][k] for r in rs])
                             for k in ("sigma_000", "sigma_075", "sigma_150")},
                "train_acc": stat([r["train_acc"] for r in rs]),
                "epochs_run": [r["epochs_run"] for r in rs],
                "wall_s_mean": round(float(np.mean([r["wall_s"] for r in rs])), 1),
                "peak_rss_mb_max": max(r["peak_rss_mb"] for r in rs),
                "params_trained": rs[0]["params_trained"],
            }

        summary = {
            "a02_trainable": {f"{a}/{t}/f{int(f * 100)}": cell_stats(rs)
                              for (a, t, f), rs in sorted(cells.items())},
        }
        # the comparable A-01 frozen numbers, same cell keys, for side-by-side
        if A01_SUMMARY.exists():
            a01 = json.loads(A01_SUMMARY.read_text())
            summary["a01_frozen"] = {k: v for k, v in a01.items() if k in
                                     {f"{a}/{t}/f{int(f * 100)}" for (a, t, f) in cells}}
        (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
        print(f"summary.json: {len(cells)} a-02 cells "
              f"({len(summary.get('a01_frozen', {}))} a-01 reference cells)", flush=True)

    if args.phase in ("manifest", "all"):
        git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE,
                             capture_output=True, text=True).stdout.strip()
        manifest = {
            "experiment": "a-02-learnable-gains",
            "circuit": {
                "dataset": "FlyWire FAFB v783 (via FlyBridge public atlas, MIT)",
                "entry": "circuits/flywire-fafb-olfactory-1536.md",
                "sha256": CIRCUIT_SHA256, "verified": True,
            },
            "treatment": TREATMENT,
            "frozen_reference": {
                "experiment": "a-01-connectome-advantage",
                "summary": str(A01_SUMMARY.relative_to(HERE.parent.parent)),
            },
            "controls": {name: rec for name, (_, _, _, rec) in
                          controls.build_controls(doc, groups, n).items()},
            "master_seed": MASTER_SEED,
            "run_seeds": seeds,
            "tasks": {k: {"n_classes": v, "n_total": 2048, "n_test": 1024,
                          "declared": "generated (random prototypes + gaussian noise), "
                                      "identical to a-01"}
                      for k, v in TASKS.items()},
            "noise_levels": [0.0, 0.75, 1.5],
            "epoch_cap": EPOCH_CAP, "patience": PATIENCE, "batch": BATCH, "lr": LR,
            "data_fractions": list(FRACTIONS),
            "deff_arms": [[a, f] for a, f in DEFF_ARMS],
            "torch_version": torch.__version__, "numpy_version": np.__version__,
            "hardware_role": HARDWARE_ROLE,
            "git_head": git,
        }
        (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print("manifest.json written", flush=True)


if __name__ == "__main__":
    main()
