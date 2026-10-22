# T-ang dedicated — the spike-arm T-ang lead from the A-03 decision pilot

*Pre-registration: this README (question, components, grid, pass
criteria, smoke, non-claims) is frozen BEFORE any grid run of this
experiment. Changes after the first grid evaluation are findings to
report, not silent corrections. This is a new focused experiment in
the brainlab tradition (like `worm-v3-sensitivity` / `worm-tau-window`
following the frozen worm-pilot): it imports A-03's frozen modules
but has its own protocol, results directory, and report.*

**Provenance of the lead.** The A-03 decision pilot (24 runs,
`a-03-sequential-learning`, STOP verdict 2026-10-13; report
`reports/2026-10-12-a03-design.md` addenda) left exactly one
sub-ceiling positive signal: **spike T-ang** — fly **84.95°** vs
degree **92.77°** (−7.82°, identical under all 3 "seeds" because the
spike arm is deterministic in the seed — one evaluation, not three).
The degree control sat *worse than chance* (89.80°), fly was below
the 45.46° ceiling but far from it; every other cell (T-del, T-xor,
tanh arm) was at or below chance. The review's own words: recorded
as a candidate for "a dedicated T-ang study with more seeds and
circuits". This is that study, at the same circuit sample (the lane
envelope keeps one 1,536-neuron flywire subgraph; a second circuit
sample is a separate experiment) with the two defects the STOP
record itself names: the 32-trial held-out prefix (a sizing fold,
not the declared 512) and the single drive realization (one Poisson
draw, one evaluation).

## Question

On the FlyWire FAFB v783 olfactory circuit (1,536 nodes, 42,921
signed edges; 256 sensory drive, 384 readout), driven exactly as the
A-03 spike arm (frozen Shiu-2024 LIF, declared Poisson sensory drive,
ridge readout), does the measured wiring beat its matched controls on
angular integration (T-ang)

1. **stably** — across 5 independent Poisson drive realizations, and
2. **specifically** — against *all five* controls (degree, sign,
   weight, population, disconnected), not only against degree?

evaluated on the declared **512-trial** held-out fold (not the 32
prefix).

## Components (declared before any run)

- **Circuit.** `circuits/flywire-fafb-olfactory-1536` staged file
  `temp/brainlab/circuit-flywire-olfactory-1536.json`, verified at
  sha256 `ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227`
  before any run (recorded in the manifest).
- **Dynamics.** Spike arm only — the A-03/B-01 treatment, imported
  from `a-03-sequential-learning/` (`lif.py` byte-identical to B-01,
  pinned; `model.py` SpikeArm; `controls.py` byte-identical to A-01):
  LIF (v0 = vrst = −52 mV, vth = −45 mV, τm = 20 ms, τsyn = 5 ms,
  2-step delay, 2.2 ms refractory), circuit **frozen** (Δw = 0 by
  construction), efficacy sign × min(log1p|w|, c) × k with p95 scaled
  to 4.7 mV (the pilot-verified revision of the inert frozen
  mapping), tonic 10 mV on the 384 outputs, Poisson sensory drive
  R0 = 2 Hz / RMAX = 48 Hz, Wx master-seed projection, 100 ms steps,
  200 ms readout window, ridge α = 1.0 fit on the 80 % training
  prefix. **The only code difference from A-03 is the drive-salt
  function** (below); every other module is imported unmodified and
  hash-checked in the manifest.
- **Task.** T-ang only: T = 10 steps, ω ~ U[−180, +180]°/step
  constant per trial, x_t = ω/360 + N(0, 0.05²), target (sin H, cos H)
  with H = 360°·Σ x_true mod 360; metric circular RMCE (deg) + R²;
  ceiling 45.46° (fixed MC seed 20261021, 200k trials), chance
  89.80°. Same master-seed stream (20261020) and same 512-trial
  held-out fold as A-03 — the task file is imported, not regenerated.
