# Circuit: fabf-cc-b02

The central-complex (CC) subcircuit of the FlyWire FAFB v783 female adult
brain — the substrate of `experiments/b-02-internal-compass-v2/`. Exactly
the B-01 subgraph **minus** the antennal-lobe projection population: the
2026-10-12 audit (B-01 review notes I/II) relocated the compass to the
EPG/EPGt readout and the P-EN shift loop, both inside the CC, and the
antennal-lobe EIP (C1/C2, Paff 2015) cells are not yet mapped to v783
types, so the ALPN set (685) is excluded as an unresolvable drive.

| Field | Value |
|---|---|
| Dataset | FlyWire FAFB v783 (female adult brain; Dorkenwald et al., *Nature* 2024, https://www.nature.com/articles/s41586-024-07558-y), 2025 release files, joined to the official FAFB v783 annotation (`flyconnectome/flywire_annotations`, Schlegel et al., *Nature* 2024, DOI 10.1038/s41586-024-07686-5) |
| Source files | `2025_Connectivity_783.parquet` (15,091,983 proven pairs; sha256 in `experiments/b-02-internal-compass-v2/data/manifest.json`) + `classification.csv` (snedea/flybrain; same file/hash as B-01, which is what makes this node set exactly "B-01 minus ALPN") + `flywire_annotations_783.tsv` (official annotation; joined on `root_id` — the TSV `supervoxel_id` does not match the parquet ids) |
| Selection | every neuron with `class == CX` (2,878 — 278 EL ring, 1,244 FBB columnar, 611 PL/PFL tangential, 745 CX-unlabeled); all proven pairs with both endpoints in the set (300,521). Population masks from the official annotation `cell_type`: EPG 47 + EPGt 4 (heading readout), PEN_a(PEN1) 20 + PEN_b(PEN2) 22 (shift loop), ER 278 (input relay), EL 17, ExR 26, PEG 20, Delta7 42, PFL1–3 50 (steering, reserved for B-03) |
| Edges | 300,521 directed, one row per pair; sign ±1 from the release's predicted-transmitter column; magnitude = PSD count. The Turner-Evans shift loop is reproduced in this subgraph exactly as in the whole-brain audit: EPG/EPGt→PEN_a 313 / PEN_b 269, PEN_a→EPG/EPGt 356 / PEN_b→EPG/EPGt 252, EPG/EPGt self 535 (see manifest `shift_loop`) |
| Derived files | `data/circuit_cc_b02.npz` + `data/neurons.csv` (built by `build_circuit.py`; the source parquet/annotation are never copied into the repo), `data/populations.json` (named index lists + root_ids + sides for every declared population), `data/wedge-map.json` (declared EB center from the 17 EL ring-cell arborization centroids; per-EPG/EPGt angle around that center, coarse 8×45° bins, 5 mismatch cells, mapping sha256) — all hashes in `data/manifest.json` |
| Dynamics | frozen Shiu et al. LIF standard (see `docs/substrate.md`); the weight rule and all added drives are declared per run (see the experiment README) — not properties of this file |
| Claim ceiling | wiring is measured; sign is a predicted label; efficacies are one global normalization; P-EN drive and visual recalibration are added interfaces (no velocity afferent source is established in v783). Supports compass-*mechanism* questions under declared dynamics, not whole-brain emulation (`docs/navigation.md` §1–§2) |
