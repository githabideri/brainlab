# Datasets — multi-organism nervous-system resources

Catalog of nervous-system datasets across phyla, aimed at the project's target
computations: **memory, navigation, learning, and sensorimotor control**. It is
the multi-organism complement to [substrate.md](substrate.md), which owns the
Drosophila dataset facts (versions, sizes, checksums, access mechanics) and is
referenced here, not duplicated.

**What this file is and is not.** It catalogs *resources* — what exists, at
what scale, under which license, with which tools, and how well each maps onto
the target computations. It is not a methods document and not a claim that
any of these datasets were analyzed in this repo. Every quantitative claim
carries a primary source; claims that could not be confirmed against a
fetchable primary source are marked *(unverified)*.

## How to read this file

**Status categories.** Each dataset carries one primary label:

| Category | Meaning |
|---|---|
| `structural` | synapse-level (or finer) wiring diagram of some part of a nervous system |
| `physiological` | activity recordings (calcium imaging, electrophysiology) on an anatomical substrate |
| `functional` | inferred connectivity (tracing maps, co-activation), no synapse-level anatomy |
| `molecular` | spatial molecular/cell-type atlases — *not* wiring diagrams |
| `behavioral` | standardized behavioral datasets or benchmarks, no wiring |
| `simulation` | runnable, anatomy-informed models (with or without a public graph) |
| `project` | announced or under construction; no stable public release yet |

**"Complete" is a strong word and used sparingly.** It means: the *entire*
nervous system of the organism at that stage/sex, per the authors' own
reconstruction. Most large-brain datasets are region-limited or still being
proofread by a community; those are labeled as such.

**Verification status.** Sources were consulted on 2026-10-12 (web + NCBI
eutils + official data portals; list at the end). Where a journal page was
paywalled, the PubMed/PMC abstract was used and the paper cited by DOI.

**Scale rule of thumb for this project's lab box** (4-core CPU, 12 GB RAM,
~10 GB free disk — see the shortlist at the end):

- **Graph analytics** (structure, motifs, path queries, small-world metrics):
  comfortable up to ~10⁴ neurons and ~10⁷ synapse edges (Drosophila FAFB is
  at the upper edge; MICrONS cubic-mm and Fish1 need subgraph extraction).
- **Whole-graph spiking simulation**: realistically only below ~10³ neurons
  with simplified synapses. C. elegans (302/385) and Ciona (177) fit;
  Drosophila subgraphs (central complex, mushroom bodies) fit.
- **Raw EM voxels**: do not fit (GB to PB); only programmatic sub-volume or
  graph-level access is relevant here.

## Summary table

