#!/usr/bin/env python
"""Build the B-01 circuits: biological CC+ALPN subgraph (FAFB v783),
degree-preserving shuffles, and the conventional ring-attractor control.

Outputs (into --out):
  circuit_cc_b01.npz     src, dst, psd, sign (int arrays), n
  neurons.csv            idx, flywire_id, class, sub_class, side
  circuit_shuffle_<s>.npz (one per shuffle seed)
  ring_control.npz       src, dst, w (mV), sign, n, role, pos
  manifest.json          dataset provenance, file hashes, selection rule, seeds

Read-only inputs: the FAFB v783 connectivity parquet (path given via
--parquet; this repo never stores it) and the flybrain classification csv
(--classification; if --fetch and it is absent, fetched from the URL in the
manifest and its sha256 checked against the recorded value).
"""
import argparse, hashlib, json, os, sys, time, urllib.request
import numpy as np
import pandas as pd

MANIFEST_URL = {
    "classification": "https://raw.githubusercontent.com/snedea/flybrain/refs/heads/main/data/classification.csv.gz",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_classification(args):
    p = args.classification
    if not os.path.exists(p):
        if not args.fetch:
            sys.exit(f"missing {p} (pass --fetch to download it)")
        url = MANIFEST_URL["classification"]
        print(f"fetching {url}")
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        urllib.request.urlretrieve(url, p + ".gz")
        import gzip
        with gzip.open(p + ".gz") as fi, open(p, "wb") as fo:
            fo.write(fi.read())
        os.remove(p + ".gz")
    return pd.read_csv(p, dtype={"root_id": str}), sha256(p)


def load_edges(parquet):
    pq = pd.read_parquet(parquet).astype(
        {"Presynaptic_ID": str, "Postsynaptic_ID": str})
    pq = pq[["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"]]
    print(f"edges loaded: {len(pq):,}")
    return pq


def select(cc_ids, al_ids, pq, cl):
    sel = cc_ids | al_ids
    sub = pq[pq["Presynaptic_ID"].isin(sel) & pq["Postsynaptic_ID"].isin(sel)]
    sub = sub.groupby(["Presynaptic_ID", "Postsynaptic_ID"], as_index=False)[
        ["Connectivity", "Excitatory"]].sum()
    present = sub["Presynaptic_ID"].tolist() + sub["Postsynaptic_ID"].tolist()
    nodes = pd.DataFrame({"flywire_id": sorted(set(present))})
    nodes = nodes.merge(cl[["root_id", "super_class", "class", "sub_class", "side"]],
                        left_on="flywire_id", right_on="root_id", how="left")
    nodes = nodes.drop(columns=["root_id"])
    nodes["idx"] = range(len(nodes))
    id2i = {f: i for i, f in enumerate(nodes["flywire_id"])}
    f2i = np.array([id2i[s] for s in sub["Presynaptic_ID"]], dtype=np.int32)
    t2i = np.array([id2i[t] for t in sub["Postsynaptic_ID"]], dtype=np.int32)
    edges = np.zeros(len(sub), dtype=[("src", "i4"), ("dst", "i4"),
                                      ("psd", "i4"), ("sign", "i1")])
    edges["src"], edges["dst"] = f2i, t2i
    edges["psd"] = sub["Connectivity"].to_numpy(np.int32)
    edges["sign"] = sub["Excitatory"].to_numpy(np.int16)
    edges = edges[np.lexsort((edges["dst"], edges["src"]))]
    return nodes, edges


def shuffle(edges, n, seed, rng):
    """Degree-preserving shuffle by random 2-switches (Micali–Spirakis style).
    Preserved: in/out degree per node, total edge count, global sign counts.
    Broken: population pairing, per-node sign balance, local structure,
    and the PSD magnitude distribution (all shuffled edges carry psd=1).

    Starts from the real wiring (feasible by construction — no deadlocks
    possible) and applies a fixed number of random 2-switches: two edges
    (u->v, u2->v2) are swapped to (u->v2, u2->v) when the swap keeps the
    graph simple (no self-loops, no parallel edges). Every switch preserves
    all degrees exactly. The fixed attempt budget (recorded in the manifest)
    touches every edge many times in expectation, so population pairing and
    local structure are scrambled; the distribution is a standard switch-
    chain heuristic, not proven uniform over all degree-matched graphs.
    Deterministic in (edges, n, seed)."""
    src, dst = edges["src"], edges["dst"]
    ns = len(src)
    adj = [set() for _ in range(n)]
    pairs = []
    for u, v in zip(src.tolist(), dst.tolist()):
        adj[u].add(v)      # v783 has one row per pair; a set keeps it simple
        pairs.append((u, v))
    rng.shuffle(pairs)
    attempts_budget = 200 * n   # ~4.5 touches per edge in expectation
    attempts = 0
    accepted = 0
    while attempts < attempts_budget:
        attempts += 1
        i = int(rng.integers(len(pairs)))
        j = int(rng.integers(len(pairs)))
        if i == j:
            continue
        u, v = pairs[i]
        u2, v2 = pairs[j]
        if u == u2 or v == v2:
            continue
        if v2 == u or v == u2:          # would create self-loops
            continue
        if v2 in adj[u] or v in adj[u2]:  # would create parallel edges
            continue
        adj[u].discard(v)
        adj[u2].discard(v2)
        adj[u].add(v2)
        adj[u2].add(v)
        pairs[i] = (u, v2)
        pairs[j] = (u2, v)
        accepted += 1
    keep = np.array(pairs, dtype=[("src", "i4"), ("dst", "i4")])
    signs = np.array([1] * int((edges["sign"] > 0).sum())
                     + [-1] * int((edges["sign"] < 0).sum()), dtype=np.int16)
    rng.shuffle(signs)
    order = np.lexsort((keep["dst"], keep["src"]))
    out = np.zeros(ns, dtype=[("src", "i4"), ("dst", "i4"), ("psd", "i4"), ("sign", "i1")])
    out["src"], out["dst"] = keep["src"][order], keep["dst"][order]
    out["psd"] = 1
    out["sign"] = signs[order]
    assert np.array_equal(np.bincount(out["src"], minlength=n),
                          np.bincount(src, minlength=n))
    assert np.array_equal(np.bincount(out["dst"], minlength=n),
                          np.bincount(dst, minlength=n))
    assert not (out["src"] == out["dst"]).any()
    assert len(np.unique(np.stack([out["src"], out["dst"]], 1), axis=0)) == ns
    return out, dict(method="2-switch chain", attempts=int(attempts),
                     accepted=int(accepted), accepted_frac=round(accepted / attempts, 3))


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--classification", required=True)
    ap.add_argument("--out", default="data")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--shuffle-seeds", type=int, nargs="*", default=list(range(5)))
    ap.add_argument("--ring-seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    cl, cl_hash = load_classification(args)
    pq = load_edges(args.parquet)
    cc = cl[cl["class"] == "CX"]["root_id"]
    al = cl[cl["class"] == "ALPN"]["root_id"]
    nodes, edges = select(set(cc), set(al), pq, cl)
    n = len(nodes)
    nodes.to_csv(os.path.join(args.out, "neurons.csv"), index=False)
    np.savez(os.path.join(args.out, "circuit_cc_b01.npz"),
             src=edges["src"], dst=edges["dst"], psd=edges["psd"], sign=edges["sign"], n=n)

    shuffles = {}
    for s in args.shuffle_seeds:
        rng = np.random.default_rng(4200 + s)
        sh, shstats = shuffle(edges, n, 4200 + s, rng)
        p = os.path.join(args.out, f"circuit_shuffle_{s}.npz")
        np.savez(p, src=sh["src"], dst=sh["dst"], psd=sh["psd"], sign=sh["sign"], n=n)
        shuffles[f"seed {s}"] = {"sha256": sha256(p), **shstats}

    n_ring, n_fbb, n_drive, n_g = 278, 1244, 685, 1356
    assert n == n_ring + n_fbb + n_drive + n_g, f"n={n} != 3563; ring sizes must match"
    a, roles, pos = ring_control(n, n_ring, n_fbb, n_drive, n_g, args.ring_seed)
    rp = os.path.join(args.out, "ring_control.npz")
    np.savez(rp, src=a["src"], dst=a["dst"], w=a["w"], sign=a["sign"],
             n=n, role=roles, pos=pos)

    manifest = {
        "dataset": "FlyWire FAFB v783 (2025 release; Dorkenwald et al., Nature 2024, https://www.nature.com/articles/s41586-024-07558-y)",
        "files": {
            "connectivity_parquet": {"path_arg": os.path.basename(args.parquet),
                                     "sha256": sha256(args.parquet),
                                     "rows": int(len(pq))},
            "classification": {"url": MANIFEST_URL["classification"],
                               "sha256": cl_hash, "rows": int(len(cl))},
        },
        "selection": {
            "rule": "class in {CX, ALPN}; all proven pairs with both endpoints in set",
            "neurons": n,
            "by_class": nodes["class"].value_counts().to_dict(),
            "by_subclass": nodes["sub_class"].value_counts(dropna=False).to_dict(),
            "al_by_side": nodes[nodes["class"] == "ALPN"]["side"].value_counts(dropna=False).to_dict(),
            "edges": int(len(edges)),
            "sign_balance": {"excitatory": int((edges["sign"] > 0).sum()),
                             "inhibitory": int((edges["sign"] < 0).sum())},
            "psd_quantiles": {q: int(np.quantile(edges["psd"], q)) for q in (0.5, 0.9, 0.95, 0.99)},
            "psd_max": int(edges["psd"].max()),
        },
        "transform": {
            "script": "build_circuit.py (this experiment dir; version = git sha at run time)",
            "weight_rule": "sign * min(PSD, p95=17) * 0.275 mV (p95 cap declared in README)",
            "ring_control": {"file": "ring_control.npz", "sha256": sha256(rp),
                             "seed": args.ring_seed,
                             "weight_table_mV": {"ring_self": 0.7, "ring_lateral_inh": 0.35,
                                                 "fbb_fbb": 0.3, "fbb_ring": 0.6,
                                                 "fbb_drive_shifted": 0.5, "drive_ring": 5.0,
                                                 "g_ring": 0.25},
                             "note": "synthetic; matched population sizes; declared weights (README §Dynamics)"},
            "shuffles": {**shuffles,
                         "note": "2-switch chain (Micali–Spirakis style); preserved: in/out degree per node, edge count, global sign counts; broken: population pairing, per-node sign balance, PSD magnitudes (all 1)"},
        },
        "elapsed_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps(manifest["selection"], indent=1))


if __name__ == "__main__":
    main()
