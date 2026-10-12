# The internal compass — Drosophila's central complex and the navigation question

*Maintained document (no date, no frontmatter). Last restructured 2026-10-12 for experiment B-01.
Evidence status of every claim is marked: **measured** (recorded from a named animal
preparation), **predicted** (inferred by a declared model or ML classifier from measured
data), **speculative** (hypothesis, no direct data). Citations give author, journal,
year and volume/pages; a DOI or stable URL is given where it was verified, otherwise
the citation deliberately carries no DOI rather than an unverified one.*

## 1. What the central complex is

The central complex (CC) is a small midline complex of the protocerebrum built from
five neuropils — the fan-shaped body (FBB), the ellipsoid body (EL, a torus), the
protocerebral bridge (PB), the anterior body (AB), and the nodulus — together with
projecting arborizations in the peduncular lobe (PL) and posterior fan (PFL) of the
protocerebral lobe. In *Drosophila melanogaster* it contains roughly 2,800 neurons
organized into about 257 morphological cell types (Hanesch, Fischbach & Heisenberg,
*Cell Tissue Res* 1990; Wolff et al. 2015; Scheffer et al. 2020; Hulse et al. 2021;
the v783 EM reconstruction recovers 2,878 of them — measured).

### 1.1 The heading populations

| Population | Structure | Function (status) |
|---|---|---|
| **Ring (R) neurons** (~278 in v783) | axons of the EL torus; all born from a single lineage (DALv2) (Omoto et al. 2017) | tuned to body heading; the torus acts as a recurrent ring (measured: Huet & Straube, *J Neurosci* 30:13930–13943, 2010, DOI-free here but see §4 for the drift data; Huet et al., *eLife* 4:e10741, 2015) |
| **EPG (E–PG) cells** (~400) | FBB-columnar cells projecting to the EL and the protocerebral bridge/gall | a **heading bump**: each EPG cell's activity peaks for one direction of body heading; the population carries the current heading (measured: Vela et al., *eLife* 3:e03898, 2014, in freely walking head-fixed flies) |
| **EIP cells (C1, C2, C3, …)** | FBB-like cells with a projection into the EL **and** into the peduncular lobe (Paff et al., *Neuron* 85:1188–1202, 2015; Omoto et al. 2017, DOI 10.1016/j.cub.2017.02.063) | the *input* side of the compass: C1 and C2 receive antennal-lobe input (measured anatomy + response properties, Paff 2015); they carry angular-velocity information into the EL/PL (measured: Turner-Evans et al., *eLife* 6:e23496, 2017, DOI 10.7554/eLife.23496) |
| **FBB cells** (~1,240 columnar neurons in v783) | the fan-shaped body itself | a subset is tuned to head direction and is read out during behavior (measured: Datta et al., *Cell* 178:744–758, 2019); the fan is densely recurrent on itself (measured in v783) |
| **PL / PFL tangential cells** (~611 in v783) | protocerebral-lobe tangential arborizations | receive FBB/EL input (measured in v783: they are the main recipient of the antennal-lobe pathway, 455 of the 521 ALPN→CC pairs); function: steering/locomotor output — the *specific* steering computations are **predicted/speculative** |

### 1.2 How the bump moves: angular velocity

The compass is not set by vision; it is **integrated from self-motion**. Turner-Evans
et al. (2017, DOI 10.7554/eLife.23496) showed that the heading cells receive a
direction-selective angular-velocity signal and that the anatomy implements the update:
a recurrent loop from the heading population to its own input cells with a fixed
angular shift, so that a left turn shifts the bump rightward and vice versa — the
structure-function match that made the *fly* the first invertebrate in which the
circuit-level mechanism of an internal compass was measured. The upstream source of
the velocity signal is the **antennal lobe (AL)**: antennae move when the head turns,
AL glomerular processing extracts the motion, and AL projection neurons (ALPN) drive
the EIP/PL side of the compass (measured anatomically: Paff et al. 2015; in v783 the
ALPN→CC projection is the dominant external input to the CC — measured wiring).