| Organism | Dataset (year) | Stage / sex | Coverage | Scale (neurons / synapses) | Status | License / access | Simulation maturity | Best-fit computations |
|---|---|---|---|---|---|---|---|---|
| *C. elegans* | Worm wiring (1998) | adult hermaphrodite | whole animal | 302 / 5,590 | `structural`, complete | free download (WormWiring), paper public | **high** (NeuroML, openWorm) | learning, sensorimotor, locomotion |
| *C. elegans* | Cook et al. update (2019) | adult, both sexes | whole animal, sensory input → end organ | 302 / 385 (4,887 + 1,447 herm edges) | `structural`, complete | open access (PMC6889226) | **high** | learning, sexual behavior, sensorimotor |
| *C. elegans* | Developmental series (2020) | L1 → adult hermaphrodite | nerve ring + ventral ganglion | 162 → 180 (brain) of 218/300 | `structural`, in progress (preprint) | preprint (bioRxiv) | medium | growth, maturation of learning circuits |
| *D. melanogaster* | FAFB (2024) | adult female | whole brain | 139,255 / ~5×10⁷ | `structural`, near-complete | CC-BY (FlyWire) | medium (subgraphs only) | memory, navigation |
| *D. melanogaster* | MaleCNS (2026) | adult male | whole brain | 166,691 / 312M PSDs | `structural`, near-complete | via FlyWire | low–medium | male-specific circuits |
| *D. melanogaster* | Fly hemibrain (2021) | adult, hemislice | central brain, one hemisphere | ~25,000 / ~10⁶ | `structural`, near-complete | CC-BY (Janelia FlyEM) | medium | memory, navigation |
| *D. melanogaster* | First-instar larva (2023) | 1st instar | whole larval brain + cord | 3,016 / 548,000 | `structural`, complete for larva | Janelia FlyEM | medium | learning, value computation |
| *D. melanogaster* | Functional companion (2024) | adult female | central-complex region, 2P + EM | subset of cells (see paper) | `physiological` + `structural` | Janelia / paper | medium | memory (MB), sensorimotor |
| *Zebrafish* | Fish1 (2025) | 7 dpf larva | brain + anterior spinal cord | >180,000 somas / 30M synapses | `structural`, in progress, open platform | open access (GCS, CAVE) | low | sensory, sensorimotor, comparative |
| *Zebrafish* | Svara et al. (2022) | 5 dpf larva | pretectum / visual motion pathway | 208 / — | `structural`, region complete; `physiological` co-data (2P) | paper | low | sensory (motion) |
| *Zebrafish* | Wanner (2016), Hildebrand (2017) | 5 dpf | optic tectum regions | region-limited | `structural`, region | papers | low | sensory |
| *Mouse* | MICrONS Phase 1 (2015) | P36 male | 250×140×90 µm, L2/3 V1 | 364 fully proofread / 3.2M putative | `structural`, region | public (CAVE "pinky_sandbox", neuroglancer) | medium (local models) | cortical processing, sensory |
| *Mouse* | MICrONS cubic mm (2025) | adult | 1.4×0.87×0.84 mm³ | ~120,000 / 523M | `structural` + `physiological` (75K cells 2P), region, in progress | public (Allen portal) | low | sensory/sensorimotor at scale |
| *Mouse* | BICCN spatial atlas (2023) | postnatal stages | whole brain (molecular) | 1.09M cells / 230 types | `molecular` — **not** a wiring diagram | public (brain-map.org) | none | cell-type reference |
| *Mouse* | Allen Connectivity Atlas (2010) | adult | whole brain, regional | region-level (viral + 2P tomography) | `functional`, whole brain | public (allenbrain.org) | low | whole-brain context |
| *C. intestinalis* | Tadpole larva CNS (2016) | tadpole | whole CNS | 177 / 6,618 (+ 1,206 gap junctions) | `structural`, complete | paper + supplements (graph access unverified) | **none** (greenfield) | comparative (chordate baseline) |
| *P. dumerilii* | Whole-body larva (2025) | larva (marine annelid) | whole body | >9,000 cells; 202 neuronal types | `structural`, whole body | paper (data access unverified) | none | intersegmental control, evolution |
| *B. impatiens* | Central complex projectome (2021) | adult bumblebee | central complex (axonal projections) | — | `functional`/projection map, not synapse-level | paper | low | navigation (reference) |
| *A. mellifera* | — (no public connectome) | adult honeybee | — | >1M neurons (est.) | `project` / gap | — | none | navigation (watch) |
| *O. biroi* (ant) | Reference brain (2025) | adult | brain nomenclature atlas | — | anatomical reference (not wiring) | paper | none | behavioral reference |
| Lepidoptera (moths) | — (none found) | — | — | — | gap | — | none | — |
| Zebra finch | HVC (2017); Area X (2026) | adult | HVC; Area X (song system) | region-level | `structural`, region | papers / lab releases | low | sensorimotor sequence generation |
| Human | 1 mm³ temporal cortex (2024) | adult | 1 mm³ | ~57,000 cells / ~150M synapses | `structural`, region, in progress | restricted (paper describes access) | none | scale reference only |
| *O. vulgaris* (octopus) | Vertical lobe (2023) | adult | vertical lobe (memory network) | region-level | `structural`, region | paper (eLife 12:e84257) | low | memory (comparative) |

---

## *Caenorhabditis elegans*

The smallest complete nervous system in the connectome literature: every
neuron, synapse, and gap junction of the adult has been traced by hand and
machine over three decades. It is the only organism where a **whole-brain,
whole-animal simulation** (nervous system *plus* soft body) already runs on
ordinary hardware.

### Adult hermaphrodite — "the 1998 connectome" (White et al. 1986)

1. **Organism / stage / sex.** *C. elegans* N2, adult hermaphrodite.
2. **Anatomical coverage.** Whole animal nervous system: head, nerve ring,
   ventral nerve cord, tail — the full 3D EM reconstruction basis of the
   series that defined the field (White, Southgate, Brenner, etc., *Phil.
   Trans. R. Soc. B* 314:1–340, doi:10.1098/rstb.1986.0051).
3. **Scale / completeness.** 302 neurons; 5,590 chemical synapses (original
   counting basis); plus gap junctions and motor-neuron → muscle connections.
   Complete for the stage.
4. **What else ships.** Neuron class identities, cell-position maps, synapse
   locations along neurites; the 2019 update (below) adds end organs and
   sex comparisons.
