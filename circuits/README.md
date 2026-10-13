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
| [fafb-cc-b01](fafb-cc-b01.md) | FlyWire FAFB v783 (measured; source parquet sha256 in `experiments/b-01-internal-compass/data/manifest.json`) | CC+ALPN subgraph (the EL/EL′ ring readout populations + ALPN drive population + surrounding CX context) | 3,563 | 315,268 pairs | see entry | `experiments/b-01-internal-compass/` |
| [c-elegans-substrate](c-elegans-substrate.md) | Cook 2019 whole-animal connectomes (SI6/SI7/SI8/SI9 workbooks, sha256-pinned in `experiments/worm-pilot/data/`) | complete hermaphrodite nervous system (both synapse classes: chemical + gap junction) | 300 (of 302) | 3,669 chemical + 1,089 canonical gap junctions (herm); 3,986 + 1,278 (male) — the SI9 sym/asym sheets are the same physical junctions, modelled once (v3, review round 5) | see entry | `experiments/worm-pilot/` |

## Upstream sources

- **FlyWire FAFB** (adult female *Drosophila* whole brain incl. optic lobes,
  no ventral nerve cord; Dorkenwald et al., *Nature* 2024, CC BY 4.0):
  the neuron/connection tables (139,255 neurons, ~5×10⁷ synapses; the
  per-connection weight is the PSD count, a structural measure) and the
  annotation release (`flywire_annotations`, pin the exact release).
  Public mirrors exist (e.g. the `flybrain` packaging); prefer downloading
  from a mirror that publishes the hashes of the originals.
- **MaleCNS v1.0** (adult male *Drosophila* complete CNS: central brain +
  optic lobes + ventral nerve cord, intact neck connective; 166,691
  neurons, 46M presynaptic sites → 312M PSDs; Berg et al., *Cell* 2026 Sep
  3, DOI 10.1016/j.cell.2026.08.015, preprint
  [10.1101/2025.10.09.680999](https://www.biorxiv.org/content/10.1101/2025.10.09.680999),
  CC BY 4.0): Janelia release v1.0 (2026-06-08, <https://male-cns.janelia.org/>);
  note the file sizes are an order of magnitude above FlyWire's.
- **eonsystemspbc/fly-brain** (MIT): a ready-to-run LIF implementation of
  the FlyWire connectome with multiple backends — used here as a
  reference implementation, not a dependency.
