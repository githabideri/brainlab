# Worm v3 sensitivity — what survives the corrected substrate

**Question.** The worm-pilot's third addendum (2026-10-13, review round 5)
left exactly one wiring-specific observation on the corrected v3
substrate: a **resting-state** activity difference (measured above the
3 shuffle graphs under Model B, 50 ms). Its ASH-response contrasts did
not survive. This experiment re-asks the pilot's question on the v3
substrate with four declared batteries, to decide whether the
resting-state difference is wiring-specific at all, and whether any
wiring-specific *response* appears once (i) the shuffle baseline is
tightly constrained, (ii) inhibition is admitted, (iii) the
summation timescale is varied, (iv) the stimulus is a graded
receptor potential instead of a step.

**Pre-registered.** This file (and the frozen configs in `config/`)
was committed before any run of this experiment. Stop rules S1–S4
below decide the verdicts; they were written down before looking at
any new number.

## Substrate and model (unchanged from worm-pilot v3)

- The 300-neuron hermaphrodite network, Cook 2019; **v3 canonical
  electrical layer** (one undirected junction per physical gap
  junction; `../worm-pilot/data/c-elegans-electrical-herm.json`);
  3,669 directed chemical edges, weight `alpha*sqrt(section count)`.
- Lab LIF conventions (tau_m 20 ms, V_th -45, V_0/V_rst -52,
  refractory 2.2 ms, dt 1 ms, delay 2 steps); **frozen v2
  parameters** (`../worm-pilot/config-50ms.json` and
  `config-50ms-v3-modelB.json`): lambda_bg 4 Hz, w_bg 7.0, alpha
  0.4, beta 0.00096, S 8, seeds 101–105. No parameter is
  re-calibrated or tuned against any readout in this experiment.
- Background models: **A** (default: pure external current; only
  threshold-crossing spikes propagate) and **B** (historical forced
  propagation, kept for comparison).
- **Paired input.** Every battery uses the pilot's seed rule
  `bg_seed = sim_seed*1000 + 1` — a function of the sim seed and
  variant only, never of the wiring, sign, or timescale — so all
  wirings of all batteries see byte-identical Poisson trains for a
  given sim seed. One measured-vs-shuf-42 event-list pair is dumped
  per battery (asserted identical, sha256 in the results).

## Wirings

The measured wiring plus **eleven independent exact-invariant
shuffle graphs** (`make_shuffled_exact`; exact degree vectors,
identical weight multiset, zero dropped records): seeds
**42, 43, 44** (the pilot's frozen graphs — deterministic, so
reproduced exactly) and **45–52** (new, the pilot's proposed
"8 further shuffles").

## Batteries (all: 5 seeds x {rest, 500 ms ASH pulse at t=5.0–5.5 s})

| id | bg model | tau_syn | signs | stimulus | wirings | runs |
|---|---|---|---|---|---|---|
| **B1** | B | 50 ms | all-excitatory (frozen) | constant depolarization (frozen S) | measured + 11 shuffles | 120 |
| **B1a** | A | 50 ms | all-excitatory (frozen) | constant depolarization | measured + 11 shuffles | 120 |
| **B2** | B | 50 ms | **signed** (see below) | constant depolarization | measured + shuf 42/43/44 | 40 |
| **B3** | B | **10 / 25 / 100 ms** | all-excitatory (frozen) | constant depolarization | measured + shuf 42/43/44 | 120 |
| **B4** | B | 50 ms | all-excitatory (frozen) | **trapezoid**: 100 ms rise, 300 ms plateau (peak = frozen S), 100 ms fall, total 500 ms | measured + shuf 42/43/44 | 40 |

Total: **440 runs.**

**Sign assignment (B2).** Inhibitory = chemical edges whose
presynaptic neuron belongs to a **GAD-synthesizing (unc-25-positive)
neuron class**: RME, RIS, AVL, DVB (DVB/DVC), DD01–06, VD01–13,
RIB — the six previously identified GABA classes of McIntire et al.
1993 plus RIB, from the 2016 GABAergic map (Gendrel, Atlas & Hobert,
eLife 5:e17686, Table 1; uptake-only "recycling/clearance" cells ALA/
AVF/SMDD and the ambiguous AVA/AVB/AVJ are excluded). In the 300-
neuron network this is **31 cells and 219 of 3,669 chemical edges
(6.0%)**; magnitudes are unchanged, only the sign flips
(`data/gabaergic-herm.json`). All non-listed presynaptic cells stay
excitatory (declared simplification: the release carries no per-
synapse transmitter identity). The exact shuffle permutes the
**signed** weight multiset independently of the edges, so shuffles
preserve the global sign balance (219 negative) but **not** the
presynaptic identity of the signs — declared.

