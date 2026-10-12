# Circuit — *C. elegans* nociceptive withdrawal (the pilot's one computation)

**Pick.** Nociceptive withdrawal: a noxious stimulus (pinprick, chemical)
depolarizes the ASH class of nociceptors; the response is a
turn-away/withdrawal generated through the command interneurons
AVA/AVB/AVD/AVJ that drive the body-wall motor neurons. This is the
circuit the pilot simulates.

## Why this one (vs. the brief's other candidates)

| Candidate | Verdict |
|---|---|
| **Nociceptive withdrawal (ASH)** | **Picked.** Every element is in the 1986 connectome and in the Cook 2019 matrices; the smallest span (~15–20 neurons input→output); the best primary-source support: the complete wiring is *measured*, and behavior (pinprick avoidance, habituation) is extensively characterized. |
| Thermotaxis (AFG) | The sensory computation (temperature memory via AFG) is real, but the motor output side is diffuse (AVF/AVG/AVD interneuron complex) and the stimulus is a slowly varying gradient, not a sharp event — a worse first computation for a bounded pilot. |
| Nose-to-tail (CIR-1/2) | A real reflex (touch at the nose → tail response), but the canonical account is genetically defined (CIR channels) and its full wiring was never mapped as a discrete circuit in the connectome literature — weaker primary-source support. |

## The measured circuit (from the data in this repo)

All weights are the released section counts (SI9, see
`c-elegans-substrate.md`); "chem" = directed chemical connection,
"gap" = gap junction (undirected unless marked →). Verified directly
from `experiments/worm-pilot/data/c-elegans-edges-herm.json`.

```
  nociceptors                       command pool (gap-junction mesh)

  ASHL  gap(7)  ASHR
   |  chem          |  chem          AVAR <--gap 18--> AVBL
   |-> AVBL (15)    |-> AVJR (27)      |  \                |
   |-> AVJR ( 7)    |-> AVBR (10)      |   \  gap 15       |  chem 14 -> AVBR
   |-> AVBR ( 1)    |-> AVAL ( 3)      |      v            |  chem 10 <- AVBR
   |-> AIYL (24)    |-> AIYR (28)      |   AVDL <----------+
      (AIY:          (AIY: modulatory, chem within pool (measured):
       modulatory)    gap-coupled to     AVAL->AVAR (16)  AVAR->AVAL (20)
       sensory pool)   ASK/AVF etc.)     AVAL->AVBR (12)  AVAR->AVBL ( 7)
                                          AVDR->AVBL (41)  AVDL->AVBL (37)
  ASJL  gap(7)  ASJR                   AVDR->AVBR (52)  AVDL->AVBR (37)
   (mechanosensory companion;           AVJR->AVAR ( 7)  AVJL->AVAL ( 5)
    no chemical output to the          gaps: AVAR-AVJR 3, AVAR-AVJL 3,
    command pool in the matrices)        AVAL-AVDL 9, AVDL-AVJL 6, AVJL-AVJR {1,1,3}

  motor output (chemical, main edges — measured):
    AVAR -> DA06(20) DA02/03(9) DA04/05(4/6) ... | VA09(13) VA04(9) | AS06-09(6-10) | DB, DD, PDA
    AVAL -> DA03(14) DA01/02(12) ...            | VA08(9) VA01-07 | AS05-09(5-8)  | DD06(8)
    AVDL -> DA01( 9) AS09(4)                    | VA01/08         | AS02/08(1-2)  | DD05(2)
    AVDR -> DA01-09(1-3) AS09(3)                | VA01/03         | AS08(2)       | DD06(1)
    AVBL -> VA12(3) DD06(3) (small)     AVBR -> AS01(3) VD01(2) DB(2)
    command neurons also reach motor neurons by gap junctions:
    AVAR~DA08(17) VA10(16) DA02(7) ...;  AVAL~VA01/05(13) DA06(10) DA01(9);
    AVBL~VB01(14) DB06(13);  AVBR~PDA(15) RID(18) (the latter two outside this circuit)
```

Notes: (i) the command pool is *bidirectionally* chemically and
electrically meshed — AVA/AVB/AVD/AVJ are not a chain but a coupled
pool, as measured; (ii) ASJ contributes mechanically (gap junctions) to
the same pathway but no chemical drive in the released matrices;
(iii) the full per-node edge list is in the data files.

## Sources

- **White et al. 1986**, *Phil. Trans. R. Soc. B* 314:1–340,
  doi:10.1098/rstb.1986.0056 — the complete hermaphrodite connectome
  (302 neurons, 5,590 chemical synapses on the original counting
  basis) including the ASH pathway as drawn from serial EM; its
  behavior section documents the pinprick response. (Note: the DOI
  recorded in `docs/datasets.md`, `…0051`, is a typo — Crossref
  resolves `.0051` to an unrelated ribulose paper and `.0056` to this
  one. Flagged for the doc owner; not edited here since `docs/` is
  outside this lane's ownership.)
- **Cook et al. 2019**, *Nature* 571:63–71,
  doi:10.1038/s41586-019-1352-7 — the quantitative matrices (weights,
  both sexes) used by this pilot; open access, PMC6889226.
- **Rankin & Broster 1992**, *Behav. Neurosci.* 106:239–249,
  doi:10.1037/0735-7044.106.2.239 — habituation and its recovery in the
  nematode (behavioral characterization of the response this circuit is
  believed to implement).
- **Rankin 2000**, *Behav. Neurosci.* 114:496–505,
  doi:10.1037/0735-7044.114.3.496 — context conditioning of
  habituation (the same behavioral assay family).

**Status of the behavior claim.** The *wiring* of this pathway is
measured (EM). That the pathway *implements* pinprick withdrawal is a
long-standing inference from the literature (connectome + genetics +
behavior); this pilot does not test that inference — it tests what the
wiring does under a declared spiking model. See the report's
non-claims.
