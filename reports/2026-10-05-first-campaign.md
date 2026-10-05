# 2026-10-05 — First campaign: does the wiring matter? (fly vs shuffled vs disconnected)

## Question

FlyBridge (see `2026-10-04-flybridge-audit.md`) left the field's open causal
question pending: when a connectome-derived network responds, how much of the
response is due to the *actual wiring* rather than to "a lot of edges
driven by a stimulus"? This campaign runs the same 138,639-neuron FlyWire
connectome three ways — **fly** (real wiring), **shuffled** (every edge keeps
its source and weight; targets re-sampled uniformly among input-receiving
neurons, no duplicate edges, seed 20261004), and **disconnected** (same
neurons, zero edges) — under the identical stimulus, model, and budget, and
compares the response landscapes.

## Protocol (what was held fixed)

- **Circuit data:** FlyWire FAFB v783 via the `eonsystemspbc/fly-brain`
  toolkit (parquet sha256-16 `efeb23fb99098e9c`), 138,639 neurons,
  15,091,983 excitatory edges (the toolkit's `Excitatory x Connectivity`
  column; the `fly` matrix is the toolkit's own, bit-identical to its
  published runs).
- **Model:** the toolkit's AlphaLIF (Shiu et al. parameter set, wScale
  0.275), dt = 0.1 ms, unmodified; the `fly` variant therefore reproduces
  the toolkit's reference behaviour (validation: our 1 s-stim window gave
  17.5–17.8k spikes / ~355 active vs the toolkit's published 16,567 / 380
  for a full 1 s stimulus).
- **Stimulus:** the toolkit's sugar experiment — 21 sugar-sensing GRNs,
  200 Hz Poisson drive. Timeline: 0.5 s settle → 1.0 s stimulus → 1.0 s
  post-offset response (20,000 steps).
- **Seeds:** 5 stimulus seeds (100–104), identical across variants;
  shuffling seed recorded in the manifest.
- **Hardware:** a 4-core desktop-CPU container (8 GB RAM), torch
  2.14.1+cpu — deliberately the commodity tier; the toolkit's published
  CSV contains no PyTorch-CPU rows, so every number here is new.
- **Readout:** per-neuron spike counts (full 2 s and post-offset window),
  active-neuron count (>1 Hz), per-seed pairwise comparisons (Spearman
  rank correlation of per-neuron rates, top-50 Jaccard, total-spike
  ratios).

## Results

Per-(variant, seed) runs, mean ± sd over 5 seeds:

| Variant | Total spikes | Active neurons | Post-offset spikes |
|---|---|---|---|
| fly | 17,589 ± 192 | ~355 | 137–338 |
| shuffled | 4,793 ± 5 | ~53 | 1–3 |
| disconnected | 4,214 ± 15 | 21 (exactly the driven set) | 0 |

Pairwise comparison (mean over the 5 seeds):

| Pair | Spearman (per-neuron rates) | Top-50 Jaccard | Spike ratio (second/first) |
|---|---|---|---|
| fly vs shuffled | 0.134 | 0.266 | 0.273 |
| fly vs disconnected | 0.230 | 0.266 | 0.240 |
| shuffled vs disconnected | 0.587 | 0.266 | 0.879 |

## Reading

1. **Magnitude:** the real wiring sustains ~3.7× more total spiking and
   ~7× more active neurons than the same circuit with randomly rewired
   targets, and ~4.2× more than no wiring at all. The sugar pathway
   amplifies; random connectivity damps to near-null.
2. **Structure:** the shuffled network's response is *more similar to the
   disconnected null (ρ = 0.587) than to the real brain (ρ = 0.134)*, and
   carries only ~88% of the null's spike count. Random rewiring does not
   just attenuate the sugar signal — it destroys the response landscape
   almost entirely; what survives looks like the Poisson floor, not a
   degraded version of the real response. In other words, the response
   depends on the *specificity* of the wiring — which edge goes where —
   not merely on the existence of edges (that is what the disconnected
   arm shows, and is the trivial half of the result).
   Two scope limits, stated rather than footnoted: (a) this is an
   *activity-structure* result, not an *information* result — we have
   not shown that the real wiring carries a decodable stimulus code the
   shuffled one destroys; that needs the multi-stimulus
   discriminability follow-up (sugar vs water vs salt: can a downstream
   readout separate them better on real than on shuffled wiring); (b) the
   olfactory pathway is a known sparse-expansion circuit, so "specific
   convergence matters" is partly *confirmatory* — a quantitative
   confirmation of why the circuit is shaped that way, not a new fact
   about the fly.
3. **Seed stability:** shuffled is astonishingly stable across seeds
   (±5 spikes on 4,793) — when the pathway is destroyed, the outcome is
   nearly deterministic; fly's ±192 is the network doing real work.
