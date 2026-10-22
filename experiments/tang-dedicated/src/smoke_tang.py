"""T-ang dedicated — smoke (declared in the pre-registration; revised
once after the first attempt, recorded in the report).

S1  import fidelity / bit-identity: realization 0 (A-03's exact drive
    salt), wirings fly + degree, n_train = 128, held-out = the FULL
    512-trial fold — must reproduce the A-03 decision-pilot values
    (84.951 / 92.767 deg) to 2 decimals. The first S1 attempt used the
    32-trial prefix (the addendum's wording); the decision-pilot JSONs
    show n_test=512, so the check runs on the full fold. The 32-prefix
    numbers (fly 81.205 / degree 85.521) are kept as a data point: the
    fly-degree gap is 4.3 deg on the 32 prefix but 7.82 deg on the
    512 fold — the lead's size is fold-size-dependent, which is
    exactly what this study measures.
S2  one full run: fly, realization 1, full 640 trials — wall time
    (drives the declared shrink rule: K drops 5 -> 3 if > 15 min),
    no NaN, sane RMCE. (Ran once; re-runs reuse the file.)

Outputs go to results/smoke/ (never the grid's files).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

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
    assert r["n_train"] == 128 and r["n_test"] == 512, \
        "decision-pilot spike runs are not (128 train, 512 test)"
    return vals[0]


def _check(r: dict) -> tuple:
    vals = [v for v in r["held_out"].values() if isinstance(v, (int, float))]
    no_nan = all(math.isfinite(v) for v in vals)
    rmce = r["held_out"]["rmce_deg"]
    sane = 20.0 < rmce < 179.0
    return no_nan, sane, rmce


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--s1-only", action="store_true",
                    help="reuse the existing S2 file if present")
    args = ap.parse_args()

    import torch
    torch.set_num_threads(4)
    import tasks as tks

    staged = Path(args.circuit)
    doc = json.loads(staged.read_text())
    prov = run_tang.verify(staged, doc)
    task = tks.generate_task("T-ang")
    task["ceiling"] = tks.ceilings()["T-ang"]
    wirings = run_tang.build_wirings(doc)
    outdir = HERE / "results" / "smoke"
    outdir.mkdir(parents=True, exist_ok=True)

    print("== S1: bit-identity vs the A-03 decision pilot "
          "(r0, full 512 fold)", flush=True)
    s1 = {}
    for w in ("fly", "degree"):
        r = run_tang.run_cell(doc, w, wirings, task, 0, outdir, prov,
                              test_prefix=None, name_prefix="s1_")
        got = r["held_out"]["rmce_deg"]
        ref = dec_pilot_value(w)
        ok = abs(got - ref) <= 0.005
        s1[w] = {"smoke": got, "decision_pilot": ref, "match": bool(ok)}
        print(f"  S1 {w}: smoke {got} vs decision-pilot {ref} -> "
              f"{'MATCH' if ok else 'MISMATCH'}", flush=True)

    s2p = outdir / "fly_r1.json"
    if args.s1_only and s2p.exists():
        r = json.loads(s2p.read_text())
        no_nan, sane, rmce = _check(r)
        wall = r["wall_s"]
        print(f"  S2 (reused): wall {wall:.0f}s, rmce {rmce}", flush=True)
    else:
        print("== S2: one full run (fly, r1, 640 trials)", flush=True)
        r = run_tang.run_cell(doc, "fly", wirings, task, 1, outdir, prov)
        no_nan, sane, rmce = _check(r)
        wall = r["wall_s"]
    shrink = wall > 900.0
    s2 = {"wall_s": round(wall, 1), "rmce_deg": rmce, "no_nan": no_nan,
          "sane_range": bool(sane), "shrink_k5_to_3": bool(shrink)}
    print(f"  S2 fly r1: wall {wall:.0f}s, rmce {rmce}, nan={not no_nan}, "
          f"sane={sane} -> K = {3 if shrink else 5}", flush=True)

    (outdir / "smoke.json").write_text(json.dumps(
        {"s1": s1, "s2": s2,
         "s1_32prefix_first_attempt":
             {"fly": 81.205, "degree": 85.521,
              "note": "first smoke run (32 prefix, the addendum's wording); "
                      "kept as a data point, not the S1 check"},
         "proceed": all(v["match"] for v in s1.values())
                    and no_nan and sane,
         "k": 3 if shrink else 5}, indent=2))
    ok = all(v["match"] for v in s1.values()) and no_nan and sane
    print("SMOKE " + ("PASS" if ok else "FAIL"), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
