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
| *C. elegans* | Worm connectome (White 1986) | adult hermaphrodite | whole animal | 302 / 5,590 | `structural`, complete | free download (WormWiring), paper public | **high** (NeuroML, openWorm) | learning, sensorimotor, locomotion |
| *C. elegans* | Cook et al. update (2019) | adult, both sexes | whole animal, sensory input → end organ | 302 / 385 (4,887 + 1,447 herm edges) | `structural`, complete | open access (PMC6889226) | **high** | learning, sexual behavior, sensorimotor |
| *C. elegans* | Developmental series (2020) | L1 → adult hermaphrodite | nerve ring + ventral ganglion | 162 → 180 (brain) of 218/300 | `structural`, in progress (preprint) | preprint (bioRxiv) | medium | growth, maturation of learning circuits |
| *D. melanogaster* | FAFB (2024) | adult female | whole brain | 139,255 / ~5×10⁷ | `structural`, near-complete | CC-BY (FlyWire) | medium (subgraphs only) | memory, navigation |
| *D. melanogaster* | MaleCNS (2026) | adult male | whole brain | 166,691 / 312M PSDs | `structural`, near-complete | via FlyWire | low–medium | male-specific circuits |
| *D. melanogaster* | BANC (v888, 2026) | adult female | brain **+ ventral nerve cord** ("CNS") | 158,262 / 3,037,361 pairs | `structural`, preview (no stable release record yet) | via FlyWire (Codex) | low | decision → motor-pathway linkage (Track B end-to-end) |
| *D. melanogaster* | Fly hemibrain (FlyEM release) | adult, hemislice | central brain, one hemisphere | unverified (see section) | `structural`, near-complete | CC-BY (Janelia FlyEM) | medium | memory, navigation |
| *D. melanogaster* | First-instar larva (2023) | 1st instar | whole larval brain + cord | 3,016 / 548,000 | `structural`, complete for larva | Janelia FlyEM | medium | learning, value computation |
| *D. melanogaster* | Functional companion (2024) | adult female | central-complex region, 2P + EM | subset of cells (see paper) | `physiological` + `structural` | Janelia / paper | medium | memory (MB), sensorimotor |
| *Zebrafish* | Fish1 (2025) | 7 dpf larva | brain + anterior spinal cord | >180,000 somas / 30M synapses | `structural`, in progress, open platform | open access (GCS, CAVE) | low | sensory, sensorimotor, comparative |
| *Zebrafish* | Svara et al. (2022) | 5 dpf larva | pretectum / visual motion pathway | 208 / — | `structural`, region complete; `physiological` co-data (2P) | paper | low | sensory (motion) |
| *Zebrafish* | Wanner (2016), Hildebrand (2017) | 5 dpf | optic tectum regions | region-limited | `structural`, region | papers | low | sensory |
| *Mouse* | MICrONS Phase 1 (2015) | P36 male | 250×140×90 µm, L2/3 V1 | 364 fully proofread / 3.2M putative | `structural`, region | public (CAVE "pinky_sandbox", neuroglancer) | medium (local models) | cortical processing, sensory |
| *Mouse* | MICrONS cubic mm (2025) | adult | 1.4×0.87×0.84 mm³ | ~120,000 / 523M | `structural` + `physiological` (75K cells 2P), region, in progress | public (Allen portal) | low | sensory/sensorimotor at scale |
| *Mouse* | BICCN spatial atlas (2023) | postnatal stages | whole brain (molecular) | 1.09M cells / 230 types | `molecular` — **not** a wiring diagram | public (brain-map.org) | none | cell-type reference |
| *Mouse* | Allen mesoscale connectome (2010) | adult | whole brain, nuclear-level | region-level (viral + 2P tomography) | `functional`, whole brain | public (allenbrain.org) | low | whole-brain context |
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

### Adult hermaphrodite — White et al. 1986 (the original connectome)

1. **Organism / stage / sex.** *C. elegans* N2, adult hermaphrodite.
2. **Anatomical coverage.** Whole animal nervous system: head, nerve ring,
   ventral nerve cord, tail — the full 3D EM reconstruction basis of the
   series that defined the field (White et al., *Phil. Trans. R. Soc. B*
   314:1–340, doi:10.1098/rstb.1986.0051).
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
7. **Simulation maturity.** High — same tooling as the 1986 connectome
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

### BANC — adult female brain + nerve cord (v888, 2026)

