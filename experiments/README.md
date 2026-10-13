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
  measured Δw per arm) — `a-03-sequential-learning/`. **Design lane
done 2026-10-12** (pre-registration committed before any run; 15/15
unit tests; 18/18 official pilot in 9 min): the pilot is a sizing
read-out, not a claim — the frozen spiking circuit saturates T-del/T-ang
in one pass at 32 trials while tanh/GRU are near chance at 4 epochs, so
the 20-epoch budget + val-loss checkpoint rule equalizes the arms before
comparison. Two load-bearing design defects were caught by measurement
(the declared spike mapping was dynamically inert; B-01's `lif.py`
`reset()` is latent-broken — sanctioned reset is fresh construction).
The 210-run main grid (≈28 h background, resumable per cell) is
pre-registered and scheduled after the heavy lane. Report:
`../reports/2026-10-12-a03-design.md`.
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
  `worm-pilot/`. **Done 2026-10-12: bounded pilot, one positive wiring
  finding + one documented null.** 300-neuron LIF network on the Cook
  2019 hermaphrodite connectome (3,618 chemical + 2,130 gap-junction
  neuron–neuron edges, sha256-pinned SI workbooks), nociceptive
  withdrawal (ASH pulse → command pool → body-wall motors) vs a
  degree/weight-matched shuffle, 5 seeds. Lab 5 ms integration: honest
  null with a calculable mechanism (w·λ·τ_syn ≈ 1.5 mV « 7 mV threshold
  gap); widened 50 ms variant (declared after A's diagnostics): measured
  wiring sustains a ~5× denser sparse rest than the shuffle and routes
  the pulse to the command pool (ri ≈ +0.9) and motor classes (ri ≈
  +0.86); the shuffle does not respond. Non-claims binding (no muscles,
  no signs in the release, spiking ≠ movement). Report:
  `../reports/2026-10-12-worm-pilot.md`.
- **plasticity-rule A/B** (dopamine-STDP vs gain-scaling vs none, same
  substrate) — after discriminability; the toolkit is read-only, so this
  one means writing the learning rule (the FlyBridge gain-scaling
  recipe is the reference to beat).
