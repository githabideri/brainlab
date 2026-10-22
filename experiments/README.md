# experiments/

One directory per experiment. Each directory carries:

- `README.md` — the protocol: question, circuit, stimulus/readout
  definitions, controls, pass conditions, and what a pass does *not*
  establish. Read [../docs/evaluation.md](../docs/evaluation.md) before
  proposing pass conditions.
- the runnable code (small; the heavy lifting is fetch + run + measure)
- `results/` — machine-readable output of the runs (JSON/CSV). Raw spikes
  and large artifacts do not go into the repo; results/ holds the
  aggregated measurements plus a pointer to where the raw artifacts live
  (private storage).

## On the bench

- **control-comparison** (the first experiment): fly vs. shuffled vs.
  disconnected FlyWire wiring, same sugar-GRN stimulus, same AlphaLIF
  model, 5 seeds. **Done — campaign 2026-10-04/05:** the real wiring
  sustains ~3.7× the spiking of shuffled wiring and ~4.2× of the
  disconnected null, and its response landscape is nearly uncorrelated
  with the shuffled one (ρ = 0.13) while shuffled sits close to the null
  (ρ = 0.59). Report: `../reports/2026-10-05-first-campaign.md`;
  aggregates: `control-comparison/results/`.
- **stimulus discriminability** (multi-stimulus: sugar vs water vs salt
  drive; can a downstream readout separate the stimuli better on real
  than on shuffled wiring?) — the direct follow-up that upgrades the
  first campaign's activity-structure result into an information
  result; reuses the same three arms and driver.
- **scorer** (the frozen 1,536-node olfactory circuit as a decision-scoring unit: learned state drive + readout + candidate-list heads, argmax with abstention) — `scorer/`. **First measurements in (2026-10-05):** one decision ≈ 1.2 ms p50 on a 4-core CPU; the 3-class toy learns through the pure-wiring passthrough at epoch 25 (100/100). **S2 in (2026-10-05, the polis decision corpus):** 92.91% on the 141-row held-out val (100% on the stuck→wait abstain slice), zero damaging choices, ~1.1 ms/decision; the shuffled-wiring control is null (92.20) — on this tanh-rate corpus the gain is in the encoder, not the connectome. **S3 in (2026-10-06, live A/B in the polis decision loop):** 10 matched episodes, scorer on/off — the decider-tier pre-veto is a *structural* null: the 27B judge sits downstream of the hook and overwrites it (scorer 91% vs judge 53%; 5 of the judge's 7 wrong picks were already right in the scorer; zero damaging in all 80 rows). The hook is specified as a **pre-judge veto** (S4, with a pre-registered re-run prediction). Reports: `../reports/2026-10-05-scorer-first-measurements.md`, `../reports/2026-10-05-scorer-polis-s2-screen.md`, `../reports/2026-10-06-scorer-polis-s3-ab-pilot.md`; numbers: `scorer/results/`.
- **a-01-connectome-advantage** (does the FlyWire-derived olfactory
  wiring win on *learnable* tasks?) — `a-01-connectome-advantage/`.
  **Done 2026-10-12: null.** Generated 3- and 6-class odor tasks, 105
  runs: fly vs degree/sign/weight/population/disconnected controls and
  MLP/GRU baselines, 5 seeds — every non-disconnected arm (and both
  baselines) sits at the same ceiling (T1 clean 99.6–99.9%, T2
  95.2–96.3%); the pre-registered criteria (a) wiring matters, (b) data
  efficiency, (c) noise robustness all fail; the disconnected floor
  lands at the 33.3% majority bound as predicted. Together with the S2
  corpus null, the tanh-rate learning regime is null for the wiring
  while the spiking stimulus-response regime is not (~3.7×, first
  campaign) — the wiring effect is dynamics-dependent. Report:
  `../reports/2026-10-12-a01-connectome-advantage.md`.
- **a-02-learnable-gains** (same battery, FlyBridge full-curriculum
treatment: the 42,921 edge gains + leaks + biases **trainable**
instead of frozen) — `a-02-learnable-gains/`. **Done 2026-10-12:
stronger null.** 45 runs (T1; the pre-registered shrink ladder
removed T2 and sign/weight on the 3 h budget): no criterion flipped
vs A-01 — (a) wiring matters fail (0/5 seeds >2 pp over best control
degree; mean below MLP/GRU), (b) data efficiency fail (fly@10% 0.9855
< degree@50% 0.9975), (c) noise robustness fail (16.9 pp drop vs
15.2); same-seed frozen→trainable deltas all inside the per-seed
spread. The A-01 null was not a freeze artifact: on this task family
and dynamics the wiring carries no learnable signal even when it may
fit its own weights. The MLP/GRU re-runs replicate A-01 exactly
(GRU bit-identical), the disconnected floor is unchanged. Report:
`../reports/2026-10-12-a02-learnable-gains.md`.
- **a-03-sequential-learning** (the 2×2 grid's open corner: spiking
  dynamics × learning, on *sequential* tasks that cannot saturate —
  delayed-cue T-del, angular integration T-ang, temporal XOR; 6
  wiring controls byte-identical to A-01's; val-**LOSS** checkpointing;
  measured Δw per arm) — `a-03-sequential-learning/`. **Corrected
2026-10-13 (external review P0)**: the v1 pilot's spike-arm scores
(T-del 1.000, T-ang 0.05° / R²=1.0) were a **train/test leak** — the
ridge was fit on the held-out features and their labels — and are
marked evaluation-invalid in the report addendum. The corrected v2
pilot (leak-free fit, explicit sensory addressing, paired per-trial
Poisson with a committed byte-identical spike-train dump, 6 hygiene
regression tests, 21/21 total) finds **no signal above chance** in the
spiking reservoir at pilot budget (T-ang RMCE 75.8–95.4° vs chance
89.8°). Renamed per review: this is a **spiking-reservoir benchmark
with a learned readout** (frozen LIF + trainable ridge), not
spiking+synaptic learning; the genuinely plastic variant is a separate
future experiment. **Review round 4 (2026-10-13) closed the lane**:
preflight fixes (seed-before-construction with bit-identity/same-init
tests, manifest repair, versioned artifacts, version-aware summary,
single-eval path, 24/24 tests) plus a **pre-registered 24-run decision
pilot** (4 arms × 2 tasks × 3 seeds, declared stopping rule) returned
**STOP** — no dynamics satisfies both clauses (tanh: T-del not
same-signed across seeds, T-ang never ≥ 5°; spike: T-del +2.3 pt <
5 pt, though T-ang passes at −7.8°) — the 210-run main grid was
**not run** per the declared rule. **Review round 5 narrowed the
wording** (revision note in the report): the verdict is *the pre-
defined expansion criteria were not met at this budget*, not "no
biological advantage" — the tanh T-del fly ≥ degree difference (all 3
seeds, two clearly positive) is seed-unstable and preserved as a
candidate; the spike arm's three per-seed values are one deterministic
evaluation re-labelled, never three replicates; `results/summary.json`
now indexes all 44 cells (18 pilot/v1, 18 pilot/v2, 8 main/v3-dec).
Report:
`../reports/2026-10-12-a03-design.md` (revision note is
authoritative).
- **b-01-internal-compass** (can a *measured* central-complex subgraph
  run a decodable heading attractor?) — `b-01-internal-compass/`.
  **Done 2026-10-12: clean null at the declared drive point.** 15 runs
  (bio / conventional-ring / degree-matched-shuffle × 5 seeds, LIF on
  the measured FAFB v783 CC+ALPN subgraph, 3,563 neurons / 315,268
  pairs): measured wiring and shuffle are both EL-silent (0 Hz) — the
  declared ALPN drive path has only 2 excitatory edges into the EL
  ring, so the declared readout cannot separate "wiring does it" from
  "drive is too weak" (A2–A5 fail; A1 passes only trivially and is
  flagged as such); the conventional ring saturates (2.1M spikes, R²
  strongly negative). First clean bulk-activity wiring effect of the
  campaign: bio 134k–156k spikes/session vs shuffle 0. One pre-existing
  semantic deviation disclosed (declared 15 mV never applied; spike-
  source delivery is the weaker, conservative realization). Report:
  `../reports/2026-10-12-b01-internal-compass.md`.
