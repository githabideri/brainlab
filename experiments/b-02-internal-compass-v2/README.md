# B-02 — internal compass v2: EPG readout, P-EN drive

**Pre-registration.** This document is the frozen protocol: variants,
weights, drives, stimulus streams, decision rules, and the endpoint
table, all declared *before* the Stage 4 battery runs. Everything
measured in this experiment is a test of a declared interface on a
measured subgraph — the claim ceiling applies (see §7).

## 0. Question

B-01 (2026-10-12) wired the angular-velocity drive into the antennal
lobe (ALPN) population and read the 17-cell EL ring: the drive did not
reach the declared readout (EL silent; the only ALPN→EL edges in the
whole v783 subgraph: 2). The 2026-10-12 connectome audit (B-01 review
notes I/II) relocated both ends of the compass: the **readout to the
47 EPG + 4 EPGt EL columnar cells** (wedge-localized, the central
pathway's output) and the **drive to the 42 P-EN cells** (the
EPG↔P-EN shift loop, Turner-Evans 2017 — the only velocity input the
released connectome contains). This experiment re-runs the B-01
protocol on the corrected anatomy.

Q1 (drive sign) and Q2 (wedge coverage) were resolved from primary
sources before any run (see `data/wedge-map.json` and the findings log):
right-side P-EN is the CW drive; P-EN1/P-EN2 differ in *timing*
(lead/lag), not direction; the E-PG peak moves *opposite* the body
rotation. The mirror-sign arm is therefore a **sensitivity analysis,
not a hypothesis** (variant `sign` below). The 360° per-cell wedge
assignment is not supported by the data (7 of 8 coarse bins covered,
11–14 cells/bin, 5 side-contradiction cells), so the readout uses the
**coarse 8×45° wedge-bin decomposition** of EPG/EPGt activity.

## 1. Circuit (data rung 1 — measured)

`data/circuit_cc_b02.npz`: the FlyWire FAFB v783 **CC-only** subgraph —
exactly the B-01 subgraph minus the ALPN population (685 cells, not
mapped to v783 types, pre-registered out of scope): **2,878 neurons**
(278 ER ring, 1,244 FBB columnar, 611 PFL tangential, 745 CX-unlabeled;
of which 47 EPG + 4 EPGt + 42 P-EN by the official annotation) and
**300,521 proven pairs** (sha256s of all three source files in
`data/manifest.json`; the source parquet is *not* copied into the
repo). The Turner-Evans shift loop is reproduced in this subgraph
exactly as in the whole-brain audit: EPG/EPGt→PEN_a 313, →PEN_b 269,
PEN_a→EPG/EPGt 356, PEN_b→EPG/EPGt 252, EPG/EPGt self 535
(`data/manifest.json: shift_loop`).

The 17 EL ring cells remain in the set (anatomically present) but play
no declared role: the readout is EPG/EPGt.

## 2. Weights (declared)

Base rule (identical to B-01): `w = sign × min(PSD, p95=17) × 0.275 mV`,
`sign` from the release's predicted-transmitter column (+1 excitatory /
−1 inhibitory), W_syn = 0.275 mV/PSD (the single free parameter of the
Shiu et al. 2024 standard). Max |w| = 4.675 mV. The p95 cap and the
sign labels are **declared normalizations/labels, not measured
properties**.

`weight05` / `weight2` arms: the entire weight vector multiplied by
0.5 / 2.0. No other arm is modified.

## 3. Dynamics

`lif_b01.py` — a byte-identical copy of B-01's frozen torch LIF
(Shiu standard: v0=−52, v_th=−45, v_rst=−52, τ_m=20 ms, τ=5 ms,
delay 1.8 ms = 2 steps at dt=1 ms, refractory 2.2 ms; O(delivered
spikes × fan-out)). Extended in `lif2.py` with three named drive APIs
(§4). A differential test against an independent plain-numpy
implementation written from the Shiu 2024 Methods equations
(`lif_np.py`, `data/stage1-tests.json`): single-neuron pulse exact;
50-neuron seeded network 12/12 spikes, max |Δt| = 4 ms (float32/64
boundary, documented).

## 4. Drives (declared — and this is exactly what is delivered)

B-01's declared-but-not-delivered 15 mV drive was its main deviation;
here every drive is declared as the mechanism it actually uses.

