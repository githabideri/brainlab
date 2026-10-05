# Results — control comparison, campaign 2026-10-04/05

Machine-readable aggregates of the first campaign (the report:
`../../../reports/2026-10-05-first-campaign.md`).

- `manifest.json` — seeds, circuit hash, toolkit commit, library versions
- `summary.json` — pairwise comparisons and per-variant aggregates
- one JSON per (variant, seed), 15 files — per-run readout: totals,
  active counts, rate stats, top-50 responder sets

Raw per-neuron rate vectors (`.npy`, ~550 KB each) and the toolkit's
spike-level artifacts stay on the campaign host (under
`/var/brainlab/runs/2026-10-04-night/control/`); they are regenerable
from the manifest.
