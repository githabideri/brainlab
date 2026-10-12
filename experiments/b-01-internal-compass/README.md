# B-01 — the smallest-defensible Drosophila central-complex internal compass

*Pre-registration: this section (hypothesis, protocol, acceptance criteria,
trained-vs-frozen split) was written BEFORE any run. Changes after the first
full evaluation are findings to report, not silent corrections.*

## Question

Does the measured wiring of the Drosophila central complex (FlyWire FAFB v783)
plus its measured antennal-lobe input, run under the declared Shiu et al. LIF
dynamics (`docs/substrate.md`), behave like an internal compass — a stable
heading representation that (1) holds a heading, (2) updates under angular
velocity, (3) drifts when deprived, and (4) recovers when a visual cue is
present — and does it do so better than a conventional ring attractor with
matched neuron count and a degree-preserving shuffle of the wiring?

## What this is not

A subcircuit of ~3.6k of a 138,639-neuron brain; a wiring diagram run under
assumed biophysics. It is **not** a claim of faithful whole-brain emulation,
not a behavior, and not evidence about allocentric position memory or
cognitive maps (see `docs/navigation.md` §1.4, §3). The "visual cue" is an
added interface (v783 proves no optic→CC edge); the "heading" is a linear
decoder, not a fly turning.

## Circuit (rung 1 — measured connectome subset)

`circuits/fafb-cc-b01.md` — FlyWire FAFB v783 (Dorkenwald et al., *Nature*
2024, https://www.nature.com/articles/s41586-024-07558-y), 2025 release files
as distributed by the eonsystemspbc/fly-brain toolkit. Selection rule (all
three):
- every neuron annotated `class == CX` (2,878: 278 EL ring, 1,244 FBB columnar,
  611 PL/PFL tangential, 745 unlabeled), and
- every neuron annotated `class == ALPN` (685: 341 left, 344 right) as the
  measured angular-velocity input,
- all proven connection pairs with both endpoints in the set (315,268).

Transform: `build_circuit.py` (this directory) → `data/circuit_cc_b01.npz`
(+ `data/neurons.csv`), hash in `data/manifest.json`. The fly-brain toolkit's
*tooling* is not used (its native format is the whole brain); only the
*published model* is the reference.

## Dynamics (declared per `docs/substrate.md`)

Custom torch LIF (`lif.py`), dt = 1 ms:
- v0 = v_rst = −52 mV, v_th = −45 mV, τ_m = 20 ms, synaptic current single-
  exponential τ = 5 ms, 1.8 ms delivery delay (→ 2 steps), refractory 2.2 ms.
- Edge weight: `sign × min(PSD, 17) × 0.275 mV` — sign from the release's
  per-pair predicted-transmitter column (a **predicted** label); PSD (the
  measured structural count) **capped at the subgraph's p95 = 17** — a
  declared normalization, applied identically to all variants, reported in
  the report if it changes anything.
- **Added drives (assumptions, identical for all variants):**
  - angular velocity: Poisson input, rate
    `2 + 60·max(±ω, 0)/300 Hz` (ω in deg/s), 15 mV per delivered event; to
    the ALPN population for `bio`/`shuffle` (left side = +ω — a declared
    polarity assumption; the real fly's laterality is not settled in the
    sources), to the drive populations for `ring`.
  - background: a tonic depolarizing current of 6 mV (steady-state
    offset of the membrane) on all EL ring cells — a declared background
    drive so the code stays alive in the absence of other input;
  - visual cue: 30 Hz Poisson, 15 mV, to the 8 EL cells geometrically
    nearest the true heading in the ring's position order (for `ring`: the
    8 ring units nearest by construction; for `bio`/`shuffle`: the 8 EL
    ring cells nearest in file order — **declared assumption**: the v783
    ring-cell file order is treated as circumferential order; it is not
    verified as such, so for the biological variants the cue targets are
    best read as "8 ring cells", not a verified position map), the added
    recalibration interface (`docs/navigation.md` §1.2).
- Trained vs frozen: the circuit (edges, signs, weights, all LIF constants)
  is frozen. The only learned object is the linear decoder (ridge,
  α = 1.0, no tuning) used for readout (cue targeting is the geometric rule above).

## Controls

| Variant | Preserves | Breaks |
|---|---|---|
| `bio` | the measured wiring | (reference) |
| `ring` | nothing of the fly wiring; total neuron count (3,563) and role counts (278 ring / 1,244 fan / 685 drive / 1,356 global) | all anatomy — the conventional spiking ring attractor: bidirectional lateral inhibition (window 24, 0.35 mV), self-excitation (window 2, 0.7 mV), fan recurrent on its own column (0.3 mV) and to the ring (0.6 mV), fan→drive at a shifted column (0.5 mV), drive→ring asymmetric windows (±[1..6] positions, 5 mV), seeded global inhibition (0.25 mV, 30 ring targets per global unit); all weights declared constants, full table in the manifest |
| `shuffle` (per seed, seed 4200+seed) | in/out degree per node, edge count, global sign counts | population pairing, per-node sign balance, local structure, PSD magnitudes (all shuffled edges carry the minimum weight level, psd = 1) — the degree control of `docs/architecture.md` |