5. **Format / version / provenance.** Free CSV/XLSX downloads per neuron
   and synapse from WormWiring (wormwiring.org); WormAtlas "MoW"
   (wormatlas.org) builds the 3D skeleton and volumetric maps
   (build 0.92, derived from White 1986 + Chen et al. 2006 + Varshney et
   al. 2011).
6. **License / cost.** Paper data public; downloads free; MB-scale — trivial
   for any lab box.
7. **Simulation maturity.** **Highest in the catalog.** NeuroML representations
   of the connectome, the openWorm soft-body "WormSim" simulator, DevoWorm
   (development), and the Geppetto platform (openworm.org). Whole-brain +
   whole-body simulations have run on desktop CPUs for a decade.
8. **Task fit.** Best small-brain substrate for **learning** (habituation is
   the textbook assay), **sensorimotor** (the 2019 matrices literally span
   sensory input to end-organ output), and **locomotion/foraging** as a
   navigation analog (open-loop path following, not map-based navigation).
9. **Confidence / limitations.** Very high (complete, repeatedly re-verified
   since 1986). Limitations: 2D serial-section provenance, single-sex
   original, no intrinsic dynamics data (no calcium traces) — simulations
   use literature-derived parameters, not fitted to activity.

### Adult, both sexes — Cook et al. 2019

1. **Organism / stage / sex.** Adult hermaphrodite and adult male (N2),
   whole animal.
2. **Anatomical coverage.** From sensory input to end-organ output, *across
   the entire animal* — the first whole-animal quantitative connectivity
   matrices (Cook et al., *Nature* 571:63–71, 2019,
   doi:10.1038/s41586-019-1352-7; open access, PMC6889226).
3. **Scale / completeness.** Graphs: hermaphrodite 460 nodes (302 neurons,
   132 muscles, 26 non-muscle end organs) with 4,887 directed chemical
   edges + 1,447 gap junctions; male 579 nodes (385 neurons, 155 muscles,
   39 end organs). Note the edge count is a different counting basis than
   the 5,590 synapses of 1998 (connections vs. synapse sites).
4. **What else ships.** Sex-differential connectivity: sex-shared neurons
   that are dimorphic in structure and connectivity; where sexual and
   non-sexual pathways converge; strength differences in shared central
   pathways.
5. **Format / version / provenance.** Paper + supplementary data (open
   access); the same graphs flow through WormWiring/WormAtlas and WormBase.
6. **License / cost.** Open access; MB-scale.
7. **Simulation maturity.** High — same tooling as the 1998 connectome
   (NeuroML/openWorm), now with whole-animal input–output coverage.
8. **Task fit.** **Sensorimotor** (full loop, both sexes), **learning**
   (sex-specific learning reported in the literature), sexual-behavior
   circuits.
9. **Confidence / limitations.** High. The reconstruction still rests on
   serial sections; some gaps were filled by extrapolation across
   repetitive regions (per the paper).

### Developmental series (bioRxiv 2020)

1. **Organism / stage / sex.** Eight isogenic hermaphrodite (N2) brains
   across post-embryonic stages, L1 → adult.
2. **Anatomical coverage.** The brain (nerve ring + ventral ganglion) only —
   not the full body.
3. **Scale / completeness.** 162 of 218 neurons at birth (L1), growing to
   180 of 300 in adulthood; connectivity and morphology per stage
   (bioRxiv 10.1101/2020.04.30.066209, still a preprint as of this writing —
   publication status *unverified*).
4. **What else ships.** Stage-by-stage network structure; the basis for
   studying how learning/memory circuits *develop*, not just function.
5. **Format / access.** Preprint + linked data (access *unverified*).
6. **License / cost.** Preprint terms.
7. **Simulation maturity.** Medium — mostly used for structural analysis;
   DevoWorm is the closest tooling for the developmental side.
8. **Task fit.** Maturation of memory circuits; developmental constraints on
   sensorimotor circuits.
9. **Confidence / limitations.** Medium — preprint; brain-only; isogenic
   series (no individual variation).

**C. elegans verdict.** The only catalog entry where you can download a
complete nervous system *and* a working whole-organism simulation today, at
MB cost. First target for any "can a small brain learn/navigate?" question.

---

## *Drosophila melanogaster*

**This repo's substrate.** Versions, sizes, checksums, access mechanics, and
the FAFB v783 / MaleCNS v1.0 facts live in [substrate.md](substrate.md) —
they are deliberately not restated here. This section gives the
cross-organism context and the other Drosophila releases.

