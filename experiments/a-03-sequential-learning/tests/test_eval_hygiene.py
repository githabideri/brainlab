"""A-03 evaluation-hygiene regression tests (2026-10-13 fix, review P0).

The v1 pilot's spike-arm scores (T-del 1.000, T-ang 0.05 deg / R^2 = 1.0,
100 % delayed-cue) were produced by a train/test leak: the ridge readout
was fit on the held-out features AND their true labels, then evaluated
on those same rows. These six tests pin the fixed evaluation and the
paired-sensory-RNG protocol so the leak cannot regress silently.

Run:
  python -m pytest tests/test_eval_hygiene.py
(or the module directly; no staged circuit needed — all six use a
synthetic mini-circuit with the atlas group layout, seconds total.)

Tests (one per brief item):
  a. permuting/altering held-out labels leaves fitted ridge parameters
     and held-out predictions unchanged
  b. train row-ID set ∩ test row-ID set = ∅ (incl. the fit prefix)
  c. normalization constants (m/M) are functions of training rows only
  d. RidgeReadout.fit receives exactly the n_fit training rows, never
     test rows (spy)
  e. with randomized held-out labels (5 fixed permutation seeds),
     held-out accuracy ≈ chance (within ±3 SD)
  f. reported held-out efficiency (ceiling from the existing ceiling
     script on the same features) ≤ 1.0 + declared margin
"""
from __future__ import annotations

import copy
import inspect
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).parent))

import controls  # noqa: E402
import learner   # noqa: E402
import model     # noqa: E402
import tasks     # noqa: E402
import test_a03  # noqa: E402  (reuses its _mini_doc)

# Declared margin for test (f): a leak-free readout on a RANDOM control
# circuit must not beat the ceiling by more than this relative amount.
# This is a small-sample tolerance (n_fit = 25 / n_test = 32 trials,
# pilot scale; mini-circuit features with tiny signal), not a hyperparameter: it
# bounds estimation noise, and any run exceeding it would itself be a
# finding (a controllable random circuit), to be investigated, not
# averaged away. Declared here, before the run, by the fix lane.
EFF_MARGIN = 0.15

N_TRAIN = 32   # pilot-scale train fold for the mini-circuit runs
N_TEST = 32    # pilot-scale held-out prefix for the mini-circuit runs

PERM_SEEDS = [7, 11, 13, 17, 19]  # the five fixed label-permutation seeds

# One arm per task, shared across tests: the mini-circuit is a pure
# function of fixed seeds (_mini_doc seed 0, master-seeded tasks), so
# every test sees the same arm and the feature pass runs once per task.
_ARM_CACHE = {}


def _arm(task_key: str, doc, wiring, task):
    cached = _ARM_CACHE.get(task_key)
    if cached is not None:
        return cached
    a = model.SpikeArm(doc, wiring, task, task["x"], task["train_idx"])
    tr_idx = tasks.split(task, N_TRAIN)[0]
    te_idx = task["test_idx"][:N_TEST]
    a.train_feats = a.run_features(task["x"][tr_idx], tr_idx)
    a.train_rows = tr_idx
    a.test_feats = a.run_features(task["x"][te_idx], te_idx)
    a.test_rows = te_idx
    _ARM_CACHE[task_key] = a
    return a


def _w(doc):
    return controls.from_doc(doc)


class _SpyRidge(model.RidgeReadout):
    """Records every fit() call as (X, Y, beta) and delegates to the
    real ridge."""
    calls = []

    def fit(self, X, Y):
        type(self).calls.append((np.array(X, copy=True),
                                 np.array(Y, copy=True), None))
        out = super().fit(X, Y)
        type(self).calls[-1] = (type(self).calls[-1][0],
                                type(self).calls[-1][1],
                                np.array(self.beta, copy=True))
        return out


class _patched:
    """Context manager swapping model.RidgeReadout for a spy subclass
    (spike_held_out_metrics does `from model import RidgeReadout` at
    call time, so patching the module attribute is picked up)."""

    def __init__(self, cls):
        self.cls, self.old = cls, model.RidgeReadout

    def __enter__(self):
        model.RidgeReadout = self.cls
        return self.cls

    def __exit__(self, *a):
        model.RidgeReadout = self.old


def _predicts(task, arm):
    """The per-step held-out predictions produced by the same fit
    recipe as spike_held_out_metrics (run under a patched ridge so
    the fit calls are recorded), without computing final metrics."""
    Xtr, Xte = arm.train_feats, arm.test_feats
    n_fit = max(1, int(0.8 * len(Xtr)))
    y_all = task["y"]
    outs = []
    for r in range(len(arm.task["report_steps"])):
        m = model.RidgeReadout(alpha=1.0).fit(
            Xtr[:n_fit, r],
            learner._Y_rows(task, y_all[arm.train_rows][:n_fit], r))
        outs.append(m.predict(Xte[:, r]))
    return np.stack(outs, 1)


