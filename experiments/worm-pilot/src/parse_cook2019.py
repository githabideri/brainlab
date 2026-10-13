"""Parse the Cook et al. 2019 whole-animal connectome spreadsheets (SI 6, 7, 8, 9).

Sources (all from the open-access paper, doi:10.1038/s41586-019-1352-7,
PMC6889226; files re-downloaded from media.springernature.com, see
data/README for URLs + sha256):

  SI8  cell lists            -> which of the matrix nodes are neurons
  SI9  connectome matrices   -> the quantitative matrices the paper's figures
                                use: weight = total EM serial sections of
                                connectivity (counts synapses and their
                                sizes), includes connections added by
                                extrapolation in gaps
  SI6  raw adjacency         -> same layout, but only synapses scored on EM
                                (no extrapolation, synapse counts not sized)

The workbook was hand-assembled: the leading columns of each block are
inconsistent (one stray banner/empty column here, two there) AND data rows
are SPARSE — the sheet XML omits empty cells entirely. The parser therefore
must NOT map values by list position: it reads each cell's explicit column
reference (the XML `r` attribute, e.g. "F4") and aligns data cells to the
label row by true column index. (A 2026-10-12 version of this parser mapped
positionally and shifted every value one label column left — it produced
fake self-edges and a connectome that failed the SI6-⊆-SI9 cross-check;
see the 2026-10-13 correction note in circuits/c-elegans-substrate.md.)
The label row (the one containing 'I1L') supplies the column→name map; the
name column comes from the I1L data row. Residual artifacts are handled
explicitly and counted, not silently dropped:

  * region-banner rows and count rows are skipped (they never name a cell)
  * self-connections are zeroed (C. elegans neurons do not synapse onto
    themselves; residual non-zero diagonal entries are workbook artifacts)
  * for the 'gap jn symmetric' sheets the two triangles of the matrix do
    not agree everywhere; the value is symmetrised by taking the max and
    disagreements are counted; a pair present in only one triangle is kept
  * a row that repeats the header (trailing block) terminates the sheet

Outputs (JSON, stable schema):
  data/c-elegans-edges-<sex>.json   neuron-only edge lists (faithful
                                     per-sheet records: chem, gap_sym,
                                     gap_asym)
  data/c-elegans-electrical-<sex>.json  CANONICAL electrical graph
                                     (one undirected record per physical
                                     junction; see canonical_electrical)
  data/c-elegans-inventory.json     counts used by the substrate document
"""
import json
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
BANNERS = {
    "PHARYNX", "SENSORY NEURONS", "INTERNEURONS", "MOTOR NEURONS",
    "SUBLATERAL MOTOR NEURONS", "VENTRAL CORD MOTOR NEURONS",
    "BODYWALL MUSCLES", "MUSCLES", "OTHER END ORGANS", "OTHER",
    "SEX-SPECIFIC CELLS", "SEX SPECIFIC", "TITLE AND LEGEND",
}


def _col_of(ref):
    """Excel column reference ('F4') -> 0-based column index."""
    s = "".join(ch for ch in ref if ch.isalpha())
    n = 0
    for ch in s:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def load_xlsx(path):
    """{sheet name: {row index: {column index: cell value}}}.

    Cells are placed at the column index from their XML `r` reference,
    so sparse rows (omitted empty cells) line up with the label row's
    columns. (Rows without references fall back to sequential order; the
    Cook 2019 sheets all carry references.)
    """
    z = zipfile.ZipFile(path)
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        r = ET.fromstring(z.read("xl/sharedStrings.xml"))
        ss = ["".join(t.text or "" for t in si.iter(NS + "t"))
              for si in r.findall(NS + "si")]
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheets = [s.get("name") for s in wb.find(NS + "sheets")]
    out = {}
    for i, name in enumerate(sheets, 1):
        r = ET.fromstring(z.read("xl/worksheets/sheet%d.xml" % i))
        rows = {}
        ridx = 0
        for row in r.iter(NS + "row"):
            d = {}
            for c in row.findall(NS + "c"):
                v = c.find(NS + "v")
                if v is None:
                    t = c.find(NS + "is")
                    val = ("".join(x.text or "" for x in t.iter(NS + "t"))
                           if t is not None else "")
                else:
                    val = ss[int(v.text)] if c.get("t") == "s" else v.text
                col = _col_of(c.get("r")) if c.get("r") else max(d) + 1
                if val is not None:
                    d[col] = str(val).strip()
            if row.get("r"):
                ridx = int("".join(ch for ch in row.get("r") if ch.isdigit())) - 1
            rows[ridx] = d
            ridx += 1
        # dense row list, in order
        out[name] = [rows.get(i, {})
                     for i in range(max(rows) + 1) if i in rows]
    return out