## Readout

Per run: total spikes, mean/max rate, NaN flag; per group (command
pool AVAR/AVAL/AVBL/AVBR/AVDR/AVDL/AVJL/AVJR; body-wall motor
classes DA/DB/DD/VA/VB/VD/AS/PDA/PDB/DVA/DVB/VC; all other;
ASH/ASJ): 15 s rate, the 5 s post-pulse window, and the pilot's
seven time-course windows (pre 1 s, the pulse, then 250/250/500/
1000/3000 ms post-pulse). **Primary metric**: the *paired* contrast
per (wiring, seed, group, window) = stim-run rate − paired rest-run
rate (same wiring, seed, bg seed).

## Stop rules (declared before execution)

- **S1 — is the resting state wiring-specific?** (B1, Model B,
  rest runs.) Let R be the whole-animal rest rate, mean over seeds.
  If **≥ 3 of the 11** shuffle graphs have R ≥ 0.75 × R(measured),
  the resting-state difference is **not robustly wiring-specific**
  (an all-excitatory bifurcation-neighbourhood effect: random
  wirings with the same degrees also sit in the active basin) and
  the resting-state lead is closed as a model artifact. If ≤ 2 of
  11, the specificity stands and the resting-state lead is promoted.
  The command-pool rest rate is reported alongside.
- **S2 — do signs change the picture?** (B2.) A wiring-specific
  *response* is found if the signed measured wiring's command-pool
  5-s paired contrast has mean > 0.5 Hz, is positive in all 5 seeds,
  and exceeds every signed shuffle's mean. The resting-state effect
  under signs is reported the same way as S1 (≥ 3-of-11 would not
  apply: only 3 shuffles; ≥ 2 of 3 with rest ≥ 0.75 × measured
  closes it).
- **S3 — timescale map** (B3, with B1/B1a's 50 ms points): report
  the command-pool and motor paired contrasts and rest rates vs
  tau_syn {10, 25, 50, 100}. Exploratory; no pass/fail.
- **S4 — graded stimulus** (B4): report the step (B1) vs trapezoid
  (B4) command-pool contrast side by side. Exploratory; no pass/fail.

**Overall verdict (the lab's control-wiring bar,
docs/evaluation.md §7).** "The wiring matters for this computation"
passes only if, in at least one (bg model, tau, signs, stimulus)
combination, the measured wiring's command-pool 5-s paired contrast
exceeds 0.5 Hz (seed mean), is positive in all 5 seeds, and exceeds
**all** its matched shuffles. Otherwise the honest result is that
the v3 wiring does not route the ASH nociceptive pulse beyond its
controls under these declared assumptions — and the experiment's
value is the map of where (S1/S3/S4) and whether (S2) the surviving
resting-state difference is a wiring property or a model artifact.

## Non-claims (inherited from the pilot, plus)

No muscles, no biomechanics, no environment: spiking ≠ movement. The
sign assignment is a class-level *partial* assignment (31 of 300
cells); it says something about inhibition's placement, not about
real GABA kinetics or real receptor transduction. Gap junctions
carry no sign. The trapezoid is a declared stimulus shape, not a
measured channel model. Everything here is a wiring-vs-control
measurement under declared assumptions, not a whole-animal model.

## Files

| File | Role |
|---|---|
| `README.md` | this protocol (frozen before execution) |
| `data/gabaergic-herm.json` | sign-assignment source (pinned citation + cells) |
| `config/` | derived frozen configs (B3 tau variants; the 50 ms configs are read from `../worm-pilot/`) |
| `src/run_sensitivity.py` | driver for B1/B1a/B2/B3/B4 (imports the frozen `../worm-pilot/src/sim.py`; nothing in worm-pilot is modified) |
| `results/` | per-battery JSON (runs, per-window group rates, paired contrasts, shuffle invariants, paired-input hashes) + `verdicts.json` (S1–S4 evaluated by code) |

## Run

```bash
PY=python3  # numpy; same box as the pilot (4-core laptop CPU)
$PY src/run_sensitivity.py        # all batteries, ~30 min, writes results/
```
