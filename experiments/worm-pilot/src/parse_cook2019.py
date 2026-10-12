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
inconsistent (one stray banner/empty column here, two there). The parser
detects the label row (the row containing 'I1L') and the name column
(from the I1L data row) per sheet, then maps data columns to labels with
the resulting offset. Residual artifacts are handled explicitly and
counted, not silently dropped:

  * region-banner rows and count rows are skipped (they never name a cell)
  * self-connections are zeroed (C. elegans neurons do not synapse onto
    themselves; non-zero diagonal entries are workbook shift artifacts)
  * for the 'gap jn symmetric' sheets the two triangles of the matrix do
    not agree everywhere; the value is symmetrised by taking the max and
    disagreements are counted
  * a row that repeats the header (trailing block) terminates the sheet

Outputs (JSON, stable schema):
  data/c-elegans-edges-<sex>.json   neuron-only edge lists
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


def load_xlsx(path):
    z = zipfile.ZipFile(path)
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        r = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in r.findall(NS + "si"):
            ss.append("".join(t.text or "" for t in si.iter(NS + "t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheets = [s.get("name") for s in wb.find(NS + "sheets")]
    out = {}
    for i, name in enumerate(sheets, 1):
        r = ET.fromstring(z.read("xl/worksheets/sheet%d.xml" % i))
        rows = []
        for row in r.iter(NS + "row"):
            vals = []
            for c in row.findall(NS + "c"):
                v = c.find(NS + "v")
                if v is None:
                    t = c.find(NS + "is")
                    vals.append("".join(x.text or "" for x in t.iter(NS + "t"))
                                if t is not None else "")
                else:
                    vals.append(ss[int(v.text)] if c.get("t") == "s" else v.text)
            rows.append([str(x).strip() for x in vals])
        out[name] = rows
    return out


def parse_matrix(sheet):
    """Return (cols, M, stats) for one adjacency-matrix sheet.

    cols: ordered column (postsynaptic) node names.
    M: {presynaptic name: {postsynaptic name: value(str)}} for rows that
       name a real cell.
    """
    rows = sheet
    nrow = next(i for i, r in enumerate(rows[:6])
                if "I1L" in [c.strip() for c in r])
    k0 = next(i for i, c in enumerate(rows[nrow]) if c.strip() == "I1L")
    cols = [c.strip() for c in rows[nrow][k0:]]
    namecol = None
    for r in rows[nrow + 1:]:
        cells = [c.strip() for c in r]
        if "I1L" in cells:
            namecol = cells.index("I1L")
            break
    if namecol is None:
        raise ValueError("no I1L data row found")
    M, stats = {}, {"rows_seen": 0, "rows_skipped_banner": 0,
                    "rows_skipped_number": 0, "rows_skipped_noname": 0,
                    "header_repeat_rows": 0}
    for r in rows[nrow + 1:]:
        cells = [c.strip() for c in r]
        nm = cells[namecol] if namecol < len(cells) else ""
        nonempty = [c for c in cells if c]
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
        if nm == "I1L" and len(nonempty) >= 20:
            stats["header_repeat_rows"] += 1
            break
        M[nm] = {}
        for j, v in enumerate(cells[namecol + 1:]):
            li = k0 + (j - namecol - 1)
            if 0 <= li < len(cols) and v:
                M[nm][cols[li]] = v
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
            cells = [c.strip() for c in r]
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
                    if kind == "symmetric":
                        if pre > post:  # undirected edge, keep one direction
                            continue
                        other = M.get(post, {}).get(pre, "0")
                        io = int(other) if other.isdigit() else 0
                        if io and io != iv:
                            asym += 1
                        iv = max(iv, io)
                    kept += 1
                    edges.append({"pre": pre, "post": post, "w": iv,
                                  "kind": key})
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
