# A-02 — does the wiring matter when it is ALLOWED TO LEARN?

**Question.** A-01
(`../a-01-connectome-advantage/`, report
`../../reports/2026-10-12-a01-connectome-advantage.md`) froze the
1,536-node FlyWire-derived olfactory circuit at zero-init (the 42,921
edge gains at gain 1.0, per-node leak 0.5, per-node bias 0 — the
pure-wiring passthrough, the strictest wiring test) and found an
honest null: on generated learnable tasks, fly wiring ≈
degree/shuffled controls ≈ MLP/GRU baselines. The A-01 report's
follow-up #1 is this experiment: re-run the **same** battery with the
**FlyBridge full-curriculum treatment** — the circuit's 42,921 edge
gains (plus per-node leaks and biases) **trainable** instead of
frozen — so the wiring can adapt its own weights during learning.
Scientific question: was the zero-init freeze suppressing the
wiring's usefulness? If trainable-fly now beats its controls/baselines,
the A-01 null was a **freeze artifact**; if it still ties, the wiring
carries **no learnable signal** in this task family at all — a
*stronger* null.

**Circuit.** `flywire-fafb-olfactory-1536`
([`../../circuits/flywire-fafb-olfactory-1536.md`](../../circuits/flywire-fafb-olfactory-1536.md)):
1,536 nodes, 42,921 signed edges (FlyWire FAFB v783 via the public
FlyBridge atlas, MIT). The staged copy in this environment is verified
by sha256 `ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227`
before any run; the hash is recorded in `results/manifest.json`.

**Dynamics declaration (assumption, per run).** The scorer's
tanh-rate core, reused verbatim via `circuit.py` (tanh hidden state,
per-node leak, signed per-edge gain, 4 internal propagation steps per
input). Same model on the same graph as A-01; nothing here claims
biological fidelity of the dynamics.

**Trained vs frozen — the one thing that changes vs A-01.**

| Frozen (never updated) | Trained |
|---|---|
| topology (which node connects to which), base edge magnitudes (`log1p\|w\|`, per-target-normalized, signed) | **circuit edge gains (42,921, zero-init → gain 1.0), per-node leak (1,536, zero-init → 0.5), per-node bias (1,536, zero-init → 0)**, state encoder (16-d → 256-d → 256-d, ELU + LayerNorm), sensory drive (256-d → the 256 drive-channel nodes), readout (LayerNorm over the 384 output nodes), per-task linear head (384-d → K) |

The zero-init convention is **identical to A-01**, so A-02's initial
state is byte-identical to A-01's frozen state: the only difference
between the two experiments is that the circuit parameters now receive
gradients (Adam, same lr as every other parameter). This is the
FlyBridge full-curriculum treatment. In **every** circuit arm (fly and
every control) the same treatment applies — the arm's own wiring
parameters train; only the wiring *pattern* differs across arms. The
MLP/GRU arms have no circuit and are re-run identically to A-01 (same
seeds/data) so the comparison stands on the same data. Total model
budget: 184,364 params (T1) / 185,519 (T2) in circuit arms —
identical to A-01's total; of these, the 45,993 circuit params that
A-01 kept frozen (42,921 gains + 1,536 leaks + 1,536 biases) are now
trainable, the remaining 138,371 (T1) / 139,526 (T2) were already
trainable in A-01. The per-run JSON reports `params_trained` = total
model params (same convention as A-01's runs).

**Control taxonomy** (`docs/architecture.md`; **byte-identical to
A-01** — `controls.py` copied verbatim: same recorded numpy seeds,
same assert-checked invariants, same edge-array hashes in the
manifest):

| Control | Seed | Preserves (asserted) | Breaks (intended) |
|---|---|---|---|
| `degree` | 20261013 | per-node in/out degree, edge count, edge-magnitude multiset | which source→target each edge is, per-source magnitude profile, per-node E/I balance |
| `sign` | 20261014 | degree + per-node E/I balance (in and out), per-source outgoing magnitude multiset, edge count | specific source→target pairing |
| `weight` | 20261015 | degree + per-edge magnitude multiset (global and per-source outgoing), edge count | per-node E/I balance, specific source→target pairing of strong edges |
| `population` | 20261016 | degree + per population-pair edge counts, per-block magnitude multiset | node-level pairing, per-node E/I balance |
| `disconnected` | — (no seed) | nodes only | all edges; the readout sees no circuit activity → majority-class floor. **Run on T1 only** (pre-registered, as in A-01). |

Every control's 42,921 (or 0) own edge gains + its nodes' leaks +
biases train under the same treatment — the question is which
*pattern* of trainable wiring learns best.

**Tasks (declared generated — verbatim A-01 `tasks.py`).** Same
generated multi-class odor-discrimination tasks as A-01: 16-d
Gaussian-blob prototypes; **T1** = 3 classes, **T2** = 6 classes;
2,048 instances per task, master seed **20261012**; fixed held-out
test set (1,024 per task, first half of the master-seed permutation),
never used in training or selection; evaluation at three additive
input-noise levels σ ∈ {0.0, 0.75, 1.5} with the **same fixed noise
realizations** as A-01; data-efficiency fractions = fixed prefixes of
the master-seed training order. Because tasks, seeds, splits and noise
realizations are verbatim A-01's, every A-02 number is directly
comparable to the A-01 frozen number for the same (arm, task, seed).

**Conventional baselines (verbatim A-01 `baselines.py`).** MLP
(16→512 ReLU →512 ReLU→K) and GRU (one GRU(16→256) time step →K), same
parameter ballast class as the circuit arms.

**Training protocol (identical for every arm and seed, identical to
A-01).** Adam, lr = 2.5e-3, batch 256, cross-entropy on the head, 4
CPU threads (no parallel inner threads beyond the default),
`torch.manual_seed(seed)` for init and data shuffling. Epoch cap
**300**; early stop at patience **30** epochs without an internal-val
improvement (10% of the training fold, split by the run seed — never
the test set); best-internal-val weights kept. One held-out
evaluation per model, at the three noise levels.

**Grid (pre-registered).** Wirings {fly, degree, sign, weight,
population, disconnected-on-T1-only} × tasks {T1, T2} × seeds
{100, 101, 102, 103, 104} (75 main runs), plus {MLP, GRU} × {T1, T2}
× 5 (20 runs); data-efficiency sub-grid: **fly @10%, fly @50%,
degree @50%** × {T1, T2} × 5 seeds (30 runs). The degree @50% arm
reuses A-01's "best control" resolution (degree was the highest mean
T1 in the A-01 main grid). **105 runs total, identical in structure
to A-01's**; the shrink path below may reduce it.

