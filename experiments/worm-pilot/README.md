# Worm pilot — one measured sensorimotor computation

**Question.** Take the *measured* hermaphrodite *C. elegans* connectome
(Cook 2019 matrices, both chemical and electrical synapses, 300
neurons) and run it as a spiking network with the lab's LIF
conventions. Drive the ASH nociceptors with one declared stimulus.
Does the real wiring route that input to the measured motor output
better than a degree-matched random wiring does — or is the answer
"the wiring did not matter for this task"?

## Protocol (frozen before final evaluation)

**Network**
- Nodes: the 300 hermaphrodite neurons with ≥ 1 neuron–neuron edge
  (`data/c-elegans-neurons-herm.json`); 2 listed neurons carry no
  neuron–neuron edge and drop out.
- Chemical synapses: 3,669 directed edges, weight `w = α·√(section
  count)`, **all excitatory** (the released data carry no signs or
  transmitters; see `circuits/c-elegans-substrate.md`).
- Gap junctions: 2,178 neuron–neuron junctions (1,089 symmetric,
  stored once; 1,089 asymmetric, directed). Modelled as **shared
  conductance** — linear current `g·(V_j − V_i)` per released EM
  section of the junction, folded into the per-neuron membrane time
  constant and solved exactly per step (per the Cook 2019 treatment
  of the symmetric/asymmetric sheets; unconditionally stable).
- Model: LIF, dt = 1 ms, τ_m = 20 ms, V_th = −45 mV, reset to
  V_0 = −52 mV, refractory 2.2 ms — the lab conventions of
  `experiments/b-01-internal-compass/lif.py`, with two declared
  deviations: (a) the gap-junction conductance term (absent from
  lif.py), (b) a constant-depolarization stimulus instead of a spike
  train (a receptor potential is the physiologically closer stimulus
  for a sensory neuron).
- **Two declared variants** (both run the full battery, gains
  calibrated independently per variant, never against the readout):
  - **A: τ_syn = 5 ms** — the lab convention, primary.
  - **B: τ_syn = 50 ms** — a physiological-range synaptic
    summation variant. Declared *after* variant A ran: A's
    run-to-run analysis showed the 5 ms decay limits the
    depolarization of a post-synaptic neuron receiving a λ Hz train
    to ≈ w·λ·τ_syn (≈1.5 mV for ASH→AVB at 94 Hz), far below the
    7 mV threshold gap, so variant A cannot route fast sensory
    input at any gain — variant B tests the wiring question with
    summation made possible. **2026-10-13 addendum: reasserted as
    EXPLORATORY** — the variant was selected after examining the 5 ms
    results, so it is a post-hoc variant; anything it shows is a
    lead, not a prospective confirmation.
- Background: each neuron receives Poisson external drive (rate λ,
  event size w — values in `config-<variant>.json`), the stochasticity
  source; **paired-input rule (2026-10-13)**: the drive's rng is
  seeded `sim_seed*1000 + variant_idx` — a function of the simulation
  seed and the variant only, never of the wiring — so the measured
  wiring and every shuffle see byte-identical input trains for a
  given (seed, variant); one example pair is dumped per variant
  (`data/paired-stim-example-<variant>.json`, sha256 in
  `results-exact.json`).

**Stimulus.** A 500 ms constant depolarization pulse on ASHL and ASHR
(t = 5.0–5.5 s), in the same units as the synaptic offset, sized so
ASH fires ~20 Hz during the pulse (a receptor potential, not a spike
train).

**Conditions** (per seed): `rest` (15 s, no pulse), `stim` (same, with
pulse) — on the **measured** wiring and on **three independent
exact-invariant shuffled wirings** (`make_shuffled_exact`, seeds
42/43/44; 2026-10-13, supersedes the v1 single-graph shuffle: the
RAW record lists are shuffled per junction class — exact per-neuron
in-/out-degree vectors, identical weight multiset, zero dropped
records — self-edge permutations repaired by swap-rejection, residual
counted and asserted 0, sym/asym class counts exact, no record
merging; an invariants block per graph lands in the results manifest
and `src/test_invariants.py` re-asserts it). 4 wirings × 2 conditions
× 5 seeds × 2 variants = **80 runs**.

