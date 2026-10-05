# circuits/

Index of circuit datasets used in this lab. **No large binaries live here**
— a circuit is referenced by dataset, release, selection rule, and hash;
experiments fetch what they need into their own working directory.

Each row is a circuit the lab has actually consumed. New rows are added in
the same commit that an experiment first uses the circuit, and must carry
the provenance fields (see [../docs/substrate.md](../docs/substrate.md)).

| Name | Dataset (release) | Selection | Neurons | Connections | Hash | Used by |
|------|-------------------|-----------|---------|-------------|------|---------|
| [flywire-fafb-olfactory-1536](flywire-fafb-olfactory-1536.md) | FlyWire FAFB v783, via the FlyBridge atlas (`dist/data/circuit.json`) | degree-based olfactory subgraph (256 sensory / 128 local / 256 projection / 512 KC / 96 MB-out / 288 LH) | 1,536 | 42,921 | `ef6a6c1d…` (full hash in the entry) | `experiments/scorer/` |

## Upstream sources

- **FlyWire** (female *Drosophila*, Dorkenwald et al., *Nature* 2024, CC BY 4.0):
  the full-brain neuron/connection tables and the annotation release
  (`flywire_annotations`, pin the exact release). Public mirrors exist
  (e.g. the `flybrain` packaging); prefer downloading from a mirror that
  publishes the hashes of the originals.
- **MaleCNS v1.0** (male *Drosophila* CNS, Berg et al., *Cell* 2026):
  Janelia's release; note the file sizes are an order of magnitude above
  FlyWire's.
- **eonsystemspbc/fly-brain** (MIT): a ready-to-run LIF implementation of
  the FlyWire connectome with multiple backends — used here as a
  reference implementation, not a dependency.
