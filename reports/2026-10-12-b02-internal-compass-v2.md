# 2026-10-12 — B-02 internal compass v2: the corrected anatomy runs, but the
# measured P-EN→EPG wiring does not transduce the declared velocity drive

**Campaign:** brainlab B-02 (a coordinator-maintained campaign brief; the
common rules live in the same private campaign directory — not part of
this repo). Worked in a dedicated git worktree (branch `b-02`), commits
per stage. Completed 2026-10-13 (night run).

The B-01 review notes (I and II, same day as B-01) relocated both ends of
the compass out of the structures B-01 had wired: the readout from the 17
silent EL cells to the **47 EPG + 4 EPGt** EL columnar cells, and the drive
from the ALPN population (not mapped to v783 types at all) to the **42
P-EN cells** of the Turner-Evans shift loop. This campaign re-runs the
B-01 protocol on the corrected anatomy, with the drive/readout declared as
the mechanisms that actually deliver them.

Per the brief, the three sections below are strictly separate: **preflight
findings** (what was verified before any campaign-scale run) / **design
decisions** (what was frozen at pre-registration) / **measured results**
(what the runs produced). Every claim carries the verification vocabulary
(implemented / locally verified / live verified). For an offline
simulation the ceiling is *locally verified*: the code ran here, the
numbers are committed, but there is no production service behind it.
Nulls are reported as-is.

---

## 1. Preflight findings (Stages 0–2)

### 1.1 Anatomy verified against the 2026-10-12 audit (Stage 0)

**Locally verified** (re-derived from the published sources, sha-pinned;
`data/manifest.json`, `circuits/fafb-cc-b02.md`):

- **CC-only subgraph.** FAFB v783 (Dorkenwald et al., *Nature* 2024; 2025
  release parquet, sha `efeb23fb…`), `class == "CX"` only: **2,878
  neurons / 300,521 proven pairs** — exactly the B-01 subgraph minus the
  685 ALPN cells (B-01's 3,563 / 315,268). The ALPN exclusion is not a
  loss of the compass: ALPN is not mapped to v783 cell types (Paff-2015
  C1/C2 EIP have no v783 analogue) and no ALPN→CX edge in the subgraph
  is part of the Turner-Evans loop.
- **The shift loop reproduces exactly** as in the whole-brain audit
  (B-01 review note I): EPG/EPGt→PEN_a **313**, →PEN_b **269**,
  PEN_a→EPG/EPGt **356**, PEN_b→EPG/EPGt **252**, EPG/EPGt self
  **535**. The 42 P-EN cells split **21 right / 21 left** by the
  official annotation side (PEN_a 20, PEN_b 22).
- **Q1 (drive sign) resolved from primary sources.** Right-side P-EN →
  right (CW) turn; P-EN1/P-EN2 differ in *timing* (lead/lag in the
  shift loop), not direction; the E-PG peak moves *opposite* the body
  rotation. Consequence: the "mirror sign" arm is a **sensitivity
  analysis, not a competing hypothesis**.
- **Q2 (wedge coverage) resolved.** The 360° per-cell wedge assignment
  is not supported by the data. Around the declared EB center (centroid
  of the 17 EL ring cells) the 51 EPG/EPGt cells fill **7 of 8 coarse
  45° bins** (11–14 cells/bin); bin 1 (45–90°) is **empty**; 5 cells
  contradict their annotation side. All of this is recorded in
  `data/wedge-map.json` (sha `ee5b98c9…`); the readout therefore uses
  the coarse bins, not per-cell wedges.
- **Reachability** (Stage 1): P-EN → EPG/EPGt in ≤ 2 hops (51/51), → ER
  ring in 2 hops (278/278); the drive population reaches the readout
  population through the measured wiring — the B-01 configuration error
  (drive into a population with 2 edges to the readout) is gone.

### 1.2 The engine (Stage 1)

**Locally verified** (`test_drives.py`, `data/stage1-tests.json`):

- `lif_b01.py` is a **byte-identical** copy of B-01's frozen LIF
  (Shiu et al. 2024 standard; sha `ecf83226…`).
- `lif2.py` names three distinct drive APIs (B-01's single "drive" was
  overloaded): **API 1** calibrated mV injection, **API 2** declared-
  weight external synaptic events, **API 3** forced spikes (what B-01's
  drive actually did).
- A differential test against an **independent plain-numpy LIF written
  from the Shiu 2024 Methods equations** (`lif_np.py`): single-neuron
  pulse exact; 50-neuron seeded network 12/12 spikes, max |Δt| = 4 ms
  (float32/64 boundary, documented). Two port bugs found and fixed in
  the independent implementation (fancy-index `+=`, block-start table).
- **Paired stimulus streams** precomputed: 5 seeds × 126 s (omega
  schedule identical to B-01's; P-EN Poisson 2 + 40·|ω|/300 Hz per
  side; visual cue 30 Hz onto the EPG cells of the wedge bin containing
  the true heading at cue onset, nearest-non-empty-bin fallback
  recorded). Every arm of every comparison consumes the identical
  stream for its seed; the streams are committed with sha256s in
  `data/manifest.json`.

### 1.3 Positive control (Stage 2) — PASS

**Locally verified** (`stage2b_ringcontrol.py`, `data/stage2b-ringcontrol.json`):

- B-01's conventional ring control (278 ring / 1,244 fbb / 685 drive /
  1,356 g, declared E/I weights) rebuilt **verbatim** from B-01's
  construction code (seed 42): the npz is **byte-identical to the sha
  recorded in the B-01 manifest** — "same parameters" proven, not
  asserted.
