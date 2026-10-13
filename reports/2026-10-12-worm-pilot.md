# Worm pilot — one measured sensorimotor computation (pilot lane)

**Date:** 2026-10-12
**Lane:** brainlab WORM, pilot lane (bounded; runs ≤ 10 min)
**Status:** DONE (all four tasks; one positive finding, one honest null)

## The question

Take the *measured* hermaphrodite *C. elegans* connectome (Cook 2019:
3,618 chemical synapses, 2,130 neuron–neuron gap junctions, 300
neurons with ≥ 1 neuron–neuron edge), run it as a spiking network with
the lab's LIF conventions, drive the ASH nociceptors with one declared
500 ms pulse, and compare the measured wiring against a
degree-matched random wiring. Does the real wiring route the input to
the textbook output (command pool → body-wall motor neurons) better
than a random wiring of the same size and degree distribution?

**Non-claims (binding):** 302 neurons is a wiring map, not a
whole-animal model. Nothing here establishes "faithful whole-animal
behavior": there are no muscles, no body mechanics, no environment,
no inhibition, no plasticity, and no transmitter identities in the
released data (all chemical synapses were run all-excitatory — the
only sign choice available from the release).

## What was done

1. **Substrate inventory** — the Cook 2019 supplementary workbooks
   (SI6 raw adjacency, SI7 synapse lists, SI8 cell lists, SI9
   matrices; sha256-pinned in `experiments/worm-pilot/data/`) were
   parsed with an artifact-counting parser; the matrices were
   cross-validated against the raw lists (2,382 chemical + 2,740
   electrical artifacts counted, both matrices internally
   consistent). White 1986 could not be fetched from the web; the
   Cook 2019 article body (the staged "PDF" is actually the article
   HTML) subsumes it. Substrate doc: `circuits/c-elegans-substrate.md`.
2. **Circuit pick** — nociceptive withdrawal: ASH/ASJ nociceptors →
   AVA/AVB/AVD/AVJ command pool → body-wall motor classes. The
   *measured* circuit matches the textbook pathway edge for edge
   (verified in `circuits/c-elegans-nociception.md`, which also
   corrects three citation errors found in the pack: the White 1986
   DOI is 10.1098/rstb.1986.0056, the 1992 habituation paper is Rankin
   & Broster, and the 2000 paper is Rankin alone).
3. **Smallest reproducible simulation** — 300-neuron LIF network
   (`experiments/worm-pilot/`): lab conventions (τ_m 20 ms, V_th −45
   mV, V_0 −52 mV, refractory 2.2 ms, dt 1 ms, 1.8 ms delay) plus two
   declared deviations (gap junctions as shared conductance, solved
   exactly per step; constant-depolarization stimulus = receptor
   potential). Two declared model variants, calibrated independently
   on logged grids before freeze (never tuned against the readout):
   - **A: τ_syn = 5 ms** — the lab convention, primary.
   - **B: τ_syn = 50 ms** — declared *after* variant A ran, because
     A's diagnostics showed the 5 ms decay limits the depolarization
     of a post-synaptic neuron receiving a λ Hz train to ≈
     w·λ·τ_syn, below the 7 mV threshold gap at any ASH rate —
     i.e. A *cannot* route fast sensory input by construction.
   Control: configuration-model shuffle (same edge counts — 3,607/3,618
   chemical, 1,901/2,033 gap pairs after self-loop rejection — same
   degree marginals, same weight multiset, seed 7). 5 seeds × 2
   wirings × 2 conditions × 2 variants = 40 runs, total wall time
   ~2 min.

## Results

**Variant A (5 ms) — honest null.** The measured network sits near
silence at rest (67–101 spikes in 15 s) and the ASH pulse adds a
modest total-spike increase (121–160), but the command pool fires
**zero** spikes post-stimulus in all five seeds, and the body-wall
motor classes ~0.01 Hz. The shuffled wiring is essentially dead
(6–13 rest spikes). The mechanism is calculable, not speculative:
ASHR→AVB carries w = 3.2 mV per spike; a 94 Hz train through a 5 ms
exponential sums to ≈ 1.5 mV of mean depolarization — far below the
7 mV threshold gap. Under the lab's exact 5 ms integration, this
wiring cannot route a 10–100 Hz sensory train at any gain. (The null
is a property of the model timescale, and we say so; it is *not*
evidence that the wiring is unstructured.)

**Variant B (50 ms) — positive, wiring-dependent.**