### FAFB — adult female (Dorkenwald et al. 2024)

1. **Organism / stage / sex.** Adult female, whole brain (both lobes, all
   neuropils and unipolar neurons).
2. **Anatomical coverage.** The complete adult female brain; ~25,000
   neurons per hemisphere.
3. **Scale / completeness.** 139,255 neurons; ~5×10⁷ synapses
   (see substrate.md). The largest complete invertebrate connectome.
4. **What else ships.** Cell types (11,691 in the male release), hemilineages,
   neurotransmitter predictions; a companion functional release pairs a
   subset of cells (central-complex region) with 2P calcium imaging
   (details in the 2024 paper set).
5. **Format / access.** FlyWire (flywire.ai), CC-BY 4.0, versioned releases
   (FAFB v783), programmatic Python API, neuroglancer visualization, CAVE
   proofreading.
6. **License / cost.** CC-BY 4.0. Raw EM does not fit a 10 GB box; graph
   products (hundreds of MB) do.
7. **Simulation maturity.** Medium. No whole-brain simulation exists;
   subgraph-level models do — central complex (heading integration /
   path integration), mushroom bodies (paired-associative learning plasticity
   models), optomotor pathway. These are the circuits most relevant to this
   project's memory and navigation goals.
8. **Task fit.** **Memory** (mushroom bodies; the canonical PAV model
   organism) and **navigation** (central complex compass / path integrator)
   are the two best-studied small-brain circuits in the literature.
9. **Confidence / completeness.** Near-complete: the release covers the whole
   adult female brain (release-level detail in substrate.md); the authors
   report a small residual gap in the reconstruction. The 2024 Nature paper
   is the primary reference.

### MaleCNS — adult male (Berg et al. 2026)

1–4. Complete adult *male* brain (166,691 neurons; 312M PSDs; 11,691 cell
   types — see substrate.md for provenance and access). The first
   complete male central nervous system; enables sex-comparative
   circuit analysis (e.g. male-specific navigation/reproductive circuits).
5–6. Same FlyWire infrastructure and license as FAFB.
7. Low–medium — inherits FAFB tooling; male-specific circuit models do not
   yet exist.
8. **Navigation and memory** comparatives (sex differences in the central
   complex and mushroom bodies); otherwise as FAFB.
9. v1.0 release (2026) — young; expect corrections.

### Fly hemibrain (Shi et al. 2021)

1. **Organism / stage / sex.** Adult, one hemisphere of the central brain
   (the historical "hemibrain", ~25,000 neurons, >4,000 cell types).
2. **Coverage.** Central brain of one hemisphere — excludes parts of the
   peripheral nerves and half the brain.
3. **Scale / completeness.** ~25,000 neurons, ~10⁶ synapses
   (Shi et al., *Nature* 592:123–128, 2021, doi:10.1038/s41586-020-3007-4).
4. **What else ships.** Cell-type annotations; the substrate for many
   circuit-level models (central complex in particular).
5. **Access.** Janelia FlyEM (flyem.janelia.org); CC-BY; CATMAID-derived.
6. **Cost.** Graph-level, tens–hundreds of MB.
7. **Simulation.** Medium — the hemibrain's central complex is the most
   modeled neuropil in the insect field.
8. **Task fit.** Navigation (central complex) first; memory (mushroom body
   arm in one hemisphere).
9. Superseded by FAFB for completeness; still the reference for some
   circuit-model work.

### First-instar larva (Winding et al. 2023)

1. **Organism / stage / sex.** 1st-instar larva (no sex; larval stage).
2. **Coverage.** Whole larval brain + ventral nerve cord.
3. **Scale / completeness.** 3,016 neurons; 548,000 synapses (Winding et
   al., *Science* 379:eadd9330, 2023; Janelia FlyEM).
4. **What else ships.** A nervous system with **no legs and no eyes** —
   locomotion (undulation), mechanosensation, chemosensory learning, value
   computation; a clean "minimal animal" for sensorimotor + learning
   questions.
5–6. Janelia FlyEM; graph-level cost.
7. Medium — whole-larva simulation is feasible at this scale; circuit-level
   models of larval locomotion exist in the literature.
8. **Learning and sensorimotor** in the simplest bilaterian-ish setup;
   navigation not applicable (no compass structure).
9. Larval brain only — extrapolating to adult behavior is a model choice,
   not data.

