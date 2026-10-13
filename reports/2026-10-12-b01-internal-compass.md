# 2026-10-12 — B-01 internal compass: the measured CC subgraph, driven as
# pre-registered, does not run a decodable ring attractor

## Goal

Pre-registered test (frozen in `experiments/b-01-internal-compass/README.md`
before the first run): does the *measured* central-complex subgraph of the
FAFB v783 connectome, run with the frozen Shiu et al. LIF dynamics and a set
of declared drive parameters, produce a coherent, decodable heading signal
in the 278 EL ring neurons — and does the measured wiring beat a
degree-matched shuffle and a conventional ring attractor?

The experiment was designed so that a null is a result: at the declared
parameter point, the circuit either runs a compass or it doesn't, and the
controls say whether that's the wiring or the drive.

## What was built

- **Circuit (data rung 1 — published measured connectome):** FAFB v783
  (Dorkenwald et al., *Nature* 2024; 2025 release files), subgraph of
  `class ∈ {CX, ALPN}`: **3,563 neurons** (278 EL ring, 1,244 FBB columnar,
  611 tangential, 753 CX-unlabeled, 341+344 ALPN) and **315,268 proven
  synaptic pairs** (176,210 excitatory / 139,058 inhibitory by the release's
  predicted-transmitter labels). Provenance: `circuits/fafb-cc-b01.md`,
  `experiments/b-01-internal-compass/data/manifest.json` (source file
  sha256s included).
- **Dynamics:** custom torch LIF, the Shiu et al. standard (v0=−52,
  v_th=−45, v_rst=−52, τ_m=20 ms, τ=5 ms, delay 1.8 ms = 2 steps at dt=1 ms,
  refractory 2.2 ms), spike-driven, O(delivered spikes × fan-out).
  Efficacy rule: `sign × min(PSD, p95=17) × 0.275 mV` — the p95 cap is a
  declared normalization, not a measured property.
- **Declared added drives (identical across variants; these are
  assumptions, not measured):** angular-velocity Poisson drive to the ALPN
  population (2 Hz base, scaled to the ±150–300 °/s segment schedule), 6 mV
  steady background on the EL ring, 30 Hz visual cue to the 8 file-order-
  nearest EL cells during the c4 recalibration phase (an added interface —
  v783 proves **no** optic→CC edge exists in the released wiring). The
  README declares the drive at 15 mV per event; the shipped implementation
  delivers drive events as spike-source events at the circuit's own
  normalized edge weights (≤ 4.7 mV/edge) — a *weaker*, more conservative
  realization, disclosed as a deviation (README deviation 5). The 6 mV tonic
  is applied as declared.
- **Variants (5 seeds each, seeds 0–4, all runs completed 2026-10-12):**
  1. `bio` — the measured wiring as extracted.
  2. `shuffle` — per-seed 2-switch (degree-preserving) rewiring: per-node
     in/out degree, edge count and global sign counts preserved; population
     pairing, per-node sign balance, local structure and PSD magnitudes
     broken (the degree control of `docs/architecture.md`).
  3. `ring` — conventional ring attractor: matched population sizes,
     declared weights (ring self 0.7, lateral inh 0.35, FBB→ring 0.6,
     drive 5.0 mV), all edges added by construction.
- **Protocol per session:** 126 s, phases A (25 s, five ±150–300 °/s
  segments) → c1 (25 s, drift with no drive) → c2 (30 s, tracking
  evaluation, per-segment error) → c3 (20 s, deprivation) → c4_off (16 s) →
  c4 (10 s, visual cue). Readout: linear ridge decoder on 250 ms windows of
  EL firing rates (13 train / 12 held-out windows), sin/cos basis.
- **Hardware (role only):** 4-core CPU box, no GPU, single process,
  sequential runs. Longest clean run 2 m 40 s — under the 3 min budget, so
  **no seed reduction was needed** (15/15 runs executed).

## Results

**Headline: at the declared parameter point, no variant runs a decodable
compass. The bio and shuffle circuits are, with respect to the EL readout,
silent; the conventional ring saturates; all are un-decodable.**

