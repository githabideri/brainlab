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
- **scorer** (the frozen 1,536-node olfactory circuit as a decision-scoring unit: learned state drive + readout + candidate-list heads, argmax with abstention) — `scorer/`. **First measurements in (2026-10-05):** one decision ≈ 1.2 ms p50 on a 4-core CPU; the 3-class toy learns through the pure-wiring passthrough at epoch 25 (100/100). **S2 in (2026-10-05, the polis decision corpus):** 92.91% on the 141-row held-out val (100% on the stuck→wait abstain slice), zero damaging choices, ~1.1 ms/decision; the shuffled-wiring control is null (92.20) — on this tanh-rate corpus the gain is in the encoder, not the connectome. Reports: `../reports/2026-10-05-scorer-first-measurements.md`, `../reports/2026-10-05-scorer-polis-s2-screen.md`; numbers: `scorer/results/`.
- **plasticity-rule A/B** (dopamine-STDP vs gain-scaling vs none, same
  substrate) — after discriminability; the toolkit is read-only, so this
  one means writing the learning rule (the FlyBridge gain-scaling
  recipe is the reference to beat).
