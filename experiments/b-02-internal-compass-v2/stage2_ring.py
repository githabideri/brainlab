"""B-02 Stage 2 — positive control: the retuned ring.

Question (brief): does the B-01 oscillation survive in the CC-only
subgraph (B-01 minus the ALPN)? B-01 observed a stable ~56 Hz ring
oscillation (47-77 Hz across seeds) with: W_SYN = 0.275 mV/PSD,
PSD_CAP = 17, tonic 6 mV on the 278 ring cells, P-EN Poisson drive
2 + 60*|omega|/300 Hz (B-01's own declared level; here we use the
B-02 paired streams' 2 + 40*|omega|/300 — the declared B-02 level,
which is the level Stage 3 freezes), no visual cue in this 10 s
window.

Protocol: 10 s of the precomputed seed stream (phase A start,
segments with omega != 0), drive delivered B-01-style (P-EN cells
spike externally; their measured outgoing edges carry the drive —
`ext_spikes` semantics, i.e. API-3-equivalent delivery, identical to
B-01), tonic 6 mV on the 278 ring cells, no other modifications.
Measure: dominant oscillation frequency of the ring population
(FFT of the 5 ms binned population rate, 10-100 Hz band) + mean
rate, per seed. Acceptance: a dominant peak in 45-75 Hz in every
seed (B-01 observed 47-77).
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

DT = 1.0
W_SYN = 0.275
PSD_CAP = 17
TONIC_RING = 6.0
DUR_S = 10.0
WIN_MS = 5.0


def dominant_freq(rates, fs, fmin=10.0, fmax=100.0):
    """Dominant spectral peak (Hz) of a binned rate series, plus the
    peak power fraction and the mean rate."""
    x = rates - rates.mean()
    if x.std() < 1e-9:
        return dict(freq=None, peak_frac=0.0, mean_hz=float(rates.mean()))
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / fs)
    m = (freqs >= fmin) & (freqs <= fmax)
    i = np.argmax(spec[m])
    f = float(freqs[m][i])
    peak = float(spec[m][i])
    frac = peak / max(spec[m].sum(), 1e-12)
    return dict(freq=f, peak_frac=round(frac, 3),
                mean_hz=round(float(rates.mean()), 2))


def run_seed(seed, circuit, populations, stream_npz):
    z = np.load(circuit)
    src, dst, psd, sign = z["src"], z["dst"], z["psd"], z["sign"]
    n = int(z["n"])
    w = (sign * np.clip(psd, 1, PSD_CAP) * W_SYN).astype(np.float32)
    ring = np.asarray(populations["ER"]["idx"], dtype=np.int64)
    # (B-01's "ring_neuron" set is this population's 278; the 17 EL
    # cells sit outside it in both B-01 and B-02 subgraphs)
    tonic = np.zeros(n, np.float32)
    tonic[ring] = TONIC_RING
    net = lif_b01.LIFNet(src.tolist(), dst.tolist(), w.tolist(), n,
                         tonic=tonic)
    st = np.load(stream_npz)
    ev = {}
    for key in ("pen_right", "pen_left"):
        for ms, k, c in st[key]:
            if ms < int(DUR_S * 1000):
                ev.setdefault(int(ms), []).append((key, int(k), int(c)))
    # map stream cell-position -> circuit index by side
    pos2idx = {}
    for key, side in (("pen_right", "right"), ("pen_left", "left")):
        cells = populations["PEN"]["idx"]
        sides = populations["PEN"]["sides"]
        side_cells = [i for i, s in zip(cells, sides) if s == side]
        for k, i in enumerate(side_cells):
            pos2idx[(key, k)] = i
    n_steps = int(DUR_S * 1000 / DT)
    n_win = int(DUR_S * 1000 / WIN_MS)
    ring_counts = torch.zeros(n_win)
    ring_ids = torch.as_tensor(ring, dtype=torch.int64)
    for step in range(n_steps):
        ms = step + 1
        e = ev.get(ms)
        if e:
            ids = [pos2idx[(key, k)] for key, k, _ in e]
            cnt = [c for _, _, c in e]
            ext = (torch.as_tensor(ids, dtype=torch.int64),
                   torch.as_tensor(cnt, dtype=torch.int64))
        else:
            ext = None
        idx = net.step(ext)
        if idx is not None:
            w_i = int(ms / WIN_MS)
            if w_i < n_win:
                ring_counts[w_i] = ring_counts[w_i] + \
                    torch.bincount(idx, minlength=n)[ring_ids].sum()
    rates = ring_counts.numpy() / (WIN_MS / 1000.0)
    fs = 1000.0 / WIN_MS
    res = dominant_freq(rates, fs)
    res["ring_spikes_10s"] = int(ring_counts.sum())
    res["spikes_all_neurons"] = int(net.total_spikes)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--circuit", default="data/circuit_cc_b02.npz")
    ap.add_argument("--populations", default="data/populations.json")
    ap.add_argument("--stimuli-dir", default="data/stimuli")
    ap.add_argument("--out", default="data/stage2-ring.json")
    a = ap.parse_args()

    pop = json.load(open(a.populations))
    t0 = time.time()
    out = {
        "params": {"W_SYN": W_SYN, "PSD_CAP": PSD_CAP,
                   "tonic_ring_mV": TONIC_RING, "duration_s": DUR_S,
                   "window_ms": WIN_MS,
                   "drive": "precomputed B-02 paired streams, B-01-style "
                            "delivery (P-EN cells spike externally; "
                            "measured edges carry it)",
                   "acceptance": "dominant frequency 45-75 Hz in every "
                                 "seed (B-01 observed 47-77, mean 56)"},
        "seeds": {},
    }
    for seed in range(a.seeds):
        r = run_seed(seed, a.circuit, pop,
                     f"{a.stimuli_dir}/stream-seed{seed}.npz")
        out["seeds"][str(seed)] = r
        print(f"seed {seed}: {r}")
    freqs = [v["freq"] for v in out["seeds"].values() if v["freq"]]
    out["all_in_band"] = bool(freqs) and all(
        45.0 <= f <= 75.0 for f in freqs)
    out["mean_freq_hz"] = round(float(np.mean(freqs)), 1) if freqs else None
    blob = json.dumps(out, sort_keys=True).encode()
    out["sha256_of_output"] = hashlib.sha256(blob).hexdigest()
    out["elapsed_s"] = round(time.time() - t0, 1)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in
                      ("all_in_band", "mean_freq_hz", "elapsed_s")}))
    print("sha256:", out["sha256_of_output"])


if __name__ == "__main__":
    main()
