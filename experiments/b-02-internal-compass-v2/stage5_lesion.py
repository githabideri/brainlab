"""B-02 Stage 5 — lesion tests (brief: "P-EN silenced / ER silenced /
EPG silenced", 5 seeds each, same precomputed streams as Stage 4).

Lesion = the named population is removed from the network (all edges
touching it dropped; no drive/tonic/cue delivered to it). Baseline
(bio, no lesion) is re-run here with per-cell readout accounting so
that every lesion delta is computed against the identical run.

Declared predictions (brief) and what they mean in this circuit:
  P-EN silenced  "bump holds but stops updating" -> in the measured
                 circuit: does anything at all change vs bio (the
                 Stage 4 null says the P-EN drive was not transduced)?
  ER silenced    "tether lost, integrator preserved" -> the tonic-held
                 ring is removed; bulk activity should collapse.
  EPG silenced   "control: no readout" -> readout is zero by
                 construction; confirms where the Stage 4 readout
                 spikes came from.

Also answers the cue-efficacy question left open by Stage 4: with
per-cell accounting, did the declared 60 mV x 30 Hz cue make the cue-
bin EPG cells fire in c4 (population level), even though the decoder
could not use it?

Output: data/stage5-lesion.json (per run: total spikes, readout
spikes per phase, per-cell c4/c4_off counts for all 51 EPG/EPGt
cells, c2 MAE/R2, elapsed).
"""
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lif2
from run_b02 import (N_MS, WIN_MS, N_WIN, PH_WIN, W_CUE, TONIC_ER,
                     true_heading, evaluate, sha256_file)

PSD_CAP = 17.0
W_SYN = 0.275


def lesion_circuit(z, lesion_ids):
    mask = np.isin(z["src"], lesion_ids) | np.isin(z["dst"], lesion_ids)
    keep = ~mask
    return z["src"][keep], z["dst"][keep], None, int(keep.sum())