| drive | mechanism | level | stream |
|---|---|---|---|
| P-EN velocity drive | **API 3 — forced spikes** of the named P-EN cells at the Poisson rate (the B-01 mechanism, named). Downstream efficacy is the **measured** edge weights (§2) on the 313/269/356/252 shift-loop edges — no declared weight is assumed for the transduction, which is the hypothesis under test | Poisson, per-cell rate `2 + 40·max(±ω,0)/300 Hz` (base 2 Hz, peak 42 Hz at ±300°/s); right-side 21 cells vs left-side 21 cells by the official annotation side | precomputed, 5 seeds × 126 s, `data/stimuli/stream-seed<s>.npz` (sha256 in manifest) |
| visual recalibration cue | **API 2 — external synaptic events** with declared weight **W_CUE = 60 mV/event** (API-2 summation at 30 Hz raises a resting cell ~3.8 mV — strong bias, sub-threshold alone; the recalibration is a declared added interface: **v783 contains no optic→CC edge** (B-01 review note II), so any visual signal is an assumption) | 30 Hz Poisson onto the EPG/EPGt cells of the 45° wedge bin containing the true heading at cue onset (nearest-non-empty-bin fallback, recorded per seed) during c4 only | same streams |
| tonic background | 6 mV steady-state on the 278 ER ring cells (B-01's declared tonic, unchanged; it keeps the ring out of the dead zone) | constant | — |

**Paired design.** Every arm of every comparison consumes the
*identical* precomputed stream for its seed (the streams are
delivery-mechanism independent: which cell, which millisecond, how
many). The seed is the only free random variable. Stream hashes are in
`data/manifest.json: stimuli`; the circuit npz hash is in the same
manifest. Re-running any (variant, seed) is exactly reproducible.

## 5. Variants (6 arms × 5 seeds, seeds 0–4)

| arm | definition |
|---|---|
| `bio` | base circuit, all drives as declared. The B-02 hypothesis: the measured P-EN→EPG wiring transduces the velocity drive into the EPG readout where the B-01 ALPN→EL path did not |
| `signflip` | `bio` with the two P-EN streams **swapped between the two sides** (right cells consume the left stream, left cells the right). **Pre-registered simplification of the brief's two arms `sign` and `flip`:** in a two-side system with side-labeled cells and side-labeled schedules there is exactly one non-identity permutation — mirroring the sign of ω and swapping the cell populations are the same intervention. This single arm is the **sensitivity analysis for Q1** (mirror sign of the drive side mapping; a sensitivity, not a competing hypothesis) and simultaneously answers the cell-address question (rules 3–4 below) |
| `weight05` | `bio` with all edge weights ×0.5 |
| `weight2` | `bio` with all edge weights ×2 |
| `pop` | the P-EN drive delivered to a **shuffled population**: 42 cells drawn uniformly (np default_rng(999)) from the 2,878 minus the 42 P-EN and 51 EPG/EPGt cells (readout kept clean), the same 42 cells in every seed; the two streams map to the first/second half of the draw (first 21 drawn cells ← left stream, last 21 ← right stream). Tests whether the drive's *address* (P-EN identity) matters, not just its statistics |
| `ring` | B-01's conventional ring control, rebuilt byte-identical (sha matches the B-01 manifest; `stage2b_ringcontrol.py`): 278 ring / 1,244 fbb / 685 drive / 1,356 g, declared E/I weights, B-01's own protocol verbatim. The positive control — Stage 2 measured 63.8–64.0 Hz in all 5 seeds (within the 45–75 Hz acceptance band) |

The omega schedule is B-01's verbatim (rng `10000·seed+7`, 5×5 s
±150–300°/s alternating, c1, 6×6 s, c3, c4_off, c4; 126 s total), and
the Poisson draw is from the precomputed streams (not redrawn), so all
arms see the identical schedule and events.

## 6. Readout, metrics, decision rules (frozen)

**Readout (Q2 resolution).** Features = the **8 coarse 45° wedge-bin
rates of EPG/EPGt** in 250 ms windows (cells assigned to bins by
`data/wedge-map.json`, sha-recorded; bin 1 is empty by the data — its
feature is identically 0; the 5 side-contradiction cells keep their
annotation side). For the `ring` arm the same 8-feature shape is
computed from the 278 ring positions (8 contiguous 34/35-cell bins) so
all arms feed the same decoder.