**Shrink path (pre-registered, applied in order, outcome recorded in
this README before the main grid starts and in the report).**

1. **Sizing.** One 50-epoch fly/T1 benchmark run first, then one
   full-cap (300-epoch, early stop) fly/T1 seed-100 run. Reference:
   A-01's measured fly/T1 cost ≈ 2.06 s/epoch (50 epochs ≈ 110 s).
2. **Seeds.** If the 50-epoch benchmark wall exceeds **4× the A-01
   reference (>440 s)** (i.e. >≈8.8 s/epoch), the grid shrinks to
   **3 seeds (100–102)** and the report says so; criterion (a) then
   stands on "≥3 of 3 seeds".
3. **Projection.** After the full-cap sizing run, project total wall
   = 1.3 × (measured sizing-run per-epoch × 100 epochs × number of
   circuit runs) + 1.3 × (measured × 30 × number of baseline runs)
   (100 = conservative epochs-to-early-stop bound; A-01's were
   31–49; 1.3 = shared-4-core-host factor). If the projection
   exceeds **3 h**, shrink in this order, recomputing after each
   step: (i) drop `sign` + `weight` from the main grid; (ii) drop
   T2 from the data-efficiency sub-grid (criterion (b) then stands
   on T1); (iii) drop T2 from the main grid entirely (all criteria
   stand on T1; "generalizes across task sizes" becomes
   untestable). The final grid and the reason for each shrink step
   are recorded here and in the report.