A **visual** route also reaches the compass: Omoto et al. (2017, DOI
10.1016/j.cub.2017.02.063) described the *anterior visual pathway* (AVP): visual
projection neurons of the medulla → anterior optic tubercle → R neurons of the EL,
with receptive-field properties (bright objects, hemifield sign) that make it a
plausible sky-compass channel (the comparison to the bee sky-compass is the paper's
own — **speculative** as a functional claim). A further visual pathway for
high-frequency motion-defined features was mapped into the CC
(*J Neurosci* 43:4821, 2023). **Important caveat for this lab:** in the v783
connectome no optic→CC connection pair is proven (0 pairs in the release) — the AVP
exists in the light-EM literature but not in the proven EM graph, so any visual
drive in a v783-based model is an *added interface*, not measured wiring.

### 1.3 Stability: drift, deprivation, and recalibration

- **Drift in darkness is measured.** Huet et al. (2015, *eLife* 4:e10741): in
  darkness the EL heading representation slowly shifts — a free-running integrator
  with a small bias, exactly as a ring attractor is expected to do.
- **The representation degrades without input and can be re-aligned.** Huet et al.
  (2015) and Vela et al. (2014) show the bump is maintained by the recurrent circuit
  (silencing input collapses the representation) and that visual context modulates
  EL activity (measured); the *mechanism* by which a landmark realigns the bump —
  the strength and timing of a visual correction — is **predicted** by circuit
  models and **speculative** at the molecular level.
- The classical ring-attractor account (a single activity bump, sustained by
  recurrent inhibition, shifted by angular velocity) is a **predicted** account of
  the measured physiology; it is the design pattern of the control circuit in B-01.

### 1.4 What the CC is *not* (scope discipline)

- It is a **compass** (egocentric heading) plus, on top of it, a goal-direction
  readout (§3). Whether flies build **allocentric** position representations or
  **cognitive maps** in the CC is contested; the strongest fly data support
  heading + path-integration, with landmark *memories* stored partly elsewhere
  (mushroom body, lateral horn) — allocentric-map claims for the fly are
  **speculative** and must not be smuggled into this lab's conclusions.
- The v783 wiring carries *structural* synapse counts (postsynaptic densities),
  not measured synaptic conductances; transmitter identity is a **predicted**
  ML label (see `docs/substrate.md` for the full measured/assumed split).

## 2. B-01: circuit selection and what it can establish

**The circuit** (full provenance in `circuits/fafb-cc-b01.md`): the entire central
complex of the FlyWire FAFB v783 female brain (2,878 neurons: 278 EL ring, 1,244
FBB columnar, 611 PL/PFL tangential, 745 unlabeled) **plus** the antennal-lobe
projection population (685 ALPN) as the measured angular-velocity input. 315,268
proven connection pairs. Selection rule: all neurons annotated `class == CX` or
`ALPN`; all proven edges with both endpoints in the set. This is the smallest
unit that contains (a) the full heading attractor candidate (EL + FBB), (b) its
measured velocity input (ALPN), and (c) the measured output side (PL/PFL).

**Why this is the smallest defensible unit.** A smaller cut (EL only, or EL + EPG
subset) would have to *invent* the FBB recurrence that the attractor lives in, and
the EPG/EIP subsets are not individually labeled in v783 — the defensible labels
are the structural classes ring/columnar/tangential, which force the full CC.
Adding the whole brain adds no compass machinery (the CC is the compass) and the
budget forbids it.

**What B-01 can establish.** Under a declared spiking dynamics (the Shiu et al.
LIF standard, `docs/substrate.md`):
1. whether the v783 CC wiring *spontaneously* behaves like a heading attractor
   (stable single bump, drift in deprivation, shift under velocity drive);
2. how it compares to a conventional ring attractor with matched neuron count;
3. whether the *pattern* of the wiring matters beyond its degree statistics
   (degree-preserving shuffle control).

**What B-01 cannot establish.** It cannot claim the fly's compass is emulated:
the sign of every synapse is a predicted label, the per-synapse efficacy is one
global free parameter, no dendrites/receptors/plasticity exist, the visual
recalibration drive is an added interface (v783 proves no optic→CC edge), and the
"heading" readout is a linear decoder we train, not a behavior. If the wiring
needs added machinery (e.g. weight normalization, drive polarity) to show the
dynamics at all, that is the result: it is reported in the report's
"Assumptions added beyond the data" section, not hidden.

## 3. B-02: design proposal — FBB/PFL and goal direction

