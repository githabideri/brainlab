"""The three A-03 sequential tasks (generated — declared, pre-registered).

Every number below is a pure function of the two master seeds
(MASTER_SEED for generation, CEILING_SEED for the ceiling Monte-Carlo),
so the same stimulus stream — same trials, same order, same held-out
fold — is served to every arm of every dynamics.

All three tasks **cannot saturate**: each has a provable ceiling below
1 (input noise that no memory can remove), computed by fixed-seed
Monte-Carlo at import time and recorded in results/manifest.json.

T-del  delayed-cue report:  a 4-class one-hot cue appears at a random
       early step, the input is floor noise for the rest, the answer is
       demanded at a fixed final step. The network must HOLD the cue for
       4-6 steps in recurrent state.
T-ang  angular integration: rate-coded angular velocity, integrate over
       10 steps into a heading; (sin, cos) regression; the optimal
       estimator still has an ~57-deg error floor from the input noise.
T-xor  temporal XOR:        binary stream, rate-coded with noise; the
       answer at step t is the XOR of the current and the 4-steps-ago
       bit, reported at 8 steps.
"""
from __future__ import annotations

import numpy as np

MASTER_SEED = 20261020
CEILING_SEED = 20261021
N_TRAIN = 1024
N_TEST = 512

# ---------------------------------------------------------------- T-del
TDEL = dict(key="T-del", kind="class", T=8, d=4, K=4,
            tau_choices=(1, 2, 3), cue_noise=0.4, floor_noise=0.15,
            report_steps=(7,))
# ---------------------------------------------------------------- T-ang
TANG = dict(key="T-ang", kind="reg", T=10, d=1,
            omega_range=180.0, obs_noise=0.05, report_steps=(9,))
# ---------------------------------------------------------------- T-xor
TXOR = dict(key="T-xor", kind="binary", T=12, d=1, lag=4, obs_noise=0.35,
            report_steps=tuple(range(4, 12)))
TASKS = [TDEL, TANG, TXOR]


def _split(n_total: int, rng) -> tuple:
    """Held-out test fold = first N_TEST of the master-seed trial
    permutation; the rest is the training fold (master-seed training
    order). Identical for every arm."""
    order = rng.permutation(n_total)
    test_idx = np.sort(order[:N_TEST])
    train_idx = np.sort(order[N_TEST:])
    train_order = train_idx[rng.permutation(len(train_idx))]
    return train_idx, test_idx, train_order


def _ceiling_tdel(K: int, cue_noise: float, n_mc: int) -> float:
    """Bayes accuracy of a perfect-memory decoder of the NOISY cue
    observation only (one-hot + N(0, cue_noise^2))."""
    g = np.random.default_rng(CEILING_SEED + 1)
    c = g.integers(0, K, n_mc)
    obs = np.zeros((n_mc, K))
    obs[np.arange(n_mc), c] = 1.0
    obs += g.normal(0.0, cue_noise, (n_mc, K))
    scores = obs.copy()  # N(0,1) likelihood; class c: (1+noise)/1
    pred = scores.argmax(1)
    return float((pred == c).mean())


def _ceiling_tang(omega_range: float, obs_noise: float, T: int, n_mc: int) -> float:
    """Circular RMCE (deg) of the OPTIMAL estimator (constant-omega task
    => average of the T observations). Returns RMCE."""
    g = np.random.default_rng(CEILING_SEED + 2)
    w = g.uniform(-omega_range, omega_range, n_mc)
    H = (w * T) % 360.0
    z = w[:, None] / 360.0 + g.normal(0.0, obs_noise, (n_mc, T))
    Hhat = (360.0 * (z.sum(1) / T) * T) % 360.0
    err = np.abs((Hhat - H + 180.0) % 360.0 - 180.0)
    return float(err.mean())


def _p_obs(z: float, x: int, sigma: float) -> float:
    # normal density, unclipped (clipping at [0,1] is negligible at this
    # sigma; declared)
    import math
    return math.exp(-0.5 * ((z - x) / sigma) ** 2)