4. **What this does not establish:** one stimulus, one readout, fixed
   wiring, no learning, one fly's connectome. It is a statement about
   static circuit function, not about intelligence, behaviour, or the
   generalizability of the result across tasks. (The equal 0.266
   top-50 Jaccard across all three pairs is a zero-count tie artifact in
   the top-50 slotting — the Spearman columns are the meaningful
   comparison.)

## The benchmark envelope (CPU tier)

From the same campaign, the toolkit's benchmark suite on the 4-core box
(run label `brainlab-cpu-20261004`; spikes disabled to keep the CSV lean):

| Backend | t (s) | n | sim wall (s) | vs the toolkit's CPU machine |
|---|---|---|---|---|
| Brian2 (CPU, brian2cpp) | 0.1 | 1 | 1.13 | ~30–60% slower |
| Brian2 (CPU) | 1 | 1 | 4.71 | ~1.5–1.7× slower |
| Brian2 (CPU) | 10 | 1 | 40.8 | ~1.4–1.8× slower |
| Brian2 (CPU) | 0.1 | 4 | 6.19 | ~0.9–1.3× |
| Brian2 (CPU) | 1 | 4 | 7.44 | ~0.6–1.1× (in the published band) |
| Brian2 (CPU) | 100 | 1 | 573.4 | ~1.9–2.1× slower |

The toolkit's published CSV has **no PyTorch-CPU rows** (its PyTorch runs
were CUDA), so the following are new data points — the first
PyTorch-CPU numbers for this model that we know of:

| Backend | t (s) | n | sim wall (s) | per step |
|---|---|---|---|---|
| PyTorch (CPU) | 0.1 | 1 | 27.3 | 27.3 ms |
| PyTorch (CPU) | 1 | 1 | 274.5 | 27.5 ms |
| PyTorch (CPU) | 10 | 1 | 2,751 | 27.5 ms |
| PyTorch (CPU) | 0.1 | 4 | 68.4 | 17.1 ms/trial |
| PyTorch (CPU) | 1 | 4 | 685.1 | 17.1 ms/trial |
| PyTorch (CPU) | 10 | 4 | 6,777 | 17.1 ms/trial |

The per-step cost is flat across t (27.5 ms, n1) and scales linearly in
the batch (n4 ≈ 4× n1 per step, 17.1 ms/trial) — the PyTorch CPU path is
a clean, predictable cost model: **a 100 s simulation of the full brain
on 4 desktop cores is ≈ 7.7 h at n = 1** (we deliberately did not wait
for it; the brian2cpp row above is the practical t = 100 s answer on
this tier). Spike columns read 0 in this CSV by design (spike output was
disabled to keep the run lean; the control-comparison section carries the
spike counts).

**The 8 GB ceiling (measured, not a limit we chose):** brian2's `n_run > 1`
runs launch one worker per trial, and each worker preallocates its network
plus per-step spike buffers. `t ≥ 10 s, n = 4` OOM-kills the process on an
8 GB box (t = 10 n = 4: the process was killed, no row; t = 100 n = 4: the
workers died but the harness recorded a bogus "success" row — 4.1 s,
"97.6× real-time" — which is how an OOM looks in the toolkit's CSV; treat
that row as a failure). On this box, brian2 batching is viable up to
t ≤ 1 s at n = 4.

## Method notes (why the numbers are trustworthy)

- **Validation against the reference:** the `fly` variant is the toolkit's
  own matrix through the toolkit's own model class; its spike/active
  counts match the toolkit's published sugar-experiment rows within
  ~6%, which is what you should expect from a different torch build and
  a 1 s-of-2 s stim window.
- **Sanity guard:** the driver computes the expected Poisson floor
  (21 neurons × 10,000 stim steps × p = 4,200) and flags any run far
  below it. The disconnected variant lands at 4,201–4,240 — the guard
  does its job as a floor check.
- **Post-mortem (kept in the repo on purpose):** an earlier version of
  the driver divided seconds by dt *in milliseconds* without converting,
  so the "2 s" protocol silently ran 2 ms; all three variants then
  returned identical 2–5-spike results with perfect pairwise correlation
  — a result that *looked like* "the wiring doesn't matter" and was in
  fact a units bug. The experiment now converts explicitly and fails
  loudly against the Poisson floor. The failure mode — a control
  comparison whose three arms all agree — is precisely what a broken
  control *looks like* when the control is broken in the same way, and
  it is the reason the guard exists.
- **Supervised, not set-and-forget:** each phase was checked as it
  landed; a missing dependency (which killed a backend), a 4-worker
  OOM, and the units bug above were each caught mid-campaign and the
  affected phases re-run. The raw CSV therefore contains exactly one
  known-bad row (the brian2 t = 100 n = 4 OOM artifact, flagged above);
  everything else in it is as run.

## Artifacts

Raw per-run JSON, per-neuron rate vectors (npy), manifest (seeds, circuit
hash, toolkit commit `a3db62f`, library versions) and the summary JSON:
`experiments/control-comparison/` results on the campaign host,
`/var/brainlab/runs/2026-10-04-night/control/`. The benchmark CSV and
this report: the brainlab repo.
