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
- `timecourse-50ms.json` — 40 new runs (4 wirings × 5 seeds ×
  rest/stim, 50 ms variant) with per-group rates in short windows
  around the ASH pulse (1 s pre, 500 ms pulse, 250/250/500/1000/3000
  ms post) plus paired contrasts. `src/timecourse.py`.

Caveats: the workbooks have hand-assembled layout quirks (see the
substrate document for the exact handling and counted artifacts); the
sheets' data rows are SPARSE (empty cells omitted from the XML), so
values must be mapped to their labels by each cell's explicit column
reference, never by list position — the v1 parser did it by position
and shifted every value one label column left (correction note in
`circuits/c-elegans-substrate.md`). The SI7 synapse lists in particular
are kept here as provenance only, not parsed into edges.