def _dense(r):
    """{col: value} -> dense list (column-index addressed)."""
    n = max(r) + 1 if r else 0
    return [r.get(i, "") for i in range(n)]


def parse_matrix(sheet):
    """Return (cols, M, stats) for one adjacency-matrix sheet.

    cols: ordered column (postsynaptic) node names (from the label row,
          aligned by true column index).
    M: {presynaptic name: {postsynaptic name: value(str)}} for rows that
       name a real cell; value cells are matched to labels by the column
       the cell actually sits in (never by list position).
    """
    rows = sheet
    # label row: the first row holding a wide stretch of node-name labels
    # (the hand-assembled sheets start with different regions per sex —
    # I1L in the herm books, ASIL in the male raw-adjacency book)
    nrow = None
    for i, r in enumerate(rows[:10]):
        if len([v for v in r.values() if v]) >= 100:
            nrow = i
            break
    if nrow is None:
        raise ValueError("no label row found")
    label = rows[nrow]
    labels = {c: v for c, v in label.items() if v}
    cols = [v for _, v in sorted(labels.items())]
    first_col = min(labels)
    first_val = labels[first_col]
    namecol = None
    for i in range(nrow + 1, len(rows)):
        hits = sorted(c for c, v in rows[i].items() if v == first_val)
        if hits:
            namecol = hits[0]
            break
    if namecol is None:
        raise ValueError("no data row matching the label row found")
    M, stats = {}, {"rows_seen": 0, "rows_skipped_banner": 0,
                    "rows_skipped_number": 0, "rows_skipped_noname": 0,
                    "header_repeat_rows": 0}
    labelset = set(labels.values())
    for i in range(nrow + 1, len(rows)):
        r = rows[i]
        nm = r.get(namecol, "")
        nonempty = [v for v in r.values() if v]
        stats["rows_seen"] += 1
        if not nm:
            stats["rows_skipped_noname"] += 1
            continue
        if nm in BANNERS:
            stats["rows_skipped_banner"] += 1
            continue
        if nm in ("1", "2", "3", "4", "5"):
            stats["rows_skipped_number"] += 1
            continue
        # a row that repeats the column labels (trailing block) terminates
        # the sheet; data rows carry at most a handful of name values, a
        # repeated label row carries hundreds
        if sum(1 for v in nonempty if v in labelset) >= 20:
            stats["header_repeat_rows"] += 1
            break
        M[nm] = {labels[c]: v for c, v in r.items()
                 if v and c in labels and labels[c] != nm}
    return cols, M, stats


def parse_cell_lists(xlsx):
    """SI8 -> {name: (category, sex_scope)}.

    The data columns run [name, category, notes...] in every sheet, the
    printed headers are offset by one and are not used.
    """
    d = load_xlsx(xlsx)
    out = {}
    scope = {"pharynx": "shared", "sex-shared": "shared",
             "hermaphrodite specific": "herm", "male-specific": "male"}
    for name, rows in d.items():
        if "TITLE" in name.upper():
            continue
        for r in rows[1:]:
            dense = _dense(r)
            cells = [c.strip() for c in dense]
            if not cells or not cells[0]:
                continue
            if cells[0] in BANNERS:
                continue
            cat = cells[1] if len(cells) > 1 else ""
            out[cells[0]] = (cat, scope.get(name, "shared"))
    return out


