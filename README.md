# brainlab

A personal lab for **small brains in agents**: complete animal-brain wiring
diagrams (connectomes) run as neural networks on consumer hardware, and the
question of what that is actually good for.

This is not a project about one fly. It is a lab: we take published
connectomes, run them, measure them, compare them against controls, and
write down what we found — the way [llmlab](https://github.com/githabideri/llmlab)
does it for LLM inference, but for brains made of real wiring.

## The premise

A complete animal brain is now a downloadable dataset (an adult fruit-fly
brain: ~140k neurons, ~50 million anatomical synapses, free to download). The
standard way to run it is a leaky integrate-and-fire network: the real
wiring (connectivity and synapse counts), with per-synapse efficacy and
excitatory/inhibitory signs assigned from predicted neurotransmitter
identities — and it runs on a laptop. That makes a strange experiment
possible: *keep the wiring fixed, put something between its inputs and
outputs, and measure what it does.*

This lab exists to do that measurement honestly: control wirings, frozen
checks, retention tests, numbers on the hardware.

## What lives here

| Path | What it is |
|------|-----------|
| [`docs/`](docs/README.md) | The maintained surface: the substrate (which brains exist, how they're modelled), the evaluation method (how a claim here is earned), the benchmarking method (how a number is measured) |
| [`circuits/`](circuits/README.md) | Index of circuit files and their provenance (the "hardware" of this lab) |
| [`experiments/`](experiments/README.md) | Runnable experiment code — one directory per experiment, each with its own protocol |
| [`scripts/`](scripts/) | Reproducible data-audit tools (e.g. `fafb-cc-audit.py` — the executable source of the FAFB v783 CC population and connection counts; outputs a checksummed JSON manifest into `data/`) |
| [`reports/`](reports/README.md) | Dated, frozen snapshots: what we ran, what we found, what we couldn't |

## What actually matters (current state)

- The substrate is settled: the open adult-female whole-brain connectome
  (FlyWire, 2024) and the first complete male CNS — brain, optic lobes and
  ventral nerve cord (MaleCNS, 2026). The modelling standard is the LIF
  model of Shiu et al. (*Nature* 2024) — see [docs/substrate.md](docs/substrate.md)
  for release dates, scales and the measured-vs-assumed split.
- The evaluation method is written down and in use:
  [docs/evaluation.md](docs/evaluation.md).
- First measurements land in `reports/` as they happen; the first is the
  [FlyBridge audit](reports/2026-10-04-flybridge-audit.md) (a third party's
  trained connectome experiment, examined claim by claim).
- The open scientific question this lab is built around: **does the wiring
  matter?** — a connectome vs. a shuffled or disconnected network of the
  same size, on the same task battery. Nobody has published this cleanly;
  it is the first experiment on the bench.

## Field links

The space this lab works in (context only — this repo is not an index):
the [FlyWire](https://www.nature.com/articles/s41586-024-07558-y) and
[MaleCNS](https://www.janelia.org/project-team/flyem/male-cns-connectome)
connectomes, the [LIF sensorimotor model](https://www.nature.com/articles/s41586-024-07763-9)
(Shiu et al., *Nature* 2024), the [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain)
LIF simulation toolkit, the
[FlyBridge](https://github.com/swotstudio/FlyBridge) trained-circuit
experiment, and [cobanov/awesome-fly](https://github.com/cobanov/awesome-fly)
for the wider scene.

## Conventions

Repo conventions (what may be committed, how reports are written, the
sanitizer sweep) live in [AGENTS.md](AGENTS.md).