- Under B-01's own ring protocol (Poisson 2 + 60|ω|/300 Hz, 30 Hz cue
  to the 8 nearest ring cells, tonic 6 mV, 126 s) the ring oscillates
  at **63.77 / 63.98 / 63.77 / 63.96 / 64.03 Hz in seeds 0–4** — inside
  the brief's acceptance band (60 ± 15 Hz) in every seed. The engine +
  measurement pipeline is verified for the B-02 environment.
- **A B-01 deviation found along the way:** B-01's ring run read the
  npz `w` column without the stored `sign` column, i.e. it ran with
  **all-positive weights** (2.09–2.16 M spikes). The signed rebuild
  (0.80–0.86 M spikes) still oscillates in-band — the control result
  is robust to that deviation, but the B-01 report's ring numbers
  correspond to the all-positive circuit.
- **Supplementary** (`stage2_ring.py`, `data/stage2-ring.json`): the
  measured CC-only subgraph under B-01 weights + the declared drive +
  tonic on the ER ring: the 278-cell ring is active (196–419 spikes/s
  total) with a **flat** power spectrum (peak fraction ≈ 0.007–0.009;
  no oscillation). The measured wiring does not spontaneously run a
  ring rhythm — consistent with B-01's measured-EL silence. The B-02
  readout hypothesis is therefore drive-driven dynamics, not a
  preserved oscillation.

---

## 2. Design decisions (Stage 3 — frozen at pre-registration,
## commit `be947b1`)

The battery and all decision rules were frozen in
`experiments/b-02-internal-compass-v2/README.md` before the Stage 4
runs. The decisions, and two declared amendments:

1. **Six arms × 5 seeds:** `bio` (the hypothesis), `signflip` (the Q1
   mirror sensitivity), `weight05` / `weight2` (weight dose-response),
   `pop` (shuffled drive population), `ring` (positive control, cited
   from Stage 2). **Amendment (declared, not silent):** the brief's
   `sign` and `flip` arms are merged into one `signflip` arm — in a
   two-side system with side-labeled cells and side-labeled schedules
   there is exactly one non-identity permutation, so the two
   descriptions denote the same intervention.
2. **Drive mechanism (amended).** The Stage 1 draft had declared the
   P-EN drive as API-2 events at 3 mV/event; the efficacy analysis
   (Stage 1) showed that sums to ≈ 0.03 mV effective depolarization at
   42 Hz — a **guaranteed null**. The frozen declaration is **API-3
   forced spikes** — B-01's actual mechanism, now named — so the
   downstream efficacy is the *measured* edge weights (≤ 4.675 mV),
   which is the transduction under test. The precomputed streams are
   delivery-mechanism independent and unchanged (hashes stand).
