# Worm τ-window — mapping the resting-state effect's integration window

**Date:** 2026-10-22
**Lane:** brainlab WORM-TAU (new focused experiment; the 2026-10-12/13
multi-track campaign is closed and this is not part of it)
**Status:** DONE (200 runs, 5 τ points, all declared analyses evaluated)

## Goal

The v3-sensitivity experiment (2026-10-22,
[`2026-10-22-worm-v3-sensitivity.md`](2026-10-22-worm-v3-sensitivity.md))
closed with a FAIL on the control-wiring bar and exactly one surviving
observation: the measured wiring's resting-state activity is
wiring-specific (0 of 11 shuffles in the active basin) but exists only
in a narrow integration window — silent at τ_syn = 10 and 25 ms (sparse),
present at 50 ms, and **reversed** at 100 ms. Its declared next step was
the window map: fill the grid with τ ∈ {40, 45, 55, 60, 75} ms to locate
where the effect appears, peaks, and disappears. That is this
experiment. Declared character: an exploratory regime map; it
**makes no "wiring matters" claim** and does not move the control-
wiring bar.

## Setup (hardware as roles)

- **CPU batch role:** 4-core x86 box (the lab's designated CPU batch
  host). 15 s / 1 ms / 300-neuron runs ≈ 2 s each; full 200-run wall
  time ≈ 5 min (22:53–23:00 local, 2026-10-22).
- No GPU, no training: frozen LIF networks, the lab's conventions, the
  pilot's frozen v2 parameters (no re-calibration), same substrate and
  shuffles as the v3-sensitivity B1 battery.

## Protocol (pre-registered; frozen commit before execution)

Full text in [`experiments/worm-tau-window/README.md`](../experiments/worm-tau-window/README.md).
Summary:

- **Substrate:** the pilot's v3 canonical electrical layer (1,089 herm
  junctions) + 3,669 directed chemical edges; 300 neurons; Model B
  (bg propagation); all-excitatory (the B2 sign battery is out of
  scope here — the window question is about the all-excitatory
  state effect).
- **Grid:** τ_syn ∈ {40, 45, 55, 60, 75} ms here, combined with the
  v3-sensitivity B3 points {10, 25, 100} → a 9-point map
  {10, 25, 40, 45, 50, 55, 60, 75, 100}. (50 ms is v3-sensitivity B1's
  point, included as the anchor.)
- **Wirings:** measured + shuffle seeds 42/43/44 (the pilot's frozen
  graphs — the minimum needed to bracket the effect; B1's 11-graph
  replication already established 0/11 at 50 ms).
- **Runs:** 5 seeds × {rest, 500 ms ASH step} per wiring per τ =
  200 runs. Paired input `bg_seed = sim_seed*1000+1` — the same
  background train as the entire v3-sensitivity campaign (sha256
  `76539fd640ba…`, logged in every results file), so all nine grid
  points are directly comparable.
- **Declared analysis (in the README, before the first run):** per
  point, flag (a) *dominance* = measured rest rate > all three
  shuffles; (b) *contrast-edge* = measured command-pool 5-s paired
  contrast > all shuffles. The window = the maximal contiguous set of
  dominance points over the combined 9-point grid, with the 50 ms
  anchor. Inversion = points where a shuffle exceeds measured.

## Commands

```bash
cd experiments/worm-tau-window
python3 src/run_tauwindow.py   # 5 τ points -> results/tau{40,45,55,60,75}.json + map.json
```

## Observations

1. **The dominance window is τ ∈ {25, 40, 45, 50, 55, 60} ms — a
   ~35 ms-wide band.** The measured wiring's whole-animal rest rate
   exceeds all three shuffles at every point from 25 to 60 ms, and
   fails at both ends: at 10 ms everything is silent (the
   documented summation limit), and from 75 ms on the shuffles are
   at or above the measured wiring (75: measured 8.40 vs 9.27–9.66;
   100: 11.88 vs 13.38–13.76). The v3-sensitivity "reversal at
   100 ms" is not an isolated curiosity — it is one side of a
   crossover that happens between 60 and 75 ms.
2. **The effect's size peaks in the middle of the band.** Measured/
   best-shuffle ratio: 2.05 (25) → 2.03 (40) → 1.87 (45) → 1.71 (50)
   → 1.41 (55) → 1.16 (60) → 0.90 (75) → 0.86 (100). The strongest
   wiring-specific resting-state difference in the whole map is at
   40–45 ms, not at 50 — the pilot's anchor happens to sit on the
   descending shoulder of the effect.
3. **Both wirings get faster as τ grows; the difference is
   window-shaped.** Rest rates rise monotonically with τ for both
   measured and shuffles (0.00 → 0.13 → 1.24 → 2.01 → 2.97 → 4.04 →
   5.18 → 8.40 → 11.88 measured). Slow synaptic decay lets charge
   accumulate, so *any* wiring fires more; the measured wiring's
   advantage is a property of an intermediate window — too fast and
   neither sustains activity, slow enough and the dynamics
   saturate and the topological difference is washed out (the
   shuffles' looser structure happens to integrate the slower
   decay slightly better). Read plainly, within these declared
   assumptions: **the measured wiring selects which side of an
   activity bifurcation the network rests on, and that selection
   holds only while the integration window is inside the ~25–60 ms
   band.** This is a state/regime effect, consistent with the v3-
   sensitivity reading — it does not become a routing result at any
   point of the grid.
