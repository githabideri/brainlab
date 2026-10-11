"""Deterministic control-wiring generators for A-01.

Each control is a pure function of (fly edge arrays, its recorded numpy
seed) — rebuilding reproduces it byte-identically (the edge arrays'
sha256 is recorded in the manifest). Every generator asserts its
preserved invariants before returning, and records what it preserves
and what it deliberately breaks (the control taxonomy in
docs/architecture.md, instantiated per row in the experiment README).

All controls preserve per-node in/out degree exactly and the edge
count, and never emit a self-loop:

  degree      independent permutations of the source and target arrays.
              Breaks: which source→target each edge is, per-source
              magnitude profile, per-node E/I balance.
  sign        pairwise target swaps restricted to SAME-sign pairs.
              Preserves additionally: per-node E/I balance (in and out)
              and the per-source outgoing magnitude multiset (magnitudes
              travel with their source).
  weight      unrestricted pairwise target swaps.
              Preserves additionally: the per-edge magnitude multiset
              (global and per-source outgoing; magnitudes travel with
              their source). Breaks: per-node E/I balance.
  population  per (src-group, tgt-group) block: independent permutations
              of sources and targets inside the block.
              Preserves additionally: per population-pair edge counts
              and per-block magnitude multisets.
  disconnected  no edges (nodes only).
"""
from __future__ import annotations

import hashlib

import numpy as np

# one recorded numpy seed per control
SEEDS = {
    "degree": 20261013,
    "sign": 20261014,
    "weight": 20261015,
    "population": 20261016,
}

MAX_ATTEMPTS_FACTOR = 50  # per desired swap (conflict retries)


def from_doc(doc: dict):
    """(src, tgt, w) numpy arrays from the atlas (the fly wiring)."""
    e = np.asarray(doc["edges"], dtype=np.int64)
    return e[:, 0].copy(), e[:, 1].copy(), e[:, 2].astype(np.float64).copy()


def edge_sha256(src, tgt, w) -> str:
    b = np.concatenate([src, tgt]).astype(np.int64).tobytes() + np.asarray(w, np.float64).tobytes()
    return hashlib.sha256(b).hexdigest()


def _deg(src, tgt, n):
    return np.bincount(src, minlength=n), np.bincount(tgt, minlength=n)


def _assert_common(src, tgt, w, orig_src, orig_tgt, orig_w, n):
    assert len(src) == len(orig_src), "edge count changed"
    assert not (src == tgt).any(), "control emitted a self-loop"
    o_out, o_in = _deg(orig_src, orig_tgt, n)
    n_out, n_in = _deg(src, tgt, n)
    assert (o_out == n_out).all(), "per-node out-degree changed"
    assert (o_in == n_in).all(), "per-node in-degree changed"
    assert np.array_equal(np.sort(orig_w), np.sort(w)), "magnitude multiset changed"


def _assert_sign_balance(src, tgt, w, orig_src, orig_tgt, orig_w, n):
    ooe = orig_w < 0
    ne = w < 0
    assert (np.bincount(orig_src[ooe], minlength=n) == np.bincount(src[ne], minlength=n)).all(), \
        "per-source outgoing inhibitory count changed"
    assert (np.bincount(orig_tgt[ooe], minlength=n) == np.bincount(tgt[ne], minlength=n)).all(), \
        "per-target incoming inhibitory count changed"


def _assert_source_magnitude_profile(src, w, orig_src, orig_w):
    """Per source node: the sorted multiset of outgoing magnitudes is unchanged."""
    o = np.argsort(orig_src, kind="stable")
    c = np.argsort(src, kind="stable")
    starts = np.searchsorted(c, np.arange(len(src) + 1))
    for a, b in zip(np.split(orig_w[o], starts[1:-1]), np.split(w[c], starts[1:-1])):
        if len(a) and not np.array_equal(np.sort(a), np.sort(b)):
            raise AssertionError("per-source outgoing magnitude multiset changed")


def _repair_self_loops(src, tgt, pool, rng) -> int:
    """Fix self-loops by SWAPPING target values within `pool` (a target-value
    permutation, so all degree invariants survive). Returns swaps made."""
    swaps = 0
    for k in np.flatnonzero(src == tgt):
        found = False
        for j in pool:
            if j == k:
                continue
            if src[k] != tgt[j] and src[j] != tgt[k]:
                tgt[k], tgt[j] = tgt[j], tgt[k]
                found = True
                swaps += 1
                break
        if not found:
            raise AssertionError(f"cannot repair self-loop at edge {k} without breaking degrees")
    return swaps


def _pair_swaps(orig_src, orig_tgt, orig_w, seed, same_sign_only) -> tuple:
    """K = E target swaps between random edge pairs (sign-restricted if asked).

    (s1->t1, s2->t2) becomes (s1->t2, s2->t1); magnitudes travel with
    their source. A swap is skipped when it would create a self-loop.
    """
    E = len(orig_src)
    src, tgt = orig_src.copy(), orig_tgt.copy()
    rng = np.random.default_rng(seed)
    neg_idx = np.where(orig_w < 0)[0]
    pos_idx = np.where(orig_w >= 0)[0]
    applied = attempts = 0
    while applied < E and attempts < MAX_ATTEMPTS_FACTOR * E:
        attempts += 1
        pool = neg_idx if (same_sign_only and bool(rng.integers(2))) else (
            pos_idx if same_sign_only else np.arange(E))
        i, j = rng.choice(pool, size=2, replace=False)
        if i == j:
            continue
        # prospective self-loops: src[i]==tgt[j] or src[j]==tgt[i]
        if src[i] == tgt[j] or src[j] == tgt[i]:
            continue
        tgt[i], tgt[j] = tgt[j], tgt[i]
        applied += 1
    assert applied == E, f"only {applied}/{E} swaps applied (conflict-retry exhausted)"
    return src, tgt, orig_w.copy()


