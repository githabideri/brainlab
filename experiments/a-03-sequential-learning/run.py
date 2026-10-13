"""A-03 grid driver: spiking + learning on non-saturating sequential tasks.

Phases:
  pilot     the design-lane small grid (1 seed; <=96 tanh/baseline
            trials, <=32 spike trials, <=4 epochs, seconds per run) —
            this is ALL that runs while the heavy lane is active
  main      the pre-registered campaign grid (5 seeds) — run by the
            coordinator after the heavy lane, via run-all.sh
  summary   per-cell mean/sd over seeds (primary metric per task)
  manifest  provenance: circuit sha256, lif.py sha256 (pinned), control
            seeds + edge-array hashes, ceilings, drive declaration,
            seeds, grid definition, versions, hardware role

Arm names: `tanh-<wiring>`, `spike-<wiring>` (wiring in fly/degree/
sign/weight/population/disconnected), `gru`, `mlp`.

Every run writes one JSON to results/. The held-out test fold (512
trials/task, master-seed) is touched exactly once per model. The A-02
checkpoint flaw is closed here: best internal-val LOSS, patience on
loss, full loss trajectories. Delta-w is recorded per tanh run
(= 0 by construction on the spike arm). See README.md for the
pre-registered protocol and pass criteria.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import controls
import learner
import model
import tasks

CIRCUIT_SHA256 = "ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227"
MASTER_SEED = tasks.MASTER_SEED
SEEDS = [100, 101, 102, 103, 104]
WIRINGS = ["fly", "degree", "sign", "weight", "population", "disconnected"]
TASK_KEYS = ["T-del", "T-ang", "T-xor"]
HARDWARE_ROLE = "4-core CPU host, 12 GB RAM"
BATCH = 64

# Pre-registered budgets (README "Grid" section).
MAIN = dict(tanh=dict(n_train=128, epochs=20, patience=5),  # 256 -> 128: declared ladder step (2) (Sizing outcome)
            spike=dict(n_train=128),
            baselines=dict(n_train=256, epochs=20, patience=5))
PILOT = dict(tanh=dict(n_train=96, epochs=4, patience=5),
             spike=dict(n_train=32),
             baselines=dict(n_train=96, epochs=4, patience=5))

PILOT_ARMS = ["tanh-fly", "tanh-degree", "spike-fly", "spike-degree",
              "gru", "mlp"]
MAIN_ARMS = ([f"tanh-{w}" for w in WIRINGS] + [f"spike-{w}" for w in WIRINGS]
             + ["gru", "mlp"])  # 32 arm columns x 3 tasks x 5 seeds = 210 runs

TREATMENTS = {
    "tanh": ("tanh-rate sequential (A-02 treatment): trainable edge "
             "gains (zero-init -> 1.0) + leaks (-> 0.5) + biases (-> 0) "
             "+ encoder/drive/readout/head; persistent hidden state, "
             "2 propagation steps per input step (A-03 sizing revision "
             "of A-02's 4); val-LOSS checkpoint"),
    "spike": ("Shiu-2024 LIF (b-01 lif.py, pinned by sha256), circuit "
              "FROZEN (B-01 treatment); fixed declared Poisson drive to "
              "the 256 sensory nodes; efficacy sign x min(log1p|w|, c) x "
              "k (p95 -> 4.7 mV, B-01's capped-max regime) — declared "
              "pilot revision of the inert per-target mapping; tonic "
              "10 mV on the 384 outputs (declared pilot revision of the "
              "sub-threshold 4 mV); ridge readout (alpha 1.0) = only "
              "learned object; dw = 0 by construction"),
    "gru": "conventional: 1 GRU layer (128 hidden), head at report steps",
    "mlp": "conventional: MLP on a window of the last W steps (4; 5 for "
           "T-xor) — declared no-long-memory comparator",
}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def weights_sha256(m: torch.nn.Module) -> str:
    h = hashlib.sha256()
    for k in sorted(m.state_dict()):
        h.update(k.encode())
        h.update(m.state_dict()[k].numpy().tobytes())
    return h.hexdigest()


def build_wirings(doc: dict) -> dict:
    groups = np.array([ne["group"] for ne in doc["neurons"]], dtype=np.int64)
    n = len(doc["neurons"])
    out = {"fly": controls.from_doc(doc)}
    for name, (src, tgt, w, _rec) in controls.build_controls(doc, groups, n).items():
        out[name] = (src, tgt, w)
    return out


def run_spike(doc, wiring, wirings, task, n_train, te_idx, seed) -> dict:
    arm = model.SpikeArm(doc, wirings[wiring], task, task["x"],
                         task["train_idx"])
    tr_idx, _ = tasks.split(task, n_train)
    t0 = time.time()
    arm.train_feats = arm.run_features(task["x"][tr_idx], tr_idx)
    arm.train_rows = tr_idx
    arm.test_feats = arm.run_features(task["x"][te_idx], te_idx)
    arm.test_rows = te_idx
    held = learner.spike_held_out_metrics(task, arm)
    e = len(wirings[wiring][0])
    dw = {"n_edges": int(e), "dw_zero_by_construction": True,
          "mean_abs_dw": 0.0, "frac_abs_gt_1e-3": 0.0,
          "frac_abs_gt_1e-2": 0.0, "abs_dw_over_abs_w0": 0.0}
    return {"held_out": held, "dw": dw,
            "wall_s": round(time.time() - t0, 1),
            "epochs_run": 0, "early_stopped": False,
            "val_loss_best": None, "train_loss_hist": [], "val_loss_hist": [],
            "weights_sha256": None}


def run_rate(arm: str, doc, wirings, task, n_train, te_idx, seed, cfg,
             version: str = "v1") -> dict:
    # Review round 4 (2026-10-13): seed BEFORE construction — the
    # recorded run seed must determine the initial parameters, not
    # only the training shuffles (which train_tanh seeds again).
    torch.manual_seed(seed)
    m = model.make_rate_model(arm, doc, wirings, task)
    m._arm_name = arm
    lossf = lambda logits, y: model.task_loss(task, logits, y)
    res = learner.train_tanh(m, task, n_train, seed, cfg["epochs"],
                             cfg["patience"], BATCH, lossf, version=version)
    Xte = torch.tensor(task["x"][te_idx], dtype=torch.float32)
    m.eval()
    with torch.no_grad():
        res["held_out"] = learner.held_out_metrics(task, m(Xte).numpy(),
                                                   te_idx)
    res["weights_sha256"] = weights_sha256(m)
    res["params_trained"] = int(sum(p.numel() for p in m.trainable()))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--phase", choices=["pilot", "main", "summary", "manifest"],
                    default="pilot")
    ap.add_argument("--tag", default="",
                    help="output tag: per-run JSONs are written as "
                         "<phase>-<tag>_*.json (e.g. --tag v2 re-runs a "
                         "phase into fresh files, original artifacts "
                         "untouched); recorded in the JSON as version")
    ap.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    ap.add_argument("--tasks", default=",".join(TASK_KEYS))
    ap.add_argument("--arms", default="")  # empty = phase default
    args = ap.parse_args()
    torch.set_num_threads(4)
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else SEEDS
    task_keys = [t.strip() for t in args.tasks.split(",")]
    assert set(task_keys) <= set(TASK_KEYS), f"unknown tasks {task_keys}"

    staged = Path(args.circuit)
    got = sha256_file(staged)
    assert got == CIRCUIT_SHA256, f"staged circuit hash mismatch: {got}"
    print(f"circuit sha256 verified: {got}", flush=True)
    doc = json.loads(staged.read_text())
    assert len(doc["neurons"]) <= 2048, "lane cap: <= 2048 nodes"
    print(f"circuit: {len(doc['neurons'])} nodes, {len(doc['edges'])} edges",
          flush=True)

    ceil = tasks.ceilings()
    for k in ceil:
        print(f"ceiling {k}: {ceil[k]}", flush=True)
    wirings = build_wirings(doc)
    all_tasks = {}
    for k in TASK_KEYS:
        t = tasks.generate_task(k)
        t["ceiling"] = ceil[k]
        all_tasks[k] = t

    outdir = HERE / "results"
    outdir.mkdir(exist_ok=True)

    if args.phase in ("pilot", "main"):
        cfg = PILOT if args.phase == "pilot" else MAIN
        if args.arms:
            arms = [a.strip() for a in args.arms.split(",")]
        else:
            arms = PILOT_ARMS if args.phase == "pilot" else MAIN_ARMS
        if args.phase == "pilot":
            seeds = [100]  # pre-registered: one seed for the lane
        known = set(PILOT_ARMS) | set(MAIN_ARMS)
        assert set(arms) <= known, f"unknown arms {arms}"
        # pilot: a 32-trial prefix of the held-out fold is evaluated
        # (labelled pilot in every JSON — sizing/smoke only, not the
        # arbiter); main: the full 512-trial fold, identical for all arms
        test_prefix = 32 if args.phase == "pilot" else None

        prefix = args.phase if not args.tag else f"{args.phase}-{args.tag}"
        done = set(p.name for p in outdir.glob(f"{prefix}_*.json"))
        for arm in arms:
            for task_key in task_keys:
                for seed in seeds:
                    name = f"{prefix}_{arm}_{task_key}_s{seed}.json"
                    if name in done:
                        continue
                    task = all_tasks[task_key]
                    te_idx = task["test_idx"]
                    if test_prefix is not None:
                        te_idx = te_idx[:test_prefix]
                    t0 = time.time()
                    dyn, wiring = (arm.split("-", 1) + [None])[:2] \
                        if arm.startswith(("tanh-", "spike-")) else (arm, None)
                    if dyn in ("tanh", "spike"):
                        if dyn == "spike":
                            r = run_spike(doc, wiring, wirings, task,
                                          cfg["spike"]["n_train"], te_idx,
                                          seed)
                        else:
                            r = run_rate(arm, doc, wirings, task,
                                         cfg["tanh"]["n_train"], te_idx, seed,
                                         cfg["tanh"], version=args.tag or "v1")
                        n_train = cfg[dyn]["n_train"]
                    else:
                        r = run_rate(arm, doc, wirings, task,
                                     cfg["baselines"]["n_train"], te_idx,
                                     seed, cfg["baselines"],
                                     version=args.tag or "v1")
                        n_train = cfg["baselines"]["n_train"]
                    res = {
                        "experiment": "a-03-sequential-learning",
                        "phase": args.phase,
                        "version": args.tag or "v1",
                        "dynamics": dyn,
                        "wiring": wiring,
                        "baseline": arm if dyn not in ("tanh", "spike") else None,
                        "task": task_key,
                        "seed": seed,
                        "n_train": n_train,
                        "n_test": int(len(te_idx)),
                        "treatment": TREATMENTS[dyn],
                        "torch_version": torch.__version__,
                        "numpy_version": np.__version__,
                        "hardware_role": HARDWARE_ROLE,
                    }
                    res.update(r)
                    res["peak_rss_mb"] = int(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)
                    p = outdir / name
                    p.write_text(json.dumps(res, indent=2))
                    print(f"  -> {name}: {res['held_out']} "
                          f"(wall {res['wall_s']}s, {time.time() - t0:.0f}s total)",
                          flush=True)

    if args.phase == "summary":
        runs = [json.loads(p.read_text())
                for p in sorted(outdir.glob("*_*.json"))
                if p.name not in ("summary.json", "manifest.json")]
        cells = {}
        for r in runs:
            # version-aware: v1 and v2 runs must never be pooled
            key = (r["phase"], r.get("version", "v1"),
                   r["dynamics"], r["wiring"] or r["baseline"], r["task"])
            cells.setdefault(key, []).append(r)
        summary = {}
        for (phase, version, dyn, w, task_key), rs in sorted(cells.items()):
            def stat(key):
                vals = [r["held_out"].get(key) for r in rs
                        if r["held_out"].get(key) is not None]
                if not vals:
                    return None
                return {"mean": round(float(np.mean(vals)), 4),
                        "std": round(float(np.std(vals)), 4),
                        "per_seed": [round(v, 4) for v in vals]}
            prim_key = "rmce_deg" if task_key == "T-ang" else "accuracy"
            cell = {
                "seeds": [r["seed"] for r in rs],
                "primary": stat(prim_key),
                "primary_lower_is_better": task_key == "T-ang",
                "held_out": {k: stat(k) for k in
                             sorted({k for r in rs for k in r["held_out"]})},
                "wall_s_mean": round(float(np.mean([r["wall_s"] for r in rs])), 1),
            }
            if rs[0].get("dw"):
                def stat2(key):
                    vals = [r["dw"].get(key) for r in rs
                            if r["dw"].get(key) is not None]
                    if not vals:
                        return None
                    return {"mean": round(float(np.mean(vals)), 8),
                            "std": round(float(np.std(vals)), 8)}
                cell["dw"] = {k: stat2(k) for k in
                              ("mean_abs_dw", "frac_abs_gt_1e-3",
                               "frac_abs_gt_1e-2", "abs_dw_over_abs_w0")}
            summary[f"{phase}/{version}/{dyn}/{w}/{task_key}"] = cell
        (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
        print(f"summary.json: {len(summary)} cells", flush=True)

    if args.phase == "manifest":
        git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE,
                             capture_output=True, text=True).stdout.strip()
        groups = np.array([ne["group"] for ne in doc["neurons"]], dtype=np.int64)
        n = len(doc["neurons"])
        ctl = {name: rec for name, (_, _, _, rec) in
               controls.build_controls(doc, groups, n).items()}
        manifest = {
            "experiment": "a-03-sequential-learning",
            "circuit": {
                "dataset": "FlyWire FAFB v783 (via FlyBridge public atlas, MIT)",
                "entry": "circuits/flywire-fafb-olfactory-1536.md",
                "sha256": CIRCUIT_SHA256, "verified": True,
            },
            "lif": {"file": "experiments/a-03-sequential-learning/lif.py",
                    "source": "verbatim copy of "
                              "experiments/b-01-internal-compass/lif.py "
                              "(Shiu et al. 2024 model)",
                    "sha256": sha256_file(HERE / "lif.py"),
                    "dependency_note": "B-02 Stage 1 differentially tests "
                                       "lif.py; if it changes, spike results "
                                       "must be re-verified before publication"},
            "controls": ctl,
            "tasks": {k: {"T": all_tasks[k]["T"], "d": all_tasks[k]["d"],
                          "kind": all_tasks[k]["kind"],
                          "report_steps": list(all_tasks[k]["report_steps"]),
                          "n_train_total": int(len(all_tasks[k]["train_idx"])),
                          "n_test": int(len(all_tasks[k]["test_idx"])),
                          "ceiling": all_tasks[k]["ceiling"],
                          "declared": "generated (tasks.py); identical "
                                      "stimulus stream across all arms"}
                      for k in TASK_KEYS},
            "spike_drive": {"r0_hz": model.R0, "rmax_hz": model.RMAX,
                            "tonic_outputs_mv": model.TONIC_OUT,
                            "w_scale_mv": model.EFFECT_P95_MV,
                            "step_ms": model.STEP_MS,
                            "window_ms": model.WINDOW_MS,
                            "w_x": f"fixed master-seed projection d->256 "
                                   f"(seed {MASTER_SEED} + 5000 + task index)"},
            "tanh_treatment": TREATMENTS["tanh"],
            "checkpoint_rule": "best internal-val LOSS (never accuracy); "
                               "patience on val-loss; full loss "
                               "trajectories in each run JSON",
            "grid": {
                "main": MAIN,
                "pilot": PILOT,
                "main_arms": MAIN_ARMS,
                "main_runs": "32 arm columns x 3 tasks x 5 seeds = 210",
                "shrink_ladder": ["drop sign+weight (both dynamics)",
                                  "tanh 256->128 / spike 128->64 trials",
                                  "5->3 seeds (criterion a: >=3 of 3)",
                                  "drop T-xor"],
            },
            "master_seed": MASTER_SEED,
            "ceiling_seed": tasks.CEILING_SEED,
            "run_seeds": SEEDS,
            "batch": BATCH, "lr": 2.5e-3,
            "torch_version": torch.__version__,
            "numpy_version": np.__version__,
            "hardware_role": HARDWARE_ROLE,
            "git_head": git,
        }
        (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print("manifest.json written", flush=True)


if __name__ == "__main__":
    main()
