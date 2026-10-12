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
