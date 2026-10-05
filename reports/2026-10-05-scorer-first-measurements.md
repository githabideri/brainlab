# 2026-10-05 — scorer: first measurements (the 1,536-node circuit on a plain CPU)

First measurements for the `experiments/scorer/` work: the
`flywire-fafb-olfactory-1536` circuit (1,536 nodes, 42,921 signed edges,
frozen wiring) as a decision-scoring unit — learned state encoder →
sensory drive → 4-step tanh recurrence → readout over 384 output nodes →
per-task candidate-list heads. 233,521 parameters, all of them the
learned parts; the wiring is the frozen part.

Machine: a 4-core laptop-class CPU test box (8 GB RAM), torch CPU.
Role label only — see `experiments/scorer/results/`.

## Latency (one decision, batch 1, 300 timed iters after warmup)

| threads | p50 (ms) | p95 (ms) |
|---|---|---|
| 1 | 1.71 | 1.78 |
| 2 | 1.26 | 1.43 |
| 4 | **1.16** | 1.46 |
| 8 | 2.44 | 3.46 (oversubscription on 4 physical cores) |

One decision — encode a 16-d state, drive 256 nodes, four internal
propagation steps over 42,921 edges, readout, head — takes **~1.2 ms on
a plain 4-core CPU**. The working hypothesis was "well under the
~6 ms/decision the FlyBridge author reported on a GPU" (their number
includes an image CNN; this version replaces it with a small MLP over a
structured state, so the comparison is directional, not
like-for-like). Confirmed with margin: a whole connectome-derived
decision fits inside one game tick with ~10× headroom.

## The toy (does the fixed wiring transmit a learnable signal?)

3-class task; state = 16-d (one-hot class + noise); circuit at
zero-init (pure wiring passthrough: gain 1.0, leak 0.5, bias 0); only
the encoder, drive, readout and head trained. **Pass at epoch 25**
(budget 300): 100% train, 100% validation. The frozen olfactory wiring
does not bury the input signal under the readout — a head can classify
*through* it with nothing in the circuit trained. (The stricter variant
— whether the learned edge gains change anything, and the shuffled-wiring
control of the toy — are S2 questions.)

## What this does not establish

- That the scorer makes *good* decisions on a real decision task: the
  toy's classes are trivially separable by construction. The real test
  is the corpus-trained stage (measured decision rows in, candidate
  choices out) and its A/B against a small fine-tuned model on the same
  battery.
- That 1.2 ms is *enough* in any particular live system: it is the
  cost of the unit, not the end-to-end budget (state assembly, I/O,
  scheduling, and whatever it sits next to all add up).
- Anything biological beyond "this subgraph, driven and read out this
  way, classifies at 1.2 ms on a laptop CPU."

## Next (S2)

Corpus adapter: measured decision rows (state → chosen action → outcome
labels) in, heads out; the pass condition is the FlyBridge offline
screen — zero invalid/damaging choices on held-out rows — plus the
shuffled-wiring control of the same training, so the result separates
"wiring" from "any 233 K-parameter network".
