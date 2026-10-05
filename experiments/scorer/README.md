# scorer — the frozen circuit as a decision-scoring unit

**Question.** A connectome subcircuit with fixed wiring (learnable edge
gains/nodes only in the FlyBridge sense) can be driven by a learned
encoder and read out by per-task heads. Can such a unit (a) learn a
simple classification task *through* the fixed wiring, and (b) do one
decision fast enough on a plain CPU to sit between an agent's policy and
its expensive deliberation tier?

**Circuit.** `flywire-fafb-olfactory-1536` (see
[`../../circuits/flywire-fafb-olfactory-1536.md`](../../circuits/flywire-fafb-olfactory-1536.md)):
1,536 nodes, 42,921 signed edges, fetched by hash from the public
FlyBridge atlas (MIT). Modelled as the FlyBridge "small brain" core:
tanh hidden state, per-node leak, signed per-edge gain (zero-init ->
1.0), 4 internal propagation steps per input, readout over the 384
output nodes.

**What is learned vs frozen.** Frozen: topology and base edge
magnitudes. Learned: the state encoder (16-d state -> 256-d), the
sensory drive (256 -> the 256 drive-channel nodes), the readout
(384 -> 128), and per-task linear heads. (In the full FlyBridge
curriculum the edge gains/leaks/biases also train; here the toy and
benchmark run with the circuit at zero-init, i.e. the pure-wiring
passthrough — the strictest test of the wiring.)

**The candidate-only contract.** A head scores a *fixed* candidate list
for its task; the decision is argmax; a top-1/top-2 margin below
threshold abstains (escalates) instead of choosing. The model never
generates actions. This is a deliberate property, not a limitation: a
fixed-list scorer cannot exhibit the generative degeneration modes
(silent loops, empty output) that a free-decoding model can.

## Files

- `scorer/circuit.py` — the recurrent circuit (fly / shuffled /
  disconnected variants; the shuffled control reuses the FlyBridge
  target-permutation scheme).
- `scorer/model.py` — `Scorer`: encoder -> drive -> circuit -> readout ->
  heads; `score()` returns scores, argmax, margin, abstention flag.
- `bench_latency.py` — one decision, batch 1, plain CPU, thread sweep;
  writes a `.latency.json` with a *role* label only (no machine
  identity).
- `toy_train.py` — 3-class toy through the frozen wiring; writes
  `toy<seed>.json`.
- `fetch_circuit.py` — fetch-by-hash helper for the circuits/ entry.
- `polis/` — **S2**: the polis decision-corpus adapter and offline screen
  (575 measured ft2 rows train the two heads; the 141-row val file — 96
  valworld + 45 stuck-situation abstain rows with oracle `wait` — is the
  held-out screen vs the three measured 2B models; the shuffled-wiring
  control is the anti-fabrication check). `dataset.md` documents the
  corpus; the damaging-choice rules live in `adapter.py`.

## Run (on a plain CPU box, torch only)

```bash
python3 fetch_circuit.py \
  https://github.com/swotstudio/FlyBridge/raw/main/dist/data/circuit.json \
  ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227 \
  -o circuit.json
python3 toy_train.py --circuit circuit.json
python3 bench_latency.py --circuit circuit.json --threads 1,2,4,8 \
  --label 4-core-cpu-testbed
```

## Pass conditions

- **Toy (smoke of the wiring):** train accuracy >= 0.95 *and*
  validation accuracy >= 0.90 within 300 epochs. A pass shows the fixed
  wiring transmits a learnable signal to the output nodes; a fail means
  the pure-wiring passthrough buries the drive and the learned gains are
  load-bearing (a result in itself, to be reported either way).
- **Latency:** a number, not a pass — one decision's p50/p95 across the
  thread sweep on a plain CPU. The working hypothesis: well under the
  ~6 ms/decision the FlyBridge author reported *on a GPU*, so the
  "faster than a deliberation model tier" claim is testable.
- **Polis screen (S2):** on the held-out val, the scorer must score at
  least as high as the *base* 2B model (74.0% on valworld; the FT models
  are the ceiling, not the bar), commit **zero** damaging-choice
  violations (the 2B models commit some), and **must beat the
  shuffled-wiring control** — if the permuted wiring scores the same,
  the gain is in the encoder, not the connectome, and that is reported
  as such. The oracle in this corpus is phase-following by design: the
  scorer is a veto tier below the LLM decider, not a replacement (the
  live A/B in S3 uses the game's own success metrics, not oracle match).

## What a pass does not establish

That the scorer makes *good* decisions on a real task (that's the
corpus-trained stage), that it beats a small fine-tuned model on a real
battery (that's the A/B), or anything about biology beyond "this wiring,
driven and read out this way, can classify".
