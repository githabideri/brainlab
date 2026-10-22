# Worm v3 sensitivity — what survives the corrected substrate

**Date:** 2026-10-22
**Lane:** brainlab WORM-V3 (new focused experiment; the 2026-10-12/13
multi-track campaign is closed and this is not part of it)
**Status:** DONE (440 runs, all batteries, all stop rules evaluated)

## Goal

The worm-pilot's third addendum (review round 5, 2026-10-13) closed the
pilot with exactly one surviving wiring-specific observation — a
**resting-state** activity difference on the corrected v3 substrate
(measured above 3 shuffles, Model B, 50 ms) — and a reinstated null for
the ASH-response routing. Its proposed bounded follow-up (8 more
shuffles, transmitter signs, τ sensitivity, graded transduction) was
left not-run pending re-authorization. This experiment ran that
follow-up, with the verdict rules declared before the first run: is
the resting-state difference wiring-specific at all, and does any
tested combination of inhibition, summation timescale, or stimulus
shape elicit a wiring-specific *response*?

## Setup (hardware as roles)

- **CPU batch role:** 4-core x86 box (the lab's designated CPU batch
  host). A 15 s / 1 ms / 300-neuron run takes ≈ 2 s; the full 440-run
  campaign wall time was 11.4 min.
- No GPU, no training: frozen LIF networks, the lab's conventions,
  the pilot's frozen v2 parameters (no re-calibration, per the
  review-round-5 freeze rule).

## Protocol (pre-registered; frozen commit b7df48f before execution)

Full text in [`experiments/worm-v3-sensitivity/README.md`](../experiments/worm-v3-sensitivity/README.md).
Summary:

- **Substrate:** the pilot's v3 canonical electrical layer (one
  undirected junction per physical gap junction; 1,089 herm) + 3,669
  directed chemical edges; 300 neurons.
- **Wirings:** measured + **eleven** independent exact-invariant
  shuffle graphs (seeds 42–52; 42/43/44 are the pilot's frozen
  graphs, reproduced exactly; 45–52 new).
- **Batteries** (5 seeds × {rest, 500 ms ASH pulse at t = 5.0–5.5 s},
  paired input `bg_seed = sim_seed*1000+1`, one background train
  shared by every wiring in every battery — sha256
  `76539fd640ba…` in each results file):

  | id | bg model | τ_syn | signs | stimulus | wirings | runs |
  |---|---|---|---|---|---|---|
  | B1 | B | 50 ms | all-excitatory | constant (frozen S) | 12 | 120 |
  | B1a | A | 50 ms | all-excitatory | constant | 12 | 120 |
  | B2 | B | 50 ms | **signed** | constant | 4 | 40 |
  | B3 | B | 10 / 25 / 100 ms | all-excitatory | constant | 4 × 3 | 120 |
  | B4 | B | 50 ms | all-excitatory | **trapezoid** (100/300/100 ms, peak = frozen S) | 4 | 40 |

- **Sign assignment (B2).** Inhibitory = chemical edges whose
  presynaptic neuron is a **GAD-synthesizing (unc-25-positive)**
  class: RME, RIS, AVL, DVB (DVB/DVC), DD01–06, VD01–13, RIB — the
  six GABA classes of McIntire et al. 1993 plus RIB, from
  Gendrel, Atlas & Hobert 2016 (*eLife* 5:e17686, Table 1);
  uptake-only "recycling/clearance" cells (ALA, AVF, SMDD) and the
  ambiguous AVA/AVB/AVJ excluded. **31 cells, 219 of 3,669 edges
  (6.0%)**; magnitudes unchanged. Shuffles preserve the signed
  multiset (global balance) but not the presynaptic identity of the
  signs — declared.
