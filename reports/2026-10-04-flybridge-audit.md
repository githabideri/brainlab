# 2026-10-04 — FlyBridge audit: a trained connectome learns to farm

## Goal

Examine a third-party experiment — **FlyBridge** (swotstudio, GitHub, MIT;
the code, data and trained brain behind the video *"I Put a Fly's Brain in
Minecraft. It Learned to Farm."*) — claim by claim: what is real in it,
what is assisted, what is untested. FlyBridge is the first public case of a
connectome-derived network being *trained* on a task (everything else in
the wave is untrained LIF plus engineered drive injection), so it sets the
bar this lab measures itself against.

## Setup

- **Circuit:** 1,536 neurons / 42,921 connections — the complete olfactory
  pathway of the FlyWire female fly (FAFB v783): 256 food-responding
  receptor neurons, 128 local neurons, 256 projection neurons, 512 Kenyon
  cells, 96 mushroom-body output neurons, 288 lateral-horn neurons. Every
  connection, its sign and its strength, is from the dataset; nothing added,
  removed or flipped.
- **Neuron model:** one activity number per neuron (rate code, not spiking);
  a decision is 4 propagation steps, ~6 ms on a consumer GPU in the author's
  runs.
- **Learnable parts:** (a) a *translator* encoding game state + a 96×54
  screenshot into the 256 receptor inputs ("the artificial nose"), (b)
  per-task *readout heads* over the output neurons, (c) a gain multiplier
  (0–2×) on every real synapse. Sign and topology are fixed.
- **What is not the fly:** the motor controller (walking, aiming, clicking —
  an explicit script), the privileged game facts (per-tile crop state,
  inventory, chest contents — the mod hands them over; the blurry image is
  not what it plays from), the stage ordering in the finale, and the
  learning rule itself (external gradient descent, not the fly's dopamine).

## Protocol

How we audited it (this is the lab's standing method for examining
outside work):

1. **Full transcript** of the video (word-timestamped ASR of the audio
   track, cross-checked against the publisher's own captions).
2. **Visual claims audit:** scene-detected key frames across the whole video
   fed to a vision LLM together with the transcript, with a fixed question
   set: what kinds of on-screen material appear and when; which quantitative
   claims are *visually backed* on screen; what is visible but never
   narrated. (ASR + scene key frames + a general vision model; the exact
   hardware is estate-internal and irrelevant to the findings.)
3. **Source inspection:** the public repository (code, the numbered test
   documents, the results JSON, the provenance files), read as the primary
   evidence — the video and the repo disagree in places, and the repo wins.
4. Each claim below is graded: **real** (in the data/code, no assistance),
   **assisted** (true but only because of an engineered scaffold), or
   **untested** (not established by any evidence we could find).

## Observations

**Visually backed by the video itself.** The on-screen instrument panel
states "1,536 neurons / 42,921 connections" throughout; the water lesson's
"TEACHER DEMO x/24" counter reaches 24 exactly as narrated; the tending
lesson's overlay reads "the teacher · 7 min 44 s · 360 decisions" against
the narration's "seven and a half minutes and 360 decisions"; the 48-plot
field states (planted/ripe/stored) track the narration. A vision model also
found details the narration omits: the in-game speed multipliers (6×, 32×,
2.4×), a small "mean latency ~5.8" label under the activity graph (the
narration says "about six milliseconds" — consistent), and one real
discrepancy: at the crafting beat the narration says "ten planks left
over" while the on-screen panel shows 6 oak planks held (12 made, 4 spent
on sticks — the "10 left" refers to post-table state; the panel is right,
the narration is loose).

**The repo is the evidence.** The video is a highlight reel; the repo's
`docs/` (numbered test ledgers with before/after scores, seeds, evidence
files) and `results/` (per-test JSON) are the actual record, and they are
honest in a way the format rarely is: failed takes are kept, "reward-practice
changes were rolled back after poorer validation" is written down, and the
pass bar is *12/12 frozen checks on seeds excluded from demonstration
collection, with every earlier lesson re-verified* after each new one.
The finale checkpoint is shipped with its exact source tree and a
manifest.

**What the wiring contributed.** The circuit is real and it carried every
one of the 387 finale decisions. But the author's own docs are explicit
that the *learning* is not the fly's: external gradient descent nudges
synapse gains; the fly learns no dopamine. And the causal question — would
a shuffled or disconnected network of the same size do as well? — is
**untested as of the last public push**. The repo builds the three variants
(fly / shuffled / disconnected) and states the bar ("matched controls are
still required"); the comparison had not run. This lab's first experiment
exists to run exactly this.

**Assisted, heavily.** The brain never touches the mouse; a script walks,
aims and clicks. It receives privileged facts the camera cannot show (crop
age, moisture, chest contents). The finale's stage ordering (wood → seeds →
crafting → tools → site → farm) is imposed by code, not chosen by the
network. None of this disqualifies the result — it defines what the result
*is*: "a fixed biological subnetwork, with learned sensory translation and
learned readout heads, makes every individual decision of a 15-lesson
farming curriculum under a scripted motor and a scripted stage plan."

## Numbers

| Item | Value | Source |
|------|-------|--------|
| Neurons / connections (circuit) | 1,536 / 42,921 (35,339 exc. / 7,582 inh.) | repo provenance; on-screen panel |
| One decision (author's GPU) | ~6 ms | narration; on-screen "mean latency ~5.8" label |
| Training per lesson | imitation from scripted teacher (16–360 examples), ~90 passes; hidden exam for model selection | repo docs |
| Lessons | 15 (plant → … → finale) | repo docs |
| Finale | fresh world, one water bucket, learning frozen: 18.5 min, 387 decisions, 0 rejected, 0 damaged — **on the 5th attempt** (attempts 1–4 each failed in a distinct, logged way) | video + repo |
| Recurring failure mode | "the last thing that worked, with total confidence, where it makes no sense" (no state between decisions; every decision is the first of its life) | repo docs |

## Conclusion

FlyBridge is a solid, unusually honest experiment, and it is *not* what the
video title suggests: it is evidence that a real biological subnetwork can
serve as a **fixed feature trunk** for learned per-task readouts, taught by
imitation with the right evaluation discipline — not that a fly brain plays
Minecraft, and not that the fly's wiring is special. The last of those is
the open question in the whole public wave, and the lab's first campaign
attacks it directly:

1. **The control comparison** — fly vs. shuffled vs. disconnected, same
   stimulus, same readout, same budget (on the bench).
2. **The performance envelope** — what decision rate these networks
   actually sustain on commodity hardware (on the bench).

What this audit does *not* establish: whether the 6 ms number holds on
other hardware (we measure it), whether the 12/12 bar generalizes beyond
Minecraft's privileged-facts environment (we'll see), or anything about
consciousness — the video's own most popular claim is the one with the
least evidence behind it, and this report deliberately does not touch it.
