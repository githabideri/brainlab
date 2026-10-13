"""B-02 paired-stimulus precomputation (Stage 1).

Precomputes, per seed, the full 126 s of drive events so that every arm
of every comparison (variants × seeds) consumes the IDENTICAL stimulus
stream; streams are hashed and the hashes are recorded in
data/manifest.json (paired design: identical stimulus across arms is
what makes variant comparisons paired; the seed is the only free
random variable).

Session layout (same skeleton as B-01, so results are comparable):
  phase A   5 segments x 5 s,  alternating +/- (150..300) deg/s
  c1       25 s  omega = 0
  c2       6 segments x 6 s, alternating +/- (150..300) deg/s
  c3       20 s  omega = 0
  c4_off   10 s  omega = 0
  c4       10 s  omega = 0  (visual cue active)
Total: 126 s = 126,000 ms.

Declared drive parameters (frozen at pre-registration, Stage 3):
  P-EN drive: 42 P-EN cells (20 PEN_a + 22 PEN_b) split by the
  official annotation side into right (21) and left (21). Per-cell
  rate r(t) = base + scale * max(+/-omega(t), 0) / 300,
  base = 2 Hz, scale = 40 Hz (peak 42 Hz at |omega| = 300 deg/s).
  Delivery in the runs is via API 3 (forced P-EN spikes — B-01's actual
  mechanism, renamed in lif2.py): Stage 1's draft had declared API 2 @
  3 mV/event, superseded at Stage 3 after the efficacy analysis (see
  data/manifest.json: stimuli.drive.api). The event STREAM computed
  here is delivery-mechanism independent either way.
  Visual cue: during c4 only, 30 Hz Poisson events onto the
  EPG/EPGt cells in the 45-deg wedge bin containing the true
  integrated heading theta(116 s) at cue onset (the command is the
  true heading in this simulation). If that bin holds fewer than 2
  cells (the wedge map has one empty bin), the nearest non-empty bin
  is used and the fallback is recorded in the manifest.

Seeds: torch.manual_seed(20000*seed + 1) for the Poisson draws,
torch.manual_seed(10000*seed + 7) for the omega segment magnitudes
(same scheme as B-01). Seeds 0..4.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def omega_schedule(seed):
    g = torch.Generator().manual_seed(10000 * seed + 7)
    segs = []
    for i in range(5):
        mag = float(torch.randint(150, 301, (1,), generator=g))
        segs.append((5.0, (-1) ** i * mag))
    segs.append((25.0, 0.0))
    for i in range(6):
        mag = float(torch.randint(150, 301, (1,), generator=g))
        segs.append((6.0, (-1) ** (i % 2) * mag))
    segs += [(20.0, 0.0), (10.0, 0.0), (10.0, 0.0)]
    total = sum(d for d, _ in segs)
    assert abs(total - 126.0) < 1e-9, total
    return segs


def omega_curve(segs):
    t = 0.0
    omega = np.zeros(126000, dtype=np.float32)
    for dur, w in segs:
        i0 = int(t * 1000)
        i1 = int((t + dur) * 1000)
        omega[i0:i1] = w
        t += dur
    return omega


def true_heading_deg(segs):
    th = 0.0
    for dur, w in segs[:14]:     # up to the start of c4 (5A + c1 + 6c2 + c3 + c4_off = 116 s)
        th += w * dur
    return th % 360.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--populations", default="data/populations.json")
    ap.add_argument("--wedge-map", default="data/wedge-map.json")
    ap.add_argument("--manifest", default="data/manifest.json")
    ap.add_argument("--out-dir", default="data/stimuli")
    a = ap.parse_args()

    pop = json.load(open(a.populations))
    right_idx, left_idx = [], []
    for i, s in zip(pop["PEN"]["idx"], pop["PEN"]["sides"]):
        (right_idx if s == "right" else left_idx).append(i)
    epg_idx = pop["EPG"]["idx"] + pop["EPGt"]["idx"]
    wedge = json.load(open(a.wedge_map))
    bin_of_cell = {c["idx"]: c["bin"] for c in wedge["cells"]}
    bins_with_cells = {}
    for c in wedge["cells"]:
        bins_with_cells.setdefault(c["bin"], []).append(c["idx"])

    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    man = json.load(open(a.manifest))
    stimuli = {}
    for seed in range(a.seeds):
        segs = omega_schedule(seed)
        omega = omega_curve(segs)
        gen = torch.Generator().manual_seed(20000 * seed + 1)
        streams = {}
        for name, cells in (("pen_right", right_idx), ("pen_left", left_idx)):
            events = []
            for ms in range(126000):
                w = omega[ms]
                for k, j in enumerate(cells):
                    r = 2.0 + 40.0 * max(w if name == "pen_right" else -w,
                                         0.0) / 300.0
                    if r <= 0:
                        continue
                    c = int(torch.poisson(torch.tensor(r / 1000.0),
                                          generator=gen))
                    if c:
                        events.append((ms, k, c))
            streams[name] = np.array(events, dtype=np.int32) \
                if events else np.zeros((0, 3), dtype=np.int32)
        # visual cue during c4 (t = 116..126 s)
        theta = true_heading_deg(segs)
        cue_bin = int(theta // 45) % 8
        cells = bins_with_cells.get(cue_bin, [])
        fallback = None
        if len(cells) < 2:
            for d in range(1, 8):
                for b in ((cue_bin + d) % 8, (cue_bin - d) % 8):
                    if len(bins_with_cells.get(b, [])) >= 2:
                        fallback = {"from_bin": cue_bin, "to_bin": b}
                        cells = bins_with_cells[b]
                        cue_bin = b
                        break
                if fallback:
                    break
        cue = []
        i0, i1 = int(116 * 1000), int(126 * 1000)
        cellpos = {j: k for k, j in enumerate(cells)}
        for ms in range(i0, i1):
            for j in cells:
                c = int(torch.poisson(torch.tensor(30.0 / 1000.0),
                                      generator=gen))
                if c:
                    cue.append((ms, cellpos[j], c))
        streams["cue"] = np.array(cue, dtype=np.int32) if cue \
            else np.zeros((0, 3), dtype=np.int32)
        npz = f"{a.out_dir}/stream-seed{seed}.npz"
        np.savez_compressed(npz, **streams)
        h = hashlib.sha256(open(npz, "rb").read()).hexdigest()
        n_events = {k: int(v.shape[0]) for k, v in streams.items()}
        stimuli[f"seed{seed}"] = {
            "file": f"data/stimuli/stream-seed{seed}.npz",
            "sha256": h,
            "n_events": n_events,
            "omega_segments": [[d, w] for d, w in segs],
            "cue": {
                "theta_true_at_cue_deg": theta,
                "bin": cue_bin,
                "n_cells": len(cells),
                "fallback": fallback,
                "cells": cells,
            },
        }
        print(f"seed {seed}: {n_events}, cue theta={theta:.1f} bin={cue_bin} "
              f"n={len(cells)} fallback={fallback}, sha={h[:12]}")

    man["stimuli"] = {
        "session_ms": 126000,
        "drive": {"base_hz": 2.0, "scale_hz": 40.0,
                  "api": "external events (API 2), declared weight "
                         "W_DRIVE = 3 mV/event (frozen at Stage 3)",
                  "pen_right_cells": right_idx,
                  "pen_left_cells": left_idx},
        "cue": {"rate_hz": 30, "phase": "c4 (116..126 s)",
                "wedge_map_sha256": wedge["sha256_of_mapping"]},
        "streams": stimuli,
    }
    json.dump(man, open(a.manifest, "w"), indent=1)
    print("manifest updated")


if __name__ == "__main__":
    main()
