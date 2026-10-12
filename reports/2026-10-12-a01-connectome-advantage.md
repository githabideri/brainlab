# 2026-10-12 — A-01: does the FlyWire-derived olfactory wiring win on learnable tasks?

## Goal

S2 (`experiments/scorer/`, report `2026-10-05-scorer-polis-s2-screen.md`)
found the shuffled wiring null on a *recorded corpus* (92.2 vs 92.9):
the gain was in the encoder, not the connectome. The spiking first
campaign (`experiments/control-comparison/`, report
`2026-10-05-first-campaign.md`) found the opposite in the
*stimulus-response* regime (fly ~3.7× the spiking of a target-permuted
control). A-01 was the sharper test of the connectome question: on
**generated, learnable multi-class classification tasks with real
training** — not corpus replay — does the real wiring beat matched
controls or conventional architectures of comparable size, in accuracy,
data efficiency, or noise robustness?

## Setup

- **Circuit:** `flywire-fafb-olfactory-1536` — 1,536 nodes, 42,921
  signed edges (FlyWire FAFB v783 via the public FlyBridge atlas, MIT),
  staged copy verified at sha256
  `ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227`.
- **Dynamics (declared assumption):** the scorer's tanh-rate core —
  per-node leak, signed per-edge gain, 4 internal propagation steps per
  input, readout over the 384 output nodes. The whole circuit is
  **frozen at zero-init** (gain 1.0, leak 0.5, bias 0): the pure-wiring
  passthrough, the strictest test of the wiring.
- **Trained (identical for every arm):** 16-d → 256-d encoder,
  256 → 256-d sensory drive, LayerNorm readout over the 384 output
  nodes, per-task linear head. 184,364 trainable params (T1) / 185,519
  (T2). The frozen circuit contributes 45,993 non-trained params in
  every arm identically.
- **Controls** (one recorded numpy seed each, assert-checked
  invariants, edge-array hashes in the manifest; taxonomy per
  `docs/architecture.md`): `degree` (per-node in/out degree + edge
  count), `sign` (degree + per-node E/I balance), `weight` (degree +
  per-edge magnitude multiset), `population` (degree + per
  population-pair edge counts), `disconnected` (nodes only; run on T1
  only, as pre-registered).
- **Tasks (declared generated):** T1 = 3 classes, T2 = 6 classes;
  16-d Gaussian-blob prototypes, 2,048 instances each, master seed
  20261012; fixed held-out test set of 1,024 per task, never used in
  training or selection; evaluation at three additive input-noise
  levels σ ∈ {0.0, 0.75, 1.5} (one fixed realization per task/level,
  identical for all arms).
- **Conventional baselines (same 16-d → K interface):** MLP (16→512
  ReLU →512 ReLU →K; 272,899/274,438 params) and GRU (one
  GRU(16→256) time step →K; 211,203/211,974 params) — i.e. the same
  parameter ballast class as the circuit arms.
- **Training:** Adam 2.5e-3, batch 256, epoch cap 300, early stop at
  patience 30 on a 10% internal-val split of the training fold (best
  weights kept); the held-out test set was touched exactly once per
  model, at the three noise levels.
- **Grid:** 6 wiring arms (disconnected T1-only) × {T1, T2} × 5 seeds
  (100–104) + both baselines × both tasks × 5 seeds (75 main runs);
  data-efficiency sub-grid: fly @10% + fly @50% + best control @50%,
  both tasks × 5 seeds (30 runs). 105 runs total.
- **Hardware (role only):** a 4-core CPU host, 12 GB RAM, torch
  2.14.1 (CPU execution; no CUDA device present), numpy 2.5.4. Total
  wall across all runs: **121 min** — under the 3 h budget, so no
  shrinkage was needed.

## Protocol / commands

```
cd experiments/a-01-connectome-advantage
python3 run.py --circuit <staged-circuit.json> --phase benchmark   # 50-epoch sizing
python3 run.py --circuit <staged-circuit.json> --phase main
python3 run.py --circuit <staged-circuit.json> --phase deff
python3 run.py --circuit <staged-circuit.json> --phase summary
python3 run.py --circuit <staged-circuit.json> --phase manifest
```

