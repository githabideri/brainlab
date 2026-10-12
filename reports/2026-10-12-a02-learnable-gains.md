# 2026-10-12 — A-02: does the wiring matter when it is allowed to learn?

## Goal

A-01 (report
`2026-10-12-a01-connectome-advantage.md`) froze the 1,536-node
FlyWire-derived olfactory circuit at zero-init — the pure-wiring
passthrough, the strictest wiring test — and found an honest null on
generated learnable tasks. Its follow-up #1 is this experiment: the
**same battery, FlyBridge full-curriculum treatment** — the circuit's
42,921 edge gains (plus per-node leaks and biases) **trainable**
instead of frozen, topology and base magnitudes still frozen — so the
wiring can adapt its own weights during learning. Question: was the
zero-init freeze suppressing the wiring's usefulness? Pass → the A-01
null was a freeze artifact; tie → a **stronger** null (the wiring
carries no learnable signal in this task family at all).

## Setup

- **Circuit:** `flywire-fafb-olfactory-1536` — 1,536 nodes, 42,921
  signed edges (FlyWire FAFB v783 via the public FlyBridge atlas, MIT),
  staged copy verified at sha256
  `ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227`
  (recorded in `results/manifest.json`).
- **Dynamics (declared assumption):** the same tanh-rate core as A-01
  (per-node leak, signed per-edge gain, 4 internal propagation steps,
  readout over the 384 output nodes).
- **The one change vs A-01:** the circuit's zero-init parameters
  (edge gains → gain 1.0, leaks → 0.5, biases → 0 — identical initial
  values to A-01's frozen state) now receive gradients, in **every**
  circuit arm under the same treatment; only the wiring *pattern*
  differs across arms. Total model budget per circuit arm: 184,364
  params (the A-01 number; 138,371 of them were already trained in
  A-01, the 45,993 circuit params are newly trainable).
- **Controls:** byte-identical to A-01's (verbatim `controls.py`, same
  recorded numpy seeds, same assert-checked invariants, same
  edge-array hashes in the manifest): `degree`, `population`,
  `disconnected` (T1 only, as pre-registered), plus the MLP/GRU
  conventional baselines re-run on the same seeds. `sign` and `weight`
  were in the pre-registered full grid but were removed by the
  pre-registered shrink ladder (below); they are **not** part of this
  run's grid.
- **Tasks:** the A-01 tasks verbatim — generated 3-class (T1)
  Gaussian-blob odor discrimination, 16-d, 2,048 instances, master
  seed 20261012, fixed held-out test set (1,024, never used in
  training or selection), three additive input-noise levels
  σ ∈ {0.0, 0.75, 1.5} with the same fixed realizations as A-01;
  10%/50% data-efficiency fractions = fixed prefixes of the
  master-seed training order. **T2 (6-class) is not in this run's
  grid** (shrink ladder, below); the A-01 frozen T2 numbers remain the
  T2 reference of record.
- **Training:** Adam 2.5e-3, batch 256, epoch cap 300, early stop at
  patience 30 on a 10% internal-val split (best weights kept), 4 CPU
  threads; held-out test set touched exactly once per model, at the
  three noise levels. Identical to A-01 in every respect except the
  treatment.
- **Grid (frozen after the sizing runs, per the pre-registered
  shrink ladder):** main {fly, degree, population, disconnected-T1,
  MLP, GRU} × T1 × seeds 100–104 (30 runs) + data-efficiency
  {fly@10%, fly@50%, degree@50%} × T1 × 5 (15 runs). **45 runs.**
  The ladder: the 50-epoch benchmark (6.09 s/epoch = 3.0× the A-01
  reference 2.06) did **not** trigger the 4× rule, so 5 seeds stand;
  the measured full-run wall (~190 s/run, 31 epochs) made the
  pre-registered 105-run structure project to ~6–7 h, so the ladder
  removed sign+weight, then T2-deff, then T2-main. See the "Sizing
  outcome" section of the experiment README.
- **Hardware (role only):** a 4-core CPU host, 12 GB RAM, torch
  2.14.1 (CPU execution), numpy 2.5.4. Total wall across all 45 runs:
  **86 min** (the sizing runs are included in the 45; a sibling
  campaign process held ~90% of one core during part of the run — the
  grid ran single-threaded-per-process as pre-registered).

## Protocol / commands

```
cd experiments/a-02-learnable-gains
python3 run.py --circuit <staged-circuit.json> --phase benchmark        # 50-ep sizing (304.5 s)
python3 run.py --circuit <staged-circuit.json> --phase main --arms fly --tasks T1 --seeds 100   # full-cap sizing run
#   (shrink ladder applied here — final grid frozen in README)
python3 run.py --circuit <staged-circuit.json> --phase main --arms fly,degree,population,disconnected,mlp,gru --tasks T1
python3 run.py --circuit <staged-circuit.json> --phase deff --tasks T1
python3 run.py --circuit <staged-circuit.json> --phase summary          # embeds matching a-01 frozen cells
python3 run.py --circuit <staged-circuit.json> --phase manifest
```

