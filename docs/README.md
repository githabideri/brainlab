# docs/ — the maintained surface

Everything in this directory is **living documentation**: it is updated in
place when the fact changes. Reports in `../reports/` are frozen; if a
report contradicts a doc, the doc is right and the report carries (or should
carry) a supersede pointer.

| Doc | Owns |
|-----|------|
| [substrate.md](substrate.md) | What brains exist as open data, the modelling standard, how a circuit file is built and provenanced |
| [evaluation.md](evaluation.md) | How a claim is earned here: frozen checks, retention, negative labels, worksheets, hidden exams, the control-wiring bar |
| [benchmarks.md](benchmarks.md) | How a number is measured: the decision-throughput protocol, the hardware envelope table |

## Fact ownership (one owner per volatile fact class)

- **Dataset facts** (neuron/synapse counts, versions, hashes) →
  `substrate.md` + `../circuits/README.md` index rows only.
- **Measured performance** (ms/step, decisions/s, per hardware) →
  `benchmarks.md` table; reports cite it, never restate drifting copies.
- **Protocol parameters** (check counts, pass thresholds) → `evaluation.md`.
- **Hardware identity** → *nowhere in this repo.* Roles only ("a 12 GB GPU
  card"). The private deployment docs hold the mapping.

Rules:

1. **No-copy.** A volatile value appears in exactly one doc; other places
   link to it.
2. **Verify before writing.** A number in these docs was measured by a run
   named in a report, or read from the named dataset release — never
   transcribed from a video or a blog post without checking the primary
   source.
3. **What is, not what will be.** No roadmap, no "planned". An experiment
   on the bench is described in its own `../experiments/<name>/README.md`.
4. **Supersede, don't rewrite.** Frozen reports keep their numbers; a newer
   finding gets a new report plus a one-line pointer in the old one.
