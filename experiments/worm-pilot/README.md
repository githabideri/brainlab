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
    summation made possible.
- Background: each neuron receives Poisson external drive (rate λ,
  event size w — values in `config.json`), the stochasticity source;
  one rng per seed.

**Stimulus.** A 500 ms constant depolarization pulse on ASHL and ASHR
(t = 5.0–5.5 s), in the same units as the synaptic offset, sized so
ASH fires ~20 Hz during the pulse (a receptor potential, not a spike
train).

**Conditions** (per seed): `rest` (15 s, no pulse), `stim` (same, with
pulse) — both on the **measured** wiring and on a **shuffled** wiring
(configuration model: same edge counts, same degree marginals, same
weight multiset, self-edges rejected, seed recorded). 4 runs × 5 seeds
= 20 runs total.

**Readout** (window t = 5.5–10.5 s, the 5 s after the pulse):
spike counts per neuron; group responses for the command pool
(AVA/AVB/AVD/AVJ, 8 neurons), the body-wall motor classes (DA, DB, DD,
VA, VB, VD, AS, PDA, PDB, DVA, DVB, VC), and all other neurons.

**Primary metric.** Post-stimulus group rate: mean firing (Hz) of each
readout group in the 5 s after the pulse, averaged over seeds
(mean ± SD), for the measured wiring and the shuffled wiring alike.
A secondary response index, (stim_rate − rest_rate) / rest_rate, is
reported where the rest rate is ≥ 0.1 Hz (it is undefined for a
sparse-silent rest — which is itself a finding of the all-excitatory
model).

**Pass / fail (declared in advance).**
- *Stable*: every run finishes 15 s without saturation (no neuron
  > 200 Hz mean, no NaN).
- *Routed*: the measured wiring's post-stim rate in the command pool
  and in the body-wall motor classes exceeds 0.5 Hz (mean over seeds)
  AND exceeds the shuffled wiring's rate for the same group.
- *Wiring matters*: the measured wiring's post-stim group rate
  exceeds the shuffled wiring's, beyond seed noise.
  If it does not — the honest, publishable result is that **the
  wiring did not matter for this task under this model**, and we say
  so.

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
| `data/` | Cook 2019 supplementary data (sha256-pinned) + parsed edges |
| `src/parse_cook2019.py` | workbook → edge JSON (artifacts counted) |
| `src/sim.py` | LIF + shared-conductance gap junctions, run one condition |
| `src/calibrate.py` | setup-phase grid for α, (λ,w), β, S (logged) |
| `src/run_campaign.py` | 5 seeds × 4 conditions → `results.json` |
| `config-5ms.json`, `config-50ms.json` | frozen parameters per variant (written by calibrate, read-only after) |
| `calibration-log.json` | the logged setup-phase grids |
| `results.json` | per-run/per-seed/per-group numbers (committed) |

## Run

```bash
PY=python3   # any Python >= 3.9 with numpy (4-core laptop CPU box)
$PY src/calibrate.py            # setup: writes config-<variant>.json + calibration log
$PY src/run_campaign.py         # final: 2 variants x 20 runs, ~2-4 min total, writes results.json
```

Runtime: a 15 s / 1 ms run of 300 neurons and ~5,700 edges takes a
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