| variant | EL mean rate (c1/c3) | total spikes | drift c1 (°/s) | drift c3 (°/s) | c2 tracking error (°) | c2 stability | c4 recovery | decoder held-out R² / MAE |
|---|---|---|---|---|---|---|---|---|
| bio (5 seeds) | **0.0 / 0.0 Hz — silent** | 134k–156k | 0.0 ×5 | 0.0 ×5 | 87–94 | 0.06–0.10 (chance) | none (err never < 30°) | ≈0 / 87–90° |
| shuffle (5 seeds) | **0.0 / 0.0 Hz — silent** | **0 ×5** | 0.0 ×5 | 0.0 ×5 | 87–94 (identical to bio) | 0.06–0.10 | none | ≈0 / 87–90° |
| ring (5 seeds) | active, saturated | 2.09M–2.16M | 0.01–49.3 (highly seed-variable) | 0.13–52.3 | 85–93 | 0.08–0.10 | none | strongly negative (−31…−123) / 97–111° |

Note the asymmetry the table hides: bio and shuffle are *identical on every
decoder-based metric* (both EL-silent) but **opposite in bulk activity** —
the measured wiring sustains a 134k–156k-spike cascade from the declared
drive while the degree-matched shuffle sustains none (0 spikes in all five
seeds). The wiring demonstrably matters for whether the network activates
at all; the declared EL-based metrics are simply blind to non-EL activity,
which is why the controls look identical on them.

Full per-run numbers: `experiments/b-01-internal-compass/results/*.json`
and `results/summary.json` (machine-readable acceptance verdicts).

**Acceptance criteria (as pre-registered):**

- **A1** (c1 drift < 2°/s median or < 5× c3 drift): *passes formally* —
  but only as a trivial consequence of a silent EL population (a constant
  angle has zero slope). This is "no compass", not "stable compass";
  the pass is flagged as such, not claimed.
- **A2** (deprivation produces positive drift): **fails** (0.0 in all bio
  seeds — nothing to deplete).
- **A3** (c2 tracking error < 15° in ≥3/5 seeds): **fails** (0/5; ~90° =
  chance for a 2-D unit vector).
- **A4** (c4 cue-driven recovery < 10 s in ≥3/5 seeds): **fails** (0/5; the
  pre-cue error never falls below 30° because the decoder has no signal to
  correct toward). Compounding: because the cue events are delivered as
  spike-source events (deviation 5), the 8 cued cells receive no direct
  15 mV depolarization at all — recovery below 30° was not achievable at
  this drive level even in principle.
- **A5** (bio beats shuffle on drift or tracking): **fails, in the
  uninteresting way** — the declared EL-based metrics are numerically
  identical for bio and shuffle because both are EL-silent at this drive
  level, so they cannot separate "wiring does it" from "drive is too
  weak". (The bulk-activity difference, 134k–156k vs 0 spikes, is a real
  wiring effect that the declared metrics do not cover.)

**The structural reason (the finding the null reveals):** the declared
drive path does not reach the readout. In the v783 subgraph, **only two
ALPN→EL edges exist** (both excitatory) out of 521 ALPN→CX pairs; the EL
ring's 20,610 incoming edges come almost entirely from within the CX (and
the ring is 99.4% self-inhibitory: 12,203 EL→EL edges, 79 excitatory). The
declared angular-velocity drive targets ALPN, which in this wiring is a
nearly closed population (14,189 ALPN→ALPN edges) that barely touches the
EL ring. So the declared drive keeps ALPN (and some CX cells) active —
134k–156k spikes per bio session, zero in shuffle — while the EL population,
held 1 mV below threshold by the 6 mV tonic, never crosses it. The only
declared drive that targets the readout is the 8-cell visual cue itself, and
in the spike-source delivery semantics it fires the cued cells' (largely
inhibitory) outputs rather than depolarizing them. The bulk activity that
do exists never reaches the 278 EL cells the decoder listens to.

## Interpretation

1. **A clean null at the declared parameter point.** No tuning was
   performed after the pre-registration; the declared drive level sits
   below the activation threshold of the EL ring for the measured wiring.
   The bio/shuffle identity shows the null is a *drive-regime* null: at
   this drive, the readout is insensitive to the wiring, so the controls
   cannot separate "wiring does it" from "drive is too weak".