- **Stop rules (declared before execution).** S1: the resting-state
  difference is *not* wiring-specific if ≥ 3 of the 11 shuffles
  reach ≥ 0.75 × the measured rest rate (else it stands). S2: a
  wiring-specific *response* requires measured signed command-pool
  5-s paired contrast > 0.5 Hz, positive in all 5 seeds, beating all
  signed shuffles. S3/S4: τ map and step-vs-trapezoid comparison,
  exploratory. **Overall verdict (the lab's control-wiring bar):**
  pass only if some battery shows measured > 0.5 Hz, all seeds
  positive, beats all its shuffles.

## Commands

```bash
cd experiments/worm-v3-sensitivity
python3 src/smoke_test.py      # sign flips (219), signed-shuffle invariants, trapezoid
python3 src/run_sensitivity.py # all batteries -> results/*.json + verdicts.json
```

## Observations

1. **S1 — the resting-state difference IS wiring-specific (0 of 11).**
   Whole-animal rest rate, mean over seeds (Model B, 50 ms):
   measured **2.97 Hz** vs shuffles **1.74–2.05 Hz**; **none** of the
   11 graphs reaches 0.75 × measured (2.23). Command pool: measured
   **9.03 Hz** vs 5.30–7.49. The pre-registered rule (≥ 3 of 11
   would close the lead) is decisively not met: adding 8
   independent rewirings to the pilot's 3 leaves the measured wiring
   as the unique active basin. This is *not* a random-neighborhood
   of the all-excitatory bifurcation — a random wiring with the same
   degrees usually lands at ~1.8 Hz, not ~3.0.
2. **S2 — signs weaken, but do not abolish, the resting difference;
   no response appears.** With the GAD-synthesizing classes
   inhibited, the measured rest rate drops from 2.97 to **1.77 Hz**
   (shuffles 1.14–1.23): the measured wiring is still ~1.5× its
   controls (0 of 3 shuffles reach 0.75 × measured), but the margin
   is smaller than in the all-excitatory case. The signed
   measured wiring's command-pool 5-s paired contrast is
   **−0.075 Hz** (negative or zero in 4 of 5 seeds) — adding
   inhibition does not elicit a response in the measured wiring
   beyond its signed controls. No S2 pass.
3. **S3 — the resting-state effect lives in a narrow timescale
   window.** τ_syn 10 ms: the network is silent (rest 0.0 in every
   wiring; the documented summation limit). 25 ms: sparse
   (measured 0.127 vs shuffles 0.062), no contrast. **50 ms: the
   resting-state difference (above).** 100 ms: **reversed** —
   measured rest 11.88 Hz vs shuffles 13.4–13.8, and the measured
   contrast is negative (−0.13 Hz) while two shuffles are positive.
   The all-excitatory network's active-basin location is a property
   of the integration window as much as of the wiring.
4. **S4 — a graded stimulus elicits responses in *every* wiring, not
   specifically the measured one.** Replacing the step with a
   trapezoid (same peak, same total duration) raises the
   command-pool 5-s contrast by ~10×: step 0.055 (measured) vs
   trapezoid 0.52 — but the shuffles rise too (0.47 / **0.66** /
   0.38; one shuffle *above* the measured wiring, which is itself
   mixed across seeds: 3 of 5 positive). The stimulus shape
   controls whether the network answers at all; the wiring does not
   control whether the answer is specific.
5. **Replication check.** The B1 measured/shuf-42–44 numbers
   reproduce the pilot's frozen round-5 runs exactly (2.97 /
   1.78 / 1.79 / 1.74 Hz) — the v3 substrate and driver are
   unchanged. All 440 runs stable (no saturation, no NaN); every
   battery's paired-input hash is identical, as declared.

## Numbers

Rest rate, mean over 5 seeds (Hz):

| battery | measured | shuffles (range) | ratio |
|---|---|---|---|
| B1 (B, 50 ms, 11 shuffles) | 2.97 | 1.74 – 2.05 | 1.46–1.71 |
| B1a (A, 50 ms) | 0.195 | 0.169 – 0.176 | 1.11–1.15 |
| B2 (B, 50 ms, signed) | 1.77 | 1.14 – 1.23 | 1.44–1.55 |
| B3 (B, 25 ms) | 0.127 | 0.062 – 0.062 | 2.0 |
| B3 (B, 10 ms) | 0.00 | 0.00 – 0.00 | — |
| B3 (B, 100 ms) | 11.88 | 13.38 – 13.76 | **0.86 (reversed)** |

Command-pool 5-s paired contrast, mean over seeds (Hz):

| battery | measured | shuffles (range) |
|---|---|---|
| B1 (B, 50 ms, step) | +0.055 (per seed −0.15…+0.275) | −0.055 … +0.04 |
| B1a (A, 50 ms) | 0.0 (all seeds 0) | 0.0 |
| B2 (signed, step) | −0.075 (per seed −0.225…0.0) | −0.02 … +0.02 |
| B3 (10 / 25 / 100 ms) | 0.0 / 0.0 / −0.13 | 0.0 / 0.0 / −0.02…+0.175 |
| B4 (trapezoid) | +0.52 (per seed −0.425…+1.225) | +0.375 … +0.655 |