3. **Cue.** API-2 events at a **declared W_CUE = 60 mV/event**, 30 Hz,
   onto the EPG/EPGt cue-bin cells, c4 only. Declared as an **added
   interface**: v783 contains **no optic→CC edge** (B-01 review note
   II), so any visual recalibration signal is an assumption.
4. **Weights.** `w = sign × min(PSD, p95=17) × 0.275 mV` (B-01's rule);
   the sign is a predicted label, the p95 cap and W_syn are declared
   normalizations — all three are part of the claim ceiling.
5. **Readout.** The 8 coarse 45° wedge-bin rates of EPG/EPGt (250 ms
   windows) feed a ridge decoder (α = 1), trained on odd phase-A
   windows, evaluated on even windows per phase. R² is reported **null
   (not a number)** when the phase's true heading is (near-)constant,
   as it is in c1/c3/c4 — only c2 has a rotating target.
6. **Seven decision rules** (transduction, cue effect, sign
   sensitivity, address, weight dose-response, pop null, control),
   each with a numeric satisfaction threshold; every rule is reported
   whether or not satisfied — a null is a result.
7. **Claim ceiling.** The wiring is measured; the edge signs are
   predicted labels; the drive and the cue are added interfaces. The
   experiment can at best establish *what the measured wiring does
   under declared dynamics* — not that the compass is faithfully
   emulated.

---

## 3. Measured results (Stages 4–5)

**Locally verified** (all runs deterministic; per-run and summary
sha256s in `results/summary.json` and `data/stage5-lesion.json`; 25
battery runs in 17 min wall, 20 lesion runs in 11 min).

### 3.1 The battery (Stage 4) — a uniform null

| arm | total spikes / run | EPG/EPGt c2 rate (Hz) | c2 R² | c2 MAE (deg) |
|---|---|---|---|---|
| bio | 57,910–79,376 | 0.06–0.28 (2–10 spikes) | −0.019…+0.023 | 87.6–91.4 |
| signflip | 60,475–80,321 | 0.08–0.36 | −0.003…+0.022 | 86.6–92.3 |
| weight05 | 45,447–56,293 | 0.0 | −0.007…+0.002 | 87.1–92.2 |
| weight2 | 1,127,145–1,388,144 | 18.6–26.0 | −0.028…+0.054 | 85.4–92.7 |
| pop | 43,219–52,636 | 0.0 | −0.007…+0.002 | 87.1–92.2 |

(per-seed values in `results/summary.json`; the weight05 and pop arms
show identical c2 numbers per seed because a silent readout makes every
arm's ridge predict the same seed-dependent constant — §3.1, rule 6)

(chance level, declared from B-01: MAE ≈ 87–94°, R² ≈ 0).

- **Rule 1 (P-EN→EPG transduction): not satisfied (0/5 seeds).** The
  drive fires the P-EN cells as declared (81–86 Hz total in
  stationary c1 = the 2 Hz base × 42 cells), but the EPG/EPGt readout stays at
  2–10 spikes over the entire 36 s rotating phase — and the decoder
  is at chance. The B-01 null **reproduces one population over**
  (ALPN→EL then P-EN→EPG): the measured shift-loop wiring does not
  transduce the declared velocity drive into a decodable heading.
- **Rule 2 (cue effect on the decode): not satisfied.** With a
  near-silent readout the ridge decoder degenerates to a
  seed-dependent **constant** (zero features → zero betas), so c3/c4
  error differences are phase-offset artifacts, not cue effects. (The
  cue's *population-level* efficacy is established separately — §3.3.)
- **Rule 3 (sign sensitivity): not satisfied.** c2 drift ≈ 0 in both
  `bio` and `signflip` (|drift| ≤ 0.14°/s); the side geometry of the
  drive is irrelevant because there is nothing downstream of P-EN to
  be signed.
- **Rule 4 (address): not satisfied** (bio not non-chance; the
  question is moot while rule 1 fails).
- **Rule 5 (weight dose-response): not satisfied on the readout** —
  but the **activity** dose-response is real and large: total spikes
  scale ≈ linearly with weight (45–56 k at ×0.5, 58–79 k at ×1,
  1.13–1.39 M at ×2, ≈ 17× the base point), and the EPG/EPGt
  population wakes up (0 → 18.6–26.0 Hz in c2 at ×2)
  **without** producing tracking. Weight buys activity, not
  information, at this dose range.
- **Rule 6 (pop null): not satisfied as worded, substantively
  satisfied.** The pre-registered wording required MAE ≥ 70° on all
  of c1, c2, c3; with a constant decoder the stationary-phase MAE is
  the constant's offset from that seed's stationary heading, and
  lucky offsets (e.g. seed 3: 18.5°) fail the letter. On the only
  informative phase (c2) the pop arm is at chance in all 5 seeds,
  exactly like every other arm — the shuffled population neither
  helps nor hurts, consistent with rules 1/3.
- **Rule 7 (control): satisfied** (Stage 2: 63.8–64.0 Hz, all seeds,
  byte-identical circuit; the ring control's heading readout was
  strongly negative in B-01 under the same bytes and protocol).

**Interpretation of the uniform null.** In all non-weight2 arms the
network's ~50–80 k total spikes are dominated by the P-EN drive
itself and its two-hop relay; the EPG/EPGt cells sit below threshold
because (a) the measured P-EN→EPG weights are small (≤ 4.675 mV, a
mix of predicted signs) and converge sparsely, and (b) the tonic-held
ER ring clamps them (Stage 5 below). The declared drive *reaches* the
readout population through the measured wiring (Stage 0
reachability, 51/51 in ≤ 2 hops) but its *efficacy* is far below what
a decodable readout needs. This is the same structural situation B-01
found, and the honest statement of it is: **at the declared
parameter point, the measured wiring does not run a decodable
compass, and the side/weight/population manipulations pre-registered
to distinguish wiring from drive all collapse onto the same null.**

### 3.2 Lesion tests (Stage 5)

Same circuit, same streams, same 5 seeds; lesion = the named
population removed (edges dropped, no drive/tonic/cue to it).

| lesion | total spikes (Δ vs same-seed baseline) | EPG/EPGt c2 |
|---|---|---|
| none (baseline) | 57,910–79,376 | 2–10 |
| P-EN silenced | 1,602–2,761 (−96.4…−97.8 %) | 0 |
| ER silenced | 51,352–87,750 (−11…+11 %) | 576–3,630 (≈ 240–908×) |
| EPG silenced | 56,109–76,435 (−3…−2 %) | 0 (by construction) |

- **P-EN silenced: the drive is the network's primary activity
  source.** Removing the 42 P-EN cells and their edges collapses
  total activity by ~97 % in every seed — the bulk activity of the
  B-02 circuit *is* the drive and its relay, not an endogenous
  rhythm (which fits Stage 2a's flat spectrum). The brief's
  "bump holds but stops updating" has no analogue here: there is no
  bump to hold; the c2 readout blip (2–10 spikes) goes to 0.
- **ER silenced: the tonic-held ring clamps the readout.** Removing
  the 278 tonic-driven ER cells increases EPG/EPGt c2 activity by
  ~100–900× (576–3,630 spikes) while total activity moves only
  ±11 % — the ring's net effect on the readout population is
  inhibitory (a clamp, not a carrier of heading information). c2
  MAE shifts by 1–7° but stays at chance. The brief's "tether lost,
  integrator preserved" maps here as: the tether (the tonic) is what
  keeps the readout silent; removing it disinhibits the readout
  without creating tracking. (The per-seed 2→576 … 10→2,397 ratios
  are 240–908×; the small baseline counts are the same order as the
  weight2 arm's, i.e. the disinhibited readout is active but still
  uncorrelated with the heading.)
- **EPG silenced: control.** Readout zero by construction; the rest
  of the network is unchanged (−3…−2 % spikes, identical c2 MAE) —
  the readout population is a functional terminal in this subgraph
  (its EPG→P-EN return edges carry no traffic because the cells are
  silent).

### 3.3 Cue efficacy (the one clean positive)

In the baseline, **100 % of the EPG/EPGt activity in c4 is in the
cue-bin cells** (1,162 / 1,110 / 1,651 / 2,006 / 2,040 spikes over
10 s on 5 cells — ≈ 23–41 Hz per cell — with **zero** EPG/EPGt
activity in c4_off and zero activity in non-cue EPG cells in c4).
The declared 60 mV × 30 Hz cue therefore works exactly as declared at
the population level: it is the *only* thing in the whole experiment
that makes the readout population fire. What it cannot do, with the
measured downstream wiring, is make the firing *track* anything the
decoder can read — the cue is a valid interface onto a dead
downstream.

---

## Limitations and claim ceiling

- Wiring measured (300,521 proven pairs); **edge signs are
  predicted labels**; p95 cap and W_syn are declared normalizations;
  the P-EN drive and the visual cue are **added interfaces** (v783
  has no velocity afferent and no optic→CC edge). This bounds the
  experiment to *what the measured wiring does under declared
  dynamics*.
- 10 of the 2,878 nodes have no official cell_type; 5 EPG/EPGt cells
  are side-contradictions (kept, flagged); wedge bin 1 is empty.
- The P-EN1/P-EN2 lead/lag timing is not implemented (the drive
  addresses the union) — declared out of scope, no velocity source
  in v783 to differentiate it.
- The decoder is only meaningful where its features move; with a
  silent readout it degenerates to a constant, and stationary-phase
  MAE values are constant-offset artifacts (documented in §3.1,
  rule 6). The informative comparison is c2.
- The single free random variable is the seed (5 of them); the
  omega schedule magnitudes come from a fixed generator scheme
  (B-01's). Statistical power for fine effects is limited by
  construction; the reported effects (97 % collapse, 100–900×
  disinhibition, 17× activity dose) are far beyond seed noise.

## Deviations from the pre-registration

1. **Drive mechanism** amended from the Stage 1 draft (API-2 @ 3 mV →
   API-3 forced spikes) **at** Stage 3, with the reason (guaranteed
   null) recorded in the commit and the manifest. Streams and their
   hashes unchanged.
2. **`sign` + `flip` merged into `signflip`** at Stage 3 (mathematical
   identity in a two-side system), documented in README §5.
3. **R² reported as null** on constant-target phases (c1/c3/c4)
   instead of a large-magnitude artifact; the pre-registered
   thresholds are applied to the values as reported.
4. **Rule 6 fails its letter** (constant-offset artifact on
   stationary phases); its substance is reported per phase (§3.1).
5. **The `ring` arm's heading readout is cited from B-01** rather than
   re-run (byte-identical circuit bytes, engine, protocol; the
   oscillation part was re-run and passes).

No deviation touched a decision rule's threshold, a stimulus stream,
or the comparison structure.

## Reproducibility

- Everything lives in `experiments/b-02-internal-compass-v2/`:
  `build_circuit.py` (rebuilds the npz from the pinned sources in
  ~20 s; the source parquet is *not* in the repo), `lif_b01.py`
  (sha-pinned B-01 engine copy), `lif2.py`, `lif_np.py`,
  `test_drives.py`, `stimulus.py`, `stage2_ring.py`,
  `stage2b_ringcontrol.py`, `run_b02.py`, `stage5_lesion.py`.
- `data/manifest.json` pins sha256 of: source parquet, classification,
  official annotation, built circuit, populations, wedge map, all 5
  stimulus streams. `results/summary.json` and
  `data/stage5-lesion.json` carry per-run and summary hashes.
- Re-running any (arm, seed) is exactly reproducible: all randomness
  is in the committed streams; torch is seeded per run.

## References

- B-01 report and its two review notes:
  `reports/2026-10-12-b01-internal-compass.md` (sections "Review
  notes — 2026-10-12" and "Review note II").
- Brief and common rules: a private, coordinator-maintained campaign
  directory outside this repository (`brief-b02.md`, `common-rules.md`).
- Circuit provenance: `circuits/fafb-cc-b02.md`; the B-01 counterpart
  `circuits/fafb-cc-b01.md`; navigation rules `docs/navigation.md`.
- Turner-Evans et al. 2017 (shift loop); Shiu et al. 2024 (LIF
  standard); Dorkenwald et al. 2024 (FAFB v783); Turner-Evans et al.
  2015 (E-PG tuning); Paff et al. 2015 (C1/C2 EIP).

## Post-hoc note — 2026-10-13 (cross-lane input from the A-03 coordinator;
## the original text above is unmodified)

Two items from the A-03 lane, recorded against the B-02 artifacts:

1. **The pinned B-01 `lif.py` `reset()` is latently broken** (A-03's
   audit): it calls `fill_` with a value whose dimensionality follows
   the `v0` argument on state fields that are multi-dim when `v0` is;
   B-01 never called it, so it never surfaced. B-02's code never
   called it either — every re-run here is a **fresh `LIFNet`
   construction**, which the A-03 lane pinned (byte-identical copy)
   and verified to be the constructor's initial state. The Stage 1
   artifacts now say this explicitly: `lif2.reset()` is a B-02-local
   rebuild that does not call the broken inherited primitive, and
   `lif_np.reset()` is the independent reference's own reset
   (verified: both rebuild the exact constructor state; the T1–T4
   re-run is byte-identical to the committed
   `data/stage1-tests.json`, sha `6a2782f6…`).
2. **Corroboration of the transduction null.** The A-03 design report
   (`reports/2026-10-12-a03-design.md`) measured that the lab's
   5 ms `tau_syn` makes fast trains unroutable — the same class of
   mechanism as the B-02/Stage-4 null and as the worm lane's
   `w·λ·τ_syn` finding: at the declared small weights and 5 ms
   integration, convergent spike trains sum to sub-threshold
   depolarization. This is a cross-lane consistency point, not new
   B-02 data; no numbers in the report change.

## Review Note IV (2026-10-13 — third external review)

This note corrects wording; it changes no number, no run, and no
conclusion.

1. **Two sentences in this report are factually wrong and must not be
   re-cited.** Design decision 3 ("v783 contains **no optic→CC
   edge** (B-01 review note II)") and the Limitations bullet ("v783
   has no velocity afferent and **no optic→CC edge**") both assert
   the very claim that B-01's review note II *refutes*, and that the
   audit manifest proves wrong: v783 contains **434,005 optic-ish →
   central** pairs, including **49 optic-ish → EPG/EPGt** pairs
   (`data/audit-manifest-2026-10-12.json`, `scripts/fafb-cc-audit.py`).
   The correct framing of the cue: it is a **declared artificial
   interface** (60 mV events directly onto the EPG/EPGt cue-bin
   cells) — a valid controlled stimulus on its own terms; it does
   not need justification by an absence of optic input, and the
   49 measured optic-ish→EPG pairs are simply not the pathway the
   cue uses.
2. **The positive control is an activity/oscillation control, not a
   heading-decoding control.** The rebuilt ring oscillates at 64 Hz
   under B-01's own protocol — that validates the simulator, the
   drive protocol, and the measurement pipeline. No ring decoder has
   been shown to read a heading; "PASS" must be read at the activity
   level.
3. **Scope of the null.** The battery tests one specific interface:
   coarse 45° wedge-bin EPG/EPGt rates (7/8 bins occupied, one empty
   bin, 5 side-contradiction cells) feeding a ridge decoder, driven
   by a forced-spike P-EN schedule at three weight scales. It shows
   that *this tested interface* does not produce a decodable heading
   under the declared dynamics. It does **not** show that the
   reconstructed compass architecture cannot support heading
   dynamics at all: a cell-type/compartment-based EPG spatial
   mapping (the v783 annotation is finer than wedges) and a decoder
   less dependent on the geometric approximation are the natural
   follow-ups and are not yet run. This report remains a
   well-recorded negative experiment.
4. The transduction null, the three lesion results, and the cue
   behavior stand as reported.