| group (5 s post-stim) | measured (5 seeds, Hz) | shuffled (5 seeds, Hz) |
|---|---|---|
| command pool (AVA/AVB/AVD/AVJ) | 0.70 / 0.98 / 1.35 / 2.83 / 6.32 (mean 2.44, sd 2.08; response index +0.92) | 0.12 / 0.15 / 0.20 / 0.28 / 0.30 (mean 0.21, sd 0.07; ri +0.02) |
| body-wall motor classes | 0.21 / 0.26 / 0.28 / 0.62 / 1.49 (mean 0.57, sd 0.48; ri +0.86) | 0.14 / 0.15 / 0.18 / 0.21 / 0.18 (mean 0.17, sd 0.02; ri −0.03) |
| all other neurons | 0.51 – 2.53 (mean 1.18; ri +0.73) | 0.16 – 0.19 (mean 0.18; ri +0.07) |
| ASH/ASJ (stimulated) | 0.05 – 0.90 (ri +0.93) | 0.05 – 0.15 (ri −0.50) |

Total spikes in 15 s: measured rest 1,918–4,322, post-stimulus
2,236–9,085 (4 of 5 seeds up, up to 2.1×); shuffled rest 641–879,
post-stimulus 691–958 (no response, ≤ +12%).

Read plainly: **the measured wiring supports a sustained sparse
resting state ~5× denser than a random wiring of the same size and
degrees, and it routes the ASH nociceptive pulse into the command
pool and body-wall motor classes — the groups the textbook says the
pathway controls — while the shuffled wiring shows no stimulus
response in any of them.** That is the answer to the lane's
question: under these declared assumptions, the wiring matters.

**Honest caveats on the positive result**
- 5 seeds; seed-to-seed variance is large (command-pool sd 2.08 vs
  mean 2.44; seed 105 at 6.32 Hz is an outlier, likely a
  switch-like state of the all-excitatory network). The declared
  "beyond seed noise" verdict holds (mean > sd and > control) but
  the margin is thin; more seeds would tighten this.
- The all-excitatory assumption is the biggest unknown: real C.
  elegans synapses include glycinergic/GABAergic inhibition that the
  release does not label. The resting state and the switch-like
  variance are plausibly artifacts of it.
- The stimulus is a depolarization pulse, not a mechanosensory
  transduction; the "response" is motor-neuron spiking, not
  movement.
- The 50 ms variant is a model variant, not a measured C. elegans
  timescale; the honest claim is "when summation is made possible,
  the measured topology routes input→output and the random topology
  does not."

## What this establishes / does not establish

Establishes:
1. The complete measured C. elegans wiring (both synapse classes)
   runs as a spiking network on a laptop CPU in seconds per 15 s of
   simulated time (40 runs in ~2 min; well under the lane's 10-min
   budget).
2. Under the lab's exact 5 ms integration convention, this wiring
   does **not** route a 500 ms nociceptive pulse to the command
   pool — a documented null with a calculable mechanism (temporal
   summation limit w·λ·τ_syn).
3. When the integration window is widened to 50 ms, the measured
   wiring (a) sustains a sparse resting state ~5× denser than its
   random counterpart and (b) routes the pulse to the command pool
   and body-wall motor classes, with no response in the control.

Does not establish: pinprick withdrawal behavior, any
spike→muscle→body→environment dynamics, the sign structure of real
synapses, or any claim about the animal.

## Next steps (outside this lane)

- 20–50 seeds on variant B to tighten the wiring-effect estimate.
- A glycinergic/GABAergic sign assignment (e.g. from the 2019
  expression-data atlas) to test whether the switch-like resting
  state is an all-excitatory artifact.
- Replace the depolarization pulse with a transduction model of the
  ASH osmotic/mechanosensitive channel.
- Pair with the B-02 lane's results to see whether the
  "wiring-matters" effect is specific to this circuit or general at
  this scale.

## Artifacts

- `circuits/c-elegans-substrate.md` — substrate inventory (measured
  counts, sex differences, what the release does/doesn't contain,
  parsing artifacts).
- `circuits/c-elegans-nociception.md` — the picked circuit, measured
  edge table, pick rationale, citation corrections.
- `experiments/worm-pilot/` — protocol README, frozen
  `config-5ms.json` / `config-50ms.json`, `calibration-log.json`,
  `results.json` (all 40 runs), source in `src/`, pinned data in
  `data/`.