## Observations

1. **The null arm behaves exactly as pre-registered.** `disconnected`
   lands at 33.2–33.5% on T1 (the 3-class majority floor, unchanged at
   all three noise levels): with no edges the 384 output nodes receive
   no drive and the readout is a constant. The harness can measure a
   wiring effect when one exists; the floor is where the floor should
   be.
2. **Every non-disconnected arm is at the same ceiling.** T1 (clean,
   mean ± sd over 5 seeds): fly 99.63±0.18, degree 99.86±0.05, weight
   99.79±0.11, sign 99.75±0.23, population 99.63±0.19, MLP 99.80±0.06,
   GRU 99.63±0.19. T2: fly 95.20±0.29, degree 95.41±0.51, sign
   95.86±0.29, weight 95.33±0.17, population 95.18±0.31, MLP
   95.92±0.74, GRU 96.31±0.29. All arms converge at the same epoch
   (≈31 on T1; 33–49 on T2) and sit within 1–2 points of each other,
   i.e. inside their own run-to-run spread.
3. **No arm shows a wiring-specific error signature.** At max noise
   (σ = 1.5) all arms drop to the same band (T1 ≈ 83–85%, T2 ≈
   62–65%), and the per-seed drops are indistinguishable across arms
   (T1: 13.3–19.0 pp, all arms).

## Numbers (held-out, mean ± sd over 5 seeds)

| Arm | T1 clean | T1 σ0.75 | T1 σ1.50 | T2 clean | T2 σ1.50 |
|---|---|---|---|---|---|
| fly | 0.9963±0.0018 | 0.9711 | 0.8342 | 0.9520±0.0029 | 0.6252 |
| degree | **0.9986**±0.0005 | 0.9746 | 0.8465 | 0.9541±0.0051 | 0.6338 |
| sign | 0.9975±0.0023 | 0.9732 | 0.8465 | **0.9586**±0.0029 | 0.6338 |
| weight | 0.9979±0.0011 | 0.9752 | 0.8475 | 0.9533±0.0017 | 0.6352 |
| population | 0.9963±0.0019 | 0.9678 | 0.8334 | 0.9518±0.0031 | 0.6248 |
| disconnected (T1 only) | 0.3334±0.0013 | 0.3334 | 0.3334 | — | — |
| MLP | 0.9980±0.0006 | 0.9748 | 0.8488 | 0.9592±0.0074 | 0.6420 |
| GRU | 0.9963±0.0019 | 0.9699 | 0.8543 | 0.9631±0.0029 | 0.6443 |

Data-efficiency sub-grid (held-out clean; "best control" = degree, the
highest mean T1 in the main grid, 0.9986):

| Arm / data | T1 | T2 |
|---|---|---|
| fly @100% | 0.9963±0.0018 | 0.9520±0.0029 |
| fly @50% | 0.9895±0.0068 | 0.9396±0.0127 |
| fly @10% | 0.9902±0.0046 | 0.8477±0.0569 |
| degree @50% | **0.9975**±0.0010 | **0.9539**±0.0071 |

**Pre-registered criteria — all three fail (null):**

- (a) *wiring matters:* **fail.** fly beats the best control (degree,
  0.9986) by >2 points in **0/5** seeds — it is below or tied with the
  best control on every seed (0.9932–0.9980 per seed vs 0.998–0.999),
  and its mean (0.9963) also loses to the MLP (0.9980).
- (b) *data efficiency:* **fail.** fly @10% (0.9902) < degree @50%
  (0.9975) on T1 (also on T2: 0.8477 < 0.9539).
- (c) *noise robustness:* **fail, by a whisker.** fly's clean→max
  drop is 16.21 pp vs 15.21 pp for the best control; the per-seed
  spreads overlap (fly 15.1–19.0 pp, degree 14.8–15.7 pp), and GRU has
  the smallest drop of all arms (14.20 pp).

## Conclusion

