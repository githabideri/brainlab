"""Invariants tests for the corrected substrate and the exact-invariant
shuffle (2026-10-13 correction of the 2026-10-12 pilot, see
reports/2026-10-12-worm-pilot.md addendum).

Run:  python src/test_invariants.py
Exit 0 = all invariants hold; non-zero = an invariant is violated.

The review findings that these tests re-assert:
  1. the parsed workbook has NO self-edges and NO shifted values
     (cross-validated against the independent SI6 raw-adjacency book);
  2. the CANONICAL electrical graph (review round 5: the two SI9
     gap-junction sheets are alternative representations of the same
     physical junctions) is well-formed — sheet-relationship findings
     (overlap, weight agreement, sym-only pairs, the one male weight
     disagreement) and the SI7 synapse-list cross-check (EM-verified
     vs extrapolation-only) are asserted;
  3. the shuffle preserves every invariant exactly (chemical record
     counts and per-neuron in-/out-degree; the SINGLE canonical
     junction layer: junction count, per-neuron junction degree,
     weight multiset; total edge count) with ZERO residual
     self-edges — no drops;
  4. the shuffle is deterministic in its seed and differs across seeds.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from sim import load_network, make_shuffled_exact, _degvec  # noqa: E402
from parse_cook2019 import load_xlsx, parse_matrix, parse_cell_lists, \
    is_neuron  # noqa: E402

DATA = os.path.join(HERE, "..", "data")
FAILS = []


def check(name, cond, detail=""):
    print(f"  [{'ok' if cond else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def test_parsed_substrate():
    print("parsed substrate")
    for sex in ("herm", "male"):
        edges = json.load(open(f"{DATA}/c-elegans-edges-{sex}.json"))
        check(f"{sex}: no self-edges",
              all(e["pre"] != e["post"] for e in edges),
              f"{sum(e['pre'] == e['post'] for e in edges)} self-edges found")
    # SI6 raw-adjacency cross-validation (independent second book)
    si9 = load_xlsx(f"{DATA}/Cook2019_SI9_connectome-matrices.xlsx")
    si6 = load_xlsx(f"{DATA}/Cook2019_SI6_raw-adjacency.xlsx")
    cells = parse_cell_lists(f"{DATA}/Cook2019_SI8_cell-lists.xlsx")
    for sex, a, b in (("herm", "hermaphrodite chemical",
                       "herm chem synapse adjacency"),
                      ("male", "male chemical",
                       "male chem synapse adjacency")):
        ns = {x for x in cells if is_neuron(x, cells)
              and cells[x][1] in ("shared", sex)}
        _, M9, _ = parse_matrix(si9[a])
        _, M6, _ = parse_matrix(si6[b])
        p9 = {(p, o) for p, r in M9.items() for o in r if p in ns and o in ns
              and p != o}
        p6 = {(p, o) for p, r in M6.items() for o in r if p in ns and o in ns
              and p != o}
        overlap = len(p9 & p6) / max(1, len(p6))
        check(f"{sex}: SI6 raw-adjacency pair overlap >= 99%", overlap >= 0.99,
              f"overlap {overlap:.3f} ({len(p9 & p6)}/{len(p6)})")




def test_canonical_electrical():
    print("canonical electrical graph (review round 5)")
    for sex in ("herm", "male"):
        edges = json.load(open(f"{DATA}/c-elegans-edges-{sex}.json"))
        canon = json.load(open(f"{DATA}/c-elegans-electrical-{sex}.json"))
        st = json.load(open(f"{DATA}/c-elegans-inventory.json"))[
            sex]["electrical_canonical"]
        sym = {tuple(sorted((e["pre"], e["post"])))
               for e in edges if e["kind"] == "gap_sym"}
        asym = {tuple(sorted((e["pre"], e["post"])))
                for e in edges if e["kind"] == "gap_asym"}
        check(f"{sex}: canonical file sorted, no self-edges, w>0",
              all(r["pre"] < r["post"] for r in canon)
              and all(r["w"] > 0 for r in canon))
        check(f"{sex}: canonical = union of the two sheets",
              st["canonical_junctions"] == len(sym | asym)
              and {tuple(sorted((r["pre"], r["post"])))
                   for r in canon} == (sym | asym))
        check(f"{sex}: asym sheet is a subset of the sym sheet "
              f"(unordered pairs), no asym-only pairs",
              st["overlap_pairs"] == st["asym_pairs"] == len(asym & sym)
              and st["asym_only_pairs"] == [])
        check(f"{sex}: weight disagreements counted (herm 0, male 1)",
              (len(st["weight_disagreements"]) == 0 if sex == "herm"
               else len(st["weight_disagreements"]) == 1))
        check(f"{sex}: SI7 cross-check non-vacuous "
              f"(EM-verified and extrapolation-only both present)",
              st["si7_em_verified_in_union"] > 0
              and st["si7_extrapolation_only_in_union"] > 0)
        check(f"{sex}: SI7 weight-relation accounting complete",
              sum(st["weight_vs_si7_sections"].values())
              == st["si7_em_verified_in_union"])
    cfg = json.load(open(f"{HERE}/../config-5ms.json"))
    net = load_network(DATA, cfg)
    canon = json.load(open(f"{DATA}/c-elegans-electrical-herm.json"))
    check("herm: loaded conductance layer = canonical file "
          "(one record per junction, both directions)",
          len(net["g_pairs"]) == len(canon)
          and len(net["g_src"]) == 2 * len(canon))
    gdeg = np.zeros(net["n"], dtype=np.int64)
    for a, b, _ in net["g_pairs"]:
        gdeg[a] += 1
        gdeg[b] += 1
    print(f"  herm: {len(net['g_pairs'])} canonical junctions, "
          f"mean junction degree {gdeg.mean():.2f}")


def test_shuffle_invariants():
    print("make_shuffled_exact invariants (herm, seeds 42/43/44)")
    cfg = json.load(open(f"{HERE}/../config-5ms.json"))
    net = load_network(DATA, cfg)
    measured = {"chem": len(net["c_src"]), "elec": len(net["g_pairs"])}
    print(f"  measured: {measured} (total {sum(measured.values())})")
    for seed in (42, 43, 44):
        shuf, inv = make_shuffled_exact(net, cfg, seed)
        c = inv["classes"]
        print(f"  seed {seed}: "
              + ", ".join(f"{k}={v['records_measured']}/{v['records_shuffled']}"
                          for k, v in c.items()))
        check(f"seed {seed}: chemical counts exact",
              c["chemical"]["records_measured"]
              == c["chemical"]["records_shuffled"] == measured["chem"])
        check(f"seed {seed}: canonical electrical count exact",
              c["electrical"]["records_measured"]
              == c["electrical"]["records_shuffled"] == measured["elec"])
        check(f"seed {seed}: zero residual self-edges (all classes)",
              all(c[k]["self_edges_residual"] == 0 for k in c))
        check(f"seed {seed}: degree vectors exact (max abs diff 0)",
              c["chemical"]["out_degree_max_abs_diff"] == 0
              and c["chemical"]["in_degree_max_abs_diff"] == 0
              and c["electrical"]["degree_max_abs_diff"] == 0)
        check(f"seed {seed}: weight multisets identical (all classes)",
              all(c[k]["multiset_equal"] for k in c))
        check(f"seed {seed}: total edge count preserved",
              inv["total_edges"]["measured"] == inv["total_edges"]["shuffled"])
        # independent recomputation (not the function's own report)
        check(f"seed {seed}: recompute — shuffled has no self-edges",
              not (shuf["c_src"] == shuf["c_dst"]).any()
              and not (shuf["g_src"] == shuf["g_dst"]).any())
        check(f"seed {seed}: recompute — shuffled chemical degrees "
              f"equal measured",
              np.array_equal(_degvec(shuf["c_src"], net["n"]),
                             _degvec(net["c_src"], net["n"]))
              and np.array_equal(_degvec(shuf["c_dst"], net["n"]),
                                 _degvec(net["c_dst"], net["n"])))
        gdeg_m = np.zeros(net["n"], dtype=np.int64)
        for a, b, _ in net["g_pairs"]:
            gdeg_m[a] += 1
            gdeg_m[b] += 1
        gdeg_s = np.zeros(net["n"], dtype=np.int64)
        for a, b, _ in shuf["g_pairs"]:
            gdeg_s[a] += 1
            gdeg_s[b] += 1
        check(f"seed {seed}: recompute — shuffled junction degrees "
              f"equal measured",
              np.array_equal(gdeg_s, gdeg_m))
        w_m = np.sort([p[2] for p in net["g_pairs"]])
        w_s = np.sort([p[2] for p in shuf["g_pairs"]])
        check(f"seed {seed}: recompute — electrical weight multiset "
              f"equal",
              np.array_equal(w_m, w_s))


def test_shuffle_determinism():
    print("determinism")
    cfg = json.load(open(f"{HERE}/../config-5ms.json"))
    net = load_network(DATA, cfg)
    s42a, _ = make_shuffled_exact(net, cfg, 42)
    s42b, _ = make_shuffled_exact(net, cfg, 42)
    s43, _ = make_shuffled_exact(net, cfg, 43)
    check("same seed -> identical shuffle",
          np.array_equal(s42a["c_dst"], s42b["c_dst"])
          and s42a["g_pairs"] == s42b["g_pairs"]
          and np.array_equal(s42a["g_w"], s42b["g_w"]))
    check("different seeds -> different shuffles",
          not np.array_equal(s42a["c_dst"], s43["c_dst"])
          or s42a["g_pairs"] != s43["g_pairs"])


if __name__ == "__main__":
    test_parsed_substrate()
    test_canonical_electrical()
    test_shuffle_invariants()
    test_shuffle_determinism()
    if FAILS:
        print(f"\n{len(FAILS)} invariant(s) FAILED: {FAILS}")
        sys.exit(1)
    print("\nall invariants hold")