def _permute_test_labels(task: dict, perm_seed: int) -> dict:
    """A copy of the task with the held-out fold's labels shuffled
    (training labels untouched)."""
    t = copy.deepcopy(task)
    g = np.random.default_rng(perm_seed)
    y = t["y"][t["test_idx"]]
    t["y"][t["test_idx"]] = y[g.permutation(len(y))]
    return t


# ------------------------------------------------------------------ (a)

def test_permuted_heldout_labels_do_not_change_fit_or_predictions():
    """(a) altering the held-out labels must leave the fitted ridge
    parameters and the held-out predictions bit-identical — impossible
    under the v1 leak, where those labels went into fit()."""
    for key in ("T-del", "T-ang", "T-xor"):
        doc = test_a03._mini_doc()
        task = tasks.generate_task(key)
        arm = _arm(key, doc, _w(doc), task)
        _SpyRidge.calls = []
        with _patched(_SpyRidge):
            p1 = _predicts(task, arm)
            calls1 = list(_SpyRidge.calls)
        for s in PERM_SEEDS[:2]:  # two permutations are enough to prove it
            _SpyRidge.calls = []
            with _patched(_SpyRidge):
                p2 = _predicts(_permute_test_labels(task, s), arm)
                calls2 = list(_SpyRidge.calls)
            assert np.array_equal(p1, p2), \
                f"{key}: predictions changed when held-out labels changed"
            assert len(calls1) == len(calls2)
            for (Xa, Ya, ba), (Xb, Yb, bb) in zip(calls1, calls2):
                assert np.array_equal(Xa, Xb), f"{key}: fit X changed"
                assert np.array_equal(Ya, Yb), f"{key}: fit Y changed"
                assert np.array_equal(ba, bb), f"{key}: ridge beta changed"


# ------------------------------------------------------------------ (b)

def test_train_and_test_row_sets_disjoint():
    """(b) the fit rows and the evaluation rows never overlap: train
    row-ID set ∩ test row-ID set = ∅, and the fit prefix stays inside
    the train set."""
    for key in ("T-del", "T-ang", "T-xor"):
        doc = test_a03._mini_doc()
        task = tasks.generate_task(key)
        arm = _arm(key, doc, _w(doc), task)
        tr = set(map(int, arm.train_rows))
        te = set(map(int, arm.test_rows))
        assert not (tr & te), f"{key}: train/test rows overlap"
        n_fit = max(1, int(0.8 * len(arm.train_feats)))
        fit = set(map(int, arm.train_rows[:n_fit]))
        assert not (fit & te) and fit <= tr
        # the master array itself has a disjoint split too
        assert not (set(map(int, task["train_idx"]))
                    & set(map(int, task["test_idx"])))


# ------------------------------------------------------------------ (c)

def test_normalization_constants_are_train_only():
    """(c) the drive's m/M normalization constants are pure functions
    of the TRAINING rows: perturbing the held-out inputs cannot move
    them."""
    for key in ("T-del", "T-ang", "T-xor"):
        doc = test_a03._mini_doc()
        task = tasks.generate_task(key)
        w = _w(doc)
        arm1 = model.SpikeArm(doc, w, task, task["x"], task["train_idx"])
        X2 = task["x"].copy()
        X2[task["test_idx"]] = X2[task["test_idx"]] * 1.7 + 0.4
        arm2 = model.SpikeArm(doc, w, task, X2, task["train_idx"])
        assert np.array_equal(arm1.m, arm2.m), f"{key}: m moved"
        assert np.array_equal(arm1.M, arm2.M), f"{key}: M moved"
        assert np.array_equal(arm1.Wx, arm2.Wx)  # fixed projection


# ------------------------------------------------------------------ (d)