**On generated learnable tasks in the tanh-rate regime, the
FlyWire-derived olfactory wiring is indistinguishable from its matched
controls and from conventional MLP/GRU networks of the same size.**
This is an honest null, and it is the result this experiment existed
to produce: S2's shuffled-wiring null was not a corpus artifact. With
a proper learning battery — generated multi-class tasks, a full
control gradient from "no edges" to "population structure only", fixed
held-out splits, five seeds, and conventional baselines — the fly
wiring's specific source→target structure, its E/I placement, and its
weight placement carry **no measurable signal** beyond what any
non-disconnected wiring (or a plain MLP) provides. Functionally, in
this regime the circuit is a learned-transparent buffer: the
encoder→drive→readout path does the work, and the readout is rich
enough to bypass the wiring entirely.

**The regime contrast is the load-bearing result.** The same substrate
shows: spiking (AlphaLIF, stimulus-response) → fly sustains ~3.7× the
activity of a target-permuted control and the response landscape is
nearly uncorrelated (ρ = 0.13) — the wiring *does* matter there.
tanh-rate (corpus, S2) → null. tanh-rate (generated learning tasks,
A-01) → null, now with the full control battery. The wiring effect is
**dynamics-dependent**, and the two independent nulls in the tanh-rate
regime (one on recorded data, one on generated data with real
training) rule out the "the S2 corpus was too small / too structured"
escape.

**What the numbers do not show.** Not "the wiring is useless" or
"biology is irrelevant": (i) only one dynamics was tested on the
learning question — the zero-init frozen tanh circuit is the
*strictest* test of the wiring; the FlyBridge full curriculum (where
edge gains, leaks and biases train) is a different experiment and
could change this result; (ii) only one organism circuit and one
task family (Gaussian blobs in 16-d) — the 16-d input is a bottleneck
the encoder can route around, and a task whose solution needs the
circuit's internal state (e.g. sequential/temporal structure) was not
in this battery; (iii) nothing about spiking function or about the fly;
(iv) the T2 @10% cell (0.8477±0.0569) is the noisiest one — the
data-efficiency conclusion at T2 rests on 5 seeds of a wide band;
(v) the near-ties (fly 0.9963 vs population 0.9963) are inside the
seeds' own spread, so no sub-point advantage is claimed in either
direction.

## What failed

Nothing mechanical: all 105 runs completed, invariants held, the
disconnected floor landed exactly where pre-registered, total wall
121 min < budget. Two process notes, kept on purpose: the first main
grid omitted the two conventional baselines (a driver bug, caught and
re-run before any analysis — the 55 circuit-arm runs were untouched),
and criterion (c) failed by less than the run-to-run noise, which is
reported as a fail per the pre-registered rule, not waived.

## Artifacts

`experiments/a-01-connectome-advantage/`: README (protocol, written
before the run), `circuit.py` (dynamics reused from
`../scorer/scorer/circuit.py`), `controls.py` (generators +
invariants), `tasks.py`, `baselines.py`, `run.py`; `results/` — 105
per-run JSON (held-out at 3 noise levels, train acc, wall, peak RSS
≤1.0 GB, epochs, weights sha256), `summary.json` (21 cells),
`manifest.json` (circuit sha256, control seeds + edge-array hashes,
master seed 20261012, run seeds, torch 2.14.1 / numpy 2.5.4, hardware
role). Report date: 2026-10-12.

## Next (follow-ups, not part of this experiment)

1. **Same battery, learnable edge gains** — the FlyBridge full
   curriculum: do the 42,921 gains, once trained, make the fly wiring
   beat the controls? (The strict zero-init test here cannot answer
   it.)
2. **Temporal tasks** — sequential multi-step input where the readout
   cannot bypass the circuit's internal state (the A-01 bottleneck is
   the known bypass route).
3. **Spiking + learning** — AlphaLIF (or similar) with reward/gradient
   on the generated tasks: the first-campaign's 3.7× is stimulus-response
   only; whether the wiring advantage survives *learning* in the
   spiking regime is the open corner of the 2×2 (dynamics × task type).

## Review note — 2026-10-12 (post-hoc)

Independently reviewed: the protocol and the five matched controls were
confirmed as declared — in particular the `weight` control preserves the
per-edge magnitude multiset (global and per-source), so this battery is
**not** affected by the weight-distribution confound found in B-01's
2-switch shuffle, and the zero-init frozen design makes weight handling
explicit. No corrections; the null stands as written.
