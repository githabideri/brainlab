# Dataset: polis-decisions-2026-09 (the jevab decision corpus)

Candidate-set + oracle + measured-model verdicts for the Polis game agent's
frozen 8-line reflex state (the `r2` contract: 3 missions × 7-action
candidate lists). Source: the **public** `githabideri/polis` repo,
`data/` (sanitized 2026-09-27: history/identity only — rows untouched;
the corpus is the 2026-09-25/26 measurement run).

| File (repo path) | sha256 | Rows | Role here |
|---|---|---|---|
| `data/ft2-rows-2026-09-26/train.jsonl` | `605e8e31…` (full in `fetch_corpus.py`) | 575 | **train** (state, options, oracle, proposed) |
| `data/ft2-rows-2026-09-26/val.json` | `2e68be90…` | 141 | **held-out screen** (96 valworld + 45 abstain/OOV-mission) |
| `data/ft2-ab/summary.json` | `a3ae962c…` | — | model-level baseline summary |
| `data/ft2-ab/qwen35-decider-2b{,-ft,-ft2}-valworld.jsonl` | see fetcher | 96 each | row-level 2B base / ft / ft2 verdicts on valworld |
| `data/ft2-ab/qwen35-decider-2b{,-ft,-ft2}-abstain.jsonl` | see fetcher | 45 each | row-level verdicts on the abstain slice |

Fetch: `fetch_corpus.py` (hash-verified, from `raw.githubusercontent.com/
githabideri/polis/main/…`). A byte-identical copy of the corpus lives in
`./corpus/` (re-extracted from the polis `main` checkout; full sha256 per
file in `corpus-hashes.json`) so the screen is reproducible without the
polis checkout.

**Overlap facts (measured 2026-10-05, before any training):**

- train(575) ∩ val(141): **0** ids, **0** exact state texts — clean.
- The older 363-row set (`data/ft-rows-v2-2026-09-25.json`) shares **362/363
  exact state texts with the train set** — it is the previous generation of
  the same rows (ids renamed). It is *not* usable as a holdout; the val
  file is. (That set is also the battery the 27B base/ft were measured on:
  84.3% / 85.4% train, 85.4% val.)
- val(141) = 96 rows with normal missions + 45 rows whose `mission` field
  is a truncated foreign-task name (e.g. `"feed the"`) with oracle `wait`
  — the abstain/OOV slice.
- Baselines on valworld-96 (from `ft2-ab`): 2B base 74.0%, 2B-ft **100.0%**,
  2B-ft2 **100.0%**; on abstain-45: 15.6% / 28.9% / **100.0%**.
  These are the bar the scorer's screen is measured against.

**Contract** (`r2/projection.py` `build_state_text`, byte-frozen;
`r2/types.py` `MISSIONS`): the 8-line state text, 3 missions (mine /
harvest / build), 7-action candidate tuples (mine-list vs harvest-list),
phases per mission, and the judge-rule "no" conditions that define our
*damaging-choice* screen (see `train_screen.py`).
