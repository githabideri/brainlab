# Circuit: fabf-cc-b01

The central-complex (CC) + antennal-lobe-projection-neuron (ALPN) subcircuit
of the FlyWire FAFB v783 female adult brain — the substrate of the
`experiments/b-01-internal-compass/` run.

| Field | Value |
|---|---|
| Dataset | FlyWire FAFB v783 (female adult brain; Dorkenwald et al., *Nature* 2024, https://www.nature.com/articles/s41586-024-07558-y), 2025 release files as distributed by the `eonsystemspbc/fly-brain` toolkit |
| Source files | `2025_Connectivity_783.parquet` (15,091,983 proven pairs; sha256 `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347`) + `classification.csv` from `snedea/flybrain` (139,255 rows; sha256 `d941a74188476d60a06dfef7c5130871edbfe9fca77cda571f81f7b9726a184c`) |
| Selection | every neuron with `class == CX` (2,878) and `class == ALPN` (685); all proven pairs with both endpoints in the set (315,268) |
| Neurons | 3,563 — 278 EL ring, 1,244 FBB columnar, 611 PL/PFL tangential, 753 CX-unlabeled, 341 ALPN left, 344 ALPN right |
| Edges | 315,268 directed, one row per pair; sign ±1 from the release's predicted-transmitter column (176,210 excitatory / 139,058 inhibitory); magnitude = PSD count (median 2, p95 17, max 322) |
| Derived files | `data/circuit_cc_b01.npz` + `data/neurons.csv` (built by `build_circuit.py`, not stored here); shuffles `data/circuit_shuffle_<s>.npz` (s = 0..4, degree-preserving 2-switch chains, seeds 4200+s); `data/ring_control.npz` (conventional ring attractor, matched population sizes, seed 42). Hashes and the full weight table in `experiments/b-01-internal-compass/data/manifest.json` |
| Dynamics | frozen Shiu et al. LIF standard (see `docs/substrate.md`); weight rule `sign × min(PSD, p95=17) × 0.275 mV` — the p95 cap is a declared normalization, not a measured property; all added drives (angular velocity, background, visual cue) are declared assumptions, identical across variants |
| Claim ceiling | wiring is measured; sign is a predicted label; efficacies are one global normalization; the visual recalibration drive is an added interface (v783 proves no optic→CC edge). This circuit supports compass-*mechanism* questions, not whole-brain-emulation claims (`docs/navigation.md` §1.4, §2) |
