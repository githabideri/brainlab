# AGENTS.md — brainlab repo rules

This is a **public** repository. Everything in it — files, history, commit
messages, author metadata — is a publication candidate.

## The public boundary

Never commit internal identifiers: machine names, IP addresses, domains,
credential values, or estate-specific paths. Where an environment *is* part
of the record (a measurement ran on a specific machine), write the **role**
the machine plays ("a 4-core laptop-class CPU host", "a 12 GB GPU card"),
never its identity.

Before every commit, run the sweep (all file types, not just `.md`). The
pattern covers address ranges and estate-specific tokens *without naming any
machine* (the specific list lives in the private deployment docs):

```bash
grep -rnE "10\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|100\.64\.[0-9]+\.[0-9]+" \
  --include="*.md" --include="*.py" --include="*.sh" --include="*.json" --include="*.yaml" .
# → zero hits required
```

(private-class addresses are the floor; the full token list for this
estate, including name and domain patterns, lives in the private
deployment docs — a public file must not enumerate the very identifiers
it is there to catch)

## Surfaces

| Surface | Rule |
|---------|------|
| `docs/` | The only maintained prose. `docs/README.md` is the index with a fact-ownership map (one owner per volatile fact class; no-copy elsewhere) |
| `reports/` | Dated frozen snapshots, `YYYY-MM-DD-<kebab-slug>.md`, **no YAML frontmatter**. Never rewrite a published report; supersede with a new report + a one-line pointer appended to the old one |
| `experiments/` | Runnable code, one directory per experiment, each with a `README.md` stating protocol, inputs, and what a pass means |
| `circuits/` | Index of circuit datasets (metadata + provenance hashes). **Large binaries never enter this repo** — circuits are referenced by dataset + hash, fetched by the experiments that need them |

## Verification vocabulary

| Term | Meaning |
|------|---------|
| implemented | code written, not verified |
| locally verified | unit tests + a small-scale run passed |
| live verified | the full measurement ran end-to-end on the target hardware |
| published | report written, swept, pushed |

Don't collapse these into "works".

## What belongs in a report

Goal / Setup (hardware as roles) / Protocol / Commands / Observations /
Numbers / Conclusion (including what failed and what the numbers do *not*
show). The honest negative result is the most valuable row in this repo:
a "the wiring made no difference" report outranks a "the fly played the
game" one.