def make_degree(doc: dict, n: int, seed: int | None = None):
    seed = seed if seed is not None else SEEDS["degree"]
    src, tgt, w = from_doc(doc)
    E = len(src)
    rng = np.random.default_rng(seed)
    src2 = src[rng.permutation(E)]
    tgt2 = tgt[rng.permutation(E)]
    _repair_self_loops(src2, tgt2, np.arange(E), rng)
    _assert_common(src2, tgt2, w, src, tgt, w, n)
    record = {
        "control": "degree", "seed": seed,
        "preserves": ["per-node in/out degree", "edge count", "edge-magnitude multiset"],
        "breaks": ["specific source->target pairing", "per-source magnitude profile",
                    "per-node E/I balance"],
        "edge_sha256": edge_sha256(src2, tgt2, w),
    }
    return src2, tgt2, w, record


def make_sign(doc: dict, n: int, seed: int | None = None):
    seed = seed if seed is not None else SEEDS["sign"]
    src, tgt, w = from_doc(doc)
    src2, tgt2, w2 = _pair_swaps(src, tgt, w, seed, same_sign_only=True)
    _assert_common(src2, tgt2, w2, src, tgt, w, n)
    _assert_sign_balance(src2, tgt2, w2, src, tgt, w, n)
    _assert_source_magnitude_profile(src2, w2, src, w)
    record = {
        "control": "sign", "seed": seed,
        "preserves": ["per-node in/out degree", "edge count", "per-node E/I balance (in and out)",
                      "per-source outgoing magnitude multiset"],
        "breaks": ["specific source->target pairing"],
        "edge_sha256": edge_sha256(src2, tgt2, w2),
    }
    return src2, tgt2, w2, record


def make_weight(doc: dict, n: int, seed: int | None = None):
    seed = seed if seed is not None else SEEDS["weight"]
    src, tgt, w = from_doc(doc)
    src2, tgt2, w2 = _pair_swaps(src, tgt, w, seed, same_sign_only=False)
    _assert_common(src2, tgt2, w2, src, tgt, w, n)
    _assert_source_magnitude_profile(src2, w2, src, w)
    record = {
        "control": "weight", "seed": seed,
        "preserves": ["per-node in/out degree", "edge count",
                      "per-edge magnitude multiset (global and per-source outgoing)"],
        "breaks": ["specific source->target pairing of strong edges", "per-node E/I balance"],
        "edge_sha256": edge_sha256(src2, tgt2, w2),
    }
    return src2, tgt2, w2, record


def make_population(doc: dict, groups, n: int, seed: int | None = None):
    """groups: per-neuron atlas group id (array len n)."""
    seed = seed if seed is not None else SEEDS["population"]
    src, tgt, w = from_doc(doc)
    src2, tgt2 = src.copy(), tgt.copy()
    rng = np.random.default_rng(seed)
    pairs = np.stack([groups[src], groups[tgt]])
    for block in np.unique(pairs, axis=1):
        mask = (groups[src] == block[0]) & (groups[tgt] == block[1])
        idx = np.flatnonzero(mask)
        if len(idx) < 2:
            continue
        src2[idx] = src[idx][rng.permutation(len(idx))]
        tgt2[idx] = tgt[idx][rng.permutation(len(idx))]
        _repair_self_loops(src2, tgt2, idx, rng)
    _assert_common(src2, tgt2, w, src, tgt, w, n)
    for block in np.unique(pairs, axis=1):
        o_c = int(((groups[src] == block[0]) & (groups[tgt] == block[1])).sum())
        n_c = int(((groups[src2] == block[0]) & (groups[tgt2] == block[1])).sum())
        assert o_c == n_c, "per population-pair edge count changed"
    record = {
        "control": "population", "seed": seed,
        "preserves": ["per-node in/out degree", "edge count",
                      "per population-pair edge counts", "per-block magnitude multiset"],
        "breaks": ["node-level source->target pairing", "per-node E/I balance"],
        "edge_sha256": edge_sha256(src2, tgt2, w),
    }
    return src2, tgt2, w, record


def make_disconnected(doc: dict, n: int):
    z = np.zeros(0, dtype=np.int64)
    record = {
        "control": "disconnected", "seed": None,
        "preserves": ["nodes only"],
        "breaks": ["all edges (the readout sees no circuit activity -> majority-class floor)"],
        "edge_sha256": edge_sha256(z, z, np.zeros(0, np.float64)),
    }
    return z, z, np.zeros(0, np.float64), record


GENERATORS = {
    "degree": make_degree,
    "sign": make_sign,
    "weight": make_weight,
}


def build_controls(doc: dict, groups, n: int) -> dict:
    """All A-01 controls: name -> (src, tgt, w, record)."""
    out = {}
    for name, gen in GENERATORS.items():
        out[name] = gen(doc, n)
    out["population"] = make_population(doc, groups, n)
    out["disconnected"] = make_disconnected(doc, n)
    for name, (_, _, _, rec) in out.items():
        print(f"control {name:<13} seed={rec['seed']} edges={rec['edge_sha256'][:16]}… "
              f"preserves={rec['preserves']}", flush=True)
    return out