def run(lesion, seed, z, pop, binmap, epg_idx, pen_right, pen_left,
        man_se, circuit_sha, stream_sha):
    L = {
        "none": [],
        "pen": list(pen_right) + list(pen_left),
        "er": list(np.asarray(pop["ER"]["idx"], dtype=np.int64)),
        "epg": [int(x) for x in epg_idx],
    }[lesion]
    Lset = set(L)
    src, dst, _, n_edges = lesion_circuit(z, np.asarray(L, dtype=np.int64))
    w = (z["sign"].astype(np.float32)
         * np.minimum(z["psd"].astype(np.float32), PSD_CAP) * W_SYN)
    w = w[~(np.isin(z["src"], np.asarray(L, dtype=np.int64))
            | np.isin(z["dst"], np.asarray(L, dtype=np.int64)))]
    n = z["n"]
    tonic = np.zeros(n, np.float32)
    er = np.asarray(pop["ER"]["idx"], dtype=np.int64)
    tonic[er] = TONIC_ER
    if lesion == "er":
        tonic[er] = 0.0
    net = lif2.LIFNet(src.tolist(), dst.tolist(), w.astype(np.float32)
                      .tolist(), n, tonic=tonic)
    torch.manual_seed(30000 * seed + 11)

    stream = np.load(f"data/stimuli/stream-seed{seed}.npz")
    H = true_heading(man_se["omega_segments"])
    H_win_mid = H[125 + 250 * np.arange(N_WIN)]
    counts = np.zeros((N_WIN, 8), np.int64)
    # per-cell c4 vs c4_off accounting for all 51 EPG/EPGt cells
    cell_c4 = np.zeros(len(epg_idx), np.int64)
    cell_c4off = np.zeros(len(epg_idx), np.int64)
    epg_pos = {int(c): k for k, c in enumerate(epg_idx)}
    if lesion == "epg":
        epg_pos = {}  # removed from the network

    force_ev = {}
    if lesion != "pen":
        for ms, k, c in stream["pen_right"]:
            force_ev.setdefault(int(ms), []).append(int(pen_right[int(k)]))
        for ms, k, c in stream["pen_left"]:
            force_ev.setdefault(int(ms), []).append(int(pen_left[int(k)]))
    cue_ev = {}
    if lesion != "epg":
        cue_cells = np.asarray(man_se["cue"]["cells"], dtype=np.int64)
        for ms, k, c in stream["cue"]:
            cue_ev.setdefault(int(ms), (int(cue_cells[int(k)]), int(c)))

    c4i0, c4i1 = PH_WIN["c4"]
    co_i0, co_i1 = PH_WIN["c4_off"]
    t0 = time.time()
    for ms in range(1, N_MS + 1):
        ev = cue_ev.get(ms)
        if ev is not None:
            net.events([ev[0]], [ev[1]], W_CUE)
        idx = net.step(forces=force_ev.get(ms))
        wi = (ms - 1) // WIN_MS
        if idx is not None:
            a = idx.numpy()
            b = binmap[a]
            m = b >= 0
            if m.any():
                counts[wi] += np.bincount(b[m], minlength=8)
            for x in a:
                k = epg_pos.get(int(x))
                if k is None:
                    continue
                if c4i0 <= wi < c4i1:
                    cell_c4[k] += 1
                elif co_i0 <= wi < co_i1:
                    cell_c4off[k] += 1
    elapsed = time.time() - t0

    metrics = evaluate(counts, H_win_mid)
    cue_cells = [int(x) for x in
                 np.asarray(man_se["cue"]["cells"], dtype=np.int64)]
    cue_fired = {
        "cells": cue_cells if lesion != "epg" else None,
        "c4_spikes_in_cue_cells": int(cell_c4[[epg_pos[c] for c in
                                               cue_cells if
                                               c in epg_pos]].sum()
                                      if (lesion != "epg" and epg_pos)
                                      else 0),
        "c4off_spikes_in_cue_cells": int(cell_c4off[
            [epg_pos[c] for c in cue_cells if c in epg_pos]].sum()
            if (lesion != "epg" and epg_pos) else 0),
        "c4_spikes_other_epg": int(cell_c4.sum()
                                   - cell_c4[[epg_pos[c] for c in cue_cells
                                              if c in epg_pos]].sum()
                                   if epg_pos else 0),
        "c4off_spikes_other_epg": int(cell_c4off.sum()
                                      - cell_c4off[[epg_pos[c] for c in
                                                   cue_cells if c in
                                                   epg_pos]].sum()
                                      if epg_pos else 0),
    }
    return {
        "lesion": lesion, "seed": seed,
        "n_edges": n_edges,
        "total_spikes": int(net.total_spikes),
        "readout_total": int(counts.sum()),
        "readout_c1": int(counts[PH_WIN["c1"][0]:PH_WIN["c1"][1]].sum()),
        "readout_c2": int(counts[PH_WIN["c2"][0]:PH_WIN["c2"][1]].sum()),
        "readout_c4": int(counts[PH_WIN["c4"][0]:PH_WIN["c4"][1]].sum()),
        "readout_c4_off": int(counts[PH_WIN["c4_off"][0]:
                                    PH_WIN["c4_off"][1]].sum()),
        "c2": metrics["c2"],
        "cue": cue_fired,
        "per_cell_c4": {int(c): int(cell_c4[epg_pos[int(c)]])
                        for c in epg_idx if int(c) in epg_pos},
        "per_cell_c4_off": {int(c): int(cell_c4off[epg_pos[int(c)]])
                            for c in epg_idx if int(c) in epg_pos},
        "elapsed_s": round(elapsed, 1),
        "circuit_sha256": circuit_sha,
        "stream_sha256": stream_sha,
    }


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    z = np.load("data/circuit_cc_b02.npz")
    pop = json.load(open("data/populations.json"))
    wedge = json.load(open("data/wedge-map.json"))
    man = json.load(open("data/manifest.json"))
    circuit_sha = sha256_file("data/circuit_cc_b02.npz")
    sides = pop["PEN"]["sides"]
    pen_right = np.asarray([i for i, s in zip(pop["PEN"]["idx"], sides)
                            if s == "right"], dtype=np.int64)
    pen_left = np.asarray([i for i, s in zip(pop["PEN"]["idx"], sides)
                           if s == "left"], dtype=np.int64)
    epg_idx = np.asarray(pop["EPG"]["idx"] + pop["EPGt"]["idx"],
                         dtype=np.int64)
    binmap = np.full(z["n"], -1, np.int64)
    for c in wedge["cells"]:
        binmap[int(c["idx"])] = int(c["bin"])

    out = {}
    for lesion in ("none", "pen", "er", "epg"):
        out[lesion] = []
        for seed in range(5):
            man_se = man["stimuli"]["streams"][f"seed{seed}"]
            r = run(lesion, seed, z, pop, binmap, epg_idx, pen_right,
                    pen_left, man_se, circuit_sha, man_se["sha256"])
            out[lesion].append(r)
            print(f"{lesion} seed {seed}: tot={r['total_spikes']} "
                  f"ro_c2={r['readout_c2']} ro_c4={r['readout_c4']} "
                  f"ro_c4off={r['readout_c4_off']} "
                  f"cue_c4={r['cue']['c4_spikes_in_cue_cells']} "
                  f"cue_c4off={r['cue']['c4off_spikes_in_cue_cells']} "
                  f"c2_mae={r['c2']['mae']} {r['elapsed_s']}s",
                  flush=True)
    # deltas vs baseline (same seed)
    base = {r["seed"]: r for r in out["none"]}
    for lesion in ("pen", "er", "epg"):
        d = []
        for r in out[lesion]:
            b = base[r["seed"]]
            d.append({
                "seed": r["seed"],
                "total_spikes_delta": r["total_spikes"] - b["total_spikes"],
                "readout_c2_delta": r["readout_c2"] - b["readout_c2"],
                "readout_c4_delta": r["readout_c4"] - b["readout_c4"],
                "c2_mae_delta": round(r["c2"]["mae"] - b["c2"]["mae"], 2),
            })
        out[lesion + "_delta_vs_none"] = d
    import hashlib
    blob = json.dumps(out, sort_keys=True, default=float).encode()
    out["sha256_of_output"] = hashlib.sha256(blob).hexdigest()
    json.dump(out, open("data/stage5-lesion.json", "w"), indent=1,
              default=float)
    print("stage5 sha:", out["sha256_of_output"])


if __name__ == "__main__":
    main()