- **Wiring arms.** fly + **all five controls** (degree, sign, weight,
  population, disconnected), built by the imported `controls.py`
  (each control asserts its preserved invariants; edge-array
  sha256s recorded in the manifest and cross-checked against A-03's).
- **Training budget.** n_train = 128 (A-03's declared main spike
  budget and the decision-pilot value); ridge fit on its 80 % prefix.
- **Drive realizations (the new dimension).** K = 5 independent
  Poisson drives. Realization k seeds each trial's sensory Poisson
  from sha256(`tang-ded:r{k}:a03-spike-drive:{task}:{row}`) for
  k ≥ 1, and **k = 0 uses A-03's exact salt**
  sha256(`a03-spike-drive:{task}:{row}`) — so realization 0 is bit-
  identical to the A-03 decision-pilot drive (verified by the smoke).
  Within every realization, all six wirings see the identical drive
  (the A-03 paired-property, preserved).
- **Grid.** 6 wirings × 5 realizations = **30 runs**; each run =
  features for 128 train + 512 test trials through the frozen LIF,
  ridge fit, held-out metrics. One JSON per (wiring, realization);
  resumable (existing JSONs are skipped).
- **Hardware.** 4-core CPU host (the lab's designated CPU batch
  host), the brainlab torch venv (CPU). Single-threaded LIF loop
  (the A-03 measured setting). No GPU.

## Cost (declared)

A-03 v2 measured ≈ 0.86 s/trial for T-ang; 640 trials ⇒ ≈ 9–10 min
per run ⇒ ≈ 5 h for the 30-run grid on the 4-core box, background.
**Shrink rule (declared in advance):** if the smoke's full run (S2)
walls at > 15 min, the grid runs K = 3 (realizations 0, 1, 2) and
the pass thresholds below read "≥ 4 of 5" as "≥ 2 of 3" and "≥ 3 of
5" as "≥ 2 of 3". No other parameter moves.

## Pass criteria (declared before the first grid run)

- **P1 — stability:** fly − degree ≤ **−5°** (fly better) in
  **≥ 4 of 5** realizations (≥ 2 of 3 if shrunk).
- **P2 — control-wiring specificity:** the fly's **mean** RMCE is
  lower than **every** control's mean RMCE, beats the **best**
  control's mean by **≥ 5°**, and fly is the single best wiring in
  **≥ 4 of 5** realizations (≥ 3 of 5 if shrunk).
- **Overall: PASS only if P1 and P2.** Otherwise the lead dies: the
  honest result is "the sub-ceiling spike T-ang signal of the A-03
  decision pilot does not survive a dedicated multi-realization,
  full-control study".
- **Ceiling efficiency is reported, not a criterion** (per the A-02
  review's relative-to-ceiling rule): efficiency =
  ceil_RMCE / model_RMCE, per wiring and realization, in the map.

## Smoke (declared; runs after this freeze, before the grid)

- **S1 — import fidelity / bit-identity.** Realization 0, wirings
  fly + degree, n_train = 128, held-out = the 32-trial prefix: must
  reproduce the decision-pilot values **84.95° / 92.77° to 2 decimals**
  (same drive salt, same code path, deterministic ridge). Any
  deviation ⇒ stop and investigate before the grid; the deviation is
  a finding either way.
- **S2 — one full run.** fly, realization 1, full 640 trials: wall
  time (drives the shrink rule), no NaN/saturation, sane RMCE
  (not 0, not exactly chance within noise).

## Non-claims (binding)

- One circuit sample (one 1,536-neuron flywire subgraph of FAFB v783).
- Frozen internal weights in the spike arm (B-01 treatment): this
  measures what the fixed reservoir + linear readout can do, not
  learned spiking plasticity.
- Readout-level task performance, not behaviour.
- K = 5 is a decision rule, not a power calculation; the paired
  (across wirings) but independent (across realizations) design
  controls for drive noise, not for wiring-sample noise.
- The 45.46° ceiling is the optimal *linear estimator of the input*
  (fixed MC seed); a nonlinear decoder is not bounded by it (the A-03
  pilot showed an MLP exceed the linear T-xor ceiling) — stated, not
  assumed.
- CPU host; the LIF is the Shiu-2024 model as pinned, not a measured
  olfactory-lobe biophysics.

## Files

- `README.md` (this pre-registration + results addendum appended
  after the grid)
- `src/run_tang.py` (driver: 6 wirings × K realizations, resumable;
  writes `results/<wiring>_r<k>.json` and `results/map.json`)
- `src/smoke_tang.py` (S1 + S2)
- `results/` (per-run JSONs, `map.json` with the P1/P2 verdicts
  evaluated by code, `manifest.json`)

## References

- A-03 pre-registration + decision pilot + STOP:
  `experiments/a-03-sequential-learning/README.md` and
  `reports/2026-10-12-a03-design.md` (correction addendum, review
  rounds 4–5).
- B-01 (the LIF treatment and the drive convention):
  `experiments/b-01-internal-compass/`, report
  `reports/2026-10-12-b01-internal-compass.md`.
- Control-wiring bar: `docs/evaluation.md` §7.
- Circuit entry: `circuits/flywire-fafb-olfactory-1536.md`.
