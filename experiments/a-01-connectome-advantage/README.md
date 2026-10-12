# A-01 — does the FlyWire-derived olfactory wiring win on learnable tasks?

**Question.** S2 (`experiments/scorer/`) trained this circuit on a *fixed
corpus* and found the shuffled wiring null (92.2 vs 92.9): on a
tanh-rate, small-corpus, head-dominated setup the gain was in the
encoder, not the connectome. The spiking first campaign
(`experiments/control-comparison/`, report
`../../reports/2026-10-05-first-campaign.md`) found the opposite in the
*stimulus-response* regime: the same kind of wiring sustains ~3.7× the
activity of a target-permuted control. A-01 is the sharper test of the
first question: on **generated, learnable multi-class classification
tasks with real training** (not corpus replay), does the real wiring
beat matched controls and conventional architectures of comparable
size — in accuracy, data efficiency, or noise robustness?

**Circuit.** `flywire-fafb-olfactory-1536`
([`../../circuits/flywire-fafb-olfactory-1536.md`](../../circuits/flywire-fafb-olfactory-1536.md)):
1,536 nodes, 42,921 signed edges (FlyWire FAFB v783 via the public
FlyBridge atlas, MIT). The staged copy in this environment is verified
by sha256 `ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227`
before any run; the hash is recorded in `results/manifest.json`.

**Dynamics declaration (assumption, per run).** The scorer's
tanh-rate core, reused verbatim in `circuit.py`: per-node leak, signed
per-edge gain, `tanh` hidden state, 4 internal propagation steps per
input. This is a *model* on the graph; nothing here claims biological
fidelity of the dynamics.

**Trained vs frozen (identical for every arm).**

| Frozen (never updated) | Trained |
|---|---|
| topology (which node connects to which), base edge magnitudes (`log1p\|w\|`, per-target-normalized), per-edge gain parameters (zero-init → gain 1.0), per-node leak (zero-init → 0.5), per-node bias (zero-init → 0) | state encoder (16-d → 256-d → 256-d, ELU + LayerNorm), sensory drive (256-d → the 256 drive-channel nodes), readout (LayerNorm over the 384 output nodes), per-task linear head (384-d → K) |

i.e. the *strictest* wiring test (pure-wiring passthrough, as in the
scorer toy/S2): **only the connectivity varies across arms.**

**Control taxonomy** (`docs/architecture.md`; all deterministic, one
recorded numpy seed each, assert-checked invariants in `controls.py`,
edge-array sha256 recorded in the manifest):

| Control | Seed | Preserves (asserted) | Breaks (intended) |
|---|---|---|---|
| `degree` | 20261013 | per-node in/out degree, edge count, edge-magnitude multiset | which source→target each edge is, per-source magnitude profile, per-node E/I balance |
| `sign` | 20261014 | degree + per-node E/I balance (in and out), per-source outgoing magnitude multiset, edge count | specific source→target pairing |
| `weight` | 20261015 | degree + per-edge magnitude multiset (global and per-source outgoing), edge count | per-node E/I balance, specific source→target pairing of strong edges |
| `population` | 20261016 | degree + per population-pair edge counts, per-block magnitude multiset | node-level pairing, per-node E/I balance |
| `disconnected` | — (no seed) | nodes only | all edges; the readout sees no circuit activity → majority-class floor. **Run on T1 only** (pre-registered): it is the "any wiring effect at all?" null, and on T2 it degenerates to the same constant floor. |

The controls form a strength gradient: `disconnected` < `degree` <
`weight` ≈ `sign` < `population` < `fly`. A result is only interpretable
relative to the *strongest* control the fly still beats.

**Tasks (generated — declared).** Two multi-class odor-discrimination
tasks. An "odor" is a 16-d vector: for each class *c* a prototype
`p_c = g_c · u_c` (random unit direction `u_c` in 16-d, random norm
`g_c ∈ U[2.5, 3.5]`), and an instance `x = p_c + N(0, 0.75²·I₁₆)`.

- **T1**: 3 classes. **T2**: 6 classes.
- 2,048 instances per task, master seed **20261012**. Fixed split: the
  first 1,024 of the master-seed permutation are the **held-out test
  set**; the remaining 1,024 are the training fold. The test set is
  never used in training or in any selection.
- **Input noise condition:** evaluation on the test set at three levels
  of additive Gaussian noise on the 16-d input, σ ∈ {0.0, 0.75, 1.5}
  ("clean", "mid", "max"); a single fixed noise realization per
  (task, level) — identical for every arm. Models are trained on
  clean (generation-noise only) inputs.
