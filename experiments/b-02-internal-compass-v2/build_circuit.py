#!/usr/bin/env python
"""B-02 Stage 0: build the CC-only subgraph of FlyWire FAFB v783.

Subgraph decision (recorded, 2026-10-12):
  node set = the B-01 subgraph MINUS the ALPN drive population, i.e. all
  neurons with flybrain classification `class == CX` (2,878). Rationale:
  the 2026-10-12 audit (B-01 review notes I/II) established that (a) the
  declared B-01 drive (ALPN) does not reach the readout, (b) the heading
  readout is EPG/EPGt (51 cells, inside CX), and (c) the measured
  angular-velocity update is the E-PG -> P-EN -> E-PG shift loop (PEN_a /
  PEN_b, inside CX). The Paff-2015 C1/C2 antennal-lobe EIP cells are NOT
  mapped to v783 types yet, so the ALPN population is excluded as an
  unresolvable drive (pre-registered out of scope). Every population the
  B-02 protocol drives or reads (EPG, EPGt, PEN_a, PEN_b, ER, EL, ExR,
  PEG, Delta7, PFL1-3) is inside the CX set.

Sources (both pinned by sha256; neither file is stored in the repo):
  1. `2025_Connectivity_783.parquet` (15,091,983 proven pairs)
  2. `classification.csv` (snedea/flybrain, 139,255 rows) — provides the
     CX/ALPN split exactly as B-01 used it (same file, same hash), so the
     B-02 node set is exactly "B-01 node set minus ALPN"
  3. `flywire_annotations_783.tsv` (official FAFB v783 annotation,
     flyconnectome/flywire_annotations, Schlegel et al. 2024) — provides
     the official cell types (EPG/EPGt/PEN_a/PEN_b/ER*/EL/ExR*/PEG/
     Delta7/PFL*), side, and arborization/soma centroids; joined on
     `root_id` (the TSV's `supervoxel_id` does NOT match the parquet ids).

Outputs (into --out):
  circuit_cc_b02.npz   src, dst, psd, sign (int arrays), n
  neurons.csv          idx, flywire_id, class, sub_class, side,
                       cell_type, hemibrain_type, ito_lee_hemilineage,
                       pos_x/y/z, soma_x/y/z
  populations.json     named index lists + root_ids (EPG, EPGt, PEN_a,
                       PEN_b, PEN, ER, EL, ExR, PEG, Delta7, PFL1-3, CX)
  wedge-map.json       declared EB geometry (center from EL arborization
                       centroids), per-EPG/EPGt angle + 45-degree bin,
                       mismatch list, mapping sha256
  manifest.json        dataset provenance, hashes, selection rule, counts
"""
import argparse, hashlib, json, os, sys, time, urllib.request
import numpy as np
import pandas as pd

CLAS_URL = ("https://raw.githubusercontent.com/snedea/flybrain/"
            "refs/heads/main/data/classification.csv.gz")
CLAS_SHA = "d941a74188476d60a06dfef7c5130871edbfe9fca77cda571f81f7b9726a184c"

# official-annotation population filters (exact cell_type strings in v783)
POPS = {
    "EPG":   lambda t: t == "EPG",
    "EPGt":  lambda t: t == "EPGt",
    "PEN_a": lambda t: t == "PEN_a(PEN1)",
    "PEN_b": lambda t: t == "PEN_b(PEN2)",
    "ER":    lambda t: bool(t) and t.startswith("ER"),
    "EL":    lambda t: t == "EL",
    "ExR":   lambda t: bool(t) and t.startswith("ExR"),
    "PEG":   lambda t: t == "PEG",
    "Delta7":lambda t: t == "Delta7",
    "PFL1":  lambda t: t == "PFL1",
    "PFL2":  lambda t: t == "PFL2",
    "PFL3":  lambda t: t == "PFL3",
}
# expected counts, from data/audit-manifest-2026-10-12.json (sha-verified run)
EXPECTED = dict(EPG=47, EPGt=4, PEN_a=20, PEN_b=22, ER=278, EL=17, ExR=26,
                PEG=20, Delta7=42, PFL1=14, PFL2=12, PFL3=24)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_classification(args):
    p = args.classification
    if not os.path.exists(p):
        print(f"fetching {CLAS_URL}")
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        urllib.request.urlretrieve(CLAS_URL, p + ".gz")
        import gzip
        with gzip.open(p + ".gz") as fi, open(p, "wb") as fo:
            fo.write(fi.read())
        os.remove(p + ".gz")
    h = sha256(p)
    if h != CLAS_SHA:
        sys.exit(f"classification.csv sha256 mismatch: {h} != {CLAS_SHA}")
    return pd.read_csv(p, dtype={"root_id": str}), h


