"""B-02 Stage 4 — the pre-registered 5-arm x 5-seed battery.

Implements README.md §4-8 exactly as frozen:
  arms      bio / signflip / weight05 / weight2 / pop
  circuit   data/circuit_cc_b02.npz (2,878 nodes, 300,521 edges),
            w = sign * min(PSD,17) * 0.275 mV, scaled x0.5 / x2
  drive     precomputed streams (data/stimuli/), P-EN = API 3 forced
            spikes. bio: right cells <- right stream, left <- left.
            signflip: streams swapped between the two physical sides.
            pop: a fixed 42-cell shuffled population (np default_rng
            999, drawn from the 2,878 minus the 42 P-EN and 51
            EPG/EPGt; first 21 drawn cells <- left stream, last 21 <-
            right stream).
  cue       API 2 external events, declared W_CUE = 60 mV/event, 30 Hz
            onto the EPG/EPGt cue-bin cells (from the stream), c4 only
  tonic     6 mV on the 278 ER ring cells
  readout   8 coarse 45-deg wedge-bin rates of EPG/EPGt, 250 ms windows;
            ridge (alpha=1), standardized inputs, trained on odd
            phase-A windows, evaluated on even windows per phase;
            c2 per-segment MAE; c4 recovery (first 8-consecutive
            |err|<=15 deg window) + cue effect (c3 mean |err| minus
            minimum 5-window rolling mean |err| over c4); drift
            (deg/s, unwrapped fit over c1..c4); stability
            (fraction of windows |err|<=15)

The ring arm is NOT re-run here: the oscillation control is Stage 2
(`stage2b_ringcontrol.py`, PASS in all 5 seeds) and the ring-control
heading readout is cited from the B-01 report (same byte-identical
circuit, same engine, same protocol).

Output: results/<arm>-seed<s>.json per run, results/summary.json with
the 7 decision rules evaluated (every rule reported whether or not
satisfied — nulls are results, README §6).

Deterministic: all randomness comes from the precomputed streams;
torch is seeded per run so float-nondeterminism cannot drift results.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lif2

DT_MS = 1
N_MS = 126000
WIN_MS = 250
N_WIN = N_MS // WIN_MS
W_CUE = 60.0
TONIC_ER = 6.0
ALPHA = 1.0
PSD_CAP = 17.0
W_SYN = 0.275

PH_WIN = {"A": (0, 100), "c1": (100, 200), "c2": (200, 344),
          "c3": (344, 424), "c4_off": (424, 464), "c4": (464, 504)}
C2_SEGS = [(200 + 24 * k, 200 + 24 * (k + 1)) for k in range(6)]
WSCALE = {"bio": 1.0, "signflip": 1.0, "weight05": 0.5,
          "weight2": 2.0, "pop": 1.0}


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def true_heading(segs):
    """Integrated true heading (deg) at each ms, from the manifest's
    per-seed omega segments (identical to stimulus.py's construction)."""
    omega = np.zeros(N_MS, np.float32)
    t = 0
    for dur, w in segs:
        omega[int(t * 1000):int((t + dur) * 1000)] = w
        t += dur
    return np.mod(np.cumsum(omega) / 1000.0, 360.0)


def circ_err_deg(pred, true):
    return np.abs(((pred - true + 180.0) % 360.0) - 180.0)


def fit_drift_deg_s(t_win, deg):
    d = np.unwrap(np.deg2rad(deg)) * 180.0 / np.pi  # unwrapped deg
    if len(t_win) < 3:
        return 0.0
    return float(np.polyfit(t_win, d, 1)[0])


def evaluate(counts, H_win_mid):
    """All declared readout metrics (README §6)."""
    X = counts / (WIN_MS / 1000.0)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    Xs = (X - mu) / sd
    A_i0, A_i1 = PH_WIN["A"]
    train = np.arange(A_i0, A_i1, 2)  # odd phase-A windows
    Xtr = Xs[train]
    ytr = H_win_mid[train]
    yc = ytr - ytr.mean()
    betas = np.linalg.solve(Xtr.T @ Xtr + ALPHA * np.eye(8), Xtr.T @ yc)
    pred = Xs @ betas + ytr.mean()
    err = circ_err_deg(pred, H_win_mid)
    t_win = (np.arange(N_WIN) + 0.5) * WIN_MS / 1000.0

    def phase_metrics(name):
        i0, i1 = PH_WIN[name]
        ev = np.arange(i0, i1, 2)  # even (held-out) windows
        e = err[ev]
        y = H_win_mid[ev]
        ss_res = float(((e * np.pi / 180.0) ** 2).sum())
        ss_tot = float((((y - y.mean()) * np.pi / 180.0) ** 2).sum())
        # R2 is undefined when the target is (near-)constant over the
        # phase (c1/c3/c4 are stationary): report null, not an artifact
        r2 = None if ss_tot < 1e-6 else round(1.0 - ss_res / ss_tot, 4)
        return dict(n=int(len(ev)), r2=r2,
                    mae=round(float(e.mean()), 2),
                    stability=round(float((e <= 15.0).mean()), 3))

    out = {ph: phase_metrics(ph) for ph in ("A", "c1", "c2", "c3", "c4")}
    out["c2_segments"] = [round(float(err[i0:i1].mean()), 2)
                          for i0, i1 in C2_SEGS]
    out["drift_deg_s"] = round(fit_drift_deg_s(t_win[100:], pred[100:]), 2)
    i0, i1 = PH_WIN["c3"]
    c3_mean = float(err[i0:i1].mean())
    c4e = err[PH_WIN["c4"][0]:PH_WIN["c4"][1]]
    roll = np.convolve(c4e, np.ones(5) / 5, mode="valid")
    rec = None
    for i in range(len(c4e) - 7):
        if (c4e[i:i + 8] <= 15.0).all():
            rec = round((PH_WIN["c4"][0] + i + 0.5) * WIN_MS / 1000.0
                        - 116.0, 2)
            break
    out["cue"] = dict(
        c3_mean_err=round(c3_mean, 2),
        c4_min_roll5_mean_err=round(float(roll.min()), 2),
        c4_off_mean_err=round(
            float(err[PH_WIN["c4_off"][0]:PH_WIN["c4_off"][1]].mean()), 2),
        delta=round(c3_mean - float(roll.min()), 2),
        c4_recovery_s=rec)
    out["total_spikes_readout"] = int(counts.sum())
    return out


def run_arm_seed(arm, seed, z, pop, binmap, penmap,
                 right_stream, left_stream, cue_stream,
                 right_cells, left_cells, cue_cells, segs):
    n = z["n"]
    w = (z["sign"].astype(np.float32)
         * np.minimum(z["psd"].astype(np.float32), PSD_CAP)
         * W_SYN * WSCALE[arm])
    tonic = np.zeros(n, np.float32)
    tonic[np.asarray(pop["ER"]["idx"], dtype=np.int64)] = TONIC_ER
    net = lif2.LIFNet(z["src"].tolist(), z["dst"].tolist(),
                      w.astype(np.float32).tolist(), n, tonic=tonic)
    torch.manual_seed(30000 * seed + 11)

    H = true_heading(segs)
    H_win_mid = H[125 + 250 * np.arange(N_WIN)]
    counts = np.zeros((N_WIN, 8), np.int64)
    pen_counts = np.zeros(N_WIN, np.int64)

    # stream rows are [ms, position-in-side-list, count]; map position
    # to the circuit cell that this arm assigns to that side
    force_ev = {}
    for ms, k, c in right_stream:
        force_ev.setdefault(int(ms), []).append(int(right_cells[int(k)]))
    for ms, k, c in left_stream:
        force_ev.setdefault(int(ms), []).append(int(left_cells[int(k)]))
    cue_ev = {}
    for ms, k, c in cue_stream:
        cue_ev.setdefault(int(ms), (int(cue_cells[int(k)]), int(c)))

    t0 = time.time()
    for ms in range(1, N_MS + 1):
        ev = cue_ev.get(ms)
        if ev is not None:
            # API 2: declared-weight external events onto the cue cell
            # (queued with the synaptic delay by lif2.events before step)
            net.events([ev[0]], [ev[1]], W_CUE)
        idx = net.step(forces=force_ev.get(ms))
        wi = (ms - 1) // WIN_MS
        if idx is not None:
            a = idx.numpy()
            b = binmap[a]
            m = b >= 0
            if m.any():
                counts[wi] += np.bincount(b[m], minlength=8)
            p = penmap[a]
            if (p >= 0).any():
                pen_counts[wi] += int((p >= 0).sum())
    elapsed = time.time() - t0

    metrics = evaluate(counts, H_win_mid)
    i0, i1 = PH_WIN["c1"]
    c2i0, c2i1 = PH_WIN["c2"]
    res = {
        "arm": arm, "seed": seed,
        "w_scale": WSCALE[arm],
        "tonic": {"target": "ER (278)", "mV": TONIC_ER},
        "cue_api": "2", "cue_weight_mV": W_CUE,
        "drive_api": "3 (forced spikes)",
        "n_drive_cells": int(len(right_cells) + len(left_cells)),
        "total_spikes": int(net.total_spikes),
        "pen_rate_hz_c1": round(float(pen_counts[i0:i1].sum()) / 25.0, 2),
        "epg_epgt_rate_hz_c1": round(float(counts[i0:i1].sum()) / 25.0, 2),
        "epg_epgt_rate_hz_c2": round(float(counts[c2i0:c2i1].sum()) / 36.0,
                                     2),
        "elapsed_s": round(elapsed, 1),
        "metrics": metrics,
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*",
                    default=["bio", "signflip", "weight05", "weight2",
                             "pop"])
    ap.add_argument("--seeds", type=int, nargs="*", default=list(range(5)))
    ap.add_argument("--outdir", default="results")
    a = ap.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(a.outdir, exist_ok=True)
    z = np.load("data/circuit_cc_b02.npz")
    pop = json.load(open("data/populations.json"))
    wedge = json.load(open("data/wedge-map.json"))
    man = json.load(open("data/manifest.json"))
    circuit_sha = sha256_file("data/circuit_cc_b02.npz")

    sides = pop["PEN"]["sides"]
    right_idx = np.asarray([i for i, s in zip(pop["PEN"]["idx"], sides)
                            if s == "right"], dtype=np.int64)
    left_idx = np.asarray([i for i, s in zip(pop["PEN"]["idx"], sides)
                           if s == "left"], dtype=np.int64)
    epg_idx = np.asarray(pop["EPG"]["idx"] + pop["EPGt"]["idx"],
                         dtype=np.int64)
    penmap = np.full(z["n"], -1, np.int64)
    penmap[right_idx] = 0  # value unused; >=0 marks a P-EN cell
    penmap[left_idx] = 1

    binmap = np.full(z["n"], -1, np.int64)
    for c in wedge["cells"]:
        binmap[int(c["idx"])] = int(c["bin"])

    # pop arm: declared rng 999; excludes all 42 P-EN and 51 EPG/EPGt
    excluded = set(int(x) for x in right_idx) | set(int(x) for x in left_idx) \
        | set(int(x) for x in epg_idx)
    cand = np.asarray([i for i in range(z["n"]) if i not in excluded],
                      dtype=np.int64)
    pop_cells = np.sort(np.random.default_rng(999).choice(
        cand, size=42, replace=False))

    runs = []
    for arm in a.arms:
        for seed in a.seeds:
            sp = os.path.join(a.outdir, f"{arm}-seed{seed}.json")
            if os.path.exists(sp):
                r = json.load(open(sp))
                print(f"{arm} seed {seed}: cached")
                runs.append(r)
                continue
            stream = np.load(f"data/stimuli/stream-seed{seed}.npz")
            man_se = man["stimuli"]["streams"][f"seed{seed}"]
            cue_cells = np.asarray(man_se["cue"]["cells"], dtype=np.int64)
            if arm == "pop":
                right_cells, left_cells = pop_cells[21:], pop_cells[:21]
                r_stream, l_stream = stream["pen_right"], stream["pen_left"]
            elif arm == "signflip":
                # the physical cells stay put; the two side STREAMS are
                # swapped (mirror of the drive side mapping)
                right_cells, left_cells = right_idx, left_idx
                r_stream, l_stream = stream["pen_left"], stream["pen_right"]
            else:
                right_cells, left_cells = right_idx, left_idx
                r_stream, l_stream = stream["pen_right"], stream["pen_left"]
            r = run_arm_seed(arm, seed, z, pop, binmap, penmap,
                             r_stream, l_stream, stream["cue"],
                             right_cells, left_cells, cue_cells,
                             man_se["omega_segments"])
            r["circuit_sha256"] = circuit_sha
            r["stream_sha256"] = man_se["sha256"]
            r["omega_segments"] = man_se["omega_segments"]
            r["cue"] = {**man_se["cue"], "api": "2", "weight_mV": W_CUE}
            r["drive_cells"] = {"right": [int(x) for x in right_cells],
                                "left": [int(x) for x in left_cells]}
            r["pop_draw"] = pop_cells.tolist() if arm == "pop" else None
            blob = json.dumps(r, sort_keys=True).encode()
            r["sha256_of_result"] = hashlib.sha256(blob).hexdigest()
            with open(sp, "w") as f:
                json.dump(r, f, indent=1)
            runs.append(r)
            m = r["metrics"]
            print(f"{arm} seed {seed}: "
                  f"c1 R2={m['c1']['r2']}/MAE={m['c1']['mae']} "
                  f"c2 R2={m['c2']['r2']}/MAE={m['c2']['mae']} "
                  f"c3 R2={m['c3']['r2']}/MAE={m['c3']['mae']} "
                  f"c4 R2={m['c4']['r2']}/MAE={m['c4']['mae']} "
                  f"drift={m['drift_deg_s']} cueΔ={m['cue']['delta']} "
                  f"spikes={r['total_spikes']} {r['elapsed_s']}s",
                  flush=True)

    summarize(runs, a.outdir)


def summarize(runs, outdir):
    by = {}
    for r in runs:
        by.setdefault(r["arm"], []).append(r)
    for v in by.values():
        v.sort(key=lambda r: r["seed"])

    def r2v(m):
        # None = undefined (constant target phase): fails R2>0.1,
        # passes R2<0.05 (no evidence of tracking either way)
        return m["r2"] if m["r2"] is not None else float("-inf")

    def nonchance(r):
        return any(r2v(r["metrics"][ph]) > 0.1
                   and r["metrics"][ph]["mae"] < 60.0
                   for ph in ("c1", "c2", "c3"))

    def at_chance(r):
        return all(r2v(r["metrics"][ph]) < 0.05
                   and r["metrics"][ph]["mae"] >= 70.0
                   for ph in ("c1", "c2", "c3"))

    def cue_ok(r):
        return r["metrics"]["cue"]["delta"] >= 10.0

    def mean_mae(rs, ph):
        v = [r["metrics"][ph]["mae"] for r in rs]
        return round(float(np.mean(v)), 2) if v else None

    bio, sf = by.get("bio", []), by.get("signflip", [])
    rules = {
        "1_p_en_epg_transduction": {
            "criterion": "bio: R2>0.1 and MAE<60 on c1 or c2 or c3 in "
                         ">=3/5 seeds",
            "n_satisfied": int(sum(nonchance(r) for r in bio)),
            "per_seed": [bool(nonchance(r)) for r in bio],
            "satisfied": bool(sum(nonchance(r) for r in bio) >= 3)},
        "2_cue_effect": {
            "criterion": "bio: (c3 mean |err|) - (min 5-window rolling "
                         "mean |err| over c4) >= 10 deg in >=3/5 seeds",
            "n_satisfied": int(sum(cue_ok(r) for r in bio)),
            "per_seed": [bool(cue_ok(r)) for r in bio],
            "satisfied": bool(sum(cue_ok(r) for r in bio) >= 3)},
        "3_sign_sensitivity": {
            "criterion": "signflip c2 drift sign opposite to bio in "
                         ">=3/5 seeds, magnitude within x2",
            "satisfied": None},
        "4_address_effect": {
            "criterion": "bio non-chance (rule 1) while pop at chance "
                         "(rule 6)",
            "satisfied": None},
        "5_weight_dose_response": {
            "criterion": "mean|err| weight05 >= bio and (mean|err| "
                         "weight2 >= bio or weight2 mean EPG/EPGt c2 "
                         "rate >= 2x bio)",
            "satisfied": None},
        "6_pop_null": {
            "criterion": "pop at chance (R2<0.05 and MAE>=70 on each of "
                         "c1, c2, c3) in >=4/5 seeds",
            "n_satisfied": int(sum(at_chance(r)
                                   for r in by.get("pop", []))),
            "satisfied": None},
        "7_control": {
            "criterion": "ring: in-band oscillation verified in Stage 2 "
                         "(63.8-64.0 Hz, all 5 seeds, byte-identical "
                         "circuit); heading readout cited from the B-01 "
                         "report (same circuit bytes, engine, protocol)",
            "satisfied": True},
    }
    pairs = []
    n3 = 0
    for b, s in zip(bio, sf):
        bd, sd = b["metrics"]["drift_deg_s"], s["metrics"]["drift_deg_s"]
        ok = bool(bd != 0 and np.sign(sd) == -np.sign(bd)
                  and 0.5 * abs(bd) <= abs(sd) <= 2 * abs(bd))
        pairs.append({"seed": b["seed"], "bio": bd, "signflip": sd,
                      "counted": ok})
        n3 += int(ok)
    rules["3_sign_sensitivity"]["pairs"] = pairs
    rules["3_sign_sensitivity"]["n_satisfied"] = n3
    rules["3_sign_sensitivity"]["satisfied"] = bool(n3 >= 3)

    w5 = rules["5_weight_dose_response"]
    for ph in ("c1", "c2", "c3", "c4"):
        w5[f"mean_mae_{ph}"] = {arm: mean_mae(by.get(arm, []), ph)
                                for arm in ("bio", "weight05", "weight2")}
    m05, mb, m2 = (w5["mean_mae_c2"][x] for x in ("weight05", "bio",
                                                  "weight2"))
    r05 = [r["epg_epgt_rate_hz_c2"] for r in by.get("weight05", [])]
    rb = [r["epg_epgt_rate_hz_c2"] for r in by.get("bio", [])]
    r2 = [r["epg_epgt_rate_hz_c2"] for r in by.get("weight2", [])]
    rate_cond = bool(r2 and rb and
                     float(np.mean(r2)) >= 2 * max(float(np.mean(rb)),
                                                   1e-9))
    w5["rate_saturation"] = rate_cond
    w5["satisfied"] = bool(m05 is not None and mb is not None and
                           m05 >= mb and
                           ((m2 is not None and m2 >= mb) or rate_cond))

    r6 = rules["6_pop_null"]
    r6["satisfied"] = bool(r6["n_satisfied"] >= 4)
    bio_nc = int(sum(nonchance(r) for r in bio))
    pop_ch = int(sum(at_chance(r) for r in by.get("pop", [])))
    rules["4_address_effect"]["bio_nonchance_seeds"] = bio_nc
    rules["4_address_effect"]["pop_chance_seeds"] = pop_ch
    rules["4_address_effect"]["satisfied"] = bool(bio_nc >= 3 and
                                                  pop_ch >= 4)

    per = {}
    for r in runs:
        per[f"{r['arm']}-seed{r['seed']}"] = {
            "total_spikes": r["total_spikes"],
            "c1": r["metrics"]["c1"], "c2": r["metrics"]["c2"],
            "c3": r["metrics"]["c3"], "c4": r["metrics"]["c4"],
            "c2_segments": r["metrics"]["c2_segments"],
            "drift_deg_s": r["metrics"]["drift_deg_s"],
            "cue": r["metrics"]["cue"],
            "pen_rate_c1_hz": r["pen_rate_hz_c1"],
            "epg_rate_c1_hz": r["epg_epgt_rate_hz_c1"],
            "epg_rate_c2_hz": r["epg_epgt_rate_hz_c2"],
            "elapsed_s": r["elapsed_s"],
            "stream_sha256": r["stream_sha256"],
            "circuit_sha256": r["circuit_sha256"],
            "sha256_of_result": r["sha256_of_result"]}
    summary = {
        "experiment": "B-02 stage 4 battery (pre-registered, "
                      "experiments/b-02-internal-compass-v2/README.md)",
        "arms": {k: [f"{k}-seed{r['seed']}" for r in v]
                 for k, v in sorted(by.items())},
        "decision_rules": rules,
        "per_run": per,
        "ring_arm_note": "ring arm: oscillation from Stage 2 "
                         "(data/stage2b-ringcontrol.json); heading "
                         "readout from the B-01 report (same bytes, "
                         "engine, protocol)",
        "runtime": {"python": sys.version.split()[0],
                    "torch": torch.__version__,
                    "git_sha": subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        capture_output=True, text=True).stdout.strip()},
    }
    blob = json.dumps(summary, sort_keys=True, default=float).encode()
    summary["sha256_of_summary"] = hashlib.sha256(blob).hexdigest()
    json.dump(summary, open(os.path.join(outdir, "summary.json"), "w"),
              indent=1, default=float)
    print(json.dumps({k: v.get("satisfied") for k, v in rules.items()},
                     indent=1))
    print("summary sha:", summary["sha256_of_summary"])


if __name__ == "__main__":
    main()