2. **The conventional ring attractor, at the same declared weights,
   saturates** (2.1M spikes/session, R² strongly negative) — the declared
   weights were never tuned, and the README said so. Its failure is
   expected noise, not a finding about biology.
3. **The most useful output is the pathway audit.** The declared
   angular-velocity→ALPN drive was chosen on the assumption that ALPN
   activity reaches the CC. In the released v783 subgraph it largely does
   not (2 excitatory edges into the EL ring; most ALPN connectivity is
   intra-ALPN). Any declared drive must be validated *against the actual
   subgraph* — reachability from drive population to readout population —
   before the run, not after. This is the concrete input to B-02
   (`experiments/b-02-design/`).
4. **What B-02 must answer** (out of scope for B-01, no tuning done here):
   (a) **drive semantics** — direct g-injection of the declared 15 mV vs
   spike-source delivery (deviation 5); the null here holds under the
   conservative semantics, the other is untested;
   (b) a drive-strength sweep (W_DRIVE, and the 0.275 mV/PSD efficacy
   normalization relative to the 6 mV tonic) to find where the EL
   population activates, if it activates at all;
   (c) whether a different *measured* path from an active population to the
   EL ring exists (the columnar and tangential cells receive the bulk of
   the 5,984 excitatory EL inputs);
   (d) whether the ring's 99.4% self-inhibition is compatible with a
   traveling-wave solution at any drive level in this parameter family;
   (e) what the bio-vs-shuffle bulk-activity difference (134k–156k vs 0
   spikes) means mechanistically — it is the first clean wiring effect the
   campaign has measured, and the declared metrics do not see it.

## Limitations and claim ceiling

- **Wiring is measured (rung 1); sign is a predicted label; efficacies are
  one global normalization** (p95 cap × 0.275 mV). The claim ceiling is the
  mechanism question under the declared normalization — not whole-brain
  emulation, and not a claim that the real EL ring's synapses have these
  weights (`docs/navigation.md` §1.4, §2).
- **The visual recalibration drive is an added interface**: v783 contains
  no optic→CC edge, so "the cue drives 8 ring cells" is an assumption
  identical across variants.
- **The 6 mV EL tonic is the best case** for EL activation (it holds EL 1
  mV below threshold); the declared drive regime is therefore at its most
  generous in exactly the place it fails — and even the declared 15 mV
  drive magnitude was never actually delivered (deviation 5), so the
  realized drive was weaker than the generous case.
- **Shuffle mechanism:** the 2-switch chain is a standard degree-matched
  heuristic (deterministic in the seed, 84.8% acceptance), not a proven
  uniform sample over all degree-matched graphs; the preserved/broken
  properties are exactly the pre-registered ones.
- **One run's wall clock is an artifact:** ring-seed2's recorded
  `elapsed_s` (490 s) includes a temporary two-process CPU contention
  window; the simulation is deterministic in the seed, so the data are
  unaffected. All other runs: 73–160 s.

## Deviations from the pre-registration

None in the declared dynamics, protocol, metrics, seeds or criteria.
Four **code-level** fixes to the previously shipped implementation were
made before the first run and are recorded in the README's deviation
section: the delay queue (which grew unboundedly, breaking the declared
1.8 ms delay), the shuffle construction (O(n·E) → 2-switch chain, same
declared control), a subgraph write-loop bug, and two decoder bookkeeping
bugs (c2 segment off-by-one, a placeholder in the held-out R²). The pandas
pyarrow string backend broke the population masks and was handled with
`to_list()` (no semantic change). One **pre-existing semantic deviation** is
disclosed: the declared 15 mV drive/cue magnitude was never applied (unused
constants); drive events were delivered as spike-source events at circuit
weights (README deviation 5) — a more conservative realization, noted here
so the null is read at the realized drive level.

## Reproducibility

- Code: `experiments/b-01-internal-compass/` (`build_circuit.py`, `lif.py`,
  `run.py`, `summarize.py`); protocol: its `README.md` (frozen
  pre-registration).