**Decoder.** Ridge regression (alpha = 1), standardized inputs,
trained on the *odd* phase-A windows, evaluated on the held-out *even*
windows (B-01's scheme). Outputs per phase: held-out R², MAE (deg),
drift (deg/s, slope of the unwrapped decoded heading), stability
(fraction of windows with |err| ≤ 15°); c2 additionally per-segment
MAE; c4 additionally recovery time (first window with 8 consecutive
|err| ≤ 15° after cue onset) and pre-cue error.

**Chance level (declared from B-01):** MAE ≈ 87–94°, R² ≈ 0,
stability ≈ 0.06–0.10.

**Decision rules** (applied to the 5-seed set of each arm; a rule is
"satisfied" as stated, and every rule's outcome is reported whether or
not it is satisfied):

1. **P-EN→EPG transduction (primary).** `bio` shows non-chance heading
   readout: held-out R² > 0.1 **and** MAE < 60° in ≥ 3/5 seeds, on
   c1 or c2 or c3.
2. **Cue effect.** In `bio`, (mean |err| over c3) − (minimum mean
   |err| over c4) ≥ 10° in ≥ 3/5 seeds.
3. **Sign sensitivity.** The c2 drift sign of `signflip` is opposite
   to `bio`'s in ≥ 3/5 seeds, at magnitude within ×2 — i.e. the
   side mapping of the drive is the mechanism of any bio tracking.
4. **Address effect.** If `bio` is non-chance (rule 1) while `pop` is
   at chance (rule 6), the drive's *cell address* (P-EN identity) —
   not merely its rate statistics — carries the signal; `signflip`
   at chance with `bio` non-chance would instead implicate the side
   geometry.
5. **Weight dose-response.** mean |err|(`weight05`) ≥ mean
   |err|(`bio`) and either mean |err|(`weight2`) ≥ mean |err|(`bio`)
   or `weight2` mean EPG/EPGt rate ≥ 2× `bio` (saturation).
6. **Pop null.** `pop` at chance (R² < 0.05 and MAE ≥ 70°) in ≥ 4/5
   seeds.
7. **Control.** `ring` in-band oscillation (Stage 2, done: PASS) and
   its readout is reported for completeness (B-01 found the ring
   control's decoder strongly negative — expected to repeat).

**Nulls are results.** A rule that fails is reported with the full
per-seed numbers; the honest null is the outcome the B-01 review says
was already the most informative one.

## 7. Claim ceiling and honesty clauses

- The wiring (300,521 pairs) is **measured**; the sign of each edge is
  a **predicted label**; the p95 cap and W_syn are **declared
  normalizations**; all three drives are **added interfaces** —
  v783 contains no velocity afferent and no optic→CC edge. This
  supports compass-*mechanism* questions under declared dynamics, not
  whole-brain emulation (`docs/navigation.md` §1–2).
- 10 of the 2,878 nodes have no official cell_type (inside the 745
  CX-unlabeled); 5 EPG/EPGt cells are flagged side-contradictions in
  the wedge map (kept, recorded).
- The 42 P-EN cells split 21/21 by side; P-EN1 (20) vs P-EN2 (22)
  timing (lead/lag) is **not** implemented — the drive addresses the
  union; the subtype split is declared out of scope (it is a timing
  property with no velocity source in v783 to differentiate).
- Reproducibility: `data/manifest.json` pins the sha256 of all source
  files (parquet, classification, annotation), the built circuit, the
  populations, the wedge map, and all five stimulus streams. The
  source parquet is not in the repo; `build_circuit.py` rebuilds the
  npz in ~20 s.

## 8. Endpoint table (what the battery produces)

| file | content |
|---|---|
| `results/<arm>-seed<s>.json` (35 files; the 5 `ring` files exist from Stage 2) | per-run: circuit/stream hashes, per-phase R²/MAE/drift/stability, c2 segment errors, c4 recovery + pre-cue err, P-EN and EPG/EPGt rates per phase, total spikes, elapsed |
| `results/summary.json` | the 6-arm × 5-seed table (31 runs incl. the 5 ring runs from Stage 2) + the 7 decision rules evaluated (satisfied / not, with the numbers) |
| `data/manifest.json` | extended with the battery's run-time hashes (torch/python versions, git sha) |

**Run order and budget** (declared): arms run bio, signflip, weight05,
weight2, pop (5 arms × 5 seeds = 25 runs; ring already done in Stage
2), sequentially, ~2–4 min each at load < 4 (checked before the
batch, per common rules); total wall budget ≤ 2.5 h. Any run that
crashes is re-run once from the same seed (deterministic); a second
crash is reported as a deviation.
