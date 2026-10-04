# Experiment: the control comparison (fly / shuffled / disconnected)

**Question.** Does the wiring matter? Three networks with the *same neurons,
the same stimulus, the same model and the same budget* — only the
connectivity differs:

| Variant | Connectivity |
|---------|-------------|
| `fly` | the real FlyWire wiring, unmodified |
| `shuffled` | every edge keeps its source and its weight (sign + magnitude), its target is re-sampled uniformly from neurons that have at least one input; no duplicate edges. One recorded numpy seed per run |
| `disconnected` | same neurons, zero edges (the null: stimulus decay only) |

## Protocol

- **Circuit.** The FlyWire FAFB v783 connectome as packaged by
  `eonsystemspbc/fly-brain` (`2025_Connectivity_783.parquet` +
  `2025_Completeness_783.csv`); the `fly` variant is the exact matrix the
  reference toolkit builds (column `Excitatory x Connectivity`), so the
  `fly` numbers are directly comparable with the toolkit's published runs.
- **Model.** The toolkit's `AlphaLIF` (Shiu et al. parameter set,
  `wScale` 0.275, dt = 0.1 ms), unmodified.
- **Stimulus.** The toolkit's `sugar` experiment: 21 sugar-sensing
  gustatory receptor neurons, 200 Hz Poisson drive. Timeline: 0.5 s
  pre-stimulus settle → 1.0 s stimulus on → 1.0 s post-offset response.
  2.0 s total = 2,000 steps.
- **Seeds.** 5 stimulus seeds (torch seed recorded per run), identical
  across variants; the shuffling seed is recorded separately in the
  manifest.
- **Readout.** Per-neuron spike counts over the whole 2 s and over the
  1 s post-offset window. Per (variant, seed): total spikes, active
  neurons (>1 Hz), rate distribution (mean/median/p90), top-50 responder
  set.
- **Comparison.** Per seed, then averaged: Spearman rank correlation of
  per-neuron rates between each pair of variants; Jaccard overlap of the
  top-50 responder sets; total-spike ratio (shuffled/fly, fly/disconnected).

## What a pass means — and what it does not

The experiment **passes** when all three variants produce comparable,
reproducible measurements under the identical protocol (no variant is
broken, seeds vary sensibly, the disconnected null behaves like a null).
That is a *measurement* pass. The *scientific* answer — whether the real
wiring produces a meaningfully different response landscape from the
shuffled one — is read out of the numbers in the report, not assumed.

The result does **not** establish anything about learning, behaviour, or
consciousness: it is a fixed-wiring stimulus-response comparison on one
sensory pathway drive. If `fly` and `shuffled` look alike, the honest
conclusion is "for this readout, the wiring did not matter" — which is
exactly the claim the public wave needs someone to test.

## Run

`run_control.py` expects the toolkit checkout at `$FLYBRAIN_DIR`
(default `/opt/fly-brain`); it imports the toolkit's loader, model and
experiment table rather than reimplementing them. Results land in
`--out` as one JSON per (variant, seed) plus a `summary.json` and a
`manifest.json` (seeds, circuit hash, toolkit commit, library versions).
