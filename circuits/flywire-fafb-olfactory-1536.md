# Circuit: flywire-fafb-olfactory-1536

The 1,536-node olfactory subcircuit of the FlyWire FAFB v783 female adult
brain, as released in the public FlyBridge project (MIT license).

| Field | Value |
|---|---|
| Dataset | FlyWire FAFB v783 (female adult brain), 139,255 proofread neurons |
| Selection | Highest weighted internal degree within upstream groups: 256 sensory, 128 local, 256 projection, 512 Kenyon, 96 mushroom-body output, 288 lateral-horn cells (384 readout units: MB-output + lateral-horn appositions) |
| File | `circuit.json` (fetched, not stored here) |
| Fetch | `https://github.com/swotstudio/FlyBridge/raw/main/dist/data/circuit.json` |
| sha256 | `ef6a6c1dd520b461b3beaca3859f0c5de4fb3fccb94336c180016d6ef0017227` |
| Neurons | 1,536 — groups: 256 OLF_ORN_FOOD (sensory drive channel), 128 OLF_LN, 256 OLF_PN, 512 MB_KC, 96 MB_MBON_APP, 288 LH_APP |
| Edges | 42,921 directed, signed (7,582 inhibitory); magnitude `log1p(|w|)` normalized per target |
| Provenance | `swotstudio/FlyBridge` repo, `dist/data/` (selection + coordinate provenance in its `provenance.json`); upstream mirror `github.com/snedea/flybrain` |

Modelled as a topology-constrained recurrent network: per-node leak,
signed per-edge gain (learnable, range (0, 2), 1.0 at zero init), tanh
hidden state, 4 internal propagation steps per input, readout over the
384 output nodes. The wiring (topology + base magnitudes) is frozen; the
drive, readout and task heads are the learned parts. This is the
"small brain" of the FlyBridge curriculum, and the substrate of the
`experiments/scorer/` work.
