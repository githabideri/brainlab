"""Invariants tests for the corrected substrate and the exact-invariant
shuffle (2026-10-13 correction of the 2026-10-12 pilot, see
reports/2026-10-12-worm-pilot.md addendum).

Run:  python src/test_invariants.py
Exit 0 = all invariants hold; non-zero = an invariant is violated.

The three review findings that these tests re-assert:
  1. the parsed workbook has NO self-edges and NO shifted values
     (cross-validated against the independent SI6 raw-adjacency book);
  2. the shuffle preserves every invariant exactly (record counts per
     junction class, per-neuron degree vectors, weight multisets,
     total edge count) with ZERO residual self-edges — no drops;
  3. the shuffle is deterministic in its seed and differs across seeds.
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


def test_shuffle_invariants():
    print("make_shuffled_exact invariants (herm, seeds 42/43/44)")
    cfg = json.load(open(f"{HERE}/../config-5ms.json"))
    net = load_network(DATA, cfg)
    measured = {"chem": len(net["c_src"]),
                "asym": len(net["g_asym_pairs"]),
                "sym": len(net["g_sym_pairs"])}
    print(f"  measured: {measured} (total {sum(measured.values())})")
    for seed in (42, 43, 44):
        shuf, inv = make_shuffled_exact(net, cfg, seed)
        c = inv["classes"]
        print(f"  seed {seed}: "
              + ", ".join(f"{k}={v['records_measured']}/{v['records_shuffled']}"
                          for k, v in c.items()))
        check(f"seed {seed}: chemical counts exact",
              c["chemical"]["records_measured"] == c["chemical"]["records_shuffled"]
              == measured["chem"])
        check(f"seed {seed}: asym counts exact",
              c["electrical_asymmetric"]["records_measured"]
              == c["electrical_asymmetric"]["records_shuffled"] == measured["asym"])
        check(f"seed {seed}: sym counts exact",
              c["electrical_symmetric"]["records_measured"]
              == c["electrical_symmetric"]["records_shuffled"] == measured["sym"])
        check(f"seed {seed}: zero residual self-edges (all classes)",
              all(c[k]["self_edges_residual"] == 0 for k in c))
        check(f"seed {seed}: degree vectors exact (max abs diff 0)",
              c["chemical"]["out_degree_max_abs_diff"] == 0
              and c["chemical"]["in_degree_max_abs_diff"] == 0
              and c["electrical_asymmetric"]["out_degree_max_abs_diff"] == 0
              and c["electrical_asymmetric"]["in_degree_max_abs_diff"] == 0
              and c["electrical_symmetric"]["degree_max_abs_diff"] == 0)
        check(f"seed {seed}: weight multisets identical (all classes)",
              all(c[k]["multiset_equal"] for k in c))
        check(f"seed {seed}: total edge count preserved",
              inv["total_edges"]["measured"] == inv["total_edges"]["shuffled"])
        # independent recomputation (not the function's own report)
        check(f"seed {seed}: recompute — shuffled has no self-edges",
              not (shuf["c_src"] == shuf["c_dst"]).any()
              and not (shuf["g_src"] == shuf["g_dst"]).any())
        check(f"seed {seed}: recompute — shuffled degrees equal measured",
              np.array_equal(_degvec(shuf["c_src"], net["n"]),
                             _degvec(net["c_src"], net["n"]))
              and np.array_equal(_degvec(shuf["c_dst"], net["n"]),
                                 _degvec(net["c_dst"], net["n"])))
        a_m = np.sort(np.asarray(net["g_asym_pairs"], dtype=object)
                      .astype(np.float64).ravel())
        a_s = np.sort(np.asarray(shuf["g_asym_pairs"], dtype=object)
                      .astype(np.float64).ravel())
        check(f"seed {seed}: recompute — asym weight multiset equal",
              np.array_equal(a_m, a_s))


def test_shuffle_determinism():
    print("determinism")
    cfg = json.load(open(f"{HERE}/../config-5ms.json"))
    net = load_network(DATA, cfg)
    s42a, _ = make_shuffled_exact(net, cfg, 42)
    s42b, _ = make_shuffled_exact(net, cfg, 42)
    s43, _ = make_shuffled_exact(net, cfg, 43)
    check("same seed -> identical shuffle",
          np.array_equal(s42a["c_dst"], s42b["c_dst"])
          and s42a["g_sym_pairs"] == s42b["g_sym_pairs"]
          and np.array_equal(s42a["g_w"], s42b["g_w"]))
    check("different seeds -> different shuffles",
          not np.array_equal(s42a["c_dst"], s43["c_dst"])
          or s42a["g_sym_pairs"] != s43["g_sym_pairs"])


if __name__ == "__main__":
    test_parsed_substrate()
    test_shuffle_invariants()
    test_shuffle_determinism()
    if FAILS:
        print(f"\n{len(FAILS)} invariant(s) FAILED: {FAILS}")
        sys.exit(1)
    print("\nall invariants hold")
