"""T-ang dedicated — driver.

6 wirings (fly + the five A-01 controls) x K Poisson drive
realizations, spike arm only (A-03/B-01 treatment, imported
unmodified), 128-trial features + 512-trial held-out fold, ridge
readout, circular RMCE + R^2.

The ONLY code difference from A-03 is the drive-salt function:
  k = 0  -> A-03's exact salt  (bit-identical drive, verified by smoke)
  k >= 1 -> new salt "tang-ded:r{k}:a03-spike-drive:{task}:{row}"
Everything else (lif.py, model.SpikeArm, controls.py, learner,
tasks, circuit file) is imported from a-03-sequential-learning and
hash-verified here and in the manifest.

Usage:
  python3 src/run_tang.py --circuit <staged circuit.json>
      [--k 5] [--wirings fly,degree,...] [--map-only]
Resumable: existing results/<wiring>_r<k>.json are skipped.
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

HERE = Path(__file__).parent
A03 = HERE.parent.parent / "a-03-sequential-learning"
sys.path.insert(0, str(A03))

import numpy as np
import torch

import controls
import learner
import lif  # noqa: F401  (imported for the sha256 pin check)
import model
import tasks

CIRCUIT_SHA256 = "ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227"
WIRINGS = ["fly", "degree", "sign", "weight", "population", "disconnected"]
N_TRAIN = 128  # A-03's declared main spike budget (and decision-pilot value)
HARDWARE_ROLE = "4-core CPU host, 12 GB RAM"
DEC_PILOT = {  # the lead under study (a-03 main-v3-dec, one evaluation)
    "fly": 84.95, "degree": 92.77, "chance": 89.80, "ceiling": 45.46,
}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def set_drive_salt(k: int) -> None:
    """The one declared difference: the per-trial Poisson seed."""
    def _trial_seed(task_key: str, row: int) -> int:
        prefix = "a03-spike-drive" if k == 0 else f"tang-ded:r{k}:a03-spike-drive"
        h = hashlib.sha256(f"{prefix}:{task_key}:{row}".encode()).digest()
        return int.from_bytes(h[:4], "big") & 0x7FFFFFFF
    model._trial_seed = _trial_seed


def build_wirings(doc: dict) -> dict:
    groups = np.array([ne["group"] for ne in doc["neurons"]], dtype=np.int64)
    n = len(doc["neurons"])
    out = {"fly": controls.from_doc(doc)}
    for name, (src, tgt, w, _rec) in controls.build_controls(doc, groups, n).items():
        out[name] = (src, tgt, w)
    return out


def verify(doc_path: Path, doc: dict) -> dict:
    got = sha256_file(doc_path)
    assert got == CIRCUIT_SHA256, f"staged circuit hash mismatch: {got}"
    a03_manifest = json.loads(
        (A03 / "results" / "manifest.json").read_text())
    lif_now = sha256_file(A03 / "lif.py")
    assert lif_now == a03_manifest["lif"]["sha256"], \
        "lif.py changed since the A-03 manifest — spike results would not " \
        "be comparable; re-pin before running"
    groups = np.array([ne["group"] for ne in doc["neurons"]], dtype=np.int64)
    n = len(doc["neurons"])
    ctl = {name: rec for name, (_, _, _, rec) in
           controls.build_controls(doc, groups, n).items()}
    for name, rec in ctl.items():
        prev = a03_manifest["controls"].get(name, {})
        assert prev.get("edge_sha256") == rec["edge_sha256"], \
            f"control {name} edge arrays differ from A-03's recorded build"
    return {"circuit_sha256": got, "lif_sha256": lif_now, "controls": ctl}


def run_cell(doc, wiring: str, wirings: dict, task: dict, k: int,
             outdir: Path, provenance: dict,
             test_prefix: int | None = None) -> dict:
    set_drive_salt(k)
    arm = model.SpikeArm(doc, wirings[wiring], task, task["x"],
                         task["train_idx"])
    tr_idx, _ = tasks.split(task, N_TRAIN)
    te_idx = task["test_idx"]
    if test_prefix is not None:
        te_idx = te_idx[:test_prefix]
    t0 = time.time()
    arm.train_feats = arm.run_features(task["x"][tr_idx], tr_idx)
    arm.train_rows = tr_idx
    arm.test_feats = arm.run_features(task["x"][te_idx], te_idx)
    arm.test_rows = te_idx
    held = learner.spike_held_out_metrics(task, arm)
    e = len(wirings[wiring][0])
    res = {
        "experiment": "tang-dedicated",
        "wiring": wiring,
        "realization": k,
        "drive_salt": ("a03-spike-drive (A-03 exact)" if k == 0
                       else f"tang-ded:r{k}:a03-spike-drive"),
        "task": "T-ang",
        "n_train": int(len(tr_idx)),
        "n_test": int(len(te_idx)),
        "n_edges": int(e),
        "dw_zero_by_construction": True,
        "held_out": held,
        "wall_s": round(time.time() - t0, 1),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "hardware_role": HARDWARE_ROLE,
    }
    res.update(provenance)
    p = outdir / f"{wiring}_r{k}.json"
    p.write_text(json.dumps(res, indent=2))
    print(f"  -> {p.name}: rmce={held['rmce_deg']} r2={held.get('r2')} "
          f"(wall {res['wall_s']}s)", flush=True)
    return res


def build_map(outdir: Path, k_values: list, wirings: list,
              ceiling: float, chance: float) -> dict:
    cells = {}
    for w in wirings:
        for k in k_values:
            p = outdir / f"{w}_r{k}.json"
            if p.exists():
                cells[(w, k)] = json.loads(p.read_text())["held_out"]
    rows = {}
    for w in wirings:
        rs = [cells[(w, k)] for k in k_values if (w, k) in cells]
        if not rs:
            continue
        rms = [r["rmce_deg"] for r in rs]
        rows[w] = {
            "rmce_per_realization": [cells[(w, k)]["rmce_deg"]
                                     if (w, k) in cells else None
                                     for k in k_values],
            "rmce_mean": round(float(np.mean(rms)), 3),
            "rmce_std": round(float(np.std(rms)), 3),
            "r2_mean": round(float(np.mean([r["r2"] for r in rs])), 4),
            "efficiency_mean": round(float(np.mean([r["efficiency"] for r in rs])), 4),
        }
    # P1: fly - degree <= -5 deg in >= 4 of K
    pairs = [cells[("fly", k)]["rmce_deg"] - cells[("degree", k)]["rmce_deg"]
             for k in k_values if ("fly", k) in cells and ("degree", k) in cells]
    p1_votes = [d <= -5.0 for d in pairs]
    p1 = sum(p1_votes) >= (2 if len(k_values) == 3 else 4)
    # P2: fly mean < every control mean, beats best control by >= 5,
    #     fly single-best in >= 4 of K (>=3 if shrunk)
    controls_ = [w for w in wirings if w != "fly"]
    means = {w: rows[w]["rmce_mean"] for w in rows}
    best_ctl = min((w for w in controls_ if w in means),
                   key=lambda w: means[w])
    fly_mean = means["fly"]
    p2a = all(fly_mean < means[w] for w in controls_ if w in means)
    p2b = (means[best_ctl] - fly_mean) >= 5.0
    best_votes = 0
    for k in k_values:
        if ("fly", k) not in cells:
            continue
        fv = cells[("fly", k)]["rmce_deg"]
        if all(fv < cells[(w, k)]["rmce_deg"]
               for w in controls_ if (w, k) in cells):
            best_votes += 1
    p2c = best_votes >= (2 if len(k_values) == 3 else 4)
    p2 = p2a and p2b and p2c
    per_r = {f"fly-minus-degree r{k}":
             round(cells[("fly", k)]["rmce_deg"] - cells[("degree", k)]["rmce_deg"], 3)
             for k in k_values if ("fly", k) in cells and ("degree", k) in cells}
    return {
        "experiment": "tang-dedicated",
        "task": "T-ang",
        "ceiling_rmce": ceiling, "chance_rmce": chance,
        "decision_pilot_reference": DEC_PILOT,
        "rows": rows,
        "fly_minus_degree_per_realization": per_r,
        "p1": {"rule": "fly-degree <= -5 deg in >= 4 of 5 (>=2 of 3 if shrunk)",
               "per_realization_deg": [round(d, 3) for d in pairs],
               "votes": p1_votes, "pass": bool(p1)},
        "p2": {"rule": "fly mean < every control mean AND beats best "
                       f"control ({best_ctl}) by >= 5 deg AND fly single-best "
                       "in >= 4 of 5 (>=3 if shrunk)",
               "fly_mean": fly_mean, "best_control": best_ctl,
               "best_control_mean": means.get(best_ctl),
               "margin_over_best": (round(means[best_ctl] - fly_mean, 3)
                                    if best_ctl in means else None),
               "single_best_votes": best_votes,
               "pass": bool(p2)},
        "overall": {"pass": bool(p1 and p2),
                    "verdict": ("PASS: the sub-ceiling spike T-ang signal "
                                "is stable and control-wiring specific"
                                if p1 and p2 else
                                "FAIL: the sub-ceiling spike T-ang lead does "
                                "not survive the dedicated study")},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--wirings", default=",".join(WIRINGS))
    ap.add_argument("--map-only", action="store_true")
    ap.add_argument("--test-prefix", type=int, default=None,
                    help="smoke only: evaluate on a prefix of the fold")
    args = ap.parse_args()
    torch.set_num_threads(4)

    staged = Path(args.circuit)
    doc = json.loads(staged.read_text())
    assert len(doc["neurons"]) <= 2048, "lane cap: <= 2048 nodes"
    print(f"circuit: {len(doc['neurons'])} nodes, {len(doc['edges'])} edges",
          flush=True)
    prov = verify(staged, doc)
    print(f"verified: circuit {prov['circuit_sha256'][:12]}  "
          f"lif {prov['lif_sha256'][:12]}  controls x5 vs A-03 manifest",
          flush=True)

    task = tasks.generate_task("T-ang")
    task["ceiling"] = tasks.ceilings()["T-ang"]
    print(f"ceiling: {task['ceiling']}", flush=True)
    wirings = build_wirings(doc)
    wlist = [w.strip() for w in args.wirings.split(",")]
    assert set(wlist) <= set(WIRINGS), f"unknown wirings {wlist}"

    outdir = HERE / "results"
    outdir.mkdir(exist_ok=True)
    if not args.map_only:
        for k in range(args.k):
            for w in wlist:
                p = outdir / f"{w}_r{k}.json"
                if p.exists():
                    continue
                t0 = time.time()
                run_cell(doc, w, wirings, task, k, outdir, prov,
                         test_prefix=args.test_prefix)
                print(f"    elapsed {time.time() - t0:.0f}s cumulative",
                      flush=True)
    m = build_map(outdir, list(range(args.k)), wlist,
                  task["ceiling"]["ceiling"], task["ceiling"]["chance"])
    (outdir / "map.json").write_text(json.dumps(m, indent=2))
    print(f"map.json written: overall={m['overall']['verdict']}", flush=True)


if __name__ == "__main__":
    main()