- Runtime: calibration 4.5 min, campaign 1.2 min/variant; every
  individual run ≤ 6 s.

## Addendum, 2026-10-13 — the v1 shuffle comparisons are superseded

This addendum (append-only; the original text above is frozen)
supersedes every shuffled-control comparison in the original. It has
three parts: (i) the v1 shuffle was not an exact control; (ii) in the
course of fixing it, a defect in the substrate parse was found and
corrected, which means the v1 "measured" wiring was itself not the
published wiring; (iii) the re-run on the corrected substrate with
exact controls does **not** reproduce the v1 positive verdict.

### (i) The v1 shuffle defect (third independent review, 2026-10-13)

`make_shuffled()` (v1) (a) dropped self-edges instead of
redistributing them (3,607 of 3,618 chemical records survived), (b)
merged the symmetric and asymmetric gap-junction records into
undirected pairs with a max-weight merge (1,901 of 2,033
electrical records — the shuffle therefore had a *different* record
structure from the "measured" wiring it was compared against), and
(c) used a single shuffle graph shared by all five simulation seeds,
so seed variability was confounded with graph variability. None of
those defects is large in isolation, but taken together the v1
comparisons were not the declared "same edge counts, same degree
marginals, same weight multiset" controls.

### (ii) Substrate correction (found while fixing the shuffle)