NEURON_CATS = {"interneuron", "sensory", "motorneuron", "sensory neuron"}


def is_neuron(name, cells):
    if name not in cells:
        return False
    cat, _ = cells[name]
    return cat.lower().replace("-", " ") in NEURON_CATS


def electrical_si7(data_dir, sheetname):
    """SI7 synapse list, electrical (gap-junction) rows.

    Each row is one scored physical synapse (unique contin id). Returns
    ({undirected cell pair: [n_synapses, sum_sections]}, stats). The
    'post' column may be comma-joined when partner number > 1 (herm:
    never; male: 7 rows); the post1..post4 columns mirror it.
    """
    si7 = load_xlsx(data_dir + "/Cook2019_SI7_synapse-lists.xlsx")
    rows = si7[sheetname]  # dense list of {col: value}; row 0 = header
    pairs = {}
    stats = {"rows": 0, "electrical": 0, "unmapped_cells": 0,
             "self_pairs": 0}
    for ri, row in enumerate(rows):
        if ri == 0:
            continue
        stats["rows"] += 1
        if "electrical" not in str(row.get(5) or "").lower():
            continue
        stats["electrical"] += 1
        pre = str(row.get(3) or "").strip()
        posts = [p.strip() for p in str(row.get(4) or "").split(",") if p.strip()]
        for c in (8, 9, 10, 11):
            p = str(row.get(c) or "").strip()
            if p and p not in posts:
                posts.append(p)
        try:
            sec = int(float(row.get(6) or 0))
        except (TypeError, ValueError):
            sec = 0
        for post in posts:
            if pre == post:
                stats["self_pairs"] += 1
                continue
            if not pre or not post or "obj" in pre or "obj" in post or \
                    "[" in pre or "[" in post:
                stats["unmapped_cells"] += 1
                continue
            k = tuple(sorted((pre, post)))
            s = pairs.setdefault(k, [0, 0])
            s[0] += 1
            s[1] += sec
    return pairs, stats