*Control mechanism note (post-pre-registration, code-level only): the shuffle is
built by a 2-switch chain (Micali–Spirakis style, `build_circuit.py`), i.e. a
fixed budget of random degree-preserving edge swaps started from the real
wiring. This preserves exactly the declared rows above and is deterministic in
the seed; it is a standard switch-chain heuristic, not a proven-uniform sample
over all degree-matched graphs. Attempt/acceptance counts are recorded per
shuffle seed in `data/manifest.json`.*

## Protocol (one continuous session per variant × seed; 5 seeds each: 0–4)

Ground-truth heading H starts at 0°; H_true(t) = ∫ω dt (the fly is
kinematically commanded — a virtual fly; no motor loop).

| Phase | t (s) | ω | cue | Purpose |
|---|---|---|---|---|
| A calibration | 0–25 | 5×5 s segments, ±150–300 deg/s (seeded) | off | train decoder; **held out: odd windows** |
| 1 constant orientation | 25–50 | 0 | on | drift / stability |
| 2 commanded rotations | 50–86 | 6×6 s, alternating sign, 150–300 deg/s (seeded) | on | update/tracking error |
| 3 deprivation | 86–106 | 0 | off | drift rate |
| 4 landmark return | 106–126 | 0 | off 10 s, then on | recovery time |

Decoder: 250 ms windows, EL ring-cell spike rates → ridge on (sin H, cos H);
trained on even windows of A, evaluated on odd windows (held-out) — the
held-out check is reported; the same decoder scores all phases.

## Metrics (declared before the run)

- **drift** (deg/s): circular least-squares slope of the decoded heading in
  phases 1 and 3 (reported signed; |drift| used for acceptance).
- **stability**: fraction of 250 ms windows with |decoded − true| ≤ 15°.
- **tracking error** (deg): per-segment mean absolute circular error in
  phase 2 (mean + spread across segments and seeds).
- **recovery** (s): time from cue onset in phase 4 until the error is ≤ 15°
  continuously for 2 s (null if not reached; final error always reported).
- Decoder held-out R² and mean absolute error (the readout's own honesty
  check), plus per-phase mean EL firing rate (a silent circuit must be
  labelled, not read as "zero drift").

## Acceptance criteria (self-set thresholds, declared before the run)

A compass-like **mechanism** (not perfection) counts as a pass when, on the
`bio` variant across 5 seeds:
- A1: median |drift| in phase 1 (cue on) < 2 deg/s, or a measured drift with
  cue on < 5× the phase-3 deprivation drift (correction works);
- A2: phase-3 deprivation drift > 0.1 deg/s (the representation is
  integrative, not locked) — a *required* positive for the mechanism to be
  compass-like at all;
- A3: phase-2 mean tracking error < 15° in at least 3 of 5 seeds;
- A4: phase-4 recovery < 10 s in at least 3 of 5 seeds;
- A5 (the comparative claim): `bio` beats `shuffle` on the drift *or*
  tracking metric (mean over seeds), with the `ring` variant reported
  wherever it falls.

A **null or failure of any of A1–A5 is a valid and publishable result** —
in particular "the measured wiring does not sustain a stable heading
attractor under these dynamics without added machinery" is itself the
finding, and the added-machinery inventory in the report is the payload.

## Commands

```bash
PY=../venv/bin/python            # torch CPU, 4-core host, 12 GB RAM
$PY build_circuit.py --parquet <FAFB-v783 connectivity parquet> \
    --classification <classification csv, fetched per manifest> \
    --out data --shuffle-seeds 0 1 2 3 4
$PY run.py --variant bio|ring|shuffle --seed 0..4
$PY summarize.py                 # results/summary.json
```

`results/<variant>-seed<s>.json` per run; `results/summary.json` aggregate;
`results/manifest.json` (dataset release, circuit hash, transform version,
library versions). Hardware is recorded as a role only.

## Code deviations (post-pre-registration bug fixes, recorded per protocol)

The dynamics and protocol above were implemented as pre-registered. The
following are code-level fixes to the *previously shipped implementation*
(they restore the declared behavior; nothing about the declared dynamics,
protocol, metrics or criteria changed):

1. **Delay queue (`lif.py`).** The original code appended internal spikes and
   external drive to the delay queue as separate entries, so the queue grew
   with every spike and the declared constant 1.8 ms (2-step) delay was not
   honored. Fixed: internal and external events of a step are merged into a
   single queue slot; the queue length is fixed at `delay_steps` and every
   event — internal or external — is delivered exactly 2 steps later.
   A source with no outgoing edges can no longer deliver another neuron's
   edges (masked in `_deliver`).
2. **Shuffle construction (`build_circuit.py`).** The original
   `rng.choice(replace=False)`-per-node algorithm was O(n·E) (it permuted the
   full 315k-edge target bag for each of 3,563 nodes) and deadlocked on
   endgame self-loop conflicts. Replaced by the 2-switch chain above — same
   declared preserved/broken properties, deterministic in the seed.
3. **Subgraph extraction (`build_circuit.py`).** The original write loop
   assigned every extracted row to the last element of the edges array, which
   collapsed the subgraph to a single pair; extraction is now vectorized.
4. **Decoder bookkeeping (`run.py`).** the c2 per-segment error table now
   uses the six rotation segments (the shipped code included the ω = 0 phase
   boundary segment), and a leftover placeholder in the held-out R²
   computation was removed.
