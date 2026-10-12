#!/usr/bin/env python
"""B-01 run: one (variant, seed) session — pre-registered protocol,
see README.md. Writes results/<variant>-seed<s>.json.

Variant circuit sources (data/):
  bio     circuit_cc_b01.npz   (FlyWire FAFB v783 CC+ALPN)
  shuffle circuit_shuffle_<s>.npz (degree-preserving shuffle of the same set)
  ring    ring_control.npz     (conventional ring attractor, matched sizes)

Drives (declared, identical across variants): velocity Poisson into the
antennal-lobe / drive populations, tonic background on EL ring cells,
visual cue Poisson into the 8 EL cells nearest the true heading.
"""
import argparse, json, os, sys, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lif import LIFNet

DT = 1.0          # ms
W_SYN = 0.275     # mV per PSD unit (Shiu et al. standard)
PSD_CAP = 17      # p95 of the subgraph PSD distribution (declared)
W_DRIVE = 15.0    # mV per Poisson drive event
W_CUE = 15.0
TONIC_EL = 6.0    # mV steady-state background on EL cells
CUE_HZ = 30.0
CUE_K = 8

WINDOW = 250.0    # ms
TOTAL_S = 126.0
PHASES = {
    "A":  (0.0, 25.0),
    "c1": (25.0, 50.0),
    "c2": (50.0, 86.0),
    "c3": (86.0, 106.0),
    "c4_off": (106.0, 116.0),
    "c4": (116.0, 126.0),
}


def wrap180(a):
    return (a + 180) % 360 - 180


def omega_schedule(rng, variant_seed):
    """(t0, t1, omega) segments per README protocol."""
    segs = []
    for k in range(5):  # calibration A
        s = 1 if k % 2 == 0 else -1
        segs.append((5 * k, 5 * (k + 1), s * rng.uniform(150, 300)))
    # c1: 25-50, omega 0
    segs.append((25, 50, 0.0))
    for k in range(6):  # c2: 6x6, alternating sign
        s = 1 if k % 2 == 0 else -1
        segs.append((50 + 6 * k, 50 + 6 * (k + 1), s * rng.uniform(150, 300)))
    segs.append((86, 106, 0.0))
    segs.append((106, 116, 0.0))
    segs.append((116, 126, 0.0))
    return segs


def cue_on(t):
    return (25.0 <= t < 50.0) or (50.0 <= t < 86.0) or (t >= 116.0)


def load_circuit(args, data):
    el_mask = None
    if args.variant == "bio":
        z = np.load(os.path.join(data, "circuit_cc_b01.npz"))
        src, dst, psd, sign = z["src"], z["dst"], z["psd"], z["sign"]
        n = int(z["n"])
        w = (sign * np.clip(psd, 1, PSD_CAP) * W_SYN).astype(np.float32)
        cl = pd.read_csv(os.path.join(data, "neurons.csv"))
        sub_cls = np.asarray(cl["sub_class"].to_list())
        cls = np.asarray(cl["class"].to_list())
        side = np.asarray(cl["side"].to_list())
        el = np.where(sub_cls == "ring_neuron")[0]
        pos = np.where((cls == "ALPN") & (side == "left"))[0]
        neg = np.where((cls == "ALPN") & (side == "right"))[0]
        file = "circuit_cc_b01.npz"
    elif args.variant == "shuffle":
        z = np.load(os.path.join(data, f"circuit_shuffle_{args.seed}.npz"))
        src, dst, psd, sign = z["src"], z["dst"], z["psd"], z["sign"]
        n = int(z["n"])
        w = (sign * np.clip(psd, 1, PSD_CAP) * W_SYN).astype(np.float32)
        cl = pd.read_csv(os.path.join(data, "neurons.csv"))
        sub_cls = np.asarray(cl["sub_class"].to_list())
        cls = np.asarray(cl["class"].to_list())
        side = np.asarray(cl["side"].to_list())
        el = np.where(sub_cls == "ring_neuron")[0]
        pos = np.where((cls == "ALPN") & (side == "left"))[0]
        neg = np.where((cls == "ALPN") & (side == "right"))[0]
        file = f"circuit_shuffle_{args.seed}.npz"
    elif args.variant == "ring":
        z = np.load(os.path.join(data, "ring_control.npz"))
        src, dst, w = z["src"], z["dst"], z["w"].astype(np.float32)
        n = int(z["n"])
        roles = z["role"]
        el = np.where(roles == "ring")[0]
        pos = np.where(roles == "drive_pos")[0]
        neg = np.where(roles == "drive_neg")[0]
        file = "ring_control.npz"
    else:
        sys.exit(f"unknown variant {args.variant}")
    return dict(src=src, dst=dst, w=w, n=n, el=el, pos=pos, neg=neg, file=file)