## Observations

1. **The pipeline replicates A-01 where nothing changed.** The GRU
   re-runs are **identical** to A-01's (same seeds, same code, no
   circuit → deterministic): all five held-out values match to 4
   decimals at all three noise levels; MLP matches within ≤1/1024 on
   every value; the disconnected floor lands at 0.3336 (A-01:
   0.3334) — the 3-class majority bound, unchanged at all noise
   levels, exactly as pre-registered. Any difference below is
   attributable to the treatment, not to drift.
2. **The trainable circuit converges at the same epoch.** Every
   non-disconnected circuit arm early-stops at 31–33 epochs, identical
   to A-01 (31 on T1): adding 45,993 trainable params neither slowed
   nor sped convergence. Cost per epoch tripled (2.06 → ~6.1 s, the
   backward pass through 4 propagation steps of 42,921 edges).
3. **Training the wiring did not unlock an effect — and did not
   measurably hurt one.** Same-seed frozen→trainable deltas on held-out
   T1 (clean): fly −0.14 pp, degree −0.06 pp, population −0.37 pp
   mean; at σ1.5: fly −0.86 pp, degree −0.02 pp, population −1.05 pp
   mean. Every delta is inside that arm's own per-seed spread. The
   fly arm's per-seed spread roughly doubled (clean sd 0.0018 →
   0.0039): the extra 42,921 free parameters make the converged state
   more seed-sensitive, but the center of the distribution moved <0.2
   pp.
4. **The same ceiling, the same order.** T1 clean: MLP 0.9982 >
   degree 0.9980 > GRU 0.9963 > fly 0.9949 > population 0.9926 >
   disconnected 0.3336 — the same pack A-01 produced (degree the best
   *control* in both, baselines at the very top, fly in the middle),
   all arms within 1 pp of each other and inside their own
   run-to-run spread.

## Numbers (held-out, mean ± sd over 5 seeds; A-01 frozen vs A-02 trainable, T1)

| Arm | A-01 frozen | A-02 trainable | Δ |
|---|---|---|---|
| fly | 0.9963±0.0018 | 0.9949±0.0039 | −0.14 pp |
| degree | **0.9986**±0.0005 | **0.9980**±0.0009 | −0.06 pp |
| population | 0.9963±0.0019 | 0.9926±0.0035 | −0.37 pp |
| disconnected (T1 only) | 0.3334±0.0013 | 0.3336±0.0012 | +0.02 pp |
| MLP | 0.9980±0.0006 | 0.9982±0.0004 | +0.02 pp |
| GRU | 0.9963±0.0019 | 0.9963±0.0019 | 0.00 pp |

Noise robustness (clean → σ1.5 drop, held-out T1, mean over seeds):
fly 16.93 pp (A-01: 16.21), degree 15.18 (15.21), population 16.97
(16.29), MLP 14.98 (14.92), GRU **14.20** (14.20) — same ordering,
same magnitudes, GRU still most robust.

Data-efficiency sub-grid (held-out T1 clean):

| Arm / data | A-01 frozen | A-02 trainable |
|---|---|---|
| fly @100% | 0.9963±0.0018 | 0.9949±0.0039 |
| fly @50% | 0.9895±0.0068 | 0.9908±0.0086 |
| fly @10% | 0.9902±0.0046 | 0.9855±0.0099 |
| degree @50% | **0.9975**±0.0010 | **0.9975**±0.0010 |

**Pre-registered criteria — verdicts (the held-out test set is the
only arbiter):**

- **(a) "wiring matters" (learnable version): fail.** fly beats the
  best trainable control (degree, 0.9980) by >2 pp in **0/5** seeds
  (per-seed fly−degree: +0.09, +0.09, −0.78, −0.10, −0.87 pp — above
  the best control by at most 0.1 pp on two seeds, below on three, and
  never near the 2 pp bar — the same pattern as A-01), and fly's
  mean (0.9949) also loses to both baselines (MLP 0.9982, GRU
  0.9963).
- **(b) "data efficiency": fail.** trainable fly @10% (0.9855) <
  trainable degree @50% (0.9975) — and below it on **all 5 seeds**
  (−0.10 to −2.93 pp). (The T2 clause is untestable in
  this run — shrink ladder; A-01's frozen T2 pair was 0.8477 <
  0.9539, the same direction.)
- **(c) "noise robustness": fail.** fly's clean→max drop (16.93 pp) >
  the best control's (degree, 15.18 pp) — a 1.75 pp gap; the
  per-seed drop bands (fly 15.23–18.26, degree 14.94–15.53) nearly
  touch, and GRU has the smallest drop of all arms (14.20 pp), as in
  A-01.