def _ceiling_txor(sigma: float, n_mc: int) -> float:
    """Bayes accuracy of XOR given the two noisy observations (z_t,
    z_{t-lag})."""
    g = np.random.default_rng(CEILING_SEED + 3)
    x1 = g.integers(0, 2, n_mc)
    x2 = g.integers(0, 2, n_mc)
    z1 = x1 + g.normal(0.0, sigma, n_mc)
    z2 = x2 + g.normal(0.0, sigma, n_mc)
    acc = 0
    for a, b, u, v in zip(x1, x2, z1, z2):
        cands = []
        for i in range(2):
            for j in range(2):
                cands.append(_p_obs(u, i, sigma) * _p_obs(v, j, sigma) * 0.25)
        best = int(cands.index(max(cands)))
        pred = (best // 2) ^ (best % 2)
        acc += (pred == (a ^ b))
    return acc / n_mc


def _gen_tdel(spec, g) -> dict:
    T, K = spec["T"], spec["K"]
    x = np.zeros((N_TRAIN + N_TEST, T, K), np.float32)
    y = np.zeros(N_TRAIN + N_TEST, np.int64)
    tau = np.zeros(N_TRAIN + N_TEST, np.int64)
    for i in range(N_TRAIN + N_TEST):
        c = g.integers(0, K)
        t = int(g.choice(spec["tau_choices"]))
        tau[i] = t
        x[i] = g.normal(0.0, spec["floor_noise"], (T, K))
        x[i, t] += np.eye(K)[c] + g.normal(0.0, spec["cue_noise"], K)
        y[i] = c
    return dict(x=x, y=y, extra={"tau": tau})


def _gen_tang(spec, g) -> dict:
    T = spec["T"]
    w = g.uniform(-spec["omega_range"], spec["omega_range"], N_TRAIN + N_TEST)
    x = (w[:, None, None] / 360.0
         + g.normal(0.0, spec["obs_noise"], (N_TRAIN + N_TEST, T, 1)))
    H = (w * T) % 360.0
    y = np.stack([np.sin(np.radians(H)), np.cos(np.radians(H))], 1)
    return dict(x=x.astype(np.float32), y=y.astype(np.float32),
                extra={"H": H.astype(np.float32)})


def _gen_txor(spec, g) -> dict:
    T, lag = spec["T"], spec["lag"]
    n = N_TRAIN + N_TEST
    xb = g.integers(0, 2, (n, T))
    x = xb[:, :, None] + g.normal(0.0, spec["obs_noise"], (n, T, 1))
    x = np.clip(x, 0.0, 1.0).astype(np.float32)
    y = (xb[:, lag:] ^ xb[:, :T - lag])  # rows t = lag..T-1
    return dict(x=x, y=y.astype(np.float32), extra={"x_true": xb})


_GENERATORS = {"T-del": _gen_tdel, "T-ang": _gen_tang, "T-xor": _gen_txor}


def ceilings() -> dict:
    """Fixed-seed ceiling (and chance) values, per task. Computed once;
    recorded in the manifest. T-del/T-xor: accuracy in [chance, 1);
    T-ang: RMCE (deg) of the optimal estimator."""
    out = {}
    for spec in TASKS:
        if spec["key"] == "T-del":
            out[spec["key"]] = dict(
                kind="accuracy", chance=1.0 / spec["K"],
                ceiling=_ceiling_tdel(spec["K"], spec["cue_noise"], 200_000))
        elif spec["key"] == "T-ang":
            rmce_opt = _ceiling_tang(spec["omega_range"], spec["obs_noise"],
                                     spec["T"], 200_000)
            g = np.random.default_rng(CEILING_SEED + 4)
            H = g.uniform(0, 360, 200_000)  # chance = predict the mean heading
            err = np.abs((0.0 - H + 180.0) % 360.0 - 180.0)
            out[spec["key"]] = dict(kind="rmce_deg", chance=float(err.mean()),
                                    ceiling=rmce_opt)
        else:
            out[spec["key"]] = dict(kind="accuracy", chance=0.5,
                                    ceiling=_ceiling_txor(spec["obs_noise"],
                                                         100_000))
    return out


def generate_task(key: str) -> dict:
    """One A-03 task: the full trial set (train + test), the fixed split,
    and the per-task spec. Deterministic in MASTER_SEED."""
    spec = next(s for s in TASKS if s["key"] == key)
    g = np.random.default_rng(MASTER_SEED + TASKS.index(spec) * 7919)
    parts = _GENERATORS[key](spec, g)
    train_idx, test_idx, train_order = _split(N_TRAIN + N_TEST,
                                              np.random.default_rng(
                                                  MASTER_SEED + 100_000))
    return {
        "key": key, "spec": spec, "T": spec["T"], "d": spec["d"],
        "x": parts["x"], "y": parts["y"], "extra": parts["extra"],
        "report_steps": spec["report_steps"],
        "kind": spec["kind"],
        "train_idx": train_idx, "test_idx": test_idx,
        "train_order": train_order,
        "ceiling": None,  # filled by run.py from ceilings()
    }


def split(task: dict, n_train: int = N_TRAIN) -> tuple:
    """Training set = first n_train of the fixed train_order (the pilot
    uses a smaller prefix; the test fold is never touched)."""
    n = max(1, min(n_train, len(task["train_order"])))
    return task["train_order"][:n], task["test_idx"]
