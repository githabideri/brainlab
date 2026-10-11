# The substrate

Which brains are available, how they are modelled, and how a circuit file
is built and provenanced. This is the "hardware" documentation of the lab.

## Open connectomes (Drosophila)

| Dataset | Animal | Coverage | Scale | Released | License | Notes |
|---------|--------|----------|-------|----------|---------|-------|
| [FlyWire FAFB](https://www.nature.com/articles/s41586-024-07558-y) (Dorkenwald et al., *Nature* 2024) | adult female | whole brain (central brain + optic lobes); **no ventral nerve cord** | 139,255 neurons / ~5×10⁷ synapses | 2024-10 (paper); data release FAFB v783 | CC BY 4.0 | The first complete fruit-fly brain connectome; the wiring most public work uses |
| [MaleCNS v1.0](https://male-cns.janelia.org/) (Berg et al., *Cell* 2026, DOI 10.1016/j.cell.2026.08.015; preprint [bioRxiv 10.1101/2025.10.09.680999](https://www.biorxiv.org/content/10.1101/2025.10.09.680999)) | adult male | complete CNS: central brain + optic lobes + ventral nerve cord, with the intact neck connective | 166,691 neurons; 46M presynaptic sites → 312M PSDs (11,691 cell types) | data v1.0: 2026-06-08; paper: 2026-09-03 | CC BY 4.0 | The first complete fly CNS (brain to nerve cord) — and the first male connectome |

Both are wiring diagrams, not recordings. What they record: which neuron
connects to which, and at each connection a **structural** measure of its
strength — the synapse count (postsynaptic densities in the EM stack). They
do **not** record measured functional synaptic strengths (conductance, release
probability, efficacy), and they do not record what the fly was doing. The
annotation releases add what class each neuron belongs to and which
neurotransmitter it is *predicted* to use — a machine-learning prediction,
not a measurement.

## The modelling standard

The de-facto way to run the FlyWire connectome — and the template for a
comparable MaleCNS simulation — is the **leaky integrate-and-fire (LIF)
model of Shiu et al., *Nature* 2024**
(<https://www.nature.com/articles/s41586-024-07763-9>): a one-compartment
spiking model of the 127,400 proofread neurons of the FlyWire volume
(FlyWire materialization v630 in the paper; the `fly-brain` toolkit runs the
same model on later releases). A run is a **simplified dynamical model
constrained by the real anatomical wiring, not a reproduction of the
biological brain** — so the division between what is measured and what is
assumed is stated once, here, because every number in this lab inherits it:

- **Measured (from the dataset):** the wiring — connectivity and synapse
  counts, which form the base of the edge weights. Structural counts, not
  measured functional strengths.
- **Assumed (model parameters):** the biophysics (membrane dynamics and
  time constants taken from earlier *D. melanogaster* modelling and
  electrophysiology, not measured on the animal); one global free
  parameter, `W_syn` — the downstream membrane-potential change per
  synapse; the excitatory/inhibitory sign, a model assumption assigned
  from the *predicted* neurotransmitter identity (a neuron is inhibitory
  if a majority of its presynaptic sites are predicted GABA- or
  glutamatergic; dopaminergic/octopaminergic/serotonergic are assigned
  excitatory; the paper assumes glutamate is inhibitory by default —
  glutamate is genuinely ambiguous in *Drosophila*, where receptor type
  decides — and sensitivity-tests that choice). No dendritic morphology,
  no receptor dynamics, no gap junctions, no learned dynamics or internal
  state. The paper's own caveat: "given the variety of assumptions the
  model relies upon, absolute firing rate predictions are unlikely to be
  accurate."
- **Validated, in scope:** in the two circuits the paper tested — feeding
  initiation and antennal grooming — the computed activation predicted the
  neurons that optogenetic, cell-type-specific and behavioural experiments
  showed to drive those behaviours, and a weight-shuffling control showed
  the prediction depends on the *specific* wiring (MN9 activated in 100%
  of runs with the real connectivity vs 1 of 100 with shuffled weights).
  That validates the model for those circuits; it is not a validation of
  whole-brain dynamics, and it is not evidence about learning, memory or
  cognition.

Everything in this lab starts from that model. Deviations (learning rules,
plasticity, extra compartments) are stated in the experiment that uses
them — they are modifications of the standard, not alternatives to it.

## What "running the brain" means here, and what it doesn't

- The network is a **cartoon with real wiring**: the measured part is the
  wiring (connectivity + synapse counts); the membrane dynamics, time
  constants, per-synapse efficacy, sign assignment and any plasticity are
  model assumptions (see the modelling standard above). One number per
  neuron, spike or rate codes, no dendrites, no ion channels, no learned
  synaptic dynamics unless an experiment adds them.
- Inputs are **injected** into named sensory populations (optogenetic-style
  Poisson stimulation of, e.g., sugar-sensing gustatory receptor neurons);
  outputs are **read out** from named motor or descending populations.
- An untrained connectome is a **stimulus-response device**: it does what
  the wiring is wired to do. It does not plan, and it does not have
  opinions. Anything that behaves like a policy on top of it is doing so
  because of (a) engineered drive mapping, (b) a learned readout head, or
  (c) added plasticity — and an honest report says which.

## Circuit files: build and provenance

A circuit file is a derived artifact: a selection (or the whole graph) of
the dataset's neurons and connections, in a format a simulator consumes.

Rules:

1. **Provenance is a first-class file.** Every circuit file is accompanied
   by a provenance record: source dataset + release, the exact selection
   rule (which populations, what quotas), input file hashes, and the tool
   + version that built it. Rebuilding the same file from the provenance
   must reproduce it bit-for-bit.
2. **Selections are declared, not discovered.** "We took the 1,536-neuron
   olfactory pathway" is a selection rule that must be written down;
   "a random 1 percent" is not.
3. **Large binaries don't live in this repo.** `circuits/` holds the index
   (what exists, where it's fetched from, its hash). Experiments fetch
   into their own working directory.
4. **Controls are circuits too.** A shuffled or disconnected variant of a
   circuit is built *from the same file, by the same tool, with the seed
   recorded* — see [evaluation.md](evaluation.md) for what a valid control
   must preserve (degree distribution, sign balance, population
   structure).