**Metrics.** Held-out accuracy (primary, all three noise levels),
training accuracy (memorization monitor), data requirement
(10%/50% sub-grid), wall time, peak RAM, run-to-run spread (mean ±
sd over seeds per cell), per-epoch cost (trainable circuit is
expected to be slower than A-01's frozen one).

**Pre-registered pass criteria (frozen before the first evaluation;
the held-out test set is the only arbiter).**

- **(a) "wiring matters" (learnable version):** on held-out T1
  (clean), trainable-`fly` beats the **best trainable control** by
  **>2 accuracy points in ≥4 of 5 seeds** (≥3 of 3 if shrunk per the
  seed rule), *and* trainable-fly beats **both** conventional
  baselines (MLP and GRU) on mean held-out T1 accuracy. "Best
  control" = the control wiring with the highest mean held-out T1
  (clean) accuracy in the main grid (tie-break: the more strongly
  preserving control — population over weight over sign over degree
  over disconnected).
- **(b) "data efficiency":** trainable-`fly` trained on **10%** of
  the data ≥ trainable-`degree` trained on **50%** of the data, on
  held-out (clean), mean over seeds — pre-registered on **T1**,
  reported for T2 as well.
- **(c) "noise robustness":** trainable-fly's accuracy drop from
  clean to max noise (held-out T1, mean over seeds) ≤ the best
  control's drop.
- **(d) "freeze effect" (new in A-02):** for each criterion (a)–(c),
  compare the A-02 (trainable) verdict with the A-01 (frozen)
  verdict (all three failed in A-01). Any **flip** (fail→pass or
  pass→fail) is reported with: which criterion flipped, the sizes of
  the two effects, and whether the flip is larger than the per-seed
  spread (sd over 5 seeds in the relevant cell). A flip smaller than
  the per-seed spread is reported as "no measurable freeze effect
  beyond run-to-run noise".

A criterion that fails is reported as such. **A null is a valid,
publishable outcome**: if the fly wiring does not clear (a) with
trainable gains, the result is a *stronger* null than A-01's — on
this task family and dynamics the wiring structure carries no
learnable signal even when the wiring may fit its own weights — and
the report states which control it did/did not beat and which, if
any, criterion flipped (d).

**Comparison design.** A-02's `summary.json` embeds the matching
A-01 frozen cells (same arm/task/fraction keys, read from
`../a-01-connectome-advantage/results/summary.json`), and the report
tables every cell side-by-side: A-01 frozen vs A-02 trainable, per
arm, so "did training unlock a wiring effect?" is answered per arm,
not just per fly.

**What a pass does not establish.** Biological function of the
olfactory circuit, that the tanh dynamics are the right dynamics
(the wiring effect is already known to be dynamics-dependent:
spiking 3.7× vs tanh-rate null), that the fly wiring is "faithfully
emulated" (it is a graph plus an assumed rate model), or any claim
beyond "driven and read out this way, on these generated tasks". A
pass also does not show the gains learned something fly-specific
(better controls would train the same way) — it shows only that the
fly *pattern* of trainable wiring is at least as learnable as its
controls on this task family.

**Files.** `circuit.py` (A-01 dynamics, un-frozen variant + a
`trainable()` accessor), `controls.py` (verbatim A-01: generators +
invariants), `tasks.py` (verbatim A-01), `baselines.py` (verbatim
A-01), `run.py` (grid driver + summary/manifest), `results/`
(per-run JSON, `summary.json` incl. A-01 reference, `manifest.json`).

---

## Sizing outcome (recorded after the sizing runs, per the pre-
registered ladder)

- **50-epoch fly/T1 benchmark:** 304.5 s wall → **6.09 s/epoch = 3.0×
  the A-01 reference** (A-01 measured 2.06 s/epoch frozen on the same
  box) — *below* the 4× rule, so **5 seeds stand** (step 1 not
  triggered).
- **Full-cap sizing run (fly/T1/s100):** early stop at **31 epochs**
  (identical to A-01's T1 convergence; internal val reaches 1.0
  early and the patience-30 tail is 30 flat epochs), **189.6 s wall**.
  Held-out: 0.9980 / 0.9727 / 0.8457.
- **Projection with measured per-run walls** (T1 circuit ≈ 190 s,
  T2 circuit ≈ 250–280 s by A-01's T2 ratio, T1 deff ≈ 120–190 s,
  baselines ≈ 5 s, × 1.3 shared-host factor):
  full 105-run grid ≈ 6–7 h → over budget; drop sign+weight →
  ≈ 5–6 h → over; drop T2-deff → ≈ 4–5 h → over; **drop T2 from
  the main grid → ≈ 2.2 h → within budget**. (The conservative
  ×100-epoch projection of the ladder points the same way at every
  step; the measured per-run wall is used for the final number.)

**Final grid (frozen now, before the remaining runs):**
{fly, degree, population, disconnected-on-T1-only, MLP, GRU} × **T1**
× seeds 100–104 (30 runs; fly/T1/s100 is the sizing run) + data-
efficiency T1: fly@10%, fly@50%, degree@50% × 5 seeds (15 runs).
**45 runs total.**

Consequences, stated up front (they enter the report):
- criteria (a), (c), (d) stand on T1 (as pre-registered, they are T1
  criteria); criterion (b) stands on T1 (pre-registered on T1) — the
  T2 clause of (b) and any T2 fly-vs-controls comparison are
  **untestable in this run** and are reported as such; the A-01
  frozen T2 numbers remain the T2 reference of record.
- `sign` and `weight` are absent from the trainable grid; the
  "best control" resolves among {degree, population, disconnected},
  which includes A-01's actual best control (degree).
- the 1.3× factor also covers the observed contention (a sibling
  campaign process at ~90% of one core during sizing).