def load_annotation(args):
    a = pd.read_csv(args.annotation, sep="\t", dtype=str)
    h = sha256(args.annotation)
    if h != args.annotation_sha:
        sys.exit(f"annotation sha256 mismatch: {h} != {args.annotation_sha}")
    cols = ["root_id", "cell_type", "hemibrain_type", "side",
            "ito_lee_hemilineage", "pos_x", "pos_y", "pos_z",
            "soma_x", "soma_y", "soma_z"]
    for c in ("pos_x","pos_y","pos_z","soma_x","soma_y","soma_z"):
        a[c] = pd.to_numeric(a[c], errors="coerce")
    return a, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--classification", required=True)
    ap.add_argument("--annotation", required=True)
    ap.add_argument("--annotation-sha",
                    default="b214970b55d2fbe0853bba536fdcb9e28730f4eb7ab06f600491df795da683cd")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    cl, cl_hash = load_classification(args)
    ann, ann_hash = load_annotation(args)
    pq = pd.read_parquet(args.parquet).astype(
        {"Presynaptic_ID": str, "Postsynaptic_ID": str})
    pq = pq[["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"]]
    pq_hash = sha256(args.parquet)
    print(f"parquet rows: {len(pq):,}; sha256 {pq_hash[:16]}")

    # ---- node set: exactly B-01 subgraph minus ALPN ----
    cx = cl[cl["class"] == "CX"]["root_id"]
    if len(cx) != 2878:
        sys.exit(f"expected 2878 CX neurons, got {len(cx)}")
    nodes = (cl[cl["class"] == "CX"]
             [["root_id", "class", "sub_class", "side"]].rename(
                 columns={"root_id": "flywire_id"})
             .reset_index(drop=True))
    nodes = nodes.merge(ann, left_on="flywire_id", right_on="root_id",
                        how="left", suffixes=("_cl", "_ann")).drop(columns=["root_id"])
    nodes["side"] = nodes["side_ann"].fillna(nodes["side_cl"])  # official side preferred
    nodes = nodes.drop(columns=["side_cl"])
    nodes["idx"] = range(len(nodes))
    id2i = {f: i for i, f in enumerate(nodes["flywire_id"])}
    matched = int(nodes["cell_type"].notna().sum())
    print(f"nodes: {len(nodes)}; annotation cell_type matched {matched}")

    # ---- edges: proven pairs, both endpoints in CX ----
    sel = set(id2i)
    sub = pq[pq["Presynaptic_ID"].isin(sel) & pq["Postsynaptic_ID"].isin(sel)]
    sub = sub.groupby(["Presynaptic_ID", "Postsynaptic_ID"], as_index=False)[
        ["Connectivity", "Excitatory"]].sum()
    edges = np.zeros(len(sub), dtype=[("src", "i4"), ("dst", "i4"),
                                      ("psd", "i4"), ("sign", "i1")])
    edges["src"] = np.array([id2i[s] for s in sub["Presynaptic_ID"]], np.int32)
    edges["dst"] = np.array([id2i[t] for t in sub["Postsynaptic_ID"]], np.int32)
    edges["psd"] = sub["Connectivity"].to_numpy(np.int32)
    edges["sign"] = sub["Excitatory"].to_numpy(np.int16)
    edges = edges[np.lexsort((edges["dst"], edges["src"]))]
    print(f"edges: {len(edges):,}")

    # ---- population masks (official types) ----
    ct = nodes["cell_type"].fillna("")
    pop_idx = {k: np.where(np.vectorize(v)(ct.to_numpy()))[0].tolist()
               for k, v in POPS.items()}
    for k, want in EXPECTED.items():
        got = len(pop_idx[k])
        if got != want:
            sys.exit(f"population {k}: {got} != expected {want} (audit manifest)")
    pop_idx["PEN"] = sorted(set(pop_idx["PEN_a"]) | set(pop_idx["PEN_b"]))
    pop_idx["PFL"] = sorted(set(pop_idx["PFL1"]) | set(pop_idx["PFL2"])
                            | set(pop_idx["PFL3"]))
    pop_idx["CX_all"] = list(range(len(nodes)))
    # every declared population must be a subset of the node set (trivially)
    # and the compass core must be fully present:
    for k in ("EPG", "EPGt", "PEN_a", "PEN_b", "ER", "EL"):
        assert pop_idx[k], k
    pmap = {}
    for k, idx in pop_idx.items():
        # per-cell side labels, aligned with `idx` (drives are split by
        # these); counts kept for quick inspection
        sl = [str(x) for x in nodes["side"][idx]] if len(idx) else []
        sc = {str(k2): int(v2) for k2, v2 in
              nodes["side"][idx].value_counts(dropna=False).items()} \
            if len(idx) else {}
        pmap[k] = dict(n=len(idx), idx=idx,
                       root_ids=[int(x) for x in nodes["flywire_id"][idx]],
                       sides=sl, side_counts=sc)
    with open(os.path.join(args.out, "populations.json"), "w") as f:
        json.dump(pmap, f, indent=1)
    print("populations:", {k: p["n"] for k, p in pmap.items()})

    # ---- wedge map: declared EB geometry, coarse 8 x 45-degree bins ----
    # Center: centroid of the 17 official EL (ring) cells' arborization
    # centroids — their processes trace the EB torus itself. Declared, not
    # fitted.
    el = pop_idx["EL"]
    cy = float(nodes["pos_y"][el].mean())
    cx0 = float(nodes["pos_x"][el].mean())
    cz = float(nodes["pos_z"][el].mean())
    epg_idx = sorted(set(pop_idx["EPG"]) | set(pop_idx["EPGt"]))
    x = nodes["pos_x"].to_numpy(float)[epg_idx]
    y = nodes["pos_y"].to_numpy(float)[epg_idx]
    z = nodes["pos_z"].to_numpy(float)[epg_idx]
    r = np.hypot(x - cx0, y - cy)
    ang = np.degrees(np.arctan2(y - cy, x - cx0)) % 360.0
    # declared bands: EB torus midline radius and depth (from EL centroids);
    # an EPG cell is a mismatch if its centroid falls far outside both.
    el_r = np.hypot(nodes["pos_x"].to_numpy(float)[el] - cx0,
                    nodes["pos_y"].to_numpy(float)[el] - cy)
    el_z = nodes["pos_z"].to_numpy(float)[el]
    r_band = (0.5 * el_r.min(), 2.0 * el_r.max())
    z_band = (el_z.min() - 2000.0, el_z.max() + 2000.0)
    # geometric half of the EB: x < center_x is the left half (angles
    # 90..270 in atan2 sense), x > center_x the right half.
    geo_left = x < cx0
    sides = nodes["side"].to_numpy()[epg_idx]
    side_conflict = [bool(geo_left[i]) != (str(s) == "left")
                     for i, s in enumerate(sides)]
    mism = [i for i, (ri, zi, sc) in enumerate(zip(r, z, side_conflict))
            if sc or not (r_band[0] <= ri <= r_band[1]
                          and z_band[0] <= zi <= z_band[1])]
    bins = [int(a // 45.0) % 8 for a in ang]
    per_bin = {b: [int(epg_idx[k]) for k, b2 in enumerate(bins) if b2 == b]
               for b in range(8)}
    coverage = {b: len(v) for b, v in per_bin.items()}
    wmap = {
        "declared": {
            "center_x": cx0, "center_y": cy, "center_z": cz,
            "center_source": "centroid of the 17 official EL ring-cell "
                             "arborization centroids (declared, not fitted)",
            "angle": "atan2(y-cy, x-cx) in degrees, 0..360; +angle is the "
                     "atan2 sense in v783 coordinates (mapping to "
                     "clockwise-as-viewed-from-above recorded in the "
                     "experiment README)",
            "bin": "floor(angle/45) mod 8 (coarse 8 x 45-degree bins; "
                   "pre-decided before any run)",
            "z_band_um": list(z_band),
            "r_band_um": list(r_band),
        },
        "cells": [
            dict(idx=i, root_id=int(nodes['flywire_id'][i]),
                 type=str(nodes['cell_type'][i]),
                 side=str(nodes['side'][i]),
                 angle_deg=round(float(ang[k]), 1),
                 bin=bins[k],
                 r_um=round(float(r[k]), 1),
                 z_um=round(float(z[k]), 1),
                 mismatch=(k in mism))
            for k, i in enumerate(epg_idx)],
        "per_bin_counts": coverage,
        "bins_empty": [b for b, n in coverage.items() if n == 0],
        "mismatch_idx": mism,
    }
    body = json.dumps(wmap, sort_keys=True)
    wmap["sha256_of_mapping"] = hashlib.sha256(body.encode()).hexdigest()
    with open(os.path.join(args.out, "wedge-map.json"), "w") as f:
        json.dump(wmap, f, indent=1)
    print(f"wedge map: center=({cx0:.0f},{cy:.0f},{cz:.0f}) bins={coverage} "
          f"empty={wmap['bins_empty']} mismatch={len(mism)}")

    # ---- write artifacts ----
    np.savez(os.path.join(args.out, "circuit_cc_b02.npz"),
             src=edges["src"], dst=edges["dst"], psd=edges["psd"],
             sign=edges["sign"], n=len(nodes))
    nodes.to_csv(os.path.join(args.out, "neurons.csv"), index=False)

    circuit_p = os.path.join(args.out, "circuit_cc_b02.npz")
    src_e, dst_e = edges["src"], edges["dst"]
    epg = np.array(sorted(set(pop_idx["EPG"]) | set(pop_idx["EPGt"])))
    pen_a, pen_b = np.array(pop_idx["PEN_a"]), np.array(pop_idx["PEN_b"])
    def count(s, d):
        return int((np.isin(src_e, s) & np.isin(dst_e, d)).sum())
    manifest = {
        "experiment": "b-02-internal-compass-v2",
        "stage": "0 (anatomical preflight)",
        "dataset": "FlyWire FAFB v783 (female adult brain; Dorkenwald et al., "
                   "Nature 2024, https://www.nature.com/articles/s41586-024-07558-y); "
                   "official FAFB v783 annotation (flyconnectome/flywire_annotations, "
                   "Schlegel et al., Nature 2024, DOI 10.1038/s41586-024-07686-5)",
        "files": {
            "connectivity_parquet": {
                "basename": os.path.basename(args.parquet),
                "sha256": pq_hash, "rows": int(len(pq))},
            "classification_csv": {"url": CLAS_URL,
                                   "sha256": cl_hash,
                                   "rows": int(len(cl)),
                                   "note": "same file/hash as B-01; provides the CX/ALPN split"},
            "annotation_tsv": {
                "basename": os.path.basename(args.annotation),
                "sha256": ann_hash, "rows": int(len(ann)),
                "join_key": "root_id (supervoxel_id does not match parquet ids)"},
        },
        "selection": {
            "rule": "node set = flybrain classification class == CX "
                    "(exactly the B-01 subgraph minus ALPN); all proven "
                    "pairs with both endpoints in the set",
            "neurons": int(len(nodes)),
            "edges": int(len(edges)),
            "annotation_matched": matched,
            "annotation_unmatched": int(len(nodes) - matched),
            "sign_balance": {
                "excitatory": int((edges["sign"] > 0).sum()),
                "inhibitory": int((edges["sign"] < 0).sum())},
            "psd_quantiles": {q: int(np.quantile(edges["psd"], q))
                              for q in (0.5, 0.9, 0.95, 0.99)},
            "psd_max": int(edges["psd"].max()),
            "populations": {k: {"n": p["n"]} for k, p in pmap.items()},
        },
        "transform": {
            "script": "build_circuit.py (this directory)",
            "weight_rule": "sign * min(PSD, p95) * 0.275 mV (p95 of THIS "
                           "subgraph's PSD distribution, declared)",
            "subgraph_file_sha256": sha256(circuit_p),
        },
        "elapsed_s": round(time.time() - t0, 1),
    }
    manifest["selection"]["shift_loop"] = {
        "EPG_EPGt_to_PEN_a": count(epg, pen_a),
        "EPG_EPGt_to_PEN_b": count(epg, pen_b),
        "PEN_a_to_EPG_EPGt": count(pen_a, epg),
        "PEN_b_to_EPG_EPGt": count(pen_b, epg),
        "EPG_EPGt_self": count(epg, epg),
        "expected (audit-manifest-2026-10-12)":
            {"EPG_EPGt_to_PEN_a": 313, "EPG_EPGt_to_PEN_b": 269,
             "PEN_a_to_EPG_EPGt": 356, "PEN_b_to_EPG_EPGt": 252},
    }
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps(manifest["selection"], indent=1)[:2000])
    print("done in", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