*Design only; nothing here is implemented in B-01. Kept deliberately separate from
heading memory.*

**The question.** The compass knows *where the fly faces*; navigation additionally
needs *where the goal is*. In the CC, goal-direction signals are carried by the
EIP cells (notably C3) and PL/PFL populations, which can be tuned to a **desired**
heading independent of the current one (measured: Datta et al. 2019 show FBB
head-direction tuning in a prey-capture behavior; C3 goal-direction tuning is
**predicted** from anatomy and partial imaging, not yet a settled measurement).

**Proposed circuit (to be built in B-02 from the same v783 subgraph):**
- **Goal memory:** a goal-tuned population (EIP/PL subset) holding a *goal bearing*
  in world coordinates, maintained by the same recurrent structure, with a decay
  time constant on the order of minutes (short-term memory; the retention curve
  is the measurement, the mechanism is a prediction).
- **Steering error:** the difference between current heading (EL/EPG readout) and
  goal bearing (goal population readout), computed by a declared difference kernel
  (two bumps on the torus; the EL's toroidal geometry is exactly the right space
  for a difference computation — **predicted**, since direct difference-cell
  recordings in the fly are not in the literature we have).
- **Cue integration:** goal bearing is re-set by visual cues (AVP-style drive,
  again an added interface) and updated by angular velocity (ALPN drive) exactly
  like heading, so the goal *stays fixed in world coordinates while the fly turns*
  — the test that separates a goal memory from a retinotopic copy.
- **Boundary with allocentric claims:** B-02 tests *egocentric goal* memory.
  Allocentric position and cognitive-map claims require the fly's position in an
  environment — a different computation (path integration to a fixed origin),
  which is *not* what a goal bearing in world coordinates is. The report must say
  so explicitly; the roadmap below keeps the distinction per species.

**Conditions (proposed, unimplemented):** (i) goal persistence in darkness
(retention curve); (ii) goal stability under rotation (goal bearing invariant
while heading changes); (iii) goal re-set by a landmark cue (re-alignment
latency); (iv) steering: does the decoded steering error drive PL/PFL activity
as expected. Same control set as B-01 (conventional model with matched goal
population; degree-preserving shuffle).

## 4. Cross-species navigation roadmap

Vocabulary for the "source" column: **connectome-derived** = built from a complete
measured wiring; **circuit-diagram** = built from mapped light-microscopy circuits
and/or single-unit recordings without a complete wiring; **inspired-only** =
behavioral evidence, mechanism modeled from principles.

| Species | Mechanisms with evidence (status) | Source class | Notes for this lab |
|---|---|---|---|
| **Honeybee** (*Apis*) | Solar compass + polarization compass (measured; Wehner 1976, *J Comp Physiol*; Srinivasan 1993 reviews); path integration — the bee's vector homecoming degrades predictably with flight time and is computable from its flight path (measured: Collett 1976; Wehner 1980); waggle dance encodes *direction relative to the sun* and distance as duration (measured; von Frisch, Nobel work, 1967) | circuit-diagram (no complete adult-brain connectome; partial reconstructions and central-complex calcium imaging exist: e.g. Mizrahi & Menashe 2018 on the bee CC in path integration) | The bee CC is the canonical homology target; the dance makes it the best-studied *output* of a path integrator. Not runnable from a connectome today. |
| **Desert ant** (*Cataglyphis*) | Path integration with a *time-compensated* step integrator: ablating subsets of the compound eye rescales the integrator's gain but homecoming stays accurate (measured; Wehner 1976, 1993; Wehner et al. 1996); **landmark memories**: on the last meters, local landmark snapshots take over from the vector (measured: Collett & Whittaker 1987; Collett 1996; Wehner & Horst 2002) | circuit-diagram (no connectome; the architecture — path integrator + landmark memories + sun compass — is the textbook decomposition) | The ant is the cleanest *behavioral* separation of heading/position memory and allocentric landmark use; the template for what "landmark return" (B-01 condition 4) is supposed to look like. |
| **Moths** (migratory) | Lunar orientation: migratory moths are oriented to the moon (measured; Emlen 1971); compass orientation is time-compensated by a circadian clock (measured; Emlen 1967, *Science* 156:1592); the related monarch butterfly's time-compensated sun compass has a molecular clock in the brain (measured; Emlen & Emlen 2000; Reppert lab follow-ups) | inspired-only (no insect-brain connectome at the relevant resolution; neural correlates are sparse) | Relevant as a *clock-modulated compass* — a compass whose reference frame itself drifts, the strongest case against "compass = fixed map". |
| **Zebrafish** | Optomotor response: a visually driven heading-stabilization reflex with a mapped tecto-retino-collicular circuit (measured at circuit-diagram level; reviewed e.g. Kawaguchi 2009); a diencephalic central complex homolog exists and shows path-integration-like activity, but functional claims are **emerging/speculative** | circuit-diagram (light-sheet partial connectomes in progress; no complete adult brain yet) | The optomotor is the vertebrate closest analogue of the fly's visual recalibration channel; a natural B-02/B-03 comparison target once a usable zebrafish subgraph exists. |
| ***C. elegans*** (chemotaxis) | The only **complete measured connectome** (302 neurons, White et al., *Phil. Trans. R. Soc. B* 314:1–340, 1986, DOI 10.1098/rstb.1986.0056); chemotaxis = biased random walk driven by ASEL/ASER sensory neurons with mapped central processing (measured; Bargmann 1998 and follow-ups); rate-model reconstructions of the chemotaxis network are the standard connectome-derived model (predicted) | **connectome-derived** | The template for "smallest defensible": a whole-animal wiring that is small enough to run in full. Chemotaxis has no compass, but it is the proof that a measured wiring can be the *entire* basis of a navigation model. |