The v1 parser mapped spreadsheet *list positions* to label positions.
The workbooks' data rows are sparse (the XML omits empty cells), while
the label row lacks the leading columns — so every value was
attributed to the label **one column left**. Evidence: the v1 files
contained impossible self-edges (e.g. AVAL→AVAL = 21, 46 total in the
herm file); the independent SI6 raw-EM book, parsed the same way,
overlapped SI9 on only 20% of pairs; and v1's 2,030 "asymmetric"
gap-junction records (1,901 after the shuffle's merges) cannot be
reproduced from the workbook under any counting rule. The v2 parser
maps each cell by its explicit column reference; it is validated two
ways — SI6 agrees with SI9 on 99.8% (herm) / 99.5% (male) of
neuron→neuron chemical pairs (residual = SI9's declared extrapolated
insertions) — and it yields zero self-edges and zero non-numeric
cells. Corrected neuron→neuron counts: herm **3,669 chemical, 1,089
symmetric, 1,089 asymmetric (2,178 electrical; 5,847 total)**; male
3,986 / 1,278 / 1,278 (2,556; 6,542 total). (The v1 figures — 3,618 /
980 / 1,150 herm, and the brief's 3,033 = 1,003 + 2,030 electrical —
are the corrupted values.) Details in
`circuits/c-elegans-substrate.md` ("Correction, 2026-10-13").

### (iii) Re-run with exact-invariant controls (80 runs)

`make_shuffled_exact()` shuffles the RAW record lists per junction
class: exact per-neuron in- and out-degree vectors, identical weight
multisets (sha256-equal), zero dropped records (self-edge
permutations repaired by swap-rejection; 0 residual), exact
sym/asym class counts, no merges. Three **independent** graphs
(seeds 42/43/44), each compared against the measured wiring on 5
simulation seeds × {rest, 500 ms ASH pulse} × {5 ms, 50 ms} = 80
runs. Paired inputs: the background Poisson rng is seeded
`sim_seed*1000 + variant_idx` — a function of the simulation seed and
variant only, never of the wiring — so measured and every shuffle see
byte-identical input trains for a given seed (verified and dumped:
`data/paired-stim-example-*.json`, sha256 in `results-exact.json`).
An invariants block (record counts, degree vectors, weight
multisets, self-edge residuals) is written per shuffle into
`results-exact.json`; `src/test_invariants.py` re-asserts all 34
checks. The frozen configs were recalibrated on the corrected
substrate (old v1 configs preserved as
`config-*-v1-corrupted-substrate.json`); no parameter was tuned
against the readout.

**5 ms (the declared primary variant): null, now on the correct
substrate.** The network is silent in all 20 of its runs (measured
and all three shuffles, rest and stimulus): the ASH pulse elicits
only a handful of receptor-cell spikes (ASH/ASJ ≈ 0.4–0.7 Hz whole
run; the 5 ms decay still limits any downstream depolarization far
below threshold, exactly the mechanism computed in the original).
stim−rest deltas are 0 Hz in every wiring. The original's "variant A
is a documented null" stands, and its controls are now exact.

**50 ms (reasserted as EXPLORATORY — the variant was selected after
examining 5 ms): the v1 positive verdict does not reproduce.**
What survives is a **resting-state** effect: the measured wiring
self-sustains a state ≈ 2× denser than every exact control, in all
three independent graphs and all five seeds (whole-animal rest
2.20 Hz vs 1.02–1.06 Hz; command pool ≈ 5.0 Hz vs ≈ 1.6–2.9 Hz;
per-neuron max 25.7 Hz vs 6.0–6.9 Hz; across-graph spread
1.02/1.06/1.06 Hz). What does **not** survive is the stimulus
routing: the stim−rest delta in the command pool is ≤ 0 in every
wiring (measured −0.16 ± 0.65 Hz; shuffles −0.09 to −0.15 Hz;
across-graph spread 0.024 Hz) — the pulse pushes the already-saturated
state no further, and no wiring shows a positive response. The
body-wall motor deltas are likewise negative-to-zero in all wirings.
(The headline table's one "measured beats shuffles" flag, on the
all-other-neurons group, is an artifact of comparing small negative
deltas and carries no meaning.) v1's "measured post-stim 14.65 Hz vs
shuffled 2.46 Hz, response index 5.7 vs 1.0" was an artifact of the
corrupted substrate plus the single non-exact graph.

**Corrected statement.** Under this all-excitatory model, (a) the
5 ms variant produces no measurable effect of the declared ASH pulse
beyond the receptor cells, in any wiring; (b) at the 50 ms
(exploratory) decay, the measured wiring differs from its exact
controls in its **self-sustained resting state**, but the pulse
elicits no measurable command-pool or body-wall delta above the
controls — i.e. the wiring does not *route the stimulus* under these
assumptions, even though it does change the baseline state. The
"resting-state" difference is the only wiring-dependent effect that
survives the exact controls, and it is an exploratory-variant result
that needs more seeds and a sign assignment before it can be taken
seriously (it may be an all-excitatory artifact: a random wiring with
the same degree marginals can also be close to a bifurcation, and
the two graphs may sit on different sides of it).

### Non-claims (unchanged from the original)

No muscles, no biomechanics, no feedback: spiking ≠ movement. The
release carries no synapse signs or kinetics; the all-excitatory
choice is a declared assumption, and several results above may be
artifacts of it. Five seeds per condition. Nothing here is a
whole-animal emulation or a behavior demonstration.

### Artifacts (2026-10-13)

- `experiments/worm-pilot/results-exact.json` — all 80 runs, per-seed
  stim−rest deltas, headline table with across-graph spread,
  per-shuffle invariants blocks, paired-artifact hashes. (v1
  `results.json` frozen, untouched.)
- `experiments/worm-pilot/data/paired-stim-example-{5ms,50ms}.json` —
  the measured vs shuf-42 background event lists for one
  (sim seed, variant), asserted identical, with sha256.
- `experiments/worm-pilot/src/make_shuffled_exact` (in `sim.py`),
  `src/test_invariants.py`; recalibrated frozen `config-5ms.json` /
  `config-50ms.json` (v1 copies kept as
  `*-v1-corrupted-substrate.json`), `calibration-log.json` (v1 log
  kept likewise); regenerated `c-elegans-edges-*.json` /
  `c-elegans-inventory.json` / `c-elegans-neurons-male.json`.
- `circuits/c-elegans-substrate.md` — correction note and v2 parse
  table.

---

## Addendum (2026-10-13, second) — the stim−rest metric was a
## within-run quantity; the correct paired contrast is positive in
## the measured wiring (review round 4)

### (i) The metric defect

The `delta_hz` in `results-exact.json` is **not** a stimulus effect:
it is the 5-s post-stimulus window rate minus the **same run's**
whole-15-s average. In a stimulated run that 15-s average *includes*
the post-stimulus window, so the "delta" is a within-run
self-comparison, not a contrast against the no-stimulus condition.
The earlier addendum's statement that "the stim−rest delta is ≤ 0 in
every wiring" is therefore **superseded**: it was computed on a
metric that cannot answer the question.

The correct primary metric — already fully contained in the committed
80-run data, no rerun — is the **paired** contrast:

    paired_delta_hz = stim-run 5-s window rate
                      − paired rest-run 5-s window rate
    (same wiring, same sim seed, same bg seed; window = [stim_end,
     stim_end + 5000))

Recomputed from `results-exact.json` and frozen as
`data/paired-stim-effect.json` (`src/reanalyze_paired.py`).

### (ii) Corrected paired numbers

**50 ms, command pool** (per-seed / mean over 5 seeds):

| wiring    | per-seed (Hz)                     | mean    |
|-----------|-----------------------------------|---------|
| measured  | +0.125 / +0.150 / +0.025 / +0.100 / +0.050 | **+0.090** |
| shuf-42   | 0 / 0 / 0 / 0 / −0.025            | −0.005  |
| shuf-43   | +0.025 / 0 / 0 / 0 / +0.050       | +0.015  |
| shuf-44   | +0.050 / 0 / 0 / 0 / 0            | +0.010  |

The measured wiring is positive in **all five seeds**; the three
exact-invariant shuffle graphs are ~zero (max +0.015). Body-wall
motors: measured +0.0125 Hz (per-seed 0.013/0.021/0.018/0.010/0.000)
vs shuffles ≤ +0.0026 — small and not clearly above the shuffles.
**5 ms:** all paired deltas 0.000 in every wiring and group (the
documented null stands on the corrected metric too).

### (iii) Time-resolved response (new data, 40 runs)

`data/timecourse-50ms.json` (`src/timecourse.py`): the 50 ms variant
re-run for all 4 wirings × 5 seeds × rest/stim with per-group rates in
short windows (1 s pre-pulse, the 500 ms pulse, then 250/250/500/
1000/3000 ms post-pulse). Paired contrasts (stim − paired rest, Hz):

- **command pool**: during the pulse, measured **+1.75** vs shuffles
  +0.75 / +0.25 / +0.40; post-pulse the measured wiring stays
  positive (+0.05 to +0.18) while all shuffles decay to ~0 by ~1 s.
- **body-wall motors**: pulse contrast ~+0.1 in *all* wirings (not
  wiring-specific); post-pulse ~0.
- **ash_ashj** (the driven receptor group): fires in all wirings
  during the pulse (the injected current), no post-pulse effect.
- **other**: measured mildly higher in the first post-pulse windows.

So the response is **not** a brief transient cancelled inside the
5-s window: if anything, the largest wiring-specific contrast is
*during* the pulse, and it persists at a small magnitude afterwards.

### (iv) Interpretation and scope

On the corrected substrate and controls, the measured C. elegans
wiring shows a **small, wiring-specific response to the ASH
nociceptive pulse in the command neuron pool** (≈ +0.09 Hz in the
5-s window, all seeds positive; ≈ +1.75 Hz during the pulse, ~2–4×
the shuffle graphs), which does not reach the body-wall motor group.
The 5-s window's ~5 Hz command-pool baseline makes the effect
≈ +1.8% relative. This is a **candidate sensorimotor lead, not a
demonstration of withdrawal**: 5 seeds, one 300-neuron circuit,
all-excitatory signs (the release carries no transmitter sign — the
resting-state bifurcation may itself be an all-excitatory artifact),
and the 50 ms timescale is post-hoc. The 5 ms lab convention remains
a clean null under every metric.

### (v) Proposed bounded follow-up (for authorization; NOT run)

1. **More independent rewirings**: 8 further exact-invariant shuffles
   (seeds 45–52) to tighten the shuffle baseline of the command-pool
   contrast.
2. **Sign sensitivity**: assign glycinergic/GABAergic signs from the
   Cook 2019 receptor-expression data (or a literature-derived
   partial assignment) and re-test whether the command-pool response
   survives (and whether the resting-state bifurcation persists).
3. **Timescale sensitivity**: the same 4-wiring battery at
   τ_syn ∈ {10, 25, 100} ms.
4. **Real ASH transduction** (graded receptor model) instead of the
   constant depolarization.

Each is a few hours or less; a pre-registered stop rule would mirror
the A-03 decision-pilot pattern (declared before execution).

### Artifacts (this addendum)

- `experiments/worm-pilot/src/reanalyze_paired.py`,
  `data/paired-stim-effect.json` (frozen recompute; no rerun).
- `experiments/worm-pilot/src/timecourse.py`,
  `data/timecourse-50ms.json` (40 new runs; all prior artifacts
  untouched).
- `experiments/worm-pilot/src/run_campaign.py` — the campaign now
  records the paired contrast as its primary metric (the within-run
  `delta_hz` is retained as a diagnostic); applies to future runs
  only, the frozen `results-exact.json` is unchanged.
