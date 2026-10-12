#!/usr/bin/env python
"""Aggregate B-01 results/ into results/summary.json and evaluate the
pre-registered acceptance criteria (experiments/b-01-internal-compass/README.md).

Usage: python summarize.py [--results results]

The criteria are evaluated exactly as pre-registered, including the
A5 comparative criterion (bio vs shuffle on drift or tracking). A null
(failing) criterion is a normal, reportable outcome.
"""
import argparse, glob, json, os, sys


def load_runs(resdir):
    runs = {}
    for p in sorted(glob.glob(os.path.join(resdir, "*-seed*.json"))):
        with open(p) as f:
            r = json.load(f)
        runs.setdefault(r["variant"], {})[r["seed"]] = r
    return runs


def med(x):
    x = sorted(x)
    n = len(x)
    return x[n // 2] if n % 2 else 0.5 * (x[n // 2 - 1] + x[n // 2])


def mean(x):
    return sum(x) / len(x) if x else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    outpath = args.out or os.path.join(args.results, "summary.json")
    runs = load_runs(args.results)
    summary = {"variants": {}, "acceptance": {}, "runs": {}}

    for variant, seedruns in sorted(runs.items()):
        seeds = sorted(seedruns)
        c1 = [seedruns[s]["c1"] for s in seeds]
        c2 = [seedruns[s]["c2"] for s in seeds]
        c3 = [seedruns[s]["c3"] for s in seeds]
        c4 = [seedruns[s]["c4"] for s in seeds]
        dec = [seedruns[s]["decoder"] for s in seeds]
        entry = {
            "seeds": seeds,
            "n_neurons": seedruns[seeds[0]]["n_neurons"],
            "total_spikes": [seedruns[s]["total_spikes"] for s in seeds],
            "elapsed_s": [seedruns[s]["elapsed_s"] for s in seeds],
            "drift_c1_deg_s": [round(c1[s]["abs_drift_deg_s"], 3) for s in seeds],
            "drift_c1_signed_deg_s": [round(c1[s]["drift_deg_s"], 3) for s in seeds],
            "drift_c3_deg_s": [round(c3[s]["abs_drift_deg_s"], 3) for s in seeds],
            "drift_c3_signed_deg_s": [round(c3[s]["drift_deg_s"], 3) for s in seeds],
            "c2_mean_abs_err_deg": [round(c2[s]["mean_abs_err_deg"], 2) for s in seeds],
            "c2_stability_frac": [round(c2[s]["stability_frac"], 3) for s in seeds],
            "c4_recovery_s": [c4[s]["recovery_s"] for s in seeds],
            "c4_final_err_deg": [round(c4[s]["final_err_deg"], 2) for s in seeds],
            "c4_pre_cue_err_deg": [round(c4[s]["pre_cue_err_deg"], 2) for s in seeds],
            "decoder_held_out_R2": [round(dec[s]["held_out_R2"], 3) for s in seeds],
            "decoder_held_out_mae_deg": [round(dec[s]["held_out_mae_deg"], 2) for s in seeds],
            "el_mean_hz_c1": [round(c1[s]["el_mean_hz"], 2) for s in seeds],
            "el_silent_c1": [bool(c1[s]["silent"]) for s in seeds],
        }
        summary["variants"][variant] = entry

    bio = summary["variants"].get("bio")
    shuf = summary["variants"].get("shuffle")
    if bio is not None:
        c1s = bio["drift_c1_signed_deg_s"]
        c3s = bio["drift_c3_signed_deg_s"]
        a1 = (med([abs(d) for d in bio["drift_c1_deg_s"]]) < 2.0) or any(
            abs(a) < 5.0 * abs(b) for a, b in zip(c1s, c3s)
        )
        a2 = any(d > 0.1 for d in bio["drift_c3_deg_s"])
        a3 = sum(1 for e in bio["c2_mean_abs_err_deg"] if e < 15.0)
        a4 = sum(1 for r in bio["c4_recovery_s"] if r is not None and r < 10.0)
        summary["acceptance"]["bio"] = {
            "A1_c1_drift": {"pass": bool(a1),
                             "median_abs_drift_deg_s": med([abs(d) for d in bio["drift_c1_deg_s"]])},
            "A2_c3_deprivation_drift_positive": {"pass": bool(a2)},
            "A3_c2_tracking_under_15deg": {"pass": bool(a3 >= 3), "n_seeds_passing": a3},
            "A4_c4_recovery_under_10s": {"pass": bool(a4 >= 3), "n_seeds_passing": a4},
        }
    if bio is not None and shuf is not None:
        b_drift = mean(bio["drift_c3_deg_s"])
        s_drift = mean(shuf["drift_c3_deg_s"])
        b_track = mean(bio["c2_mean_abs_err_deg"])
        s_track = mean(shuf["c2_mean_abs_err_deg"])
        summary["acceptance"]["A5_comparative"] = {
            "bio_vs_shuffle_c3_drift": {"bio": b_drift, "shuffle": s_drift,
                                        "bio_better": bool(b_drift < s_drift)},
            "bio_vs_shuffle_c2_tracking": {"bio": b_track, "shuffle": s_track,
                                           "bio_better": bool(b_track < s_track)},
            "pass": bool(b_drift < s_drift or b_track < s_track),
            "note": "ring variant reported wherever it falls (not part of the pass condition)",
        }

    with open(outpath, "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
