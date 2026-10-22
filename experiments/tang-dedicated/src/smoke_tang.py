"""T-ang dedicated — smoke (declared in the pre-registration).

S1  import fidelity / bit-identity: realization 0 (A-03's exact drive
    salt), wirings fly + degree, n_train = 128, held-out = the 32-trial
    prefix — must reproduce the A-03 decision-pilot values (84.95 /
    92.77 deg) to 2 decimals. Any deviation stops the grid.
S2  one full run: fly, realization 1, full 640 trials — wall time
    (drives the declared shrink rule: K drops 5 -> 3 if > 15 min),
    no NaN, sane RMCE.

Outputs go to results/smoke/ (never the grid's files).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import run_tang  # noqa: E402

A03 = HERE.parent.parent / "a-03-sequential-learning" / "results"


def dec_pilot_value(wiring: str) -> float:
    """The decision-pilot T-ang RMCE (identical across its 3 seed rows)."""
    p = A03 / f"main-v3-dec_spike-{wiring}_T-ang_s300.json"
    r = json.loads(p.read_text())
    vals = [json.loads(q.read_text())["held_out"]["rmce_deg"]
            for q in A03.glob(f"main-v3-dec_spike-{wiring}_T-ang_s3*.json")]
    assert len(set(vals)) == 1, f"decision pilot not deterministic: {vals}"
    return vals[0]


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuit", required=True)
    args = ap.parse_args()

    import torch
    torch.set_num_threads(4)
    import tasks as tks
    from pathlib import Path as P

    staged = P(args.circuit)
    doc = json.loads(staged.read_text())
    prov = run_tang.verify(staged, doc)
    task = tks.generate_task("T-ang")
    task["ceiling"] = tks.ceilings()["T-ang"]
    wirings = run_tang.build_wirings(doc)
    outdir = HERE / "results" / "smoke"
    outdir.mkdir(parents=True, exist_ok=True)

    print("== S1: bit-identity vs the A-03 decision pilot (r0, 32 prefix)",
          flush=True)
    s1 = {}
    for w in ("fly", "degree"):
        r = run_tang.run_cell(doc, w, wirings, task, 0, outdir, prov,
                              test_prefix=32)
        got = r["held_out"]["rmce_deg"]
        ref = dec_pilot_value(w)
        ok = abs(got - ref) <= 0.005
        s1[w] = {"smoke": got, "decision_pilot": ref, "match": bool(ok)}
        print(f"  S1 {w}: smoke {got} vs decision-pilot {ref} -> "
              f"{'MATCH' if ok else 'MISMATCH'}", flush=True)

    print("== S2: one full run (fly, r1, 640 trials)", flush=True)
    t0 = time.time()
    r = run_tang.run_cell(doc, "fly", wirings, task, 1, outdir, prov)
    wall = time.time() - t0
    rmce = r["held_out"]["rmce_deg"]
    nan = any(v != v for row in (r["held_out"].items()) for v in
              (row[1] if isinstance(row[1], (int, float)) else []))
    sane = 20.0 < rmce < 179.0
    shrink = wall > 900.0
    s2 = {"wall_s": round(wall, 1), "rmce_deg": rmce, "no_nan": not nan,
          "sane_range": bool(sane), "shrink_k5_to_3": bool(shrink)}
    print(f"  S2 fly r1: wall {wall:.0f}s, rmce {rmce}, nan={nan}, "
          f"sane={sane} -> K = {3 if shrink else 5}", flush=True)

    (outdir / "smoke.json").write_text(json.dumps(
        {"s1": s1, "s2": s2,
         "proceed": all(v["match"] for v in s1.values())
                    and s2["no_nan"] and s2["sane_range"],
         "k": 3 if shrink else 5}, indent=2))
    ok = all(v["match"] for v in s1.values()) and s2["no_nan"] and sane
    print("SMOKE " + ("PASS" if ok else "FAIL"), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
