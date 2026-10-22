# reports/

Dated, frozen snapshots of what this lab has run and found. Naming:
`YYYY-MM-DD-<kebab-slug>.md`. **No YAML frontmatter.**

A report is written once and never rewritten. When a later report
supersedes one of its findings, the older one gets a one-line pointer
appended at the end:

> **Update (YYYY-MM-DD):** the result here was superseded by
> [new-report](new-report.md) — <one sentence>.

Sections, in order: **Goal / Setup (hardware as roles) / Protocol /
Commands / Observations / Numbers / Conclusion** (including what failed
and what the numbers do not show).

## Recent

- [2026-10-22-worm-v3-sensitivity](2026-10-22-worm-v3-sensitivity.md) — the
  worm-pilot's bounded follow-up, run: 440 runs, 11 independent
  exact-invariant shuffles, signs/τ/graded-stimulus batteries. The
  resting-state difference is confirmed wiring-specific (0 of 11
  shuffles in the active basin) but is a narrow-τ state effect that
  weakens under partial GABAergic signs; the ASH-response routing
  remains a null in every tested combination (control-wiring bar
  not met anywhere).

- [2026-10-04-flybridge-audit](2026-10-04-flybridge-audit.md) — a third
  party's trained-connectome experiment (FlyBridge), examined claim by
  claim: what is real, what is assisted, what is untested.
- [2026-10-05-first-campaign](2026-10-05-first-campaign.md) — the
  first campaign (control-comparison): real vs shuffled vs disconnected
  FlyWire wiring, same stimulus, same spiking model, 5 seeds — the real
  wiring sustains ~3.7× the spiking of shuffled.
- [2026-10-05-scorer-first-measurements](2026-10-05-scorer-first-measurements.md) — S1: the
  frozen 1,536-node circuit as a scoring unit: ~1.2 ms/decision on a
  4-core CPU; the toy task learns through the pure-wiring passthrough.
- [2026-10-05-scorer-polis-s2-screen](2026-10-05-scorer-polis-s2-screen.md) — S2: the
  Polis decision corpus through the frozen wiring — 92.9% on the
  141-row held-out val, zero damaging choices, shuffled control null
  (the gain is in the encoder, not the wiring, on this corpus).
- [2026-10-06-scorer-polis-s3-ab-pilot](2026-10-06-scorer-polis-s3-ab-pilot.md) — S3: the
  live A/B in the Polis decision loop — a structural null: the 27B
  judge sits downstream of the decider-tier hook and overwrites a
  91%-accurate scorer; the hook's correct position is specified as a
  pre-judge veto (S4).
- [2026-10-12-a01-connectome-advantage](2026-10-12-a01-connectome-advantage.md) — A-01: does the
  FlyWire-derived olfactory wiring win on *learnable* tasks? 105 runs
  (fly vs 5 matched controls + MLP/GRU, 2 generated tasks, 3 noise
  levels, 5 seeds): honest null — all three pre-registered criteria
  fail; the wiring is indistinguishable from shuffled in the tanh-rate
  learning regime.
- [2026-10-12-a02-learnable-gains](2026-10-12-a02-learnable-gains.md) — A-02: the same
  battery with the 42,921 edge gains trainable (FlyBridge full
  curriculum, all arms under the same treatment): a *stronger* null,
  no criterion flipped — the A-01 null was not a freeze artifact.
- [2026-10-12-b01-internal-compass](2026-10-12-b01-internal-compass.md) — B-01: the measured
  FAFB v783 CC+ALPN subgraph, driven exactly as pre-registered, is EL-
silent (A2–A5 fail): the declared ALPN drive path has only 2
  excitatory edges into the EL ring, so the declared readout is blind
  to the wiring at this drive. First clean bulk-activity wiring effect
  of the campaign (bio 134k–156k spikes vs shuffle 0); the pathway
  audit is the concrete input to B-02.
