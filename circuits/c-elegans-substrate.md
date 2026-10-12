# Substrate — *C. elegans* whole-animal connectomes

What the published connectomes actually provide, which machine-readable
release we use, and how its raw files parse. Numbers marked **measured**
were computed from the released data files in
`experiments/worm-pilot/data/` (recomputable with
`experiments/worm-pilot/src/parse_cook2019.py`); numbers marked
**reported** are the authors' own counts as printed in the papers.

## The two primary sources

### White et al. 1986 — the original connectome

- Adult hermaphrodite (N2), whole animal: head, nerve ring, ventral cord,
  tail, pharynx.
- **Reported** scale: 302 neurons, 5,590 chemical synapses (original
  counting basis), plus gap junctions and neuromuscular junctions; the
  first complete nervous-system wiring map (White, Southgate, Stein,
  Brenner & Evans, *Phil. Trans. R. Soc. B* 314:1–340,
  doi:10.1098/rstb.1986.0051).
- Serial 2D EM provenance; single sex (hermaphrodite); no activity data —
  any simulation uses literature-derived parameters, not fitted dynamics.
- The 1986 PDF itself was not fetchable at packaging time (publisher
  403); its content is subsumed and superseded by Cook 2019 (below),
  which re-analyses the same EM series plus new sections.

### Cook et al. 2019 — whole animal, both sexes

- Adult hermaphrodite **and** adult male (N2), "from sensory input to
  end-organ output across the entire animal" — the first whole-animal
  *quantitative* connectivity matrices (Cook et al., *Nature*
  571:63–71, 2019, doi:10.1038/s41586-019-1352-7, open access,
  PMC6889226).
- **Reported** graph scale: hermaphrodite 460 nodes (302 neurons, 132
  muscles, 26 non-muscle end organs) with 4,887 directed chemical edges
  and 1,447 gap junctions; male 579 nodes (385 neurons, 155 muscles, 39
  end organs). The edge counts use a different basis than White 1986's
  5,590 synapse count (connections, with size-weighted section counts,
  vs. scored synapse sites).
- New material vs. 1986: male head data; sex-differential connectivity
  (sex-shared neurons dimorphic in structure and connectivity;
  convergence points of sexual and non-sexual pathways; strength
  differences in shared central pathways).
- The published matrices are assembled from multiple animals and include
  connections **added by extrapolation** in gaps with no data (stated in
  the supplementary legend); a second, raw-EM-only matrix set (no
  extrapolation) ships alongside.

## What is *not* in the connectomes

- **Muscles are nodes, not dynamical units**: the matrices give
  neuron→muscle (neuromuscular junction) and some neuron→end-organ
  edges, but muscles and the 19–26 non-muscle end organs have no
  physiology, no return path, and no biomechanics. Anything downstream
  of the motor neuron (the worm body, bending, swimming, locomotion
  feedback) is outside the dataset.
- **No dynamics**: no spike rates, no calcium traces, no per-synapse
  kinetics. Sign and strength per synapse are not measured: the
  released weights are "total number of EM serial sections of
  connectivity" (a size-weighted contact count), unsigned.
- Gap junctions are listed in two sheets (symmetric vs. asymmetric
  conductance) with the same section-count weight; per-junction
  conductance values are not given.

## Sex differences (measured from the released cell lists)

- **measured** (SI8 cell lists): 451 shared cells, 24 hermaphrodite-
  specific, 149 male-specific.
- **measured** (neuron-only edge sets below): hermaphrodite 300
  neurons, male 380 — two shy of the reported 302/385 (see parsing
  notes); the male carries ~80 additional neurons (cephalic + tail
  complement) and the hermaphrodite a small sex-specific set (HSN,
  vulval and egg-laying cells) absent from the male.

## Machine-readable release used

Primary release: **Cook 2019 supplementary data, SI 9 (connectome
adjacency matrices)** — the matrices the paper's own figures are built
from. Re-downloaded 2026-10-12 (UTC) from the publisher's media host
(verified live at download time); files and hashes are recorded in
`experiments/worm-pilot/data/README.md`. All four files together are
~11 MB.

| File | Content | Role here |
|---|---|---|
| SI9 `...MOESM9_ESM.xlsx` | 6 quantitative matrices (both sexes × chemical / gap-junction-symmetric / gap-junction-asymmetric) | **simulation source** |
| SI6 `...MOESM6_ESM.xlsx` | raw-EM-only adjacency matrices (no extrapolation, no size weighting) | inventory cross-check |
| SI7 `...MOESM7_ESM.xlsx` | per-synapse lists (9,678 herm / 14,851 male records) | inventory cross-check |
| SI8 `...MOESM8_ESM.xlsx` | cell lists (name, category, sex scope) | neuron/muscle classification |

## Parsing the released matrices

The SI9 workbook was hand-assembled: each block's leading columns are
inconsistent (a stray banner column here, a count row there).
`experiments/worm-pilot/src/parse_cook2019.py` detects the label row
(the one containing `I1L`) and the name column (from the `I1L` data row)
per sheet and maps data columns to labels with the resulting offset.
Residual artifacts are handled explicitly and **counted, not silently
dropped**: region-banner/count rows skipped; self-connections zeroed
(C. elegans neurons do not synapse onto themselves — non-zero diagonal
entries are shift artifacts); the "symmetric" gap-junction sheets are
symmetrised by max with disagreements counted; trailing header repeats
terminate each block.

**measured** parse results (neuron-to-neuron edges after filtering to
the SI8 neuron lists, SI9 basis = section-weighted, extrapolation
included):

| Sex | Neurons in sim | Chemical edges | Gap junctions (sym) | Gap junctions (asym) |
|---|---|---|---|---|
| hermaphrodite | 300 of 302 listed | 3,618 | 980 | 1,150 |
| male | 380 of 383 listed | 3,986 | 1,257 | 1,262 |

Against the authors' **reported** herm totals (4,887 chemical + 1,447
gap, on 460 nodes incl. muscles/end organs): our chemical count splits
as 3,618 neuron→neuron + ~1,182 neuron→muscle/end-organ (the matrices
list 4,800 non-zero neuron-source entries in total; the remainder of the
gap-junction sheets is consumed by non-neuron nodes and by the
sym/asym double representation). The two missing neurons per sex are
listed cells that carry no neuron–neuron edge in the matrices.

**Known parse artifacts** (all small; none touches the nociceptive
circuit's trunk — verified by direct inspection of every ASH/AVJ/AVA/
AVB/AVD row): 52/60 zeroed diagonal entries per sex; 135/70 symmetric
gap-junction disagreements (max kept); hundreds of non-numeric cells in
shifted rows (skipped and counted).

## Modelling decisions imposed by the substrate

Because the release carries **no signs, no kinetics, no transmitters**:

1. Chemical-synapse sign is an *assumption*, not a measurement. This
   pilot uses all-excitatory chemical weights (the standard first-order
   assumption in whole-worm spiking models built on this connectome;
   the openWorm/NeuroML toolchain does the same when no transmitter
   annotation is supplied). GABAergic inhibition is the known large
   refinement — a follow-up, not part of the bounded pilot.
2. Weight magnitude scales with the released section count (the only
  measured strength proxy), with one global gain chosen during setup
   (declared in the experiment README before the final runs).
3. Gap junctions are modelled as shared conductance (linear current
   between the two membrane potentials, per the Cook 2019 treatment of
   the symmetric/asymmetric sheets), which is the minimal physically
   meaningful reading of the data.

See `c-elegans-nociception.md` for the one circuit picked from this
substrate, and `reports/2026-10-12-worm-pilot.md` for what a run on it
shows.
