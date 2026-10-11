# The shared interface

The minimal organism-independent shape every experiment in this lab takes.
Deliberately small: it is a contract for file layouts and provenance, not a
framework. Do not add machinery until the first experiment that needs it
exists; then add it here and link it.

## The two layers

Everything separates into **substrate** (what was measured) and
**dynamics** (what was assumed). A result is only as honest as the line
between the two.

- **Substrate** = a directed graph with provenance: neurons, edges with
  structural weights, annotations. It is organism-specific fact.
- **Dynamics** = the equations put on that graph: LIF, tanh-rate, rate
  models, or more detailed neuron models. They are assumptions, declared
  per run. The same graph may be run under several dynamics; each is valid
  only within the limits its author states. One model is not assumed
  biologically appropriate for every organism or circuit.

## Circuit specification

A circuit is a derived artifact with a record of this shape (a
`circuits/<name>.md` row plus a machine-readable `manifest` in the
experiment that builds or fetches it):

```
dataset:        name + release/version   (e.g. "FlyWire FAFB v783")
source hashes:  file(s) fetched, sha256 each
selection:      the declared rule (populations, quotas, regions) — written
                down, never "random"
transform:      tool + version that built the runnable file
seeds:          every random choice, named (shuffle seed, stimulus seed,
                init seed)
```

Rebuilding from the record must reproduce the file. Controls are circuits:
same base file, same tool, seed recorded.

## Control taxonomy

Controls are named by what they preserve. Each name answers a different
question; one control never stands in for another.

| Name | Preserves | Question it answers |
|------|-----------|---------------------|
| `disconnected` | nodes only | Is there any effect of wiring at all? (null) |
| `degree` | in/out degree per node, edge count, (optionally) sign per edge | Does the *pattern* of connections matter, beyond density? |
| `sign` | degree + per-node sign balance | Does the placement of inhibition matter? |
| `weight` | degree + per-edge magnitude multiset | Does the specific source→target pairing of strong edges matter? |
| `population` | degree + which populations an edge joins | Does cross-population structure matter? |

A control that is claimed to be "matched" must state, per row, what it
preserves and what it breaks.

## The run contract

One experiment directory contains:

- `README.md` — question, circuit (by `circuits/` entry), dynamics
  declaration, protocol, seeds, pass conditions **written before the run**.
- runnable code, independently invokable (`python3 ...` from the
  directory; no hidden state outside the declared fetches).
- `results/` — one JSON per (variant, seed): metrics, seeds, hardware
  *role*, software versions; plus `summary.json` and `manifest.json`
  (dataset release, circuit hash, transform version, library versions,
  toolkit commit). Results are frozen; a rerun is a new report.
- a dated frozen report in `../reports/` — numbers, what failed, what the
  numbers do *not* show.

## Task interface

A task is: a **stimulus encoder** (external signal → named input
populations), a **readout decoder** (named output populations → task
variables), and **metrics** declared before the run (accuracy, generalization,
data requirement, convergence, noise robustness, retention, runtime, memory).
Held-out evaluation material is fixed before training; test-set-driven
tuning is a finding to report, not a silent correction.

## What this is not

No neuron-level API is defined here. LIF runs use the
`eonsystemspbc/fly-brain` toolkit (see
[substrate.md](substrate.md)); rate/recurrent runs use plain torch. The
moment a second organism needs a different data source, the dataset
specifics live in that experiment's `manifest`, not here.