- Data: `data/circuit_cc_b01.npz`, `data/circuit_shuffle_{0..4}.npz`,
  `data/ring_control.npz`, `data/neurons.csv` (all gitignored; rebuild via
  `build_circuit.py` from the FAFB v783 parquet + classification CSV —
  source sha256s in `data/manifest.json`, which is committed).
- Runs: `python run.py --variant bio|ring|shuffle --seed 0..4`;
  aggregation: `python summarize.py` → `results/summary.json`.
- Results: `results/<variant>-seed<s>.json` (15 files, each with circuit
  file, torch/python versions, all phase metrics) + `results/summary.json`.
- Run date 2026-10-12 (CEST); hardware role: 4-core CPU, no GPU.

## Review notes — 2026-10-12 (post-hoc; the original text above is unmodified)

Independent review of this experiment against the primary literature
(Seelig & Jayaraman 2015; Turner-Evans 2017/2020; Green 2017; Hulse 2021;
Garner 2024; Shiu 2024) and the **official FAFB v783 annotation**
(`flyconnectome/flywire_annotations`, Schlegel et al. 2024,
DOI 10.1038/s41586-024-07686-5) found that the declared drive and readout
were not the populations the literature describes. The recorded results
stand as written; the interpretation below supersedes where it conflicts.
Full source pack: `notes/CRITICAL_B01_AUDIT.md` (private, 2026-10-12).

1. **The readout population was the wrong cells.** The 278 "ring_neuron"
   readout neurons are the official FAFB v783 **ER** types (ER1–ER6; 278 in
   the whole brain, all from lineage `EBa1`). ER neurons are the *input
   relay into* the compass (bulb/TuBu → ER → EB; Hulse 2021; the
   TuBu→ER→EPG route, Garner 2024) — not the heading population. The
   actual heading population, **EPG (E–PG)**, is a distinct set of
   **47 EPG + 4 EPGt** wedge-localized EL columnar neurons (24/23 per
   side, lineages DM1–4_CX) — **all 51 are present in this subgraph but
   were not used** (Seelig & Jayaraman 2015, Nature 521:186; Turner-Evans
   2017, eLife 6:e23496).
2. **The drive population was the wrong cells.** The 685 ALPN
   (CB olfactory-pathway types) drive is not the angular-velocity
   pathway. The measured update circuit is the **shifted recurrent loop
   E-PG → P-EN (PB) → E-PG (EL)** with P-EN1/P-EN2 showing
   clockwise/counterclockwise signatures (Turner-Evans 2017; Green 2017,
   Nature 546:101). The official **PEN_a(PEN1)/PEN_b(PEN2)** types
   (20 + 22) are present in this subgraph. The navigation review's
   "ALPN drives the compass" sentence described the *antennal-lobe →
   C1/C2 (EIP)* route (Paff 2015) — a different pathway — and was
   misread in the B-01 brief as a direct EL drive.
3. **The shuffled control is confounded.** The 2-switch shuffle set every
   edge to `psd = 1` (recorded in `data/manifest.json`) while the
   biological circuit retained `min(PSD, 17)`. The 134k–156k vs 0
   bulk-activity contrast therefore mixes topology, sign localization and
   the weight distribution; it cannot be attributed to topology alone.
   It remains a real *wiring + weights* effect; a **weight-magnitude-
   matched shuffle** (preserving the PSD multiset, as A-01/A-02's `weight`
   control does) is required before any attribution.
4. **The stimulus is not reproducible from the recorded seed.** `run.py`
   seeds NumPy (the rotation schedule) but the Poisson drives draw from
   PyTorch's **unseeded global RNG**; paired bio/shuffle runs received
   unpaired, unreproducible noise realizations. The declared
   `W_DRIVE`/`W_CUE` = 15 mV were never applied — drive events were
   delivered as the drive neurons' own outgoing synaptic weights
   (≤ 4.675 mV/event; disclosed above).
