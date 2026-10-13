"""Paired stimulus-effect reanalysis (review round 4, 2026-10-13).

The campaign's recorded `delta_hz` is NOT a stimulus effect: it is the
5-s post-stimulus window rate minus the SAME run's whole-15-s average
(in a stimulated run, that average includes the post-stimulus window).
The correct primary metric is the PAIRED contrast already contained in
the committed data: for each (variant, wiring, sim seed, group)

    paired_delta_hz = stim_run.stim_window_hz - rest_run.stim_window_hz

(the same 5-s window, the paired no-stimulus run, same wiring and
seed). This script recomputes that contrast from results-exact.json —
no simulation is re-run — and freezes it as data/paired-stim-effect.json.

Verification target (independent re-review of 787bc3a): at 50 ms the
command-pool paired effect is +0.090 Hz in the measured wiring
(per-seed +0.125/+0.150/+0.025/+0.100/+0.050), about zero in the three
shuffle graphs, and ~+0.013 Hz in the body-wall motors; 5 ms stays
null.

Usage:  python src/reanalyze_paired.py
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

VARIANTS = ["5ms", "50ms"]


def main():
    src = os.path.join(HERE, "results-exact.json")
    with open(src) as f:
        results = json.load(f)

    out = {
        "derived_from": "results-exact.json (committed; no rerun)",
        "definition": (
            "paired_delta_hz = stim_run.stim_window_hz - "
            "rest_run.stim_window_hz, same (variant, wiring, sim seed, "
            "group); window = [stim_end, stim_end + 5000) in both runs. "
            "The same-run delta_hz stored in results-exact.json is a "
            "diagnostic (window minus the same run's whole-15-s mean) "
            "and is NOT a stimulus effect."),
        "variants": {},
    }

    for name in VARIANTS:
        runs = results[name]["runs"]
        by = {}
        for r in runs:
            by.setdefault((r["wiring"], r["seed"]), {})[r["cond"]] = r
        gnames = sorted({g for r in runs for g in r["groups"]})
        vout = {}
        for g in gnames:
            gout = {}
            for (wiring, seed) in sorted(by):
                pair = by[(wiring, seed)]
                if "rest" not in pair or "stim" not in pair:
                    continue
                rest_w = pair["rest"]["groups"].get(g, {}).get(
                    "stim_window_hz")
                stim_w = pair["stim"]["groups"].get(g, {}).get(
                    "stim_window_hz")
                if rest_w is None or stim_w is None:
                    continue
                gout.setdefault(wiring, {"per_seed": {}, "deltas": []})
                d = stim_w - rest_w
                gout[wiring]["per_seed"][str(seed)] = {
                    "rest_window_hz": round(rest_w, 6),
                    "stim_window_hz": round(stim_w, 6),
                    "paired_delta_hz": round(d, 6),
                }
                gout[wiring]["deltas"].append(d)
            for wiring in gout:
                ds = gout[wiring]["deltas"]
                gout[wiring]["mean_paired_delta_hz"] = round(sum(ds) / len(ds), 6)
                gout[wiring]["all_same_sign"] = bool(
                    all(d > 0 for d in ds) or all(d < 0 for d in ds))
            vout[g] = gout
        out["variants"][name] = vout

    p = os.path.join(DATA, "paired-stim-effect.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {os.path.relpath(p, HERE)}")

    # headline check
    v = out["variants"]["50ms"].get("command_pool", {})
    for w in sorted(v):
        m = v[w]
        per = [m["per_seed"][s]["paired_delta_hz"]
               for s in sorted(m["per_seed"], key=int)]
        print(f"50ms command pool {w}: mean {m['mean_paired_delta_hz']:+.4f} Hz "
              f"(per-seed {[round(d, 4) for d in per]})")


if __name__ == "__main__":
    main()
