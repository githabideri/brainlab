# The substrate

Which brains are available, how they are modelled, and how a circuit file
is built and provenanced. This is the "hardware" documentation of the lab.

## Open connectomes (Drosophila)

| Dataset | Animal | Scale | Released | License | Notes |
|---------|--------|-------|----------|---------|-------|
| [FlyWire](https://www.nature.com/articles/s41586-024-07558-y) (Dorkenwald et al., *Nature* 2024) | adult female, brain + ventral nerve cord | 139,255 neurons / ~50M synapses | 2024-10 | CC BY 4.0 | The first complete fruit-fly connectome; the wiring most public work uses |
| [MaleCNS v1.0](https://www.janelia.org/project-team/flyem/male-cns-connectome) (Berg et al., *Cell* 2026) | adult male, brain + optic lobes + ventral nerve cord | ~166k neurons / ~125M synapses | 2026-09-03 | open (Janelia/Google/Cambridge) | Second complete fly CNS; the one that started the public simulation wave |

Both are wiring diagrams, not recordings: they say which neuron connects to
which and with what strength, and (via the annotation releases) what class
each neuron belongs to and which neurotransmitter it is predicted to use.
They do not say what the fly was doing.

## The modelling standard

The de-facto way to run either dataset is the **leaky integrate-and-fire
(LIF) model of Shiu et al., *Nature* 2024**
(<https://www.nature.com/articles/s41586-024-07763-9>):

- each neuron is one compartment that leaks and fires a spike on threshold;
- synaptic weights come from the connectome's connection strengths, with
  sign from the **predicted neurotransmitter identity** (excitatory vs.
  inhibitory);
- the model has a single global free parameter (the weight scale `W_syn`);
- it is validated: computed activation of taste and grooming circuits
  predicted the neurons that real optogenetic experiments showed to drive
  feeding and grooming — i.e. *connectivity plus transmitter sign is enough
  to make testable sensorimotor predictions*.

Everything in this lab starts from that model. Deviations (learning rules,
plasticity, extra compartments) are stated in the experiment that uses
them — they are modifications of the standard, not alternatives to it.

## What "running the brain" means here, and what it doesn't

- The network is a **cartoon with real wiring**: one number per neuron,
  spike or rate codes, no dendrites, no ion channels, no learned synaptic
  dynamics unless an experiment adds them.
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