def test_fit_receives_exactly_the_nfit_train_rows():
    """(d) spy on RidgeReadout.fit: it receives exactly n_fit rows,
    equal to the training-feature prefix, with the matching training
    targets, and no row equal to any held-out feature row."""
    for key in ("T-del", "T-ang", "T-xor"):
        doc = test_a03._mini_doc()
        task = tasks.generate_task(key)
        task["ceiling"] = tasks.ceilings()[key]
        arm = _arm(key, doc, _w(doc), task)
        _SpyRidge.calls = []
        with _patched(_SpyRidge):
            learner.spike_held_out_metrics(task, arm)
        n_fit = max(1, int(0.8 * len(arm.train_feats)))
        R = len(task["report_steps"])
        assert len(_SpyRidge.calls) == R, \
            f"{key}: expected {R} fit calls, got {len(_SpyRidge.calls)}"
        for r, (Xf, Yf, _b) in enumerate(_SpyRidge.calls):
            assert len(Xf) == n_fit, \
                (f"{key} step {r}: fit got {len(Xf)} rows, "
                 f"expected n_fit={n_fit}")
            assert np.allclose(Xf, arm.train_feats[:n_fit, r]), \
                f"{key} step {r}: fit X is not the train-feature prefix"
            expY = learner._Y_rows(task, task["y"][arm.train_rows[:n_fit]], r)
            assert np.array_equal(Yf, expY), \
                f"{key} step {r}: fit targets are not the train targets"
            # No *identifiable* held-out row is in the fit set. (On the
            # mini circuit many feature rows are genuinely duplicate —
            # most outputs are input-free and fire at a constant tonic
            # rate — so only rows unique within train+test are
            # checkable; on the real atlas every row is unique and the
            # check is total.)
            allf = np.vstack([arm.train_feats[:, r], arm.test_feats[:, r]])
            te = arm.test_feats[:, r]
            for i in range(len(te)):
                n_dup = int((np.abs(allf - te[i]).max(1) < 1e-6).sum())
                if n_dup > 1:
                    continue  # not identifiable; cannot be tracked by value
                in_fit = int((np.abs(Xf - te[i]).max(1) < 1e-6).any())
                assert not in_fit, \
                    f"{key} step {r}: identifiable test row {i} is in the fit"


# ------------------------------------------------------------------ (e)

def test_randomized_heldout_labels_give_chance_accuracy():
    """(e) with randomized (permuted) held-out labels — five fixed
    permutation seeds — the held-out accuracy of the leak-free readout
    is chance ± 3 SD (SD = empirical spread of the 0/1 mismatch vector,
    scaled by √n; for T-ang: RMCE vs the chance RMCE with the SD of a
    single circular-error draw). The v1 leak would show a strong
    deviation from chance here — its T-del was 1.000."""
    for key in ("T-del", "T-ang", "T-xor"):
        doc = test_a03._mini_doc()
        task = tasks.generate_task(key)
        task["ceiling"] = tasks.ceilings()[key]
        arm = _arm(key, doc, _w(doc), task)
        held = learner.spike_held_out_metrics(task, arm)
        assert held is not None and len(arm.test_rows) == N_TEST
        n = N_TEST
        for s in PERM_SEEDS:
            h = learner.spike_held_out_metrics(
                _permute_test_labels(task, s), arm)
            if key == "T-ang":
                ref = task["ceiling"]["chance"]
                sd = 103.9 / np.sqrt(n)  # SD of one circular-error draw
                assert abs(h["rmce_deg"] - ref) <= 3 * sd, \
                    f"{key} perm {s}: rmce {h['rmce_deg']} vs chance {ref}"
            else:
                p0 = task["ceiling"]["chance"]
                mism = 1.0 - h["accuracy"]
                sd = np.sqrt(mism * (1.0 - mism)) / np.sqrt(n)
                assert abs(h["accuracy"] - p0) <= 3 * sd, \
                    f"{key} perm {s}: acc {h['accuracy']} vs chance {p0}"


# ------------------------------------------------------------------ (f)

def test_heldout_efficiency_not_above_ceiling_by_more_than_margin():
    """(f) the reported held-out efficiency — (model − chance)/(ceiling
    − chance) for the accuracy tasks, ceiling/RMCE for T-ang, ceiling
    from the existing tasks.ceilings() script on the same features —
    must be ≤ 1.0 + EFF_MARGIN. The v1 leak reported 1.141 on T-del."""
    for key in ("T-del", "T-ang", "T-xor"):
        doc = test_a03._mini_doc()
        task = tasks.generate_task(key)
        task["ceiling"] = tasks.ceilings()[key]
        arm = _arm(key, doc, _w(doc), task)
        held = learner.spike_held_out_metrics(task, arm)
        eff = held["efficiency"]
        assert eff <= 1.0 + EFF_MARGIN, \
            (f"{key}: held-out efficiency {eff} exceeds "
             f"1.0 + {EFF_MARGIN} (leak-shaped; investigate before "
             f"widening the margin)")


TESTS = [(k, v) for k, v in sorted(globals().items())
         if k.startswith("test_") and inspect.isfunction(v)]


def _main():
    fails = 0
    for name, t in TESTS:
        t0 = time.time()
        try:
            t()
            print(f"PASS {name}  ({time.time() - t0:.1f}s)")
        except Exception as e:
            fails += 1
            import traceback
            print(f"FAIL {name}  ({time.time() - t0:.1f}s): {e}")
            traceback.print_exc()
    print(f"\n{len(TESTS) - fails}/{len(TESTS)} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    _main()