5. **"No optic→CC pairs in the release" is false.** Counted against the
   **full v783 connectivity parquet** (15,091,983 pair rows; sha256 in
   `data/manifest.json`): **434,005 optic-ish** (`optic` /
   `visual_projection` / `visual_centrifugal` super-classes) **→
   central-class pairs exist**, and the ER→EPG compass input is directly
   proven (**11,847 central→EPG pairs**, dominated by ER2/ER3d/ER1/ER3w/
   ER4d, with a reciprocal EPG→ER branch of 2,691 pairs). The zero in the
   navigation review was an artefact of the class filter used, not of the
   data (navigation.md corrected the same day).
6. **The LIF implementation is faithful to Shiu 2024.** All parameters
   (V_rest = V_reset = −52 mV, V_th = −45 mV, T_refr = 2.2 ms,
   T_m = C·R = 20 ms, τ = 5 ms, T_delay = 1.8 ms, W_syn = 0.275 mV ×
   sign × PSD) match the published model (Shiu et al. 2024, Nature
   584:160, Methods, via the fly-brain toolkit) exactly. This is the
   reusable asset for B-02.

**Net.** B-01 asked "does a declared (but anatomically misplaced) drive
activate a declared (but upstream-relay) readout" — it answered *no*, for
the measurable reasons above (items 1, 2, 4), and its one positive
contrast (item 3) is confounded. It does **not** test the biological
compass. B-02 (see `experiments/README.md`) re-preflights with:
drive = P-EN under the Turner-Evans asymmetric velocity input; readout =
EPG/EPGt; weight-magnitude-matched and population-preserving controls;
seeded, paired, precomputed stimulus streams; distinct stimulation
semantics (current injection vs external synaptic events vs forced
spikes) each unit-tested; and positive controls (calibrated EPG pulse →
spiking; ER→EPG propagation).

## Review note II — 2026-10-12 (evening; second external review of this report)

Two citation corrections to the review note above (original experiment text
still untouched):

1. The Shiu et al. 2024 reference in item 6 is **Nature 634:210–219, 2024**
   (DOI 10.1038/s41586-024-07763-9); "Nature 584:160" was a citation error.
   The parameter-table comparison itself is unchanged.
2. The TuBu route in item 2 is part of the **anterior visual pathway**
   (anterior optic tubercle → bulb → ER; Omoto et al. 2017, DOI
   10.1016/j.cub.2017.02.063; Garner et al. 2024, DOI
   10.1038/s41586-024-07967-z), not a mechanosensory/antennal relay — the
   corresponding wording in `docs/navigation.md` was corrected the same day.
   The TuBu→ER→EPG route stands, as a *visual* route into the EPG.

A further audit the same evening found four additional unverified
citations in `docs/navigation.md` (Vela 2014; Huet & Straube 2010; Huet
2015; Paff 2015 — none resolvable in Crossref/PubMed/OpenAlex); they are
listed there under "Unverified citations" and the affected claims were
re-anchored to verified references. The B-01 experiment, its data, and its
conclusions as stated in review note I are unaffected by this.

## Review note III — 2026-10-13 (from the executed B-02,
## `reports/2026-10-12-b02-internal-compass-v2.md`)

Two findings from the B-02 preflight bear on this report:

1. **The ring control ran with all-positive weights.** B-02's
   byte-identical rebuild (npz sha verified against this experiment's
   manifest) shows that B-01's ring run read the npz `w` column
   without the stored `sign` column — i.e. the 2.1 M spike saturation
   figure corresponds to an all-positive circuit, not the declared
   E/I mix. The signed rebuild (0.80–0.86 M spikes) still oscillates
   in B-01's declared band, so the "the conventional control runs,
   the biological wiring does not" contrast is unaffected; the
   absolute ring number is a property of the all-positive variant.
2. **The B-01 null reproduces one population over.** With the
   corrected readout (EPG/EPGt) and drive (P-EN, forced spikes —
   B-01's actual mechanism, now named) and the full preflight in
   place, the measured wiring is at chance on the rotating-phase
   readout in every arm of a 6-arm battery: the drive reaches the
   readout (51/51 cells in ≤ 2 hops) but its measured efficacy is far
   below what a decodable readout needs; the tonic-held ER ring
   clamps the readout. The declared 60 mV visual cue is the only
   input that fires the readout population, and it does so exactly as
   declared. Nothing in this report's stated conclusions changes;
   this note adds the mechanism of the null and the ring-weight
   deviation.
