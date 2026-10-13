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
- Gap junctions are listed in two sheets ("symmetric" and
  "asymmetric" conductance) with the same section-count weight; per-
  junction conductance values are not given. **Correction (2026-10-13,
  review round 5):** the two sheets are *alternative representations
  of the same physical junctions*, not additive edge classes — every
  asymmetric pair occurs in the symmetric sheet as the same unordered
  pair (identical weight; herm 1,086/1,086, male 1,276/1,276 with one
  weight discrepancy, VB06/VB07), plus a few symmetric-only pairs
  (herm 3, male 1). Corroborated by the SI7 synapse list (one row per
  physical synapse, each junction exactly once, partner = 1) and the
  paper's undirected depiction (Fig. 1). The simulation therefore uses
  a single canonical undirected layer (union of the sheets): 1,089
  herm / 1,278 male junctions. The v2 treatment (both sheets as
  independent layers, 2,178/2,556 records) double-counted the
  electrical conductance and has been retired — see the worm report,
  third addendum.

## Sex differences (measured from the released cell lists)

- **measured** (SI8 cell lists): 451 shared cells, 24 hermaphrodite-
  specific, 149 male-specific.
- **measured** (neuron-only edge sets below): hermaphrodite 300
  neurons, male 378 — a few shy of the reported 302/385 (see parsing
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

The SI9/SI6 workbooks were hand-assembled: each block's leading columns
are inconsistent (a stray banner column here, a count row there), AND
the data rows are **sparse** — the spreadsheet XML omits empty cells
entirely, so a row's value list is shorter than its column span. The
parser (`experiments/worm-pilot/src/parse_cook2019.py`) therefore maps
every cell to its label by the cell's explicit column reference (the
XML `r` attribute), never by list position; the label row (the one
holding the wide stretch of node names) supplies the column→name map
and the name column comes from the first data row. Residual artifacts
are handled explicitly and **counted, not silently dropped**:
region-banner/count rows skipped; self-connections zeroed (C. elegans
neurons do not synapse onto themselves — residual non-zero diagonal
entries would be workbook artifacts); the "symmetric" gap-junction
sheets are symmetrised by max with disagreements counted (a pair
present in only one triangle is kept); trailing header repeats
terminate each block.

> **Correction, 2026-10-13** (supersedes the 2026-10-12 parse counts
> below; the 2026-10-12 pilot report's shuffle comparisons are
> invalidated accordingly — see that report's addendum). The 2026-10-12
> v1 parser mapped data-cell *list positions* to label positions.
> Because the label row is missing the leading columns while the data
> rows keep them, every value was attributed to the label **one column
> left**: the v1 files contained fabricated self-edges (e.g.
> AVAL→AVAL = 21), lost shifted values, and wrong counts (herm
> 3,618 chem / 2,130 gap — including 2,030 "asymmetric" gap-junction
> records, a number that cannot be reproduced from the workbook under
> any counting rule). The v2 column-reference parse is validated two
> ways: (a) the independent SI6 raw-EM-only book, parsed the same way,
> agrees with SI9 on 99.8% (herm) / 99.5% (male) of neuron→neuron
> chemical pairs, the disagreements being SI9's declared extrapolated
> insertions; (b) the corrected matrices contain **zero** self-edges
> and **zero** non-numeric cells — v1's signature of the shift — while
> known weights (e.g. the AVAL→AVAR entry) read correctly.

**measured** parse results, v2 (neuron-to-neuron edges after filtering
to the SI8 neuron lists, SI9 basis = section-weighted, extrapolation
included):

| Sex | Neurons in sim | Chemical edges | Gap junctions (canonical, undirected; one per physical junction) |
|---|---|---|---|
| hermaphrodite | 300 of 302 listed | 3,669 | 1,089 |
| male | 378 of 383 listed | 3,986 | 1,278 |

(The male chemical count 3,986 is unchanged from v1 — that sheet
parsed correctly even positionally; the male *neuron* count moves
380 → 378 because three listed neurons lose their only, shifted edge.)

Against the authors' **reported** herm totals (4,887 chemical + 1,447
gap, on 460 nodes incl. muscles/end organs): our 3,669 neuron→neuron
chemical edges sit inside 4,841 non-zero neuron-source entries (the
~1,172 remainder is neuron→muscle/end-organ; 4,841 vs the reported
4,887 is the authors' own counting-basis difference); the 1,089
canonical neuron–neuron junctions sit inside 2,865 non-zero gap-sheet
entries (the remainder touches muscles/end organs; the reported
1,447 full-graph junctions and our 1,089 neuron–neuron junctions are
different counting bases, both consistent with one junction per
sheet pair — see the third addendum for the full cross-check). The few
missing neurons per sex are listed cells that carry no neuron–neuron
edge in the matrices.

**Known parse artifacts, v2** (all small; none touches the
nociceptive circuit's trunk — verified by direct inspection of every
ASH/AVJ/AVA/AVB/AVD row): 1 symmetric gap-junction triangle
disagreement per sex (max kept; v1's 135/70 were the shift's
artefact); 0 non-numeric cells, 0 non-zero diagonals; a handful of
one-triangle-only symmetric pairs kept. The 52 (herm) / 2 (male)
chemical SI6 vs SI9 pair disagreements are the paper's declared
extrapolated connections.

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