def canonical_electrical(edges, neuron_names, si7_pairs, si7_stats):
    """Collapse the two SI9 gap-junction sheets into ONE canonical
    undirected junction graph.

    Review round 5 (2026-10-13) found — independently of the agent —
    that the 'gap jn asymmetric' sheet is a near-duplicate of the
    'gap jn symmetric' sheet: for herm, all 1,086 of its unique
    unordered pairs also occur in the symmetric sheet with exactly
    identical weights (3 symmetric-only pairs); the paper's own
    figures draw gap junctions as a single undirected edge class, the
    SI6 raw-adjacency book has a single gap-junction sheet, and the
    SI7 synapse list records each physical synapse once. Treating the
    two SI9 sheets as independent conductance layers therefore
    double-counted 1,086/1,089 of the electrical weight and let the
    shuffle randomize two layers of the same physical junctions
    independently — a confound for measured-vs-shuffled comparisons.

    Canonical rule (declared, deterministic):
      * one undirected record per unique neuron-neuron pair in the
        union of the two sheets (the union equals the symmetric sheet
        for both sexes);
      * weight = the symmetric-sheet value when present (SI9 weight =
        total EM serial sections, extrapolation included — matches the
        SI7 section sums for 795/948 EM-verified herm pairs, the rest
        by extrapolation), else the asymmetric value;
      * every disagreement is recorded in the record and counted in
        the stats (herm: 0; male: 1, (VB06, VB07) sym 5 / asym 1).
    The SI7 synapse list is the physical ground truth used for the
    cross-check (EM-verified vs extrapolation-only pairs).
    """
    sym, asym = {}, {}
    for e in edges:
        a, b = e["pre"], e["post"]
        if a not in neuron_names or b not in neuron_names:
            continue
        k = tuple(sorted((a, b)))
        if e["kind"] == "gap_sym":
            sym[k] = max(sym.get(k, 0), e["w"])
        elif e["kind"] == "gap_asym":
            asym.setdefault(k, []).append((a, b, e["w"]))
    union = sorted(set(sym) | set(asym))
    out, disagreements = [], []
    for a, b in union:
        ws = sym.get((a, b))
        dirs = asym.get((a, b), [])
        w = ws if ws is not None else dirs[0][2]
        if ws is not None and dirs and ws != dirs[0][2]:
            disagreements.append([a, b, int(ws), [int(x[2]) for x in dirs]])
        s7 = si7_pairs.get((a, b))
        out.append({
            "pre": a, "post": b, "w": int(w),
            "w_sym": int(ws) if ws is not None else None,
            "w_asym": [int(x[2]) for x in dirs] or None,
            "directions": [[p, d] for p, d, _ in dirs] or None,
            "si7_synapses": int(s7[0]) if s7 else None,
            "si7_sections": int(s7[1]) if s7 else None,
        })
    em = [r for r in out if r["si7_synapses"]]
    ext = [r for r in out if not r["si7_synapses"]]
    si7_nn = {k: v for k, v in si7_pairs.items()
              if k[0] in neuron_names and k[1] in neuron_names
              and k[0] != k[1]}
    outside = sorted(k for k in si7_nn if k not in set(union))
    wt_eq = sum(1 for r in em if r["si7_sections"] == r["w"])
    wt_gt = sum(1 for r in em if r["si7_sections"] < r["w"])
    wt_lt = sum(1 for r in em if r["si7_sections"] > r["w"])
    stats = {
        "sym_pairs": len(sym),
        "asym_records": sum(len(v) for v in asym.values()),
        "asym_pairs": len(asym),
        "overlap_pairs": len(set(sym) & set(asym)),
        "sym_only_pairs": sorted([list(k) for k in set(sym) - set(asym)]),
        "asym_only_pairs": sorted([list(k) for k in set(asym) - set(sym)]),
        "canonical_junctions": len(union),
        "pairs_with_two_directed_records":
            sum(1 for v in asym.values() if len(v) > 1),
        "weight_disagreements": disagreements,
        "si7": si7_stats,
        "si7_em_verified_in_union": len(em),
        "si7_extrapolation_only_in_union": len(ext),
        "si7_pairs_outside_union": [list(k) for k in outside],
        "weight_vs_si7_sections": {"equal": wt_eq, "si9_higher": wt_gt,
                                   "si9_lower": wt_lt},
    }
    return out, stats


