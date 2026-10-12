#!/usr/bin/env python3
"""Reproducible counting audit of the FAFB v783 central complex (CC) populations
and of the connectivity claims in `docs/navigation.md` (B-01/B-02 preflight,
2026-10-12).

Run (from any checkout; inputs are NOT committed — they are pinned by sha256
in the output manifest and recorded in its `inputs` section):

    python3 scripts/fafb-cc-audit.py \
        --tsv   <flywire_annotations_783.tsv> \
        --parquet <2025_Connectivity_783.parquet> \
        --out   data/audit-manifest-<date>.json

Inputs
------
1. Official FAFB v783 neuron-type annotation
   (flyconnectome/flywire_annotations, file
   `Supplemental_file1_neuron_annotations.tsv`; 139,248 rows).
   Column names used: root_id, super_class, cell_class, cell_type, side.
   `root_id` is the stable FlyWire ID that joins to the connectivity file
   (the materialization-local `supervoxel_id` does NOT).
2. FAFB v783 connectivity, one row per connection pair
   (FlyWire release; 15,091,983 pair rows).
   Columns used: Presynaptic_ID, Postsynaptic_ID, Connectivity, Excitatory.
   `*_ID` are the stable root_ids.

What it computes (all counts are **pair rows**, not PSD sums, unless noted)
--------------------------------------------------------------------------
- population sizes: EPG, EPGt, PEN_a(PEN1), PEN_b(PEN2), ER* (all ER types,
  with per-type split), EL, ExR*, PEG, Delta7, PFL1/2/3, PFN*, FS*;
- optic-ish -> central pairs  (optic-ish = pre super_class in
  {optic, visual_projection, visual_centrifugal});
- central -> EPG/EPGt pairs, with the top-20 source cell_type breakdown;
- optic-ish -> EPG/EPGt pairs;
- all -> ER* pairs by source super_class, and the central-only subset with
  its top-20 source cell_type breakdown;
- EPG -> ER* and EPGt -> ER* separately, and EPG/EPGt -> central.

Output: a JSON manifest with all counts, the sha256 of each input file, the
exact value sets used as filters, and a wall-time stamp. The manifest is the
authoritative record: prose in the repo documents numbers, the manifest
produces them.
"""
import argparse
import hashlib
import json
import os
import time