- **(d) "freeze effect": no flip on any criterion.** (a), (b) and
  (c) failed in A-01 (frozen) and fail in A-02 (trainable); none
  flipped in either direction, so there is no flip to compare
  against the per-seed spread — the frozen→trainable deltas above
  are all inside it (fly clean sd 0.0039; 0.0018 in A-01). The
  failure margins: (a) fly mean − best control −0.31 pp (inside the
  fly arm's 0.39 pp sd; per-seed fly is within ±0.9 pp of degree on
  every seed and above it by more than 2 pp on none); (b) fly@10% −
  degree@50% −1.20 pp (comparable to the two cells' combined ~1.0 pp
  spread — a consistent *failure*, not a tie); (c) 1.75 pp
  (comparable to the fly arm's per-seed drop spread of 1.64 pp — a
  marginal failure, as in A-01). **Conclusion of (d): no measurable
  freeze effect. The A-01 null was not a freeze artifact.**

**Verdict: a stronger null.** Allowing the fly wiring to learn its
own 42,921 edge gains (plus leaks and biases) on the A-01 task
family does not make it beat its controls or the conventional
baselines on any of the three pre-registered criteria — and it does
not measurably hurt it either (same-seed deltas all inside the
per-seed spread). In this regime the wiring, frozen or trainable, is
indistinguishable from its matched controls and from a plain MLP.

## What the numbers do not show

- **Not "trainable wiring is useless in general".** One circuit, one
  dynamics (tanh-rate), one task family (16-d Gaussian blobs — the
  16-d input is a bottleneck the encoder→drive→readout path can route
  around, the A-01 bypass route), one curriculum (single Adam
  lr = 2.5e-3 for every parameter, 300-epoch cap, no per-group
  learning rates or schedules). A task whose solution *requires* the
  circuit's internal state (sequential/temporal structure), a spiking
  dynamics with learning, or a curriculum shaped per parameter group
  are all different experiments.
- **Not a T2 result.** T2 was removed by the pre-registered shrink
  ladder; the T2 comparison stands on A-01's frozen numbers only.
- **No `sign`/`weight` trainable cells.** The best control resolved
  among {degree, population, disconnected} as frozen; had sign or
  weight beaten degree in the trainable grid, the best-control
  resolution could change — that question is left open, deliberately
  (the grid was frozen before the remaining runs, and expanding it
  after seeing results would be evaluation-data-driven tuning).
- **The small negative drifts (fly −0.14 pp clean; fly @10% −0.47 pp)
  are not claimed to be real**: each is inside the arm's per-seed
  spread (fly clean sd 0.0039; fly@10 sd 0.0099) and the same-seed
  deltas mix signs (+0.20, +0.49, −0.49, 0.00, −0.88 pp). The honest
  statement is "no measurable change either way".
- Nothing about spiking function or about the fly; the circuit is a
  graph plus an assumed rate model, not a faithful emulation.
- The 3.0× per-epoch slowdown is the cost of backpropagating through
  4 propagation steps of 42,921 edges on a 4-core CPU; it bounds how
  much of this grid was affordable, which is why the ladder shrank
  more than the measured convergence (31 epochs vs the ladder's
  conservative 100-epoch bound) strictly required.

## What failed

Nothing mechanical: all 45 runs completed, the control invariants
held, the disconnected floor landed exactly where pre-registered,
total wall 86 min < the 3 h budget. Two process notes, kept on
purpose: (1) the shrink ladder's conservative 100-epoch bound
over-shrank relative to the measured 31-epoch convergence — the run
used 86 of 180 budgeted minutes; per the frozen protocol the grid was
*not* expanded after the sizing result, so the unused budget stayed
unused; (2) a sibling campaign process (an unrelated circuit build)
held ~90% of one core during part of the grid — the pre-registered
1.3× contention factor covered it (measured per-run walls matched the
projection within ~10%).

## Artifacts

`experiments/a-02-learnable-gains/`: README (protocol + pre-registered
criteria + sizing outcome, all written before the affected runs),
`circuit.py` (A-01 dynamics, un-frozen variant with `trainable()`),
`controls.py` / `tasks.py` / `baselines.py` (verbatim A-01 copies with
attribution), `run.py` (grid driver; `--phase benchmark/main/deff/
summary/manifest`); `results/` — 45 per-run JSON (held-out at 3 noise
levels, train acc, wall, peak RSS ≤1.1 GB, epochs, treatment string,
weights sha256), `summary.json` (9 cells; embeds the matching A-01
frozen cells under `a01_frozen`), `manifest.json` (circuit sha256,
control seeds + edge-array hashes, treatment, master seed 20261012,
run seeds 100–104, torch 2.14.1 / numpy 2.5.4, hardware role). Report
date: 2026-10-12.

## Next (follow-ups, not part of this experiment)

1. **Temporal tasks** — the open corner from A-01: multi-step input
   where the 16-d bottleneck cannot be bypassed by the readout; both
   treatments (frozen, trainable) in the same run.
2. **Spiking + learning** — AlphaLIF with reward/gradient on the
   generated tasks: the first campaign's 3.7× is stimulus-response
   only; whether the wiring advantage survives *learning* in the
   spiking regime is the last cell of the 2×2 (dynamics × task type).
3. **Per-group curricula** — if a future task family shows a trainable
   effect for any control family, a shaped curriculum (separate lr /
   schedule for the 42,921 gains vs the head) is the next control to
   add before claiming the effect is wiring-specific.
