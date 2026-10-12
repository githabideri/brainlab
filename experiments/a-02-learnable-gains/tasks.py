"""Generated multi-class odor-discrimination tasks for A-02.

Copied verbatim (code unchanged) from ../a-01-connectome-advantage/tasks.py
so A-02's numbers are directly comparable to A-01's: same master seed
20261012, same prototypes, same held-out sets, same noise levels and
fixed noise realizations.

DECLARED GENERATED (docs/evaluation.md rule 5): no recorded data is
used. An "odor" is a 16-d vector: per class c a prototype
p_c = g_c * u_c (random unit direction u_c, random norm g_c in
U[2.5, 3.5]); an instance x = p_c + N(0, 0.75^2 * I16).

Everything below is a pure function of MASTER_SEED: the prototypes,
the instance labels, the train/test split, the training order used for
the 10%/50% data-efficiency fractions, and the fixed per-(task, level)
test-noise realizations — all identical for every model arm.
"""
from __future__ import annotations

import numpy as np

MASTER_SEED = 20261012
STATE_DIM = 16
GEN_NOISE = 0.75          # per-dim generation noise (part of the stimulus)
NOISE_LEVELS = (0.0, 0.75, 1.5)   # added at evaluation; "clean/mid/max"
NOISE_NOISE_SEED = 20261012 + 1000


def generate_task(n_classes: int, n_total: int = 2048) -> dict:
    """One generated task: prototypes, instances, split, noise realizations.

    Returns a dict with:
      x (n_total, 16) float32, y (n_total,) int
      train_idx, test_idx  (disjoint; the test half is the held-out set)
      train_order          (master-seed permutation of train_idx; the 50%/10%
                           training fractions are fixed prefixes of it)
      noise[level] (n_test, 16) float32  — one fixed realization per level
      class_counts (n_classes,)
    """
    g = np.random.default_rng(MASTER_SEED + n_classes * 7919)
    protos = np.zeros((n_classes, STATE_DIM), dtype=np.float64)
    for c in range(n_classes):
        u = g.standard_normal(STATE_DIM)
        u /= np.linalg.norm(u)
        protos[c] = g.uniform(2.5, 3.5) * u
    # balanced labels, one block per class, then a master-seed shuffle
    labels = np.repeat(np.arange(n_classes), n_total // n_classes)
    if len(labels) < n_total:
        labels = np.append(labels, g.integers(0, n_classes, n_total - len(labels)))
    x = np.zeros((n_total, STATE_DIM), dtype=np.float32)
    for c in range(n_classes):
        m = labels == c
        x[m] = protos[c] + g.normal(0.0, GEN_NOISE, (int(m.sum()), STATE_DIM))
    order = g.permutation(n_total)
    n_test = n_total // 2
    test_idx = order[:n_test]
    train_idx = order[n_test:]
    train_order = train_idx[g.permutation(len(train_idx))]
    noise = {}
    gn = np.random.default_rng(NOISE_NOISE_SEED + n_classes * 7919)
    for lvl in NOISE_LEVELS:
        noise[lvl] = (gn.normal(0.0, lvl, (n_test, STATE_DIM)).astype(np.float32)
                      if lvl > 0 else np.zeros((n_test, STATE_DIM), np.float32))
    return {
        "n_classes": n_classes, "x": x, "y": labels,
        "train_idx": np.sort(train_idx), "test_idx": np.sort(test_idx),
        "train_order": train_order, "noise": noise,
        "class_counts": np.bincount(labels, minlength=n_classes),
        "gen_noise": GEN_NOISE, "noise_levels": list(NOISE_LEVELS),
    }


def split(task: dict, fraction: float = 1.0) -> tuple:
    """Training set = first ceil(fraction * len) of the fixed train_order.

    The held-out test set is untouched by every fraction.
    """
    n = max(1, int(round(fraction * len(task["train_idx"]))))
    train = task["train_order"][:n]
    return train, task["test_idx"]


def eval_inputs(task: dict, level: float) -> np.ndarray:
    """Held-out test inputs with the task's fixed noise realization at `level`."""
    return (task["x"][task["test_idx"]] + task["noise"][level]).astype(np.float32)