def ridge(X, Y, alpha=1.0):
    mu = X.mean(0)
    sd = X.std(0)
    sd[sd == 0] = 1.0
    Xs = (X - mu) / sd
    A = Xs.T @ Xs + alpha * np.eye(Xs.shape[1])
    W = np.linalg.solve(A, Xs.T @ Y)
    return W, mu, sd


def decode(W, mu, sd, rates, t_centers):
    Xs = (rates - mu) / sd
    Y = Xs @ W  # (nwin, 2)
    h = np.degrees(np.arctan2(Y[:, 0], Y[:, 1]))
    return h, Y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["bio", "shuffle", "ring"], required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    rng = np.random.default_rng(10000 * args.seed + 7)
    segs = omega_schedule(rng, args.seed)
    C = load_circuit(args, args.data)
    n = C["n"]
    el = torch.as_tensor(C["el"], dtype=torch.int64)
    n_el = len(el)

    tonic = np.zeros(n, np.float32)
    tonic[C["el"]] = TONIC_EL
    net = LIFNet(C["src"], C["dst"], C["w"], n, tonic=tonic)

    n_steps = int(TOTAL_S * 1000 / DT)
    n_win = int(TOTAL_S * 1000 / WINDOW)
    el_counts = torch.zeros(n_win, n_el)
    el_ids = torch.as_tensor(C["el"], dtype=torch.int64)
    pos_ids = torch.as_tensor(C["pos"], dtype=torch.int64)
    neg_ids = torch.as_tensor(C["neg"], dtype=torch.int64)

    H_true = 0.0
    h_true_hist = np.zeros(n_steps)
    cue_target = torch.zeros(0, dtype=torch.int64)
    cue_last_update = -1.0
    decW = None  # trained after the session; cue targeting below is
    # geometric until then (declared: during the run the cue targets the 8 EL
    # cells geometrically nearest the true heading for all variants — the
    # decoder-preferred variant is not used because the decoder needs the run
    # itself; recorded as an assumption in the report)

    ring_pos = None
    if args.variant == "ring":
        rz = np.load(os.path.join(args.data, "ring_control.npz"))
        ring_pos = (rz["pos"], rz["role"])

    def el_near_true(h_true):
        p = int((np.radians(h_true) / (2 * np.pi)) * 278) % 278
        if args.variant == "ring":
            pos_a, role_a = ring_pos
            ring_idx = np.where(role_a == "ring")[0]
            rp = np.asarray(pos_a[ring_idx], dtype=np.int64)
            d = np.minimum(np.abs(rp - p), 278 - np.abs(rp - p))
            return torch.as_tensor(ring_idx[np.argsort(d)[:CUE_K]],
                                   dtype=torch.int64)
        # biological/shuffle: 8 EL ring cells geometrically nearest via the
        # ring's own position order (EL cells are indexed in anatomical order,
        # one per torus position — declared approximation)
        d = np.minimum(np.abs(np.arange(n_el) - p), n_el - np.abs(np.arange(n_el) - p))
        return el[torch.as_tensor(np.argsort(d)[:CUE_K], dtype=torch.int64)]

    for step in range(n_steps):
        t = (step + 1) * DT / 1000.0
        omega = 0.0
        for (a, b, om) in segs:
            if a <= t < b:
                omega = om
                break
        H_true = (H_true + omega * DT / 1000) % 360
        h_true_hist[step] = H_true

        # external drives
        r_pos = 2.0 + 60.0 * max(omega, 0.0) / 300.0
        r_neg = 2.0 + 60.0 * max(-omega, 0.0) / 300.0
        src_parts, cnt_parts = [], []
        if len(pos_ids) > 0:
            c = torch.poisson(torch.full((len(pos_ids),), r_pos * DT / 1000))
            src_parts.append(pos_ids); cnt_parts.append(c)
        if len(neg_ids) > 0:
            c = torch.poisson(torch.full((len(neg_ids),), r_neg * DT / 1000))
            src_parts.append(neg_ids); cnt_parts.append(c)
        if cue_on(t):
            if abs(t - cue_last_update) > 0.1 or cue_last_update < 0:
                cue_target = el_near_true(H_true)
                cue_last_update = t
            c = torch.poisson(torch.full((len(cue_target),), CUE_HZ * DT / 1000))
            src_parts.append(cue_target); cnt_parts.append(c)
        ext = (torch.cat(src_parts) if src_parts else None,
               torch.cat(cnt_parts) if cnt_parts else None)

        idx = net.step(ext)
        if idx is not None:
            c_all = torch.bincount(idx, minlength=n)
            w = int(t * 1000 / WINDOW)
            if w < n_win:
                el_counts[w] += c_all[el]

    # ---- decoder on phase A ----
    rates = (el_counts.numpy() / (WINDOW / 1000.0)).astype(np.float64)
    win_centers = (np.arange(n_win) + 0.5) * WINDOW / 1000.0
    a0, a1 = PHASES["A"]
    ai = (win_centers >= a0) & (win_centers < a1)
    Ai = np.where(ai)[0]
    train = Ai[0::2]
    hold = Ai[1::2]
    hA = np.array([h_true_hist[int(win_centers[i] * 1000)] for i in train])
    hh = np.array([h_true_hist[int(win_centers[i] * 1000)] for i in hold])
    Xtr = rates[train]
    Ytr = np.stack([np.sin(np.radians(hA)), np.cos(np.radians(hA))], 1)
    Wd, mu, sd = ridge(Xtr, Ytr, alpha=1.0)
    h_dec, Yall = decode(Wd, mu, sd, rates, win_centers)

    # held-out decoder quality
    Yho = np.stack([np.sin(np.radians(hh)), np.cos(np.radians(hh))], 1)
    pred = rates[hold] @ Wd
    ss_res = ((pred - Yho) ** 2).sum()
    ss_tot = ((Yho - Yho.mean(0)) ** 2).sum()
    r2 = 1 - ss_res / max(ss_tot, 1e-12)
    mae_hold = float(np.abs(wrap180(h_dec[hold] - hh)).mean())

    def phase_stats(pname):
        a0, a1 = PHASES[pname]
        i0, i1 = int(a0 * 1000 / WINDOW), int(a1 * 1000 / WINDOW)
        h = h_dec[i0:i1]
        ht = np.array([h_true_hist[int((a0 + k * WINDOW / 1000) * 1000)]
                       for k in range(i1 - i0)])
        err = wrap180(h - ht)
        h_un = np.unwrap(np.radians(h))
        slope = float(np.polyfit(np.arange(len(h)) * WINDOW / 1000, h_un, 1)[0])
        rate = float(rates[i0:i1].mean())
        return dict(
            drift_deg_s=float(np.degrees(slope)),
            abs_drift_deg_s=float(abs(np.degrees(slope))),
            stability_frac=float((np.abs(err) <= 15).mean()),
            mean_abs_err_deg=float(np.abs(err).mean()),
            el_mean_hz=rate,
            silent=bool(rate < 0.1),
        )

    out = dict(
        variant=args.variant, seed=args.seed,
        circuit_file=C["file"],
        n_neurons=n, n_el=int(n_el),
        torch=torch.__version__, python=sys.version.split()[0],
        total_spikes=int(net.total_spikes),
        elapsed_s=round(time.time() - t0, 1),
        decoder=dict(held_out_R2=float(r2), held_out_mae_deg=mae_hold,
                     n_train_windows=int(len(train)), n_hold_windows=int(len(hold))),
    )
    for p in ("c1", "c2", "c3"):
        out[p] = phase_stats(p)

    # c2 per-segment error
    seg_errs = []
    for (a, b, om) in segs[6:12]:  # the 6 rotation segments of phase c2
        i0, i1 = int(a * 1000 / WINDOW), int(b * 1000 / WINDOW)
        ht = np.array([h_true_hist[int((a + k * WINDOW / 1000) * 1000)]
                       for k in range(i1 - i0)])
        err = wrap180(h_dec[i0:i1] - ht)
        seg_errs.append(float(np.abs(err).mean()))
    out["c2"]["segment_errs_deg"] = [round(e, 2) for e in seg_errs]

    # c4: recovery from cue onset
    i0 = int(116.0 * 1000 / WINDOW)
    i1 = int(126.0 * 1000 / WINDOW)
    ht4 = np.array([h_true_hist[int((116.0 + k * WINDOW / 1000) * 1000)]
                    for k in range(i1 - i0)])
    err4 = np.abs(wrap180(h_dec[i0:i1] - ht4))
    rec = None
    for k in range(len(err4) - 7):
        if (err4[k:k + 8] <= 15).all():
            rec = float(k * WINDOW / 1000)
            break
    out["c4"] = dict(
        recovery_s=rec,
        final_err_deg=float(err4[-1]),
        err_series_deg=[round(float(e), 1) for e in err4[::2]],
        pre_cue_err_deg=float(err4[0]),
    )
    out["c3"] = phase_stats("c3")
    out["c4_drift_phase"] = phase_stats("c4_off")

    p = os.path.join(args.out, f"{args.variant}-seed{args.seed}.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