**Drosophila verdict.** The richest *tooling + annotation + community*
combination in the catalog; the right second substrate after *C. elegans*,
used as subgraphs (central complex, mushroom bodies, larva) rather than as
one brute-force 139k-neuron simulation.

---

## Zebrafish

The first synapse-resolution vertebrate connectomes; the field is moving
from single circuits (2016–2022) toward whole-larva volumes (Fish1, 2025).
Larvae are transparent, small, and behaviorally tractable — the closest
vertebrate analog to the invertebrate workhorses in this catalog.

### Fish1 (Petkova et al. 2025)

1. **Organism / stage / sex.** *Danio rerio*, 7-day-old (7 dpf) larva;
   combined light + electron microscopy (CLEM) specimen.
2. **Anatomical coverage.** The brain **plus the anterior spinal cord** —
   not the entire adult CNS (the larval spinal cord continues posteriorly
   and is not in scope of this release).
3. **Scale / completeness.** >180,000 segmented soma, >40,000 molecularly
   annotated neurons (26,915 excitatory *vglut2a* / 14,510 inhibitory
   *gad1b* via the confocal channel), ~30 million synapses, most
   classified excitatory / inhibitory / modulatory; 4×4×30 nm serial
   section EM (Petkova et al., bioRxiv 10.1101/2025.06.10.658982, 2025;
   preprint under CC-BY-NC 4.0).
4. **What else ships.** The confocal channel gives molecular identity
   (excitatory vs. inhibitory) directly from the same specimen — a
   structural + functional fusion. The authors validate three circuit
   readouts: water-flow direction encoding in the lateral line, a
   hindbrain motion integrator with recurrent excitation and
   contralateral inhibition, and long-range projections from a
   tegmental excitatory nucleus.
5. **Format / access.** Open-access platform on a public Google Cloud
   Storage bucket (`fish1-release.storage.googleapis.com`): CAVE
   programmatic Python API, VAST for region-limited viewing, FishExplorer
   for search. Versioned releases.
6. **License / cost.** Open-access data policy: independent publication
   encouraged, no co-authorship required, citation of the primary paper
   required, all manual edits tracked in a public CAVE changelog. The
   preprint itself is CC-BY-NC 4.0; the data policy page does not state an
   explicit CC license for the raw data *(license wording unverified)*.
   Raw EM is TB–PB scale — not fetchable to a 10 GB box; graph-level and
   sub-volume access only.
7. **Simulation maturity.** Low — too young; no whole-brain simulation,
   region-level analyses are the current frontier.
8. **Task fit.** **Sensory and sensorimotor** (lateral line flow sensing is
   a clean sensorimotor loop; the motion integrator is a visual
   sensorimotor circuit). **Navigation** in the map sense is limited at
   7 dpf. **Memory** is weak at this stage — treat it as a sensory
   substrate, not a memory one.
9. **Confidence / limitations.** High for what it covers (transparent
   specimen, CLEM, large-scale automation). In-progress: community
   proofreading is ongoing; treat synapse-level completeness as
   improving, not final.

### Predecessors

- **Wanner et al. 2016 / Hildebrand et al. 2017** — single-region EM of
  the larval optic tectum (visual pathway); region-limited `structural`.
- **Svara et al. 2022** (*Nature Methods*, doi:10.1038/s41592-022-01621-0) —
  a 208-neuron network for visual motion processing in the pretectum,
  **reconstructed in the same specimen as 2P calcium imaging**: the clean
  `structural` + `physiological` fusion of the zebrafish line. Best small
  readout of a sensory/sensorimotor loop in a vertebrate.

**Zebrafish verdict.** Fish1 is the only whole-larva vertebrate
connectome in the catalog — the right comparative anchor for "what does a
vertebrate sensory/sensorimotor system look like at synapse resolution?",
used as subgraphs given the lab-box constraint.

---

## Mouse

Two regimes exist and they are not comparable in scale: **region-level
synapse-resolved EM** (MICrONS) and **whole-brain molecular / functional
atlases** (BICCN, Allen). The first is "wiring"; the second is "what cells
are where and what talks to what at regional scale".

### MICrONS Phase 1 (Kasthuri et al. 2015)

1. **Organism / stage / sex.** *Mus musculus*, P36, male.
2. **Anatomical coverage.** 250 × 140 × 90 µm of layer 2/3 visual cortex
   (V1); 3.58 × 3.58 × 40 nm serial-section EM.
3. **Scale / completeness.** 364 excitatory neurons fully proofread
   (dendrites and axons), dense segmentation of the rest, and a 3.2
   million-row putative-synapse table. The synapse table is a *detection*,
   not a validated connectivity graph (the project says so explicitly).