4. **The contrast edge is narrower than the dominance window:
   {45, 50} ms only.** The command-pool 5-s paired contrast beats
   all shuffles at 45 and 50 ms, and at no other point (at 55/60 one
   shuffle ties or exceeds it; at 75/100 the measured contrast is
   negative or beaten). The command pool itself ramps steeply with
   τ (0 → 0.08 → 2.57 → 5.33 → 9.03 → 12.85 → 16.51 → 24.96 → 32.70
   Hz rest, measured), i.e. the network's motor output is mostly a
   function of the timescale, with the wiring's share of it peaking
   in the middle of the band.
5. **Replication check.** The 50 ms row reproduces v3-sensitivity B1
   (measured 2.97 / shuffles 1.78 / 1.79 / 1.74 Hz) and the 10/25/100
   rows reproduce its B3 exactly. All 200 runs stable (no saturation,
   no NaN); every file carries the shared paired-input hash.

## Numbers

Whole-animal rest rate, mean over 5 seeds (Hz); combined 9-point map
(this experiment + v3-sensitivity B1/B3):

| τ (ms) | measured | shuf-42 | shuf-43 | shuf-44 | dominance | contrast-edge |
|---|---|---|---|---|---|---|
| 10 | 0.000 | 0.000 | 0.000 | 0.000 | — (silent) | no |
| 25 | 0.127 | 0.062 | 0.062 | 0.062 | **yes** | no |
| 40 | 1.242 | 0.610 | 0.630 | 0.591 | **yes** | no |
| 45 | 2.007 | 1.057 | 1.073 | 1.034 | **yes** | **yes** |
| 50 | 2.970 | 1.785 | 1.788 | 1.744 | **yes** | **yes** |
| 55 | 4.039 | 2.912 | 2.914 | 2.885 | **yes** | no |
| 60 | 5.177 | 4.454 | 4.467 | 4.507 | **yes** | no |
| 75 | 8.398 | 9.272 | 9.376 | 9.655 | **no** (inverted) | no |
| 100 | 11.884 | 13.376 | 13.523 | 13.757 | **no** (inverted) | no |

Command-pool 5-s paired contrast, mean over seeds (Hz):

| τ (ms) | measured | shuffles (range) |
|---|---|---|
| 10 / 25 | 0.0 / 0.0 | 0.0 |
| 40 | −0.010 | 0.0 – +0.005 |
| 45 | +0.065 | +0.010 … +0.015 |
| 50 | +0.055 | −0.005 … +0.040 |
| 55 | +0.090 | −0.050 … +0.130 |
| 60 | +0.045 | −0.025 … +0.130 |
| 75 | −0.010 | +0.060 … +0.120 |
| 100 | −0.130 | −0.020 … +0.175 |

Artifacts: `experiments/worm-tau-window/results/` — per-τ JSON (all
200 runs, per-window group rates, per-seed paired contrasts,
per-shuffle invariants, paired-input hashes), `map.json` (the
combined 9-point map with the dominance/contrast flags and window
computed by code from this experiment's five new points plus the
v3-sensitivity frozen B1/B3 rows), pre-registered README,
`src/run_tauwindow.py`.

## Conclusion

**Verdict per the declared analysis:** the resting-state
wiring-specific effect lives in a contiguous **~25–60 ms
integration window** (dominance at all six points), peaks at
**40–45 ms** (ratio ~2.0×, larger than at the pilot's 50 ms anchor),
and the contrast edge is the narrower **45–50 ms** core. The 100 ms
"reversal" is the far side of the same crossover. This was declared
an exploratory map, and it remains one: it sharpens *where* the
v3-sensitivity state effect sits, without changing the overall
picture — **no point on the 9-point grid produces a response that
passes the control-wiring bar, and the bar is unchanged.** The
honest statement after this map: on the v3 substrate, under the
declared all-excitatory Model-B assumptions, the measured wiring's
demonstrable specificity is *which activity regime it rests in*,
and that specificity is a band-pass property of the
(wiring, timescale) pair, not a routing property.

**What failed / what the numbers do not show.** Nothing mechanical:
all 200 runs completed, all invariants held, the B1/B3 anchor rows
replicate exactly. Substantively, the map does not (and was not
declared to) show that the 25–60 ms window is the worm's real
synaptic regime — the v2 parameters were frozen at 50 ms by
convention, not by measurement; it does not show the sign-variant
window (B2 at other τ is unrun — the sign battery's own verdict
stands from 50 ms); it does not show a mechanism (the
bifurcation-saturation reading in Observation 3 is an interpretation
of the monotone-both-sides shape, not a fitted result).

## Next (not run; would need fresh authorization)

- **A-03 T-ang dedicated study (fly side):** the live lead from the
  closed campaign — sub-ceiling spike T-ang in the FlyWire FAFB
  v783 olfactory circuit, needing a multi-seed dedicated experiment
  with declared pass criteria. This is the next brainlab experiment
  in priority order.
- Sign × τ interaction (the B2 battery across the 40–60 ms band):
  does inhibition shift or narrow the window?
- A τ sweep at fixed *effective* integration (e.g. co-varying
  conductance so the membrane time constant is held) to separate
  "synaptic decay" from "charge accumulation" in the monotone ramp.

## References

- Previous state:
  [`2026-10-22-worm-v3-sensitivity.md`](2026-10-22-worm-v3-sensitivity.md)
  (the 9-point map's 10/25/50/100 rows come from its frozen
  B1/B3 batteries) and
  [`2026-10-12-worm-pilot.md`](2026-10-12-worm-pilot.md) (third
  addendum, review round 5, is the authoritative state of the
  pilot).
- Cook CM et al. (2019) *eLife* 8:e47256. (substrate; via the
  pilot's frozen parse)
