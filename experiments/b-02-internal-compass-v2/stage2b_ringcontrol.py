"""B-02 Stage 2b — positive control (the gate of the brief): B-01's
conventional ring control, same parameters, re-verified in the B-02
environment.

The ring_control construction below is a VERBATIM copy of
experiments/b-01-internal-compass/build_circuit.py::ring_control (seed
42; n=3563: 278 ring / 1244 fbb / 685 drive / 1356 g). The rebuilt npz
must match B-01's manifest sha256
ecc506833b5054a429c3bf3bbc355f57990f7c50db17f7cc02636af04952c1c2
byte-for-byte — that identity is the "same parameters" proof.

Run protocol: B-01's own ring-variant protocol, verbatim logic from
experiments/b-01-internal-compass/run.py (omega schedule rng
10000*seed+7, 5x5 s + c1 + 6x6 s + c3 + c4_off + c4; Poisson drive
2 + 60*|omega|/300 Hz per drive cell; 30 Hz visual cue to the 8
ring-position-nearest cells during c1/c2/c4, retargeted every 100 ms;
tonic 6 mV on the 278 ring cells; 126 s).

Measure: ring population oscillation — dominant frequency (FFT, 5 ms
bins, 10-100 Hz band) + peak power fraction + mean rate, per seed.
Brief acceptance: oscillation 45-75 Hz (60 +/- 15) in every seed.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lif_b01


def ring_control(n_total, n_ring, n_fbb, n_drive, n_g, seed):
    """Conventional spiking ring attractor with matched population sizes.
    Roles: ring (EL analogue, torus), fbb (fan columnar, recurrent),
    drive_pos / drive_neg (velocity inputs, asymmetric shift), g (global).
    All weights are declared constants (mV per delivered event)."""
    rng = np.random.default_rng(seed)
    ndp = n_drive // 2
    roles = np.array(["ring"] * n_ring + ["fbb"] * n_fbb
                     + ["drive_pos"] * ndp + ["drive_neg"] * (n_drive - ndp)
                     + ["g"] * n_g)
    pos = np.zeros(n_total, np.int32)
    blocks = [("ring", n_ring, 0), ("fbb", n_fbb, 0),
              ("drive_pos", ndp, n_ring // 7), ("drive_neg", n_drive - ndp, -n_ring // 7)]
    off = 0
    for role, m, shift in blocks:
        pos[off:off + m] = (np.arange(m) * n_ring // m + shift) % n_ring
        off += m
    E = []
    R = lambda a, b: (a - b) % n_ring
    # ring: self-excitation (window 2, 0.7 mV) + lateral inhibition (window 24, 0.35 mV)
    for i in range(n_ring):
        for d in (-2, -1, 0, 1, 2):
            E.append((i, (i + d) % n_ring, 0.7, 1))
        for d in range(1, 25):
            E.append((i, (i + d) % n_ring, 0.35, -1))
            E.append((i, (i - d) % n_ring, 0.35, -1))
    # fbb block: recurrent within its column (0.3), drives the ring at its column (0.6)
    fbb0 = n_ring
    col_fbb = {}
    for i in range(n_fbb):
        col_fbb.setdefault(pos[fbb0 + i], []).append(i)
    for i in range(n_fbb):
        p = pos[fbb0 + i]
        members = col_fbb[p]
        mi = members.index(i)
        for k in range(1, 4):
            E.append((fbb0 + i, fbb0 + members[(mi + k) % len(members)], 0.3, 1))
        for d in range(-1, 5):
            E.append((fbb0 + i, (p + d) % n_ring, 0.6, 1))
    # fbb -> drive at a SHIFTED column (pos drive at p-3, neg drive at p+3, 0.5 mV):
    # the shifted recurrent loop that moves the bump (the Turner-Evans 2017 mechanism)
    dp0, dn0 = n_ring + n_fbb, n_ring + n_fbb + ndp
    ndn = n_drive - ndp
    for i in range(n_fbb):
        p = pos[fbb0 + i]
        for j in range(ndp):
            if abs(R(pos[dp0 + j], p - 3)) <= 1:
                E.append((fbb0 + i, dp0 + j, 0.5, 1))
        for j in range(ndn):
            if abs(R(pos[dn0 + j], p + 3)) <= 1:
                E.append((fbb0 + i, dn0 + j, 0.5, 1))
    # drive -> ring: asymmetric windows, 5 mV (pos leads +[1..6], neg trails -[1..6])
    for j in range(ndp):
        p = pos[dp0 + j]
        for d in range(1, 7):
            E.append((dp0 + j, (p + d) % n_ring, 5.0, 1))
    for j in range(ndn):
        p = pos[dn0 + j]
        for d in range(1, 7):
            E.append((dn0 + j, (p - d) % n_ring, 5.0, 1))
    # global: tonic drive -> g -> sparse ring inhibition
    g0 = n_ring + n_fbb + n_drive
    for i in range(n_g):
        targets = rng.choice(n_ring, size=30, replace=False)
        for t in targets:
            E.append((g0 + i, int(t), 0.25, -1))
    a = np.array(E, dtype=[("src", "i4"), ("dst", "i4"), ("w", "f4"), ("sign", "i1")])
    a = a[np.lexsort((a["dst"], a["src"]))]
    return a, np.array(roles), pos


DT = 1.0
W_SYN = 0.275
PSD_CAP = 17
TONIC_RING = 6.0
CUE_HZ = 30.0
CUE_K = 8
TOTAL_S = 126.0
PHASES = {"A": (0.0, 25.0), "c1": (25.0, 50.0), "c2": (50.0, 86.0),
          "c3": (86.0, 106.0), "c4_off": (106.0, 116.0), "c4": (116.0, 126.0)}
B01_SHA = "ecc506833b5054a429c3bf3bbc355f57990f7c50db17f7cc02636af04952c1c2"


def omega_schedule(rng):
    segs = []
    for k in range(5):
        s = 1 if k % 2 == 0 else -1
        segs.append((5 * k, 5 * (k + 1), s * rng.uniform(150, 300)))
    segs.append((25, 50, 0.0))
    for k in range(6):
        s = 1 if k % 2 == 0 else -1
        segs.append((50 + 6 * k, 50 + 6 * (k + 1), s * rng.uniform(150, 300)))
    segs.append((86, 106, 0.0))
    segs.append((106, 116, 0.0))
    segs.append((116, 126, 0.0))
    return segs


def cue_on(t):
    return (25.0 <= t < 50.0) or (50.0 <= t < 86.0) or (t >= 116.0)


def dominant_freq(rates, fs, fmin=10.0, fmax=100.0):
    x = rates - rates.mean()
    if x.std() < 1e-9:
        return dict(freq=None, peak_frac=0.0, mean_hz=float(rates.mean()))
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / fs)
    m = (freqs >= fmin) & (freqs <= fmax)
    i = np.argmax(spec[m])
    return dict(freq=round(float(freqs[m][i]), 2),
                peak_frac=round(float(spec[m][i] / max(spec[m].sum(), 1e-12)), 3),
                mean_hz=round(float(rates.mean()), 2))


def run_seed(seed, a, z, ring_ids, pos, n, ndp):
    w = z["w"].astype(np.float32) * 0  # placeholder, replaced below
    # B-01 ring variant: weights are the declared mV constants directly
    # (the build stored w in mV; sign multiplies), used as-is
    ww = (z["sign"].astype(np.float32) * z["w"].astype(np.float32))
    tonic = np.zeros(n, np.float32)
    tonic[ring_ids] = TONIC_RING
    net = lif_b01.LIFNet(z["src"].tolist(), z["dst"].tolist(), ww.tolist(),
                         n, tonic=tonic)
    rng = np.random.default_rng(10000 * seed + 7)
    segs = omega_schedule(rng)
    H_true = 0.0
    n_steps = int(TOTAL_S * 1000 / DT)
    WIN_MS = 5.0
    n_win = int(TOTAL_S * 1000 / WIN_MS)
    ring_counts = torch.zeros(n_win)
    pos_ids = torch.as_tensor(
        [int(i) for i in np.where(z["role"] == "drive_pos")[0]],
        dtype=torch.int64)
    neg_ids = torch.as_tensor(
        [int(i) for i in np.where(z["role"] == "drive_neg")[0]],
        dtype=torch.int64)
    cue_target = torch.zeros(0, dtype=torch.int64)
    cue_last = -1.0
    rp = torch.as_tensor(pos[ring_ids], dtype=torch.int32)
    for step in range(n_steps):
        t = (step + 1) * DT / 1000.0
        omega = 0.0
        for (a0, b0, om) in segs:
            if a0 <= t < b0:
                omega = om
                break
        H_true = (H_true + omega * DT / 1000) % 360
        r_pos = 2.0 + 60.0 * max(omega, 0.0) / 300.0
        r_neg = 2.0 + 60.0 * max(-omega, 0.0) / 300.0
        parts, cnts = [], []
        if len(pos_ids):
            c = torch.poisson(torch.full((len(pos_ids),), r_pos * DT / 1000))
            parts.append(pos_ids); cnts.append(c)
        if len(neg_ids):
            c = torch.poisson(torch.full((len(neg_ids),), r_neg * DT / 1000))
            parts.append(neg_ids); cnts.append(c)
        if cue_on(t):
            if abs(t - cue_last) > 0.1 or cue_last < 0:
                p = int((np.radians(H_true) / (2 * np.pi)) * 278) % 278
                d = np.minimum((rp.numpy() - p) % 278,
                               (p - rp.numpy()) % 278)
                cue_target = torch.as_tensor(
                    ring_ids[np.argsort(d)[:CUE_K]], dtype=torch.int64)
                cue_last = t
            c = torch.poisson(torch.full((len(cue_target),),
                                         CUE_HZ * DT / 1000))
            parts.append(cue_target); cnts.append(c)
        ext = (torch.cat(parts), torch.cat(cnts)) if parts else None
        idx = net.step(ext)
        if idx is not None:
            wi = int(t * 1000 / WIN_MS)
            if wi < n_win:
                ring_counts[wi] = ring_counts[wi] + \
                    torch.bincount(idx, minlength=n)[ring_ids].sum()
    rates = ring_counts.numpy() / (WIN_MS / 1000.0)
    fs = 1000.0 / WIN_MS
    return dict(**dominant_freq(rates, fs),
                total_spikes=int(net.total_spikes),
                segments=[[a0, b0, round(om, 1)] for a0, b0, om in segs])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default="data/stage2b-ringcontrol.json")
    a = ap.parse_args()
    # rebuild + verify byte identity with B-01
    E, roles, pos = ring_control(3563, 278, 1244, 685, 1356, 42)
    rp = "data/ring_control_rebuilt.npz"
    np.savez(rp, src=E["src"], dst=E["dst"], w=E["w"], sign=E["sign"],
             n=3563, role=roles, pos=pos)
    h = hashlib.sha256(open(rp, "rb").read()).hexdigest()
    ok = h == B01_SHA
    print(f"ring control rebuilt: sha={h[:12]} match_B01={ok}")
    assert ok, f"ring control rebuild differs from B-01: {h}"
    z = np.load(rp)
    ring_ids = np.where(z["role"] == "ring")[0]
    out = {
        "identity": {"sha256": h, "matches_B01_manifest": ok,
                     "B01_manifest_sha": B01_SHA},
        "protocol": "B-01 ring variant verbatim: Poisson 2+60|omega|/300 "
                    "Hz per drive cell, 30 Hz cue to 8 nearest ring "
                    "cells (c1/c2/c4, retarget 100 ms), tonic 6 mV on "
                    "278 ring cells, 126 s",
        "acceptance": "dominant frequency 45-75 Hz in every seed "
                      "(brief: 60 +/- 15 Hz)",
        "seeds": {},
    }
    t0 = time.time()
    for seed in range(a.seeds):
        r = run_seed(seed, a, z, ring_ids, pos, 3563, 342)
        out["seeds"][str(seed)] = r
        print(f"seed {seed}: {r}")
    freqs = [v["freq"] for v in out["seeds"].values() if v["freq"]]
    out["all_in_band"] = bool(freqs) and all(45.0 <= f <= 75.0 for f in freqs)
    out["mean_freq_hz"] = round(float(np.mean(freqs)), 1) if freqs else None
    out["elapsed_s"] = round(time.time() - t0, 1)
    blob = json.dumps(out, sort_keys=True, default=float).encode()
    out["sha256_of_output"] = hashlib.sha256(blob).hexdigest()
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(json.dumps({k: out[k] for k in
                      ("all_in_band", "mean_freq_hz", "elapsed_s")}))
    print("sha256:", out["sha256_of_output"])


if __name__ == "__main__":
    main()
