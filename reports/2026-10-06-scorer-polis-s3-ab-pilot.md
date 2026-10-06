Date: 2026-10-06

Role label: the Polis decision loop is the real-world testbed for the scorer
tier — a 1.4 MB frozen-connectome second opinion next to a 2B decider and a
27B LLM judge, in a live game world.

# The Polis fly-scorer A/B pilot (stage S3): a structural null, and the
# tier's correct position

## What was tested

Stages S1 and S2 of the scorer project (this repo: the engine report and the
`reports/2026-10-05-scorer-polis-s2-screen.md` screen) produced a
1,536-node frozen tanh circuit that scores Polis mission actions at
**1.16 ms/decision on 4 CPU threads** — 92.9% on a 141-row held-out set,
**zero damaging choices**, 100% on the abstain slice; the shuffled-wiring
control was null (92.2%), so on this corpus the gain is in the encoder, not
the wiring.

Stage S3 ran the scorer **live in the companion estate's decision loop**, as
the integration point designed with the estate owner: a *pre-veto
re-ranker at the small-model (decider) tier*. Battery: 10 matched episodes
in one live world — 5 scorer-**on** / 5 **off**, order alternated per slot,
3 harvest + 2 mine per arm, 8 steps each. Identical for both arms: world,
base, the Decider-2B ft2 (the S2 baseline), the 27B judge, the prompt
service. The only difference: the on-arm re-ranks the candidate action list
softly (no hard override — `scorer_overrides = 0` in every on episode, and
the abstain flag never fired live, matching the offline result). The full
per-episode data (per-row state / oracle / scorer / decider / judge /
executed action + per-component latencies) is in the private companion
repo under the matching report date; this document reports the aggregate.

## Result 1 — null on every measured outcome

| mission | arm | game success | decision quality (executed = oracle) |
|---|---|---|---|
| harvest | ON  | 3/3 (100%) | 3/6 (50%) |
| harvest | OFF | 3/3 (100%) | 3/6 (50%) |
| mine    | ON  | 0/2 (0%)   | 12/16 (75%) |
| mine    | OFF | 0/2 (0%)   | 12/16 (75%) |

The scorer changed nothing it was measured on. N=5/arm cannot detect a
game-success delta — but the null below is not merely under-powered; it is
*structural*.

## Result 2 — the scorer is 91% accurate and is bypassed by a 53% judge

Per-step oracle agreement on the **on-arm**, by component:

| component | oracle match |
|---|---|
| **scorer** (22 non-abstained steps) | **20/22 (91%)** |
| decider (2B ft2) | 20/22 (91%) |
| **27B judge** | **8/15 (53%)** — the weak link |

Off-arm for reference: decider 19/21 (90%), judge 11/18 (61%). Live scorer
accuracy (91%) tracks its offline held-out accuracy (92.9%) — no visible
corpus-to-live distribution shift in this sample.

Head-to-head on the on-arm: in **7 steps the judge's (executed) pick was
wrong, and in 5 of those 7 the scorer already held the correct action** —
ranked #1, 1.16 ms in the bench — and it never reached the executed move.

**The mechanism.** The cascade is reflex → decider → judge. The soft scorer
re-ranks the *decider's* candidate list, but in escalated steps
(`path = reflex→judge`) it is the **judge's** pick that executes, and the
judge sits *downstream of the scorer* — the scorer never sees the judge's
output. A 91%-accurate gate is structurally unable to stop a 53%-accurate
overrider from overwriting a 91%-accurate decider.

Worked example (on-arm mine episode, step 1): travel phase, bot 8 blocks
from the mine marker, no line of sight. Reflex proposes the injected
`goto_base`; the decider picks `goto_target` (= oracle); the scorer ranks
`goto_target` #1 (margin 4.6, far above any rival); the judge escalates to
`mine_target` (≠ oracle) — and that is what executes (and fails: no line of
sight).

This answers the research doc's open question #3 (*"inside the judge
escalation, or as a pre-veto next to the small model?"*): the hook must be
a **pre-veto on the judge**, not a re-rank of the decider's list. The
scorer's natural job is exactly the cheap second opinion the 27B judge
doesn't have — except it has to sit where it can actually veto.

The **zero-damaging guarantee held live**: across all 80 logged rows (10
episodes × 8 steps) in both arms, zero damaging choices by the scorer and
zero by any executed action.

The mine arm is a separate, honest null: `exec_success 1/8` per episode,
failing on "no line of sight to target" — an **execution** problem (pathing
over 1-block-step terrain), not a decision one (75% oracle match). No
decision-layer intervention fixes that; the estate tracks it as its own
pathing work item. Mine stays a control; harvest is the clean A/B mission.

## Caveats (the honest ones)

- N=10, one world, one decider model. The game-success null is
  under-powered; the mechanism finding is not — it is visible in every
  on-arm row, not a sample artifact.
- Live on-box scorer latency was **not instrumented in this run** (rows
  carry decider/judge/prompt-service latencies but no scorer ms). The S1
  bench (1.16 ms, 4-core CPU testbed) stands; a one-line timing field in
  the hook is part of the S4 spec.
- The on-arm judge was *worse* than the off-arm judge (53% vs 61%) —
  different escalated steps per arm, not a treatment effect of the scorer
  (the scorer never touches the judge's input).

## S4 — the specified next experiment

Hook the scorer as a **pre-judge veto**: when the cascade is about to
escalate to the judge and the judge's candidate disagrees with the scorer's
confident top pick, veto the judge's pick and fall back to the scorer/
decider choice (or escalate with the disagreement flagged). The margin
threshold never fired offline or live, so the on/off flag is the live
switch; margin travels as metadata.

Re-run the same 10-episode battery. **Pre-registered prediction:** the 7
wrong judge steps shrink toward the 2 the scorer also missed; the 5 steps
where the scorer held the right pick flip to correct executions. That is
the measurable signal — a *decision-quality* delta, not a game-success
delta, at this N. Harvest completion must stay 3/3 (no regression);
damaging must stay 0. A full-N battery (the 96-row val-world set,
≥50 episodes) only after the pilot shows the signal.

## What this says about the connectome

Both honest negatives in this project — the S2 shuffled-wiring null and the
S3 decider-tier null — point the same way. On this tanh-rate, low-
dimensional corpus, what the tier contributes to a real decision loop is
not the wiring: it is a frozen, calibrated, **zero-damaging, 1 ms** second
opinion, plus the measurement that tells you where it must sit. The
wiring question stays open to the spiking regime, where the sibling
campaign found the same wiring driving 3.7× the shuffled circuit's spiking
activity (this repo's control-comparison report).

Verification status: the battery itself (harness runs, per-row logs,
block-scan) is locally verified on the estate; the cascade-bypass behavior
is live-verified (observed in every on-arm episode's rows).

## References

- S1: `reports/2026-10-04-scanner-latency.md` (latency bench)
- S2: `reports/2026-10-05-scorer-polis-s2-screen.md` (the offline screen)
- Control contrast: the `campaigns/control-comparison/` report (wiring vs
  shuffled in the spiking regime)
- Live data: the private companion repo, `reports/` 2026-10-06 A/B pilot
  report + the 10 per-episode JSONs and the aggregate.