- **Data-efficiency condition:** the 50% and 10% training sets are the
  first 512 / 102 rows of the master-seed training order (fixed
  prefixes; the test set is untouched).

**Conventional baselines (same 16-d in → K-out interface).**

- **MLP**: 16→512 ReLU → 512 ReLU → K.
- **GRU**: one GRU(16→256) time step → 256-d state → K.

`baselines.py` reports both parameter budgets against the A-01 model's
(same encoder/drive/readout/head, ~0.20 M trained params; the circuit's
frozen params are excluded from every arm's budget identically).

**Training protocol (identical for every arm and seed).** Adam,
lr = 2.5e-3, batch 256, cross-entropy on the head, 4 CPU threads,
`torch.manual_seed(seed)` for init and data shuffling. Epoch cap
**300**; early stop at patience **30** epochs without an internal-val
improvement (10% of the training fold, split by the run seed — never
the test set); best-internal-val weights are kept. One held-out
evaluation per model, at the three noise levels.

**Grid.** Wirings {fly, degree, sign, weight, population,
disconnected-on-T1-only} × tasks {T1, T2} × seeds {100, 101, 102, 103,
104} (11 wiring-task cells × 5 = 55 runs), plus {MLP, GRU} × {T1, T2}
× 5 (20 runs). Data-efficiency sub-grid (run after the main grid, once
the best control is known): fly at 10% and 50% data, and the
**best-control** at 50% data, each on {T1, T2} × 5 seeds (30 runs).
Per run: one JSON in `results/` (held-out accuracy at all three noise
levels, final training accuracy, best internal-val accuracy, wall time,
peak RSS, epochs run, data fraction, torch version, hardware role,
trained-weights sha256). Plus `summary.json` (mean ± sd over seeds per
cell) and `manifest.json` (circuit sha256, control seeds and control
edge-array hashes, master seed, run seeds, library versions, hardware
role "4-core CPU host, 12 GB RAM", epoch cap, noise levels).

**Metrics.** Held-out accuracy (primary, at all three noise levels),
training accuracy (memorization monitor), data requirement (10%/50%
sub-grid), wall time, peak RAM, run-to-run spread (mean ± sd over 5
seeds per cell).

**Pre-registered pass criteria (frozen before the first evaluation;
the held-out test set is the only arbiter).**

- **(a) "wiring matters":** on held-out T1 (clean), `fly` beats the
  **best control** wiring by **>2 accuracy points in ≥4 of 5 seeds**,
  *and* `fly` beats **both** conventional baselines (MLP and GRU) on
  mean held-out T1 accuracy. "Best control" = the control wiring with
  the highest mean held-out T1 (clean) accuracy in the main grid
  (tie-break: the more strongly preserving control — population over
  weight over sign over degree over disconnected).
- **(b) "data efficiency":** `fly` trained on **10%** of the data ≥
  the best control trained on **50%** of the data, on held-out T1
  (clean), mean over seeds (reported for T2 as well).
- **(c) "noise robustness":** `fly`'s accuracy drop from clean to max
  noise (held-out T1, mean over seeds) ≤ the best control's drop.

A criterion that fails is reported as such. **A null is a valid,
publishable outcome**: if the fly wiring does not clear (a), the
result is "on this tanh-rate learning setup, the connectome-specific
structure added no measurable signal beyond the matched controls", and
the report states which control it did/did not beat.

**Compute budget and shrink path.** One 50-epoch fly/T1 benchmark run
first; per-run epoch cap 300; total wall ≤ ~3 h. If the projection
overruns, shrink in this order and record what the reduced grid can
and cannot establish: (1) drop T2 from the data-efficiency sub-grid
(10% vs 50% then stands on T1 only — criterion (b) is pre-registered on
T1), (2) drop the whole T2 column (criteria then stand on T1 only;
"generalizes across task sizes" becomes untestable), (3) 5 → 3 seeds
(per-seed counts in criterion (a) re-scale to "≥3 of 3").

**What a pass does not establish.** Biological function of the olfactory
circuit, that the tanh dynamics are the right dynamics (the S2 null and
the spiking 3.7× result already show the answer is
dynamics-dependent), that the fly wiring is "faithfully emulated" (it
is a graph plus an assumed rate model), or any claim beyond "driven and
read out this way, on these generated tasks".

**Files.** `circuit.py` (dynamics, reused from
`../scorer/scorer/circuit.py`), `controls.py` (control generators +
invariants), `tasks.py` (generation, splits, noise), `baselines.py`
(MLP/GRU + budgets), `run.py` (grid driver + summary/manifest),
`results/` (per-run JSON, `summary.json`, `manifest.json`).