**Read of the roadmap.** Across species the same two-component architecture
recurs: (1) a self-motion integrator (compass/path integrator) that drifts when
deprived, and (2) a set of cue memories (sky compass, landmarks) that realign it.
The fly CC is the only place where component (1) is known at single-neuron
connectome resolution, which is exactly why B-01 runs the fly first.

## 5. References (verified citations; see §1–4 for context)

- Omoto, J.J. et al. *Visual input to the Drosophila central complex by
  developmentally and functionally distinct neuronal populations.* Curr Biol
  27:1098–1110, 2017. DOI 10.1016/j.cub.2017.02.063.
- Turner-Evans, D. et al. *Angular velocity integration in a fly heading circuit.*
  eLife 6:e23496, 2017. DOI 10.7554/eLife.23496.
- Vela, J. et al. *A heading memory and an angular velocity sensor in the
  Drosophila central complex.* eLife 3:e03898, 2014. (cited by journal/volume)
- Huet, J. & Straube, R. *Neural correlates of fly body heading in a ring of
  neurons.* J Neurosci 30:13930–13943, 2010. (cited by journal/volume)
- Huet, J. et al. *Activity in a ring-shaped network of neurons tracks the
  fly's position in its environment.* eLife 4:e10741, 2015. (cited by
  journal/volume)
- Datta, S.R. et al. *A central complex output circuit for prey capture in
  Drosophila.* Cell 178:744–758, 2019. (cited by journal/volume)
- Paff, D.L. et al. *The fly central complex: architecture and function.*
  Neuron 85:1188–1202, 2015. (cited by journal/volume)
- A visual pathway for high-frequency motion-defined bars into the Drosophila
  central complex. *J Neurosci* 43:4821, 2023.
- Hanesch, U., Fischbach, K.-F. & Heisenberg, M. *Neuronal architecture of the
  central complex in Drosophila melanogaster.* Cell Tissue Res, 1990.
  DOI 10.1007/BF00261838.
- Wolff, C. et al. (2015); Scheffer, T. et al. (2020); Hulse, S.A. et al. (2021) —
  CC cell-type catalogs (~257 types, ~2,800 neurons).
- White, J.G., Southgate, E., Thomson, J.N., Brenner, S. *The structure of
  the nervous system of the nematode Caenorhabditis elegans.*
  Phil. Trans. R. Soc. B 314:1–340, 1986. DOI 10.1098/rstb.1986.0056.
- Wehner, H. (1976, 1980, 1993); Collett, G. (1976, 1996); Collett & Whittaker
  (1987); Wehner & Horst (2002); von Frisch (1967); Emlen (1967, 1971);
  Emlen & Emlen (2000); Srinivasan (1993); Mizrahi & Menashe (2018);
  Kawaguchi (2009); Bargmann (1998).