1. **Organism / stage / sex.** Adult *female*; the first *Drosophila* release
   covering **brain and ventral nerve cord in one reconstruction** ("CNS").
2. **Coverage.** Whole brain + ventral nerve cord — unlike FAFB (brain only),
   this reaches from central decision circuits down to the motor pathways.
3. **Scale / completeness.** 158,262 neurons / 3,037,361 connection pairs.
   *Verification note (2026-10-12):* figures read from the official FlyWire
   Codex portal (live check: "BANC v888 (CNS) Female Adult Fly Brain and Nerve
   Cord — 158,262 neurons, 3,037,361 connections"). **No stable DOI or final
   release record is published yet** — treat as a preview; re-verify before
   making data claims.
4. **What else ships.** Same FlyWire infrastructure as FAFB (NeuPrint,
   Neuroglancer, flywire Python API, Codex exploration).
5–6. License/access as FAFB (CC-BY, FlyWire).
7. **Simulation maturity.** Low — no models yet. The scale is inside the
   demonstrated LIF regime (Shiu 2024 simulated a whole-brain FAFB (v630)
   LIF model on the same model class — ~10⁵ neurons) but 4–5× the scope of
   current subgraph work.
8. **Best-fit computations.** The missing link for Track B: heading/decision
   circuits (CX) to steering/locomotor output — Westeinde et al. 2024's
   heading→steering transform can only be tested end-to-end once a release
   includes the VNC. Cross-sex comparison with MaleCNS.
9. **Release status.** v888 (2026) — preview; pin to a stable release before
   production use.

### Fly hemibrain (Janelia FlyEM release)

1. **Organism / stage / sex.** Adult, one hemisphere of the central brain.
2. **Coverage.** Central brain of one hemisphere — excludes the peripheral
   nerves and half the brain.
3. **Scale / completeness.** *(unverified — a 2025-10-12 coordinator check
   found the originally cited paper and DOI do not resolve; the neuron/synapse
   scale needs re-verification against the FlyEM release notes before this row
   is trusted.)* The FlyEM portal releases a hemibrain reconstruction with
   connectivity and cell-type annotations.
4. **What else ships.** Cell-type annotations; used as the substrate for
   circuit-level models (central complex in particular).
5. **Access.** Janelia FlyEM (flyem.janelia.org); CC-BY; CATMAID-derived.
6. **Cost.** Graph-level, tens–hundreds of MB (check release before
   downloading; budget ~2 GB on this box).
7. **Simulation.** Medium — the central complex is the most modeled
   neuropil in the insect field.
8. **Task fit.** Navigation (central complex) first; memory (mushroom-body
   arm in one hemisphere).
9. Superseded by FAFB for completeness; still a reference for some
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

1. **Scope.** Whole-brain **mesoscale** connectivity of the mouse — "a
   mesoscale connectome" — derived from viral trans-synaptic tracing plus
   2P tomography (Lee et al., *Nature* 464:755–759, 2010,
   doi:10.1038/nature13186; the Allen Brain Institute release).
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

## *Ciona intestinalis* (tunicate / sea squirt)

### Tadpole larval CNS (Ryan, Lu, Meinertzhagen 2016)

1. **Organism / stage / sex.** *Ciona intestinalis* (L.), tadpole larva —
   a tunicate, i.e. a **chordate** (the sister lineage to the
   craniates/vertebrates).
2. **Anatomical coverage.** Whole CNS (brain + ventral nerve cord); the
   first complete chordate connectome (Ryan et al., *eLife* 5:e16962,
   2016, doi:10.7554/eLife.16962; PMC5140270).
3. **Scale / completeness.** 177 neurons; 6,618 synapses (including 1,772
   neuromuscular junctions); 1,206 gap junctions; 922 **polyadic**
   synapses (one presynaptic terminal contacting multiple postsynaptic
   targets — a motif that is rare in the other entries here).
4. **What else ships.** Chordate "sidedness": pronounced left-right
   asymmetry in the brain; a small brain with chordate-grade
   organization, which is the point of the paper.
5. **Format / access.** Paper + supplementary material. A
   machine-readable public graph could **not** be located in this
   session *(access unverified)* — assume paper-derived reconstruction
   work is needed for simulation use.
6. **Cost.** Trivial (177-neuron graph).
7. **Simulation maturity.** **None found** — greenfield. At 177 neurons
   this is the *easiest* greenfield whole-organism simulation target in
   the catalog (smaller than *C. elegans*, chordate).
8. **Task fit.** **Comparative baseline**: the chordate reference point
   for "what did the vertebrate brain start from?" Tunicate larvae show
   simple sensory responses and ciliary-beat plasticity in the literature
   — a learning-adjacent readout, not a navigation one (the tadpole
   swims; it does not navigate in the map sense).
9. **Confidence / limitations.** High for completeness (small, fully
   traced); a single specimen, 2D serial sections; machine-readable data
   access unverified.

## *Platynereis dumerilii* (marine annelid)

### Whole-body larval connectome (Verasztó, Jasek, et al., Jékely 2025)

1. **Organism / stage / sex.** *Platynereis dumerilii*, segmented marine
   annelid, larva.
2. **Anatomical coverage.** The **whole body** — the first
   whole-body (not just CNS) connectome in the catalog: brain, nerve
   cord, and peripheral nerves across all segments, from whole-body
   serial-section EM (Verasztó et al., *eLife* 13:RP97964, 2025,
   doi:10.7554/eLife.97964; PMC12387772).
3. **Scale / completeness.** >9,000 neuronal and non-neuronal cells;
   202 neuronal and 92 non-neuronal cell types; segment-specific
   (heteromeric) and segmentally repeated (serially homologous) types;
   intersegmental, ascending/descending, and peptidergic circuits; a
   multimodal mechanosensory girdle.
4. **What else ships.** Motor circuits for ciliated cells, glands,
   pigment cells, and muscles — a template for **whole-body
   sensorimotor coordination** (the animal moves every segment
   deliberately).
5. **Format / access.** Paper (open access, eLife); machine-readable
   reconstruction data access **not verified** this session.
6. **Cost.** Small graph (thousands of nodes).
7. **Simulation maturity.** None found — greenfield; no whole-body
   multi-segment simulation exists in the literature as of this writing.
8. **Task fit.** **Sensorimotor** (intersegmental coordination — the
   closest invertebrate analog to "body-level" control). Not memory, not
   navigation.
9. **Confidence / limitations.** High (eLife, complete reconstruction);
   larval stage only; data access unverified.

## Hymenoptera: honeybee, bumblebee, ants

### Honeybee (*Apis mellifera*) — gap

1. **Status.** **No complete connectome has been published.** The adult
   brain is estimated at **>1 million neurons** — roughly an order of
   magnitude above *D. melanogaster* and well beyond current
   single-volume invertebrate connectome capacity (Frontiers in
   Neuroscience review, 2026, doi:10.3389/fnins.2026.1911198).
2. **Projects.** A honeybee **nodulus** (central complex) reconstruction
   was advertised on a lab project page (braininbrain.org); that domain
   now resolves to an unrelated site, so the project's current status is
   **unverified**.
3. **What is known without a connectome.** The honeybee central complex
   is a well-characterized compass/path-integrator neuropil (the insect
   navigation module, homologous to the fly's); the waggle dance and
   spatial learning are among the richest behavioral datasets in
   entomology.
4. **Task fit.** **Navigation** (the reference system) and **memory**
   (dance learning) — at the level of *behavioral and light-microscopy
   circuit* models, not wiring diagrams.
5. **Expectation.** Regional releases (central complex first) before any
   whole-brain attempt; watch list.

### Bumblebee central complex projectome (Sayre et al. 2021)

1. **Organism / stage / sex.** *Bombus impatiens*, adult bumblebee.
2. **Coverage.** The central complex — a **projectome** (axonal
   projection map), *not* a synapse-level graph (Sayre et al., *eLife*
   10:e68911, 2021; Lund Vision Group).
3. **Category.** `functional`/projection map.
4. **Task fit.** **Navigation** reference: the projection architecture of
   the insect path-integrator neuropil.
5. **Confidence.** Solid (peer-reviewed eLife); but it is projections,
   not wiring — do not cite it as a connectome.

### Ants

1. **Status.** No connectome.
2. **What exists.** A **reference brain** (nomenclature + anatomical
   atlas) for the clonal raider ant *Ooceraea biroi* — Frank et al.,
   *Current Biology* 2025 (PII S0960-9822(25)01520-9) — built for
   behavioral-neuroscience reference, not wiring.
3. **Task fit.** Colony-level navigation (trail following, foraging
   networks) is a *behavioral* literature domain; no neural substrate is
   published.

## Lepidoptera (moths)

**Gap.** No whole-brain or regional EM connectome of a moth was found in
this session. The 2026 Frontiers review lists Lepidoptera as a frontier
for comparative connectomics (alongside Coleoptera and Orthoptera).
Light-level anatomy and physiology of the antennal lobe (olfaction) and
the central complex (the same path-integrator neuropil as flies and bees)
are well studied; wiring is not. **Task fit:** navigation reference at
the literature level only.

## Larger vertebrates and human

### Zebra finch — song system

- **HVC (Kornfeld et al. 2017, eLife):** dense serial-section EM of HVC,
  the cortico-basal forebrain nucleus that *generates the temporal
  sequences* of song; the paper's focus is how axonal targets vary
  within a sequence-generating network — i.e. the anatomy of a learned
  **sensorimotor sequence generator**.
- **Area X (Shvedov et al. 2026, *Current Biology*, PII
  S0960-9822(26)00377-5):** dense EM of the striatal Area X; enables
  studies of neuronal migration and adult neurogenesis within a
  connectomic framework.
- **Task fit.** **Sensorimotor** (sequence generation) — the best
  small-vertebrate reference for "learned sequences"; memory/navigation
  only indirectly (song memory).

### Human — 1 mm³ temporal cortex

1. **Scope.** Shapson-Coe et al., *Science* 384:eadk4858, 2024: ~57,000
   cells and ~150 million synapses in 1 mm³ of temporal cortex; ~1.4 PB
   of EM.
2. **Access.** Restricted (described in the paper); not a lab-box
   dataset.
3. **Task fit.** **Scale reference only**: what mammalian cortex looks
   like at synapse resolution, in the organism that matters for the
   project's long-term question. No simulation at this scale.
4. **Mesoscale watch.** A *mesoscale* (region-level) human brain
   connectome is projected "within the next decade" (Trends in
   Neurosciences 2025, PII S0166-2236(25)00238-3) — a watch item, not a
   dataset.

### Octopus (distant comparator)

- *Octopus vulgaris* **vertical lobe** (Bidel et al., *eLife* 12:e84257,
  2023): the memory-acquisition network in a mollusc — a connectomic
  comparison point for **convergent evolution of memory circuits**.
  Region-limited; reference only.

---

## Prioritized shortlist (lab-box constrained)

Hardware assumption: **4-core CPU, 12 GB RAM, ~10 GB free disk** (no GPU,
no TB-scale storage). The shortlist orders the catalog by *what is
actually runnable here*, mapped to the target computations
(memory, navigation, learning, sensorimotor).

### Tier 1 — end-to-end feasible (graph **and** simulation on this box)

| # | Substrate | Why it fits |
|---|---|---|
| 1 | **C. elegans adult** (herm 302 / male 385) | Complete, MB-scale, NeuroML/openWorm code exists; best small-brain **learning** (habituation) + **sensorimotor** (full sensory→effector matrices) target. *First choice.* |
| 2 | **Ciona tadpole** (177) | Smallest complete **chordate** graph; no published simulation → the easiest greenfield whole-organism model in the catalog. |
| 3 | **Drosophila FAFB subgraphs** — central complex (**navigation**: heading integrator / path integrator) and mushroom bodies (**memory**: PAV plasticity models) | Each is 10²–10³ neurons; graph products are CC-BY via FlyWire; reference circuit models exist to compare against. |
| 4 | **D. melanogaster 1st-instar larva** (3,016) | Whole-organism simulation feasible at this scale; **learning** + **sensorimotor** in the minimal bilaterian setup (no compass — navigation not applicable). |

### Tier 2 — graph-level analysis feasible, whole-brain simulation is not

| # | Substrate | How to use it here |
|---|---|---|
| 5 | **Drosophila FAFB full graph** (139,255) | Structural analytics (motifs, paths, cross-comparison with the subgraphs in Tier 1) — borderline at 12 GB; use indexed/sparse formats. |
| 6 | **Fish1** (30M synapses, 7 dpf) | Region-limited pulls via the CAVE programmatic API / GCS; the only whole-larva **vertebrate** brain; **sensory/sensorimotor** circuits (lateral line, motion integrator). |
| 7 | **MICrONS cubic mm** (523M synapses) | Subgraph extracts via the Allen portal / neuroglancer; **mammalian sensory/sensorimotor** reference at synapse resolution. |

### Tier 3 — reference only (no runnable model; use for design and comparison)

| # | Substrate | Use |
|---|---|---|
| 8 | **Bumblebee CC projectome** + honeybee (watch) | **Navigation** reference: the path-integrator neuropil across Hymenoptera. |
| 9 | **Zebra finch HVC / Area X** | **Sensorimotor** sequence generation in a vertebrate. |
| 10 | **Human 1 mm³** + mesoscale watch item | **Scale reference** for the long-term question; Ciona (Tier 1) is the chordate anchor in between. |

### Task map (what to reach for first, per target computation)

- **Memory:** *C. elegans* (habituation) → *Drosophila* mushroom bodies
  (PAV) → *Ciona* (comparative) → octopus vertical lobe (distant reference).
- **Navigation:** *Drosophila* central complex (compass/path integrator) →
  *C. elegans* foraging/locomotion (open-loop path following, not map
  navigation) → bumblebee/honeybee central complex (reference) → Fish1
  lateral line (sensory, not map-based).
- **Sensorimotor:** *C. elegans* whole body (best in catalog) → *Ciona* →
  Fish1 motion integrator → zebra finch HVC (learned sequences).
- **Learning:** *C. elegans* (habituation/PAV) → *Drosophila* larva +
  adult MB → honeybee (behavioral literature only, no wiring).

## Gaps and watch items

- **No complete connectome exists for honeybee, moths, or ants.** The
  honeybee alone is estimated at >10⁶ neurons — well beyond the current
  invertebrate connectome frontier (the fly, ~10⁵ neurons, took a decade
  of work); expect central-complex/regional releases first.
- **Fish1 is in progress** — community proofreading is ongoing; synapse-
  level completeness will improve with versions.
- **Unverified in this session** (flagged inline): the hemibrain row's
  original paper citation did not resolve (2026-10-12 coordinator check) and
  was removed — the row now cites the FlyEM release with the scale marked
  unverified; BICCN wiring-diagram release details; machine-readable data
  access for *Ciona* and *Platynereis*; honeybee nodulus project status;
  Kornfeld 2017 exact eLife article ID.
- **Watch list:** FAFB residual-gap closure; MaleCNS post-v1.0
  corrections; a honeybee central-complex release; the human mesoscale
  connectome (projected "within the next decade").

## Sources consulted (2026-10-12)

Direct fetches:

- wormwiring.org (hermaphrodite, male, Pristionchus pages)
- wormatlas.org/neuronalwiring.html
- openworm.org
- pmc.ncbi.nlm.nih.gov: PMC6889226 (Cook 2019), PMC5140270 (Ryan 2016),
  PMC12387772 (Verasztó 2025)
- nature.com/articles/s41586-024-07558-y (FlyWire, referenced)
- flywire.ai
- biorxiv.org/content/10.1101/2025.06.10.658982v1 (Fish1)
- fish1-release.storage.googleapis.com (index, data policy)
- microns-explorer.org/phase1
- frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2026.1911198/full
- nature.com/articles/s41592-022-01621-0 (Svara 2022)

Via search snippets (not full-text fetched):

- pubmed.ncbi.nlm.nih.gov: 31270481 (Cook 2019), 27921996 (Ryan 2016),
  40862480 (Verasztó 2025), 34523418 (Sayre 2021)
- nature.com/articles/s41586-023-06569-5 (BICCN, Shi 2023)
- biccn.org (cell-type counts)
- phys.org / sciencedirect.com (Frank 2025, ant reference brain)
- edge.org (Barron, honeybee scale)
- en.wikipedia.org/wiki/Drosophila_connectome (larval counts cross-check)

Primary papers cited (DOI in text): White 1986 (10.1098/rstb.1986.0051);
Cook 2019 (10.1038/s41586-019-1352-7); Dorkenwald 2024
(10.1038/s41586-024-07558-y); Berg 2026 (10.1016/j.cell.2026.08.015, via
substrate.md)Winding 2023
(10.1126/science.add9330); Petkova 2025 (bioRxiv 10.1101/2025.06.10.658982);
Svara 2022 (10.1038/s41592-022-01621-0); Kasthuri 2015 (Cell
162:648–661); MICrONS Consortium 2025 (10.1038/s41586-025-08790-w);
Shi 2023 (10.1038/s41586-023-06569-5); Lee 2010 (10.1038/nature13186);
Ryan 2016 (10.7554/eLife.16962); Verasztó 2025 (10.7554/eLife.97964);
Sayre 2021 (10.7554/eLife.68911); Bidel 2023 (10.7554/eLife.84257);
Shapson-Coe 2024 (Science 384:eadk4858).