import pandas as pd


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tsv", required=True, help="official FAFB v783 annotation TSV")
    ap.add_argument("--parquet", required=True, help="FAFB v783 connectivity parquet")
    ap.add_argument("--out", required=True, help="output manifest path")
    args = ap.parse_args()

    t0 = time.time()

    ann = pd.read_csv(args.tsv, sep="\t", dtype=str)
    ann = ann[["root_id", "super_class", "cell_class", "cell_type", "side"]]
    ann = ann.drop_duplicates("root_id").rename(
        columns={"root_id": "ID", "super_class": "sc", "cell_type": "ct", "side": "side"}
    )

    conn = pd.read_parquet(
        args.parquet, columns=["Presynaptic_ID", "Postsynaptic_ID"]
    )
    conn["Presynaptic_ID"] = conn["Presynaptic_ID"].astype(str)
    conn["Postsynaptic_ID"] = conn["Postsynaptic_ID"].astype(str)

    m = conn.merge(
        ann, left_on="Presynaptic_ID", right_on="ID", how="inner"
    ).rename(columns={"sc": "pre_sc", "ct": "pre_ct", "side": "pre_side"}).drop(columns=["ID"])
    m = m.merge(
        ann, left_on="Postsynaptic_ID", right_on="ID", how="inner"
    ).rename(columns={"sc": "post_sc", "ct": "post_ct", "side": "post_side"}).drop(columns=["ID"])

    OPTIC = ["optic", "visual_projection", "visual_centrifugal"]
    EPG = ["EPG", "EPGt"]
    er_cts = sorted(set(ann["ct"].dropna()[ann["ct"].dropna().str.startswith("ER")]))

    def top20(s: pd.Series) -> dict:
        return s.value_counts().head(20).to_dict()

    out = {
        "audit": "fafb-v783-central-complex-populations-and-connections",
        "date": time.strftime("%Y-%m-%d"),
        "wall_s": round(time.time() - t0, 1),
        "inputs": {
            "tsv": {"path": os.path.basename(args.tsv), "sha256": sha256(args.tsv), "rows": int(len(ann)),
                    "source": "flyconnectome/flywire_annotations — Supplemental_file1_neuron_annotations.tsv (official FAFB v783 neuron-type annotation, CC-BY)"},
            "parquet": {"path": os.path.basename(args.parquet), "sha256": sha256(args.parquet),
                        "pair_rows": int(len(conn)),
                        "source": "FlyWire FAFB v783 connectivity release (one row per connection pair)"},
            "join_key": "root_id (stable FlyWire id); TSV supervoxel_id does NOT match parquet IDs",
            "matched_pair_rows": int(len(m)),
        },
        "filters": {
            "optic-ish (pre super_class)": OPTIC,
            "central (super_class)": "central",
            "EPG (cell_type)": EPG,
            "ER (cell_type startswith 'ER')": er_cts,
        },
        "populations": {
            "EPG": int((ann["ct"] == "EPG").sum()),
            "EPGt": int((ann["ct"] == "EPGt").sum()),
            "PEN_a(PEN1)": int((ann["ct"] == "PEN_a(PEN1)").sum()),
            "PEN_b(PEN2)": int((ann["ct"] == "PEN_b(PEN2)").sum()),
            "ER_total": int(ann["ct"].str.startswith("ER").sum()),
            "ER_by_type": {k: int(v) for k, v in ann["ct"].str.startswith("ER").groupby(ann.loc[ann["ct"].str.startswith("ER"), "ct"]).size().items()},
            "EL": int((ann["ct"] == "EL").sum()),
            "ExR_total": int(ann["ct"].str.startswith("ExR").sum()),
            "PEG": int((ann["ct"] == "PEG").sum()),
            "Delta7": int((ann["ct"] == "Delta7").sum()),
            "PFL1": int((ann["ct"] == "PFL1").sum()),
            "PFL2": int((ann["ct"] == "PFL2").sum()),
            "PFL3": int((ann["ct"] == "PFL3").sum()),
            "PFN_total": int(ann["ct"].str.startswith("PFN").sum()),
            "FS_total": int(ann["ct"].str.startswith("FS").sum()),
            "whole_brain_neurons": int(len(ann)),
        },
        "connections": {
            "optic-ish_to_central": int(((m["pre_sc"].isin(OPTIC)) & (m["post_sc"] == "central")).sum()),
            "central_to_EPG_EPGt": int(((m["pre_sc"] == "central") & (m["post_ct"].isin(EPG))).sum()),
            "central_to_EPG_EPGt_by_source_type": top20(m[(m["pre_sc"] == "central") & (m["post_ct"].isin(EPG))]["pre_ct"]),
            "EPG_self_within_central_to_EPG": int(((m["pre_ct"].isin(EPG)) & (m["post_ct"].isin(EPG)) & (m["pre_sc"] == "central")).sum()),
            "optic-ish_to_EPG_EPGt": int(((m["pre_sc"].isin(OPTIC)) & (m["post_ct"].isin(EPG))).sum()),
            "all_to_ER_by_source_super_class": m[m["post_ct"].str.startswith("ER")]["pre_sc"].value_counts().to_dict(),
            "central_to_ER": int(((m["pre_sc"] == "central") & (m["post_ct"].str.startswith("ER"))).sum()),
            "central_to_ER_by_source_type": top20(m[(m["pre_sc"] == "central") & (m["post_ct"].str.startswith("ER"))]["pre_ct"]),
            "EPG_to_ER": int(((m["pre_ct"] == "EPG") & (m["post_ct"].str.startswith("ER"))).sum()),
            "EPGt_to_ER": int(((m["pre_ct"] == "EPGt") & (m["post_ct"].str.startswith("ER"))).sum()),
            "EPG_EPGt_to_central": int(((m["pre_ct"].isin(EPG)) & (m["post_sc"] == "central")).sum()),
            "PEN_a_to_EPG_EPGt": int(((m["pre_ct"] == "PEN_a(PEN1)") & (m["post_ct"].isin(EPG))).sum()),
            "PEN_b_to_EPG_EPGt": int(((m["pre_ct"] == "PEN_b(PEN2)") & (m["post_ct"].isin(EPG))).sum()),
            "EPG_EPGt_to_PEN_a": int(((m["pre_ct"].isin(EPG)) & (m["post_ct"] == "PEN_a(PEN1)")).sum()),
            "EPG_EPGt_to_PEN_b": int(((m["pre_ct"].isin(EPG)) & (m["post_ct"] == "PEN_b(PEN2)")).sum()),
        },
    }

    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {args.out} ({out['wall_s']}s)")
    for k, v in out["connections"].items():
        if not isinstance(v, dict):
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