- **b-02-internal-compass-v2** (the drive-semantics question B-01 left
  open — executed) — `b-02-internal-compass-v2/`. **Done 2026-10-13:
  the corrected design runs clean and lands a uniform, mechanism-rich
  null.** Staged preflight (CC-only subgraph 2,878 / 300,521, shift
  loop reproduced exactly, three named drive APIs + independent numpy
  LIF differential test, positive control PASS at 64 Hz on a
  byte-identical rebuild of B-01's ring) then a 6-arm × 5-seed
  pre-registered battery: the measured P-EN→EPG wiring does **not**
  transduce the declared velocity drive into a decodable heading at
  ×0.5/×1/×2 weights (c2 MAE 85–93°, at chance in every arm; the side
  geometry is irrelevant — signflip ≡ bio), and the B-01 null
  reproduces one population over. Lesions explain the null: P-EN is
  the network's primary activity source (−97 % when silenced), the
  tonic-held ER ring is an inhibitory clamp on the readout (240–908×
  disinhibition, still no tracking); the declared 60 mV visual cue is
  the only thing that fires the readout population, and it works
  exactly as declared (a valid interface onto a dead downstream). Also
  found: B-01's ring run used the npz without its sign column
  (all-positive weights). Report:
  `../reports/2026-10-12-b02-internal-compass-v2.md`.
- **worm-pilot** (multi-organism expansion: does the *measured* C. elegans
  connectome route a textbook sensorimotor computation?) —
  `worm-pilot/`. **CLOSED 2026-10-13 (review round 5).** The lane went
  through three substrate corrections: (1) v1 parse corruption
  (positional reading of sparse spreadsheet rows — fabricated
  self-edges; counts 3,618/2,130 wrong) → v2 column-reference parse,
  cross-validated against the independent SI6 raw-EM book (99.8% pair
  overlap). (2) Review round 4: the recorded stim−rest "delta" was a
  within-run quantity, not a stimulus effect; the corrected *paired*
  contrast (recomputed from the frozen 80 runs) looked positive in the
  measured wiring (+0.090 Hz 5-s; +1.75 Hz during the 500 ms pulse in
  a 40-run time-resolved subset) — flagged exploratory. (3) Review
  round 5 found the v2 electrical layer **double-counted**: the SI9
  "symmetric" and "asymmetric" gap-junction sheets are two
  representations of the *same* ~1,089 physical junctions (every asym
  pair occurs in the sym sheet, same weight; corroborated by the SI7
  synapse list, which lists each junction exactly once), and the
  background Poisson events additionally propagated as forced presynaptic
  spikes (a second, unlabelled behaviour). The corrected **v3
  substrate** (one canonical undirected junction layer, 1,089 herm /
  1,278 male; explicit background Model A = pure external current vs
  Model B = historical forced propagation) was re-measured without
  parameter changes (160 runs): the round-4 positive contrasts **do
  not survive** — 5 ms is a silent network under Model A (the +0.090
  Hz was a few-spike difference in a pool kept barely alive by doubled
  conductance); 50 ms Model A shows 0.0 paired contrast in every
  window and wiring; 50 ms Model B shows a small, not-beating-all-
  shuffles response (+0.040 Hz, 4/5 seeds positive, shuf-44 ≥
  measured). What survives: a **resting-state** activity difference
  (measured command pool above all shuffles: 9.03 vs 5.4–6.1 Hz under
  Model B; weak and non-decisive under Model A). Net: the original
  v1 "no positive ASH response in any wiring" null is reinstated on a
  defensible substrate; the +0.090/+1.75 Hz are recorded as a
  substrate artifact (not revalidated). The bounded follow-up
  (more shuffles, transmitter signs, τ sensitivity, graded
  stimulus) was executed 2026-10-22 as the new
  **worm-v3-sensitivity** experiment (below). Non-claims binding
  (no muscles, no signs in the release, spiking ≠ movement). Report:
  `../reports/2026-10-12-worm-pilot.md` (third addendum is
  authoritative).
- **worm-v3-sensitivity** (the pilot's bounded follow-up, re-
  authorized 2026-10-22 and run as a new focused experiment on the
  v3 substrate) — `worm-v3-sensitivity/`. **Done 2026-10-22:**
  440 runs, pre-registered stop rules evaluated by code.
  **(1)** The surviving **resting-state difference is
  wiring-specific**: measured rest 2.97 Hz vs 11 independent
  exact-invariant shuffles at 1.74–2.05 Hz — 0 of 11 reach the
  pre-registered 0.75× threshold, so it is not a random-neighborhood
  of the all-excitatory bifurcation; but it lives in a narrow τ
  window (silent at 25 ms, *reversed* at 100 ms) and weakens
  (2.97→1.77 Hz) when the 6.0% of edges from GAD-synthesizing
  classes (Gendrel/Atlas/Hobert 2016) are made inhibitory — a state
  effect, more sign-sensitive than a random wiring's. **(2)** The
  **ASH-response routing remains a null in every tested
  combination** (bg model × τ 10–100 ms × signs × step/trapezoid):
  the pre-registered control-wiring bar (measured > 0.5 Hz, all
  seeds, beats all shuffles) is not met anywhere. A graded
  (trapezoid) stimulus elicits ~0.4–0.7 Hz command-pool responses in
  *every* wiring (one shuffle above the measured) — the stimulus
  shape controls responsiveness, the wiring does not control
  specificity. Report: `../reports/2026-10-22-worm-v3-sensitivity.md`.
  (Its declared next step — the τ window map — was executed 2026-10-22
  as the **worm-tau-window** experiment below.)
- **worm-tau-window** (the v3-sensitivity follow-up, run as a new
  focused experiment on the v3 substrate) — `worm-tau-window/`.
  **Done 2026-10-22:** 200 runs over τ_syn ∈ {40,45,55,60,75} ms
  (Model B, all-excitatory, measured + shuf 42/43/44, 5 seeds ×
  {rest, stim}, the shared `bg_seed = sim_seed*1000+1` train),
  combined with v3-sensitivity's frozen B1/B3 points into a 9-point
  map. **The resting-state wiring effect is a band-pass:** dominance
  over all three shuffles at every point of the contiguous **25–60 ms
  window**, peaking at **40–45 ms** (ratio ~2.0×, larger than at the
  50 ms anchor); the contrast edge is the narrower **45–50 ms**
  core; the 100 ms "reversal" is the far side of a crossover between
  60 and 75 ms. Both wirings fire monotonically faster as τ grows —
  the effect is a property of the (wiring, timescale) pair, not a
  routing result at any grid point; the control-wiring bar is
  unchanged (FAIL stands). Exploratory map by declaration. Report:
  `../reports/2026-10-22-worm-tau-window.md`.
- **plasticity-rule A/B** (dopamine-STDP vs gain-scaling vs none, same
  substrate) — after discriminability; the toolkit is read-only, so this
  one means writing the learning rule (the FlyBridge gain-scaling
  recipe is the reference to beat).