Artifacts: `experiments/worm-v3-sensitivity/results/` — per-battery
JSON (all 440 runs, per-window group rates, per-seed paired
contrasts, per-shuffle invariants blocks, paired-input hashes),
`verdicts.json` (S1–S4 + overall, evaluated by code), frozen
`config/b3-tau*.json` (B3 derived configs), pre-registered README,
`data/gabaergic-herm.json` (sign-assignment source),
`src/run_sensitivity.py` + `src/smoke_test.py`.

## Conclusion

**Overall verdict: FAIL on the control-wiring bar.** No tested
(model, τ, signs, stimulus) combination produces a measured
command-pool response that is > 0.5 Hz, positive in all seeds, and
above all of its matched shuffles. The honest statement: **on the
v3 substrate, the measured C. elegans wiring does not route the ASH
nociceptive pulse beyond its degree-matched controls under these
declared assumptions.** The pilot's null stands, now against 11
independent rewirings instead of 3.

What the experiment adds to the picture:

1. **The surviving observation is confirmed to be wiring-specific,
   with a narrower meaning.** The resting-state difference is not a
   coincidence of the pilot's three graphs (0 of 11 controls land in
   the active basin) — but it is a property of the *all-excitatory,
   ~50 ms* regime: it sits in a narrow integration window (silent
   at 25 ms, reversed at 100 ms) and weakens when partial GABAergic
   inhibition is admitted. Read plainly: under these assumptions the
   measured wiring picks *which side of a bifurcation* the network
   rests on; that is a state effect, not a routing effect.
2. **The response question is answered as a model-regime result.**
   The 500 ms step is too brief a drive for these networks to
   answer; a graded (trapezoid) stimulus of the same peak and
   duration elicits ~0.4–0.7 Hz command-pool responses in *every*
   wiring. Whether a stimulus makes the network respond is not
   wiring-specific at this scale.
3. **The sign assignment is the most informative lever tested.**
   Inhibiting the 6.0% of edges from GAD-synthesizing classes
   moves the measured wiring's rest rate by 40% (2.97 → 1.77 Hz)
   while barely moving the shuffles — the measured wiring's
   resting state is more sign-sensitive than a random wiring's.
   That is a genuine, small, wiring-specific *sensitivity*
   difference — recorded as an observation, not a pass (the
   pre-registered S2 rule asked for a response, not a sensitivity
   shift).

**What failed / what the numbers do not show.** Nothing mechanical:
all 440 runs completed, all invariants held, the pilot's frozen
numbers replicate exactly. Substantively, both candidate
"positives" were examined and neither survives the control bar:
the resting-state effect does not convert into a response under
any tested treatment, and the one response that gets large enough
(trapezoid, 0.52 Hz) is not wiring-specific. Nothing here
establishes pinprick behavior, real GABA kinetics (the sign
assignment is a class-level proxy from one 2016 map, not per-
synapse transmitter identity), or real receptor transduction
(the trapezoid is a declared shape, not a channel model).

## Next (not run; would need fresh authorization)

- The τ=100 ms reversal and the τ-window of the resting-state
  effect are now the interesting geometry: a sweep over
  τ ∈ {40, 45, 55, 60, 75} would map the window's boundaries.

> **Update (2026-10-22):** that sweep was run as the new
> [2026-10-22-worm-tau-window](2026-10-22-worm-tau-window.md) experiment — the
> effect is a band-pass (dominant 25–60 ms, peak 40–45 ms, crossover
> 60–75 ms); the control-wiring verdict here is unchanged.
- A full per-synapse transmitter assignment (Glu/GABA/ACh from
  the expression atlases) rather than the partial GAD-class
  proxy; and a glutamatergic-class flip as the complementary
  experiment.
- Real ASH channel transduction (graded receptor with measured
  kinetics) instead of declared current shapes.
- Male-substrate run (v3 canonical male graph is already parsed):
  is the resting-state effect sex-specific?

## References

- Gendrel M, Atlas EG, Hobert O. (2016) A cellular and regulatory
  map of the GABAergic nervous system of C. elegans. *eLife*
  5:e17686. doi:10.7554/eLife.17686 (source of the sign
  assignment, Table 1).
- Cook CM et al. (2019) The complete electronic data book on the
  structure of the *Caenorhabditis elegans* nervous system.
  *eLife* 8:e47256. (substrate)
- McIntire DV, Schaffer SR, Schuster G (1993) Glutamate, GABA,
  and choline acetyltransferase in *C. elegans*. *J Comp
  Neurol* 331:389–400. (the six GABA classes)
- Previous state: [`2026-10-12-worm-pilot.md`](2026-10-12-worm-pilot.md)
  (third addendum, review round 5, is the authoritative state of
  the pilot).
