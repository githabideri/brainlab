# T-ang dedicated — does the A-03 spike-arm T-ang lead survive?

**Date:** 2026-10-22/23
**Lane:** brainlab TANG-DED (new focused experiment; the 2026-10-12/13
multi-track campaign is closed and this is not part of it)
**Status:** DONE (30/30 runs; declared pass criteria evaluated by code;
verdict **FAIL**)

## Goal

The A-03 decision pilot (24 runs, STOP verdict 2026-10-13;
`reports/2026-10-12-a03-design.md`, addenda through review round 5)
left exactly one sub-ceiling positive signal: **spike T-ang** — fly
**84.95°** vs degree **92.77°** RMCE (−7.82°, "identical" under its 3
"seeds" because the spike arm is deterministic in the seed — one
evaluation, not three), with the degree control worse than chance
(89.80°) and both far from the 45.46° ceiling. The review recorded it
as a candidate for "a dedicated T-ang study with more seeds and
circuits". This is that study (same single 1,536-neuron circuit
sample — a second circuit is a separate experiment), attacking the
two defects the STOP record itself names: the *one* Poisson drive
realization (one evaluation's worth of drive noise) and the *sizing*
held-out fold (the pilot's addendum called it a "32-trial held-out
prefix"; its JSONs actually say `n_test=512` — a wording error this
study documents).

**Question.** On the FlyWire FAFB v783 olfactory circuit (1,536 nodes,
42,921 signed edges), driven exactly as the A-03 spike arm (frozen
Shiu-2024 LIF, declared Poisson sensory drive, ridge readout), does the
measured wiring beat its matched controls on angular integration

1. **stably** — across 5 independent Poisson drive realizations, and
2. **specifically** — against *all five* controls (degree, sign,
   weight, population, disconnected), not only against degree?

evaluated on the 512-trial held-out fold.

## Setup (hardware as roles)

- **CPU batch role:** 4-core x86 box (the lab's designated CPU batch
  host), the lab's torch venv (CPU; torch 2.14.1, numpy 2.5.4).
  Single-threaded LIF loop (the A-03 measured setting: 10× faster
  than 4 threads on these 1,536-element kernels).
- No GPU, no training inside the spiking network: frozen LIF
  circuit (B-01 treatment); the only learned object is the ridge
  readout (Δw = 0 by construction).

## Protocol (pre-registered; frozen commit f1024bb before execution)

Full text in
[`experiments/tang-dedicated/README.md`](../experiments/tang-dedicated/README.md).
Summary:

- **Circuit:** staged file, sha256 `ef6a6c1d…` verified before every
  run; `lif.py` byte-identical to B-01 and all five controls'
  edge arrays hash-checked against A-03's recorded manifest in every
  run.
- **Task:** T-ang only (T = 10 steps, ω ~ U[−180, +180]°/step,
  x_t = ω/360 + N(0, 0.05²), target (sin H, cos H), report at step 9):
  same master-seed stream and same 512-trial held-out fold as A-03;
  ceiling 45.464°, chance 89.804°.
- **Grid:** 6 wirings (fly + all five A-01 controls) × **5 drive
  realizations** = 30 runs. Realization k = 0 uses A-03's exact drive
  salt (bit-identical to the decision pilot); k = 1…4 use new salts.
  Within every realization all six wirings see the identical drive
  (the A-03 paired property). 128-trial ridge (80 % fit prefix).
- **Pass criteria (declared before the first grid run).** P1
  stability: fly − degree ≤ −5° in ≥ 4 of 5 realizations. P2
  control-wiring specificity: fly's mean RMCE < every control's mean,
  beating the best control by ≥ 5°, fly single-best in ≥ 4 of 5.
  **PASS only if both.** Shrink rule (K 5→3 if the smoke's full run
  > 15 min) declared and not triggered (smoke full run 625 s).
- **Declared deviations (recorded; both forced by the A-03 record,
  not by outcomes):** (1) the smoke's S1 bit-identity check runs on
  the **full 512 fold**, not the 32 prefix the pilot addendum's
  wording suggested (the decision-pilot JSONs say `n_test=512`); the
  first 32-prefix attempt is kept as a data point (Observation 4).
  (2) the `disconnected` control is **computed directly as the
  mean-predictor null floor** rather than run through the LIF: the
  pinned `lif.py` cannot construct a zero-edge network (its
  `lif_weights` percentiles the empty magnitude array; its
  `_deliver` indexes the empty update queues) — a latent B-01
  defect, out of this lane's hands — and a zero-edge arm's output is
  *exactly* the mean predictor (tonic-only constant features →
  ridge → training-fold mean target), so the direct computation is
  its exact value, flagged in every JSON.

## Commands

```bash
cd experiments/tang-dedicated
PY=/root/homelab/temp/brainlab/venv/bin/python   # lab torch venv (CPU)
CIRCUIT=<staged flywire-fafb-olfactory-1536 circuit.json, hash-verified>
$PY src/smoke_tang.py --circuit $CIRCUIT --s1-only   # S1+S2 -> results/smoke/
$PY src/run_tang.py --circuit $CIRCUIT --k 5         # 30 runs -> results/ + map.json
```

## Observations

1. **Import fidelity holds (smoke S1, MATCH).** Realization 0
   (A-03's exact drive salt) reproduces the decision pilot **exactly**:
   fly 84.951 / degree 92.767° (3 decimals), R² −0.3375 / −0.4842 —
   bit-identical features, deterministic ridge. The dedicated study
   is measuring the same machine, not a reimplementation.
2. **The null floor is 84.575° — and it is *better than chance*.**
   The no-information mean predictor (predict the training-fold mean
   heading for every test trial) scores 84.575°: better than the
   89.804° chance value, because one fixed direction beats a
   zero-information guess against a dispersed heading cloud, and
   worse than the 45.464° ceiling by a wide margin. **The fly
   wiring's r0 value (84.951°) is 0.38° above this floor** — the
   "sub-ceiling" position of the decision pilot is, to within MC
   noise, the no-information position. Every LIF wiring's ridge has
   negative R² (−0.40…−0.50): the learned readout *degrades* the
   trivial mean in (sin, cos) space in every wiring and realization;
   the RMCEs stay close to the floor because the fitted direction
   stays near the data-mean direction.
3. **P1 FAIL — the lead is not stable: 1 of 5.** fly − degree per
   realization: **−7.82, −2.97, +1.63, +0.90, +2.17°** (fly better
   only in r0 and marginally in r1). The decision pilot saw the
   outlier draw: in four of five independent drives the fly-degree
   gap is ≤ 3° (inside the ~2–4° MC error of a 512-trial RMCE) or
   inverted.
4. **The lead's size is fold-size-dependent.** The first smoke
   attempt (the addendum's 32-prefix wording) measured fly 81.205 /
   degree 85.521 — a gap of 4.3°; the same wiring pair on the 512
   fold gives 84.951 / 92.767 — 7.82°. The 32-prefix numbers are
   kept in `results/smoke/` as a data point, not the S1 check.
   Whatever the pilot "measured", it measured the 512 fold; the
   addendum sentence was simply wrong.
5. **P2 FAIL — and the best "control" is no wiring at all.** Mean
   RMCE over realizations: fly **87.89** < weight 88.40 < sign 88.87
   < degree 89.11 < population 91.32 — fly is the best *LIF* wiring
   on average — but **disconnected (the null floor) scores 84.575,
   below fly in every realization** (best-control margin
   **−3.32°**, i.e. negative; single-best votes **0 of 5**). One
   wrinkle, reported as found: the `weight` shuffle dipped to
   **83.266° in r4 — below the floor itself and below fly** — so
   the floor is not a hard bound on what a ridge over a lucky
   Poisson draw can do; the LIF wirings' values wobble ±2–3° around
   the floor (their per-realization stds are 1.8–2.9°), which is
   exactly the scale of the decision pilot's 7.82° "effect".
6. **No arm approaches the ceiling.** Ceiling efficiency
   (45.464 / RMCE): 0.50–0.54 for every wiring; the spike reservoir
   + linear readout on this circuit, under the declared drive
   (R0 = 2 / RMAX = 48 Hz, 100 ms steps, 200 ms window), carries
   essentially no angular-integration information — consistent with
   the A-03 STOP and its revision note (the tanh arm's fly ≥ degree
   T-del differences were the *other* seed-unstable signal; both are
   now "recorded, not discarded", and this study adds the same
   verdict for the spike T-ang one).
7. **Mechanics.** 30/30 runs completed; the one crash (the pinned
   `lif.py`'s zero-edge incompatibility, caught on the first
   `disconnected` cell) is a documented latent B-01 defect, worked
   around by the exact-value computation above (commit `a1ff8b9`);
   no NaN, all control invariants asserted by the imported
   `controls.py` in every run.

## Numbers

RMCE (deg), mean over 5 realizations (per-realization in
`results/map.json`):

| wiring | r0 | r1 | r2 | r3 | r4 | mean ± std | R² mean | efficiency |
|---|---|---|---|---|---|---|---|---|
| fly | 84.951 | 87.490 | 87.978 | 88.727 | 90.310 | **87.89 ± 1.75** | −0.423 | 0.518 |
| degree | 92.767 | 90.457 | 86.350 | 87.828 | 88.137 | 89.11 ± 2.25 | −0.398 | 0.511 |
| sign | 86.101 | 87.994 | 91.581 | 89.364 | 89.332 | 88.87 ± 1.80 | −0.426 | 0.512 |
| weight | 90.879 | 89.812 | 90.844 | 87.176 | 83.266 | 88.40 ± 2.90 | −0.415 | 0.515 |
| population | 89.962 | 93.145 | 94.057 | 89.814 | 89.643 | 91.32 ± 1.88 | −0.498 | 0.498 |
| disconnected (null floor, direct) | 84.575 ×5 | | | | | **84.575 ± 0.00** | ≈0 | 0.538 |

Reference points: chance 89.804°, ceiling 45.464°. The decision
pilot's row is r0 (fly 84.951 / degree 92.767 — bit-identical).

Artifacts: `experiments/tang-dedicated/results/` — 30 per-run JSONs
(per-realization RMCE/R²/efficiency, drive salt, n_train/n_test,
null-floor flag, provenance block), `map.json` (P1/P2 evaluated by
code), `results/smoke/` (S1 bit-identity records incl. the 32-prefix
first attempt, S2 wall-time record, `smoke.json`),
`src/run_tang.py` + `src/smoke_tang.py`, frozen README.

## Conclusion

**Verdict per the declared criteria: FAIL.** P1 (stability) 1 of 5;
P2 (specificity) — fly is the best *LIF* wiring on average but sits
**3.3° worse than the no-information mean-predictor floor** and
single-best in 0 of 5 realizations. The A-03 decision pilot's
"sub-ceiling spike T-ang signal" does not survive a dedicated
multi-realization, full-control study. The honest statement:

1. **The "lead" was a fold-size-dependent degradation contrast.**
   The fly wiring's value (84.95°) is the no-information floor
   (84.58°) to within MC noise, in *every* realization; the pilot's
   7.82° gap came from the degree shuffle's ridge degrading that
   same trivial mean much more (92.77°) — and on four of five
   independent drives the degree ridge does not degrade that much.
   No arm shows evidence of information: every R² is negative, no
   arm approaches the 45.46° ceiling, and one *control* (weight, r4)
   even beat the floor once.
2. **The campaign's STOP stands, confirmed from its own surviving
   lead.** "No biological advantage of the measured wiring over
   matched controls at this budget" — now also: no advantage over
   the *no-wiring* floor. The 210-run A-03 grid remains not run.
3. **Two records were fixed along the way.** The pilot addendum's
   "32-trial held-out prefix" wording is wrong (its JSONs are
   n_test=512) — recorded in its report's pointer and here. The
   pinned B-01 `lif.py` cannot construct a zero-edge network
   (`lif_weights` percentile on the empty array; `_deliver`
   indexing empty queues) — a latent defect handed to B-02 Stage 1
   with the earlier `reset()` one; this lane worked around it with
   the exact-value computation rather than touching the pinned file.

**What failed / what the numbers do not show.** Nothing mechanical:
30/30 runs, bit-identity verified, invariants asserted.
Substantively: this is *not* a power statement — 5 realizations is
a decision rule, and a 1.3° true effect could hide inside the ±2–3°
per-realization wobble; it does not refute angular integration in
this circuit under other drives (R0/RMAX/rate range, step duration,
window), other readouts (nonlinear), or the tanh arm (whose T-ang
values, 84.2–86.9°, sit at the same floor); it says only that the
declared spike-arm machine on this circuit carries no measurable
T-ang information beyond the no-wiring predictor.

## Next (not run; would need fresh authorization)

- **Drive-sensitivity follow-up** (cheapest remaining angle on the
  same circuit): RMAX 48 → 20 Hz (a slower sensory population — does
  the reservoir compute anything at all at a more moderate rate)
  and obs-noise 0.05 → 0.02 (the ceiling rises toward 0°, giving
  headroom for a small real effect to clear the floor).
- **The second-circuit sample** the review asked for: repeat this
  exact protocol on `fafb-cc-b01` (the B-01/B-02 circuit) — the
  cross-circuit question is the only one this design cannot answer
  alone.
- **B-02 Stage 1** owns the `lif.py` zero-edge fix (with the
  logged `reset()` defect); until then no lane can run a true
  disconnected LIF arm.
- The tanh-side T-ang at the 512 fold (the decision pilot's tanh
  T-ang cells — 84.19–86.90° — are also at the floor; a dedicated
  tanh T-ang would close the last task cell of the pilot's 2×2).

## References

- A-03 pre-registration, pilot, correction addendum, decision pilot
  and STOP: `experiments/a-03-sequential-learning/README.md` and
  [`2026-10-12-a03-design.md`](2026-10-12-a03-design.md) (addenda,
  reviews rounds 3–5).
- B-01 (the LIF treatment, drive convention, and the pinned
  `lif.py`): `experiments/b-01-internal-compass/`, report
  [`2026-10-12-b01-internal-compass.md`](2026-10-12-b01-internal-compass.md).
- Control-wiring bar: `docs/evaluation.md` §7.
- Circuit: `circuits/flywire-fafb-olfactory-1536.md` (FlyWire FAFB
  v783 via the public FlyBridge atlas, MIT).