4. **What else ships.** Soma valence table (excitatory/inhibitory/glial),
   fixed meshes, versioned releases (v185.4 at time of writing).
5. **Format / access.** Public: CAVE datastack "pinky_sandbox" for
   proofreading, neuroglancer for visualization, release notes per
   version; bulk download by request (there is a cost, so request
   efficiently). (microns-explorer.org/phase1)
6. **License / cost.** Public; raw volume is large — graph/sub-volume
   access for the lab box.
7. **Simulation maturity.** Medium — local cortical models (feedforward +
   recurrent) are the standard use; no whole-brain model (obviously not
   at this scale).
8. **Task fit.** **Sensory** (V1) and **sensorimotor** (cortical
   processing); memory/navigation only indirectly (cortex as substrate).
9. **Confidence / limitations.** High for the proofread subset; the rest
   is dense-but-unproofed. Region-limited — a patch of cortex, not a
   brain.

### MICrONS Cubic Millimeter (MICrONS Consortium 2025)

1. **Organism / stage / sex.** Adult mouse; ~1 mm³ of neocortex.
2. **Anatomical coverage.** 1.4 × 0.87 × 0.84 mm³ volume.
3. **Scale / completeness.** >200,000 cells, ~120,000 neurons, **523
   million synapses**; 75,000 of the cells were also imaged with 2P
   calcium imaging in the same animal (MICrONS Consortium, *Nature*
   640:435–47, 2025, doi:10.1038/s41586-025-08790-w).
4. **What else ships.** The largest functional + structural fusion of the
   mammalian line: EM anatomy paired with in-vivo activity on a large
   cell subset in the same specimen.
5. **Format / access.** Public via the Allen Brain Portal / MICrONS
   infrastructure; versioned.
6. **License / cost.** Public; raw volume is PB-scale — graph/sub-volume
   only for the lab box.
7. **Simulation maturity.** Low — no whole-brain model; region-level
   analysis is the current frontier.
8. **Task fit.** **Sensory/sensorimotor at scale** (neocortex); a reference
   for "what a mammalian local circuit looks like at synapse resolution".
   Memory/navigation are not the focus of a 1 mm³ cortical patch.
9. **Confidence / limitations.** High (large consortium, Nature).
   Region-limited, adult mouse, neocortex only.

### BICCN — Brain Research through Advancing Innovative Neurotechnologies, Cell Census Network

1. **Scope.** A consortium (NIH BRAIN) producing a **spatial molecular
   atlas** of the mouse brain and cross-species (mouse/monkey/human)
   cell-type resources — not a wiring diagram.
2. **Flagship (Shi et al. 2023).** *Nature* 622:552–561,
   doi:10.1038/s41586-023-06569-5: STARmap PLUS whole-brain molecular
   atlas — 1.09M cells, 230 molecular cell types, 106 tissue regions.
3. **What else ships.** The consortium has catalogued >5,300 cell types
   across mouse/monkey/human (biccn.org); wiring-diagram data is produced
   by the network and distributed via brain-map.org *(specific release
   details unverified)*.
4. **Format / access.** Public via brain-map.org and the Allen Brain
   Portal; web + programmatic access.
5. **Simulation maturity.** None directly — it is a reference atlas, not a
   substrate for simulation.
6. **Task fit.** **Cell-type reference** for whatever substrate is chosen;
   contextualizes "which cell types are in which region" for
   memory/navigation circuits. Not a wiring substrate.
7. **Confidence / limitations.** High (large consortium, Nature). It is a
   *molecular/cell-type* atlas — do not conflate with a connectome.

### Allen Connectivity Atlas (Lee et al. 2010)

1. **Scope.** Whole-brain **regional** connectivity of the mouse, derived
   from viral trans-synaptic tracing plus 2P tomography (Lee et al.,
   *Nature* 464:755–759, 2010, doi:10.1038/nature08854).
2. **Status.** `functional` / `molecular` at **regional** (nuclear)
   resolution — not synapse-level.
3. **Task fit.** Whole-brain context: which regions talk to which. Useful
   for framing where memory/navigation circuits sit relative to the rest
   of the brain; not a simulation substrate.

**Mouse verdict.** The region-level EM (MICrONS) is the reference for
mammalian local circuit anatomy and the functional + structural fusion;
the whole-brain atlases (BICCN, Allen) give context and cell-type
reference. Neither is a lab-box simulation substrate at full scale —
use subgraphs.

---
