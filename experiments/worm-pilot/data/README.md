# Data — Cook 2019 supplementary matrices (raw downloads)

Machine-readable releases of Cook et al. 2019, *Nature* 571:63–71
(doi:10.1038/s41586-019-1352-7, open access, PMC6889226). Re-downloaded
from the publisher's media host on **2026-10-12 (UTC)**; all URLs
returned HTTP 200 at download time. Total size ~11 MB (the brief's
≤1 GB / ≤2 GB budgets are comfortably met).

| File | SI sheet | Upstream URL (media.springernature.com) | Size (bytes) | SHA-256 |
|---|---|---|---|---|
| `Cook2019_SI6_raw-adjacency.xlsx` | SI 6 "Synapse Adjacency Matrices" (raw EM only) | `https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-019-1352-7/MediaObjects/41586_2019_1352_MOESM6_ESM.xlsx` | 2,650,751 | `cff825a6be2c110a78bbde766352fa8c515781c035df701af6d507e064a11073` |
| `Cook2019_SI7_synapse-lists.xlsx` | SI 7 "List of Synapses" | `.../41586_2019_1352_MOESM7_ESM.xlsx` | 1,381,843 | `e72b5ff3dba07d12cc4c11f814b1b4a5d1969a8e1fb5d3a954dc9cecf833a1b1` |
| `Cook2019_SI8_cell-lists.xlsx` | SI 8 "Cell Lists" | `.../41586_2019_1352_MOESM8_ESM.xlsx` | 27,554 | `cf442a285c43f6fd95fbaa6b50b3e0696187cdf39242377d95a5446354ae2244` |
| `Cook2019_SI9_connectome-matrices.xlsx` | SI 9 "Connectome Adjacency Matrices" (the matrices used in the paper's figures) | `.../41586_2019_1352_MOESM9_ESM.xlsx` | 4,172,457 | `86d3f24c77752b1f7df4b26cdf9583461fe7e8fc76f86d2d81b3879cdaa0e389` |

(Each `.../` is the same path as the first row:
`https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-019-1352-7/MediaObjects/`.)

Derived, reproducible products (do not edit by hand; regenerate with
`src/parse_cook2019.py`):

- `c-elegans-edges-herm.json` / `c-elegans-edges-male.json` —
  neuron-to-neuron edge lists `{pre, post, w, kind}`; `w` = total EM
  serial sections of connectivity (the released weight), `kind` ∈
  {`chem`, `gap_sym` (undirected, stored once), `gap_asym` (directed)}.
  **2026-10-13 regeneration**: 3,669 `chem` + 1,089 `gap_sym` + 1,089
  `gap_asym` = 5,847 records (herm); 3,986 + 1,278 + 1,278 = 6,542
  (male). The 2026-10-12 v1 files are replaced (their counts, 3,618 /
  2,130 and 3,986 / 2,519, came from a positional parse of sparse
  spreadsheet rows — see the correction note in
  `circuits/c-elegans-substrate.md`); the old files remain in git
  history at the 2026-10-12 commit.
- `c-elegans-neurons-herm.json` / `c-elegans-neurons-male.json` — the
  neuron names that carry at least one neuron–neuron edge (the
  simulation node list). herm 300; male 378 (was 380 under v1).
- `c-elegans-inventory.json` — all parse statistics (rows seen/skipped,
  diagonal entries zeroed, symmetry disagreements, edge counts per
  sheet) used by `circuits/c-elegans-substrate.md`.


## Canonical electrical graph (v3, 2026-10-13, review round 5)

The two SI9 gap-junction sheets ("symmetric", "asymmetric") are
alternative representations of the **same physical junctions**, not
additive edge classes (verified: every asymmetric pair occurs in the
symmetric sheet as the same unordered pair with the identical weight —
herm 1,086/1,086, 0 mismatches; male 1,276/1,276, 1 mismatch
(VB06/VB07: sym 5 vs asym 1); a few symmetric-only pairs: herm 3
(DD06/PDB, M2R/M3R, M4/M5), male 1 (M1R/M2R); corroborated by the SI7
synapse list, which lists each physical synapse exactly once with
partner = 1, and by the paper's undirected depiction). The v2
simulation double-counted the electrical conductance (2,178 records
herm); v3 uses one canonical undirected layer.

- `c-elegans-electrical-herm.json` / `c-elegans-electrical-male.json`
  — **the** electrical graph: one undirected record per physical
  junction `{pre, post, w, in_sym_sheet, in_asym_sheet, em_verified,
  si7_sections_sym, si7_sections_asym}` (pre < post; `w` = symmetric
  sheet section count, the preferred weight; `em_verified` = listed
  in the SI7 synapse list). herm 1,089 (939 EM-verified, 150
  extrapolation-only; 2 in the graph but not EM-verified); male 1,278.
  Regenerate: `python src/parse_cook2019.py`.
- The `c-elegans-edges-<sex>.json` `gap_sym` / `gap_asym` records are
  retained for provenance only; `src/sim.py` no longer builds the
  conductance matrix from them (it loads the canonical file). The
  inventory now carries the sheet-relationship statistics and the SI7
  cross-check numbers.

## Background-drive models (v3)

`src/sim.py` `WormNet.step()`: `cfg["bg_propagate"] = False`
(**Model A**, default) — background Poisson events are pure external
current; only genuine threshold-crossing spikes propagate.
`bg_propagate = True` (**Model B**) — the historical v2 behaviour, in
which every background event was *also* enqueued as a presynaptic
spike and propagated through the neuron's chemical output fan-out
even when the neuron never crossed threshold. `src/test_bg_models.py`
demonstrates the difference on a minimal network and asserts the
background event trains are byte-identical across models. Every run
record carries the model label.

## v3 results (review round 5 minimal re-run; 160 runs, frozen
parameters)

- `../results-v3-canonical.json` — canonical substrate, Model A,
  both variants (80 runs). 5 ms: silent network (0 rest spikes in all
  wirings); 50 ms: sparse (all-neuron rest ≈ 0.17–0.20 Hz), paired
  contrasts 0.0 in every group/wiring.
- `../results-v3-modelB-50ms.json` — canonical substrate, Model B,
  50 ms only (40 runs). Alive (measured rest 2.97 Hz vs ≈ 1.78 in all
  shuffles); ASH response contrast +0.040 Hz (4/5 seeds positive,
  shuf-44 at or above the measured mean).
- `timecourse-50ms-v3.json` — 40 runs (Model A, 50 ms), same window
  layout as `timecourse-50ms.json` (v2 substrate): paired contrasts
  0.0 in every window and wiring.
- `paired-stim-example-{5ms,50ms}-v3.json` — v3-substrate versions of
  the paired-input artifacts (the event trains are substrate-
  independent by the seed rule; sha256 recorded per file).
- `../config-5ms-v2-dual-electrical.json` /
  `../config-50ms-v2-dual-electrical.json` — the frozen v2 configs
  (renamed, unmodified); `../config-5ms.json` / `../config-50ms.json`
  — v3 (same frozen parameters, `bg_propagate: false`, substrate
  label); `../config-50ms-v3-modelB.json` — the Model B comparison
  config.

Round-4 verdicts on the v2 substrate (the +0.090 Hz 5-s and the
+1.75 Hz during-pulse command-pool contrasts) **do not survive** the
corrected substrate under either background model — see the report's
third addendum. All v1/v2 artifacts above (`results.json`,
`results-exact.json`, `timecourse-50ms.json`, `paired-stim-effect.
json`, calibration logs, `paired-stim-example-{5ms,50ms}.json`) are
frozen and untouched.

Analysis artifacts (2026-10-13, review round 4; regenerate with the
named scripts — never edit by hand):

- `paired-stim-example-{5ms,50ms}.json` — measured vs shuf-42
  background event lists for one (sim seed, variant), asserted
  byte-identical, with sha256 (`src/run_campaign.py`).
- `paired-stim-effect.json` — the corrected PRIMARY metric,
  recomputed from the frozen `../results-exact.json` without rerun:
  per (wiring, sim seed, group) `stim-run 5-s window rate − paired
  rest-run 5-s window rate` (the `delta_hz` inside
  `../results-exact.json` is a within-run diagnostic, not a stimulus
  effect). `src/reanalyze_paired.py`.
- `timecourse-50ms.json` — 40 runs (4 wirings × 5 seeds × rest/stim,
  50 ms variant, **v2 substrate**) with per-group rates in short
  windows around the ASH pulse (1 s pre, 500 ms pulse, 250/250/500/
  1000/3000 ms post) plus paired contrasts. `src/timecourse.py`.
  (v3-substrate re-run: `timecourse-50ms-v3.json`, below.)

Caveats: the workbooks have hand-assembled layout quirks (see the
substrate document for the exact handling and counted artifacts); the
sheets' data rows are SPARSE (empty cells omitted from the XML), so
values must be mapped to their labels by each cell's explicit column
reference, never by list position — the v1 parser did it by position
and shifted every value one label column left (correction note in
`circuits/c-elegans-substrate.md`). The SI7 synapse lists in particular
are kept here as provenance only, not parsed into edges.