def main(data_dir):
    si9 = load_xlsx(data_dir + "/Cook2019_SI9_connectome-matrices.xlsx")
    si6 = load_xlsx(data_dir + "/Cook2019_SI6_raw-adjacency.xlsx")
    cells = parse_cell_lists(data_dir + "/Cook2019_SI8_cell-lists.xlsx")

    inv = {"cell_lists": {
        "shared": sum(1 for c, s in cells.values() if s == "shared"),
        "herm_specific": sum(1 for c, s in cells.values() if s == "herm"),
        "male_specific": sum(1 for c, s in cells.values() if s == "male"),
        "neuron_categories": {
            cat: sum(1 for c, _ in cells.values() if c == cat)
            for cat in sorted(set(c for c, _ in cells.values()))},
    }}

    si9_sheets = {
        "herm": {
            "chem": ("hermaphrodite chemical", "directed"),
            "gap_sym": ("herm gap jn symmetric", "symmetric"),
            "gap_asym": ("herm gap jn asymmetric", "directed"),
        },
        "male": {
            "chem": ("male chemical", "directed"),
            "gap_sym": ("male gap jn symmetric", "symmetric"),
            "gap_asym": ("male gap jn asymmetric", "directed"),
        },
    }

    for sex in ("herm", "male"):
        neuron_names = {n for n in cells
                        if is_neuron(n, cells)
                        and (cells[n][1] in ("shared", sex))}
        edges, stats = [], {"sheets": {}, "neurons_in_lists": len(neuron_names)}
        for key, (sheetname, kind) in si9_sheets[sex].items():
            cols, M, st = parse_matrix(si9[sheetname])
            nodes = set(cols)
            diag = 0
            asym = 0
            kept = 0
            nonnumeric = 0
            for pre, row in M.items():
                if pre not in nodes:
                    continue
                for post, v in row.items():
                    if post not in nodes:
                        continue
                    if pre == post:
                        diag += 1
                        continue
                    iv = int(v) if v.isdigit() else 0
                    if iv == 0:
                        nonnumeric += 1
                        continue
                    if kind == "symmetric" and pre > post:
                        # undirected: the pair may live in either triangle;
                        # handled in a second pass after both directions are
                        # seen (see below)
                        continue
                    if kind == "symmetric":
                        other = M.get(post, {}).get(pre, "0")
                        io = int(other) if other.isdigit() else 0
                        if io and io != iv:
                            asym += 1
                        iv = max(iv, io)
                    kept += 1
                    edges.append({"pre": pre, "post": post, "w": iv,
                                  "kind": key})
            if kind == "symmetric":
                # pairs present only in the lower triangle (pre > post) were
                # skipped above; recover them so no record is lost
                seen_pairs = {(e["pre"], e["post"]) for e in edges
                              if e["kind"] == key}
                for pre, row in M.items():
                    if pre not in nodes:
                        continue
                    for post, v in row.items():
                        if post not in nodes or pre <= post or pre == post:
                            continue
                        if (post, pre) in seen_pairs:
                            continue
                        iv = int(v) if v.isdigit() else 0
                        if iv == 0:
                            nonnumeric += 1
                            continue
                        other = M.get(pre, {}).get(post, "0")
                        io = int(other) if other.isdigit() else 0
                        if io and io != iv:
                            asym += 1
                        iv = max(iv, io)
                        kept += 1
                        edges.append({"pre": post, "post": pre, "w": iv,
                                      "kind": key})
                        seen_pairs.add((post, pre))
            stats["sheets"][key] = {
                "sheet": sheetname, "mode": kind,
                "nodes_in_columns": len(nodes),
                "rows_named": sum(1 for r in M if r in nodes),
                "nonzero_entries_neuron_to_node": kept,
                "non_numeric_entries_skipped": nonnumeric,
                "diagonal_entries_zeroed": diag,
                "symmetry_disagreements": asym if kind == "symmetric" else None,
                "parse": st,
            }
        # neuron-only chemical + electrical edge lists
        nn = [e for e in edges if is_neuron(e["pre"], cells)
              and is_neuron(e["post"], cells)]
        for k in ("chem", "gap_sym", "gap_asym"):
            sub = [e for e in nn if e["kind"] == k]
            stats["neuron_only_" + k] = len(sub)
        stats["neuron_only_total"] = len(nn)
        stats["dropped_non_neuron_edges"] = len(edges) - len(nn)
        inv[sex] = stats
        with open(data_dir + "/c-elegans-edges-%s.json" % sex, "w") as f:
            json.dump([{"pre": e["pre"], "post": e["post"],
                        "w": e["w"], "kind": e["kind"]}
                       for e in nn], f, indent=0)
        # canonical electrical graph (one record per physical junction)
        sheet = "hermaphrodite" if sex == "herm" else "male"
        si7_pairs, si7_stats = electrical_si7(data_dir, sheet)
        canon, cstats = canonical_electrical(
            [e for e in nn if e["kind"] in ("gap_sym", "gap_asym")],
            neuron_names, si7_pairs, si7_stats)
        with open(data_dir + "/c-elegans-electrical-%s.json" % sex, "w") as f:
            json.dump(canon, f, indent=0)
        stats["electrical_canonical"] = cstats
        # neuron names used by the simulation
        names = sorted(n for n in neuron_names
                       if any(e["pre"] == n or e["post"] == n for e in nn))
        with open(data_dir + "/c-elegans-neurons-%s.json" % sex, "w") as f:
            json.dump(names, f, indent=1)
        stats["sim_neurons"] = len(names)

    with open(data_dir + "/c-elegans-inventory.json", "w") as f:
        json.dump(inv, f, indent=1)
    print(json.dumps(inv, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