**Readout** (window t = 5.5–10.5 s, the 5 s after the pulse):
spike counts per neuron; group responses for the command pool
(AVA/AVB/AVD/AVJ, 8 neurons), the body-wall motor classes (DA, DB, DD,
VA, VB, VD, AS, PDA, PDB, DVA, DVB, VC), and all other neurons.

**Primary metric (2026-10-13, replaces the v1 post-stim rate).**
Per wiring, seed and group: the **stim−rest delta** — stim-window
rate (5 s after the pulse) minus rest rate (whole 15 s) — plus the
response index (delta / rest where rest ≥ 0.1 Hz). The headline
table compares the measured wiring against each of the 3 shuffle
graphs on the delta, with the spread **across the independent
graphs** reported explicitly (v1's one shared graph confounded graph
and seed variability).

**Pass / fail (declared in advance, 2026-10-13 restatement).**
- *Stable*: every run finishes 15 s without saturation (no neuron
  > 200 Hz mean, no NaN).
- *Routed / wiring matters* (on the delta metric): the measured
  wiring's stim−rest delta in the command pool and in the body-wall
  motor classes exceeds 0.5 Hz (mean over seeds) AND exceeds the
  delta of **all three** independent shuffle graphs. A "beats the
  shuffle" flag on a group whose deltas are all ≤ 0 is an artifact
  of comparing small negatives and is not a pass. If it does not
  pass — the honest, publishable result is that **the wiring did
  not route this stimulus under this model**, and we say so.

**Calibration (setup phase, before freeze).** For each variant, a
logged grid search (see `calibration-log.json`) chose, in order: the
chemical gain α (largest value keeping the rest run stable and below
20 Hz mean — the all-excitatory network is a switch, so the stable
window is narrow); the background drive (λ, w) closest to a ~2 Hz
sparse rest; the gap-junction gain β so that the mean gap current at
rest is 10% of the mean chemical current; and the stimulus S as the
smallest grid value giving ≥ 20 Hz ASH firing during the pulse. The
chosen values are written into `config-<variant>.json` **before** the
final runs and never tuned against the readout.

## Files

| File | Role |
|---|---|
| `README.md` | this protocol |
| `data/` | Cook 2019 supplementary data (sha256-pinned) + parsed edges (v2 column-reference parse, 2026-10-13) + paired-input artifacts |
| `src/parse_cook2019.py` | workbook → edge JSON (artifacts counted; v2 maps cells by XML column reference) |
| `src/sim.py` | LIF + shared-conductance gap junctions; `make_shuffled_exact` (exact-invariant controls) |
| `src/calibrate.py` | setup-phase grid for α, (λ,w), β, S (logged) |
| `src/run_campaign.py` | 2 variants × 4 wirings × 5 seeds × 2 conditions → `results-exact.json` (80 runs) |
| `src/test_invariants.py` | re-asserts the substrate and shuffle invariants (34 checks) |
| `config-5ms.json`, `config-50ms.json` | frozen parameters per variant, recalibrated 2026-10-13 on the corrected substrate (v1 copies kept as `*-v1-corrupted-substrate.json`), read-only after |
| `calibration-log.json` | the logged setup-phase grids (v1 log kept as `*-v1-corrupted-substrate.json`) |
| `results-exact.json` | the 80 runs, per-seed deltas, headline table, invariants blocks (v1 `results.json` frozen) |

## Run

```bash
PY=python3   # any Python >= 3.9 with numpy (4-core laptop CPU box)
$PY src/parse_cook2019.py data   # regenerate edges/inventory from the workbooks
$PY src/test_invariants.py       # 34 invariants must hold before any run
$PY src/calibrate.py             # setup: writes config-<variant>.json + calibration log
$PY src/run_campaign.py          # final: 2 variants x 80 runs, ~3-5 min total, writes results-exact.json
```

Runtime: a 15 s / 1 ms run of 300 neurons and ~5,800 edges takes a
few seconds, far under the 10-minute per-run budget.

## What this can and cannot establish

It can establish: that a complete measured wiring of this size runs
as a spiking network on a laptop CPU, what a nociceptive pulse does to
it, and whether the *wiring itself* (vs. its size and degree
distribution) contributes to the measured input→output routing under
these declared assumptions.

It cannot establish (see the report for the full list): that the
network implements pinprick withdrawal in the animal; any behavior
beyond motor-neuron spiking (muscles, body, environment absent); or
anything about inhibition, plasticity, or real synaptic kinetics,
which the released data do not contain.
