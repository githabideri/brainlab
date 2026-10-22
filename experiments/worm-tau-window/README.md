# Worm τ-window — mapping the boundary of the resting-state effect

**Question.** The v3-sensitivity experiment (2026-10-22) found the
surviving wiring-specific effect (the resting-state difference) in a
narrow τ_syn window: silent at 10 ms, sparse at 25 ms, present at
50 ms, *reversed* at 100 ms. This experiment fills the window: it
maps the effect across τ_syn = {40, 45, 55, 60, 75} ms to locate the
boundaries of the τ range in which the measured wiring sits in the
active basin above its degree-matched controls.

**Pre-registered.** This file and the frozen configs were committed
before any run. No "wiring matters" claim is made from this map
alone — the lab's control-wiring bar (docs/evaluation.md §7) is
unchanged; this is an exploratory regime map of the *state* effect,
exactly as declared in the 2026-10-22 report's "Next" section.

## Protocol

- Substrate: v3 canonical (frozen `../worm-pilot/` data), 300
  neurons, 3,669 chemical edges (all-excitatory, frozen weights),
  one canonical undirected junction layer.
- Model: **Model B** (bg_propagate = true; the historical forced
  propagation — the regime in which the effect exists). Background
  Poisson λ_bg 4 Hz, w_bg 7.0; paired-input seed rule
  `bg_seed = sim_seed*1000 + 1` (never the wiring) — the same
  train as the v3-sensitivity batteries, so this map is directly
  comparable to them.
- Wirings: measured + shuffles 42/43/44 (the pilot's frozen
  exact-invariant graphs, reproduced deterministically).
- Grid: **τ_syn ∈ {40, 45, 55, 60, 75} ms** (declared; combined with
  the already-frozen 10/25/50/100 points this gives a 9-point map).
  All other parameters are the frozen v2 values.
- Conditions: 5 seeds × {rest, 500 ms ASH pulse at t = 5.0–5.5 s}
  per τ and wiring = **200 runs**.

## Readout and declared boundary criterion

Per run: total spikes, mean/max rate, NaN; per group (command pool,
body-wall motors, other, ASH/ASJ): 15 s rate, the 5 s post-pulse
window, and the pilot's seven time-course windows. Per (τ, wiring):
- `rest` — whole-animal and command-pool 15 s rate, mean over
  seeds;
- `contrast` — command-pool 5 s *paired* contrast (stim − paired
  rest), mean over seeds.

**Declared boundary criterion (written before looking at any new
number).** For each τ point, two flags:
1. **dominance** — the measured rest rate (whole animal) exceeds
   *all three* shuffle rest rates;
2. **contrast-edge** — the measured command-pool paired contrast
   exceeds *all three* shuffle contrasts.

The **window** is the maximal contiguous set of τ values (over the
combined 9-point grid {10, 25, 40, 45, 50, 55, 60, 75, 100})
satisfying flag 1. The 100 ms reversal is recorded as the map's
upper anomaly. No threshold on response size is part of this
experiment; a "wiring matters" claim would still require the
control-wiring bar on a response metric.

## Non-claims

Inherited from the worm-pilot and v3-sensitivity: no muscles, no
biomechanics, no environment; spiking ≠ movement; all-excitatory
chemistry is a declared assumption (the sign version of this map is
a different, unrun experiment); Model B is a historical background
model, not a claim about the animal.

## Files

| File | Role |
|---|---|
| `README.md` | this protocol (frozen before execution) |
| `config/` | the five derived frozen configs (τ only changed; sha of the source config recorded in each) |
| `src/run_tauwindow.py` | driver (imports the frozen `../worm-pilot/src/sim.py`; nothing in worm-pilot is modified) |
| `results/` | per-τ JSON (runs, per-window group rates, paired contrasts, shuffle invariants, paired-input hashes) + `map.json` (the 9-point combined map with the declared flags) |

## Run

```bash
python3 src/run_tauwindow.py   # 200 runs, ~8 min, writes results/
```
