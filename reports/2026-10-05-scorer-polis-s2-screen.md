# S2 screen: the scorer on the polis decision corpus (2026-10-05)

**Goal.** S1 established that a frozen 1,536-node FlyBridge olfactory
circuit, driven by a learned encoder and read out by per-task heads, can
learn a toy classification task and scores one decision in ~1.1 ms on a
4-core CPU. S2 asks the corpus question: trained on the measured polis
decision rows, does the scorer (a) reach the accuracy bar of the small
language models on the held-out val set, (b) commit *zero* damaging
choices (the "zero-damaging" screen), and (c) beat the **shuffled-wiring
control** — the anti-fabrication check that separates "the connectome
helps" from "a small MLP with a frozen identity layer inside helps"?

**Setup.** Circuit `flywire-fafb-olfactory-1536` (frozen wiring,
zero-init base gains; 42,921 signed edges; tanh recurrence, 4 internal
steps; readout over 384 output nodes). Learned: state encoder (143 → 64 →
64), sensory drive (64 → 256 drive nodes), readout (384 → 32), two linear
heads (mine-list ×7, harvest-list ×7). 89,687 trainable parameters,
~1.4 MB. Features are a closed one-hot encoding of the 8-line r2 state
(task class, phase, proximity flags, fixture presence, carrying/items
one-hots over a 35-item vocabulary, since/last one-hots, proposal
one-hot) — `polis/adapter.py`. Corpus: the polis decision rows of
2026-09-25/26 (`polis/dataset.md`, hash-pinned in `polis/corpus/`): 575
train, 141 held-out val (96 valworld + 45 stuck-situation abstain rows
with oracle `wait`). Baselines: the three measured 2B deciders
(`data/ft2-ab/`). Hardware: a 4-core CPU testbed (role only), torch CPU,
317 s wall for both variants.

**Protocol.** Adam 2e-3, batch 32, 400-epoch cap, early stop on a
deterministic 20% internal split of the train fold (115 rows; best-epoch
weights kept). The val file is touched once, at screen time, per model.
The shuffled variant gets *identical* training with a permuted output
index map (the FlyBridge target-permutation scheme). Seed 0 throughout;
re-running produces byte-identical decisions.

## Numbers

| model | valworld (96) | abstain (45) | total (141) | damaging choices on val |
|---|---|---|---|---|
| **scorer-fly** (this work) | 89.58 | **100.0** | **92.91** | **0** |
| scorer-shuffled (same training, permuted index map) | 88.54 | 100.0 | 92.20 | 1 (give-tool-already-held, valw-045) |
| 2B base | 73.96 | 15.56 | 55.32 | 4 (mine-without-pickaxe ×4) |
| 2B-ft | 100.0 | 28.89 | 77.30 | 0 measurable (abstain rows carry no state) |
| 2B-ft2 | 100.0 | 100.0 | 100.0 | 0 |

2B accuracies are the in-file numbers (their row files record
choice/oracle but no state, so the abstain slice can only be measured
in-file; the 45-row abstain set is the same set as the val file's,
verified by multiset). Damaging-choice rules: mine without pickaxe,
harvest a gone crop, give a tool already held, pick up with nothing
present — `adapter.violations`.

**The scorer's ten errors, all one class.** Every one of the 10 valworld
misses is a *harvest-mission, tool-required state*: the state reports a
tool requirement, the oracle is `give_tool`, and the scorer commits
`harvest_target` (valw-027/033/049/056/059/064/066/073/089 + 1 more of the
same shape). These are *harmless* errors (the attempt fails clean and the
loop returns to tool-giving) — which is why the zero-damaging screen
holds despite them. The mine-mission analogue of the same situation
(`mine_target` rejected, `give_tool` correct) is one the scorer *gets
right*; the harvest head apparently reads the tool-required signal less
reliably. The abstain slice (stuck states → `wait`) is perfect: 45/45,
vs 15.56% (base) and 28.89% (ft) for the 2B models.

## Findings

1. **The zero-damaging screen passes.** 0 damaging choices on held-out
   val (base 2B commits 4; ft2 also 0). On the valworld slice the scorer
   beats base 2B by 15.6 pp but *loses* 10 rows (10.4 pp) to both
   fine-tuned models (ft, ft2); those 10 rows are the harmless
   tool-required class. On the abstain slice it beats base (15.56) and
   ft (28.89) by 84.4 and 71.1 pp respectively.
2. **The wiring is not load-bearing on this corpus — the control worked
   as designed.** Shuffled vs fly: 92.20 vs 92.91 (one row: valw-045,
   where the shuffled variant additionally commits the single damaging
   choice), identical internal-val accuracy (99.13), same error class.
   The olfactory connectome, zero-init and frozen, adds no measurable
   signal beyond what the encoder→readout path already carries. Per the
   pre-registered interpretation: the gain in S2 lives in the learned
   encoder, and the circuit is — functionally — a fixed nonlinear
   buffer. A connectome-specific claim needs a corpus where the
   wiring's inductive bias (sparse expansion, signed recurrence) buys
   something the encoder cannot; this corpus does not show that. Note
   the regime contrast with the sibling experiment
   (`control-comparison`, report `2026-10-05-first-campaign.md`): there
   the *same* wiring, simulated as spiking (AlphaLIF) neurons, sustains
   ~3.7× the activity of the shuffled control. The wiring effect is
   therefore dynamics-dependent — present in the spiking regime, not
   measurable in this tanh-rate scorer — which is exactly the sort of
   specificity a connectome claim needs (and lacks, here).
3. **The veto-tier hypothesis is alive.** What S2 *does* establish,
   independent of the wiring question: a ~90k-parameter, ~1.1 ms
   decision unit that matches or beats the small LLMs on everything
   except one narrow error class, with zero damaging choices, fits the
   "pre-veto next to the small-model veto" integration the polis build
   owner asked for. S3 (live A/B on the game battery) is the test of
   that claim — and it tests the *veto tier*, not the connectome.

## What this does not establish

That the scorer improves the *live* agent (S3, game-battery metrics,
scorer on vs off); that it generalizes beyond the three measured
missions; anything about the biology of the olfactory circuit beyond
"driven and read out this way, it classifies"; or that its valworld
accuracy survives a corpus with more diverse state dynamics (the 2026-09
rows are one world, two fixture types).

## Artifacts

`experiments/scorer/polis/train_screen.py` (deterministic;
`--corpus polis/corpus --circuit circuit.json --epochs 400`),
`results/2026-10-05-s2-polis-screen.json` (this run),
`results/64x32-polis-widths.latency.json` (1.085 ms p50 / 4 threads,
1.662 / 1 thread), trained weights `scorer-fly.pt` /
`scorer-shuffled.pt` (1.4 MB; not in the repo — retrain in ~5 min, seed
0).

## Next (S3, owned by the polis build session)

Live A/B on the game battery: scorer as pre-veto (ranks the candidate
list; the small-model veto keeps final say — per the build owner's
integration decision), scorer-on vs scorer-off arms, N episodes each,
game success + damaging-action + decision-latency metrics. The S2
error class (harvest tool-required states) is the predicted failure
mode to watch in the on-arm logs.
