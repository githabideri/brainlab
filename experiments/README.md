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
  model, 5 seeds. The campaign that produces it is running on a
  4-core CPU host; its report lands here when the numbers are in.
