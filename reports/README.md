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
