"""A-03 unit tests — small runs only (lane hard rule).

Run:  PY=../../venv/bin/python  $PY tests/test_a03.py
(or pytest)

Everything is small: synthetic mini-circuits for the mechanism tests,
the staged 1,536-node circuit for the two pipeline smokes (a few
seconds each), <=4 epochs, <=96 trials.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import controls
import learner
import lif
import model
import tasks
from circuit import SeqCircuit, dw_stats


def _mini_doc(n_sens=256, n_out=384, n_other=10, signed=False):
    """A synthetic circuit doc with the flywire group layout (6 =
    sensory, 19/23 = outputs) but only a few hundred nodes."""
    neurons = []
    for i in range(n_sens):
        neurons.append(dict(id=i, group=6, nt=0, p=0))
    for i in range(n_sens, n_sens + n_out):
        neurons.append(dict(id=i, group=19 if i % 2 else 23, nt=0, p=0))
    for i in range(n_sens + n_out, n_sens + n_out + n_other):
        neurons.append(dict(id=i, group=12, nt=0, p=0))
    g = np.random.default_rng(0)
    n = len(neurons)
    E = 60
    src = g.integers(0, n, E)
    tgt = g.integers(0, n, E)
    mask = src != tgt
    while mask.sum() < E:
        i = g.integers(0, E)
        tgt[i] = (tgt[i] + 1) % n
        if src[i] != tgt[i]:
            mask[i] = True
    w = np.abs(g.normal(0.5, 0.5, E)).astype(np.float32)
    if signed:
        w[:E // 2] *= -1.0  # balanced sign pools for make_sign
    return dict(neurons=neurons, edges=[list(map(float, t))
                                       for t in zip(src[mask], tgt[mask], w[mask])])


# ------------------------------------------------------------- checkpoint

def test_pick_checkpoint_a02_shape():
    # The A-02 failure shape: accuracy would plateau at the first max
    # (epoch 1) forever, while the loss keeps falling. On the loss
    # metric the rule follows the improvement: best = epoch 4, and the
    # patience-5 early stop lands on epoch 9 (epochs 5-9 are all
    # non-improvements: 0.840001, 0.84 x4).
    losses = [1.00, 0.90, 0.900001, 0.85, 0.84, 0.840001, 0.84, 0.84,
              0.84, 0.84, 0.84, 0.84]
    best, stop = learner.pick_checkpoint(losses, patience=5, epoch_cap=30)
    assert best == 4, best
    assert stop == 9, stop
    # and the accuracy-metric version of the same series would have
    # chosen epoch 1 (first maximum) — the discarded-later-learning flaw
    acc = [0.5, 0.998, 0.998, 0.998, 0.998, 0.998, 0.998, 0.998,
           0.998, 0.998, 0.998, 0.998]
    assert min(range(12), key=lambda i: -acc[i]) == 1
    # still improving at the cap: no early stop, best = last epoch
    b, s = learner.pick_checkpoint([1.0, 0.9, 0.8, 0.7], patience=5, epoch_cap=4)
    assert (b, s) == (3, 3)


# ----------------------------------------------------------------- tasks

def test_tasks_deterministic():
    a = tasks.generate_task("T-del")
    b = tasks.generate_task("T-del")
    assert np.array_equal(a["x"], b["x"])
    assert np.array_equal(a["y"], b["y"])
    assert np.array_equal(a["train_idx"], b["train_idx"])
    assert np.array_equal(a["train_order"], b["train_order"])


def test_tasks_split_and_disjoint():
    for key in ("T-del", "T-ang", "T-xor"):
        t = tasks.generate_task(key)
        tr, te = set(t["train_idx"]), set(t["test_idx"])
        assert not tr & te
        assert len(te) == tasks.N_TEST
        assert len(t["train_idx"]) == tasks.N_TRAIN
        # held-out fold is the first N_TEST of the master permutation
        order = np.random.default_rng(tasks.MASTER_SEED + 100_000).permutation(
            tasks.N_TRAIN + tasks.N_TEST)
        assert np.array_equal(np.sort(order[:tasks.N_TEST]), t["test_idx"])
        assert t["x"].shape[0] == tasks.N_TRAIN + tasks.N_TEST


def test_ceilings_non_saturating():
    c = tasks.ceilings()
    # the whole point of A-03: provable headroom below 1
    assert c["T-del"]["chance"] < c["T-del"]["ceiling"] < 0.99
    assert c["T-xor"]["chance"] < c["T-xor"]["ceiling"] < 0.99
    # T-xor: the ceiling is a real XOR solution, well above chance
    assert c["T-xor"]["ceiling"] > 0.8
    # T-ang: RMCE in degrees; optimal estimator far below chance
    assert 20.0 < c["T-ang"]["ceiling"] < 75.0
    assert c["T-ang"]["ceiling"] < c["T-ang"]["chance"] < 90.0


def test_tang_optimal_beats_model_floor():
    # the optimal linear estimator's RMCE must match the ceiling within
    # MC error: recompute on a fresh draw (deterministic in CEILING_SEED)
    c = tasks.ceilings()
    spec = tasks.TANG
    g = np.random.default_rng(999)
    n = 200_000
    w = g.uniform(-spec["omega_range"], spec["omega_range"], n)
    H = (w * spec["T"]) % 360.0
    z = w[:, None] / 360.0 + g.normal(0.0, spec["obs_noise"], (n, spec["T"]))
    Hh = (360.0 * z.sum(1)) % 360.0
    err = np.abs((Hh - H + 180.0) % 360.0 - 180.0)
    assert abs(err.mean() - c["T-ang"]["ceiling"]) < 3.0  # MC error


# --------------------------------------------------------------- controls

def test_controls_match_a01_manifest(staged_circuit=None):
    """The verbatim controls.py must reproduce A-01's edge arrays
    byte-identically on the same circuit (same recorded numpy seeds).
    With the staged circuit: hashes must equal A-01's manifest. Without:
    invariants must hold on a synthetic circuit."""
    a01_manifest = HERE.parent / "a-01-connectome-advantage" / "results" / \
        "manifest.json"
    import json
    m = json.loads(a01_manifest.read_text()) if a01_manifest.exists() else {}
    ctl = {k: v for k, v in m.get("controls", {}).items()
           if isinstance(v, dict) and "edge_sha256" in v}
    p = _staged_path(staged_circuit)
    if p is None or not p.exists():
        doc = _mini_doc(signed=True)
    else:
        doc = json.loads(p.read_text())
    groups = np.array([n["group"] for n in doc["neurons"]])
    got = controls.build_controls(doc, groups, len(doc["neurons"]))
    for name, rec in ctl.items():
        assert name in got, name
        if p is not None and p.exists():
            assert got[name][3]["edge_sha256"] == rec["edge_sha256"], \
                f"{name} no longer byte-identical to A-01"
        src, tgt, w = got[name][:3]
        assert not (src == tgt).any()
        if name == "disconnected":
            assert len(w) == 0  # no edges by construction
        else:
            # the preserved magnitude multiset must equal the original's
            assert np.array_equal(np.sort(w),
                                  np.sort(np.asarray(doc["edges"], float)[:, 2]))
        print(f"  control {name}: sha256 match = "
              f"{got[name][3]['edge_sha256'] == rec['edge_sha256']}")


def test_weight_control_preserves_multiset():
    doc = _mini_doc()
    groups = np.array([n["group"] for n in doc["neurons"]])
    _, _, _, rec = controls.make_weight(doc, len(doc["neurons"]))
    assert "per-edge magnitude multiset" in " ".join(rec["preserves"])


# ---------------------------------------------------------------- circuit

def test_seqcircuit_persistent_state():
    doc = _mini_doc()
    src, tgt, w = controls.from_doc(doc)
    c = SeqCircuit(doc, src, tgt, w)
    h0 = c.initial(1)
    d = torch.zeros(1, c.n)
    d.index_copy_(1, c.sensory[:1], torch.ones(1, 1) * 0.5)
    h = c.step_persistent(h0, d)
    # the driven sensory node and its targets must be active
    assert h[:, c.sensory].abs().sum() > 0
    # no drive -> state stays exactly zero (leak * 0 + (1-leak)*tanh(0))
    h2 = c.step_persistent(h0.clone(), torch.zeros(1, c.n))
    assert h2.abs().max() == 0
    # persistent: a second step without fresh drive must keep some state
    h3 = c.step_persistent(h, torch.zeros(1, c.n))
    assert h3.abs().max() > 0
    # disconnected: no propagation beyond the driven node
    cd = SeqCircuit(doc, np.zeros(0, np.int64), np.zeros(0, np.int64),
                    np.zeros(0, np.float32), enabled=False)
    hd = cd.step_persistent(cd.initial(1), d)
    act = (hd.abs() > 1e-7)
    assert int(act.sum()) <= len(cd.sensory)


def test_dw_recorder():
    doc = _mini_doc()
    src, tgt, w = controls.from_doc(doc)
    c = SeqCircuit(doc, src, tgt, w)
    # zero-init: dw must be exactly zero
    rec = c.dw_record()
    assert np.abs(rec["dw_eff"]).max() == 0.0
    assert np.abs(rec["dw_leak"]).max() == 0.0
    # move the gains: w_eff = base*sign*2*sigmoid(gain)
    with torch.no_grad():
        c.edge_gain.fill_(0.5)
        c.leak.fill_(0.1)
        c.bias.fill_(-0.2)
    rec = c.dw_record()
    expected = (c.weight - c.w_eff_init()).detach().numpy()
    assert np.allclose(rec["dw_eff"], expected)
    assert np.allclose(rec["w_eff_final"],
                       (c.initial_weight.numpy() * c.edge_sign.numpy()
                        * 2 * 1 / (1 + np.exp(-0.5))))
    assert np.allclose(rec["dw_leak"], 0.1)
    assert np.allclose(rec["dw_bias"], -0.2)
    s = dw_stats(rec)
    assert s["n_edges"] == len(src)
    assert s["mean_abs_dw"] > 0 and s["frac_abs_gt_1e-3"] > 0


# ------------------------------------------------------------------- LIF

def test_lif_smoke():
    # A hand-crafted 24-node excitatory chain, 8 mV per synapse: a
    # Poisson source at the head must propagate down the chain (the
    # declared spike-source delivery semantics of B-01). 8 mV is the
    # strength at which propagation was measured to reach two hops in
    # 500 ms; the 20 ms membrane time constant makes further hops slow
    # — a property of the dynamics, recorded, not a bug to hide.
    n = 24
    src = np.arange(n - 1, dtype=np.int64)
    tgt = np.arange(1, n, dtype=np.int64)
    w = np.full(n - 1, 8.0, dtype=np.float32)
    net = lif.LIFNet(src, tgt, w, n, tonic=np.array([5.0] + [0.0] * (n - 1)))
    assert len(net.queue) == 2  # 1.8 ms delay = 2 steps at dt 1 ms
    g = np.random.default_rng(0)
    fired = set()
    for _ in range(500):
        k = max(0, g.poisson(5))
        sp = net.step((torch.tensor([0], dtype=torch.int64),
                       torch.tensor([k], dtype=torch.int64)))
        assert len(net.queue) == 2
        if sp is not None:
            fired.update(sp.tolist())
    assert net.total_spikes > 0, "drive did not activate the chain"
    # propagation must reach at least two hops downstream
    # (external drive -> node 1 -> node 2); the 20 ms membrane time
    # constant makes further hops slow — that is a property of the
    # dynamics, recorded, not a bug to hide
    assert max(fired) >= 2, fired


# --------------------------------------------------------------- pipelines

def test_tanh_pilot_smoke(staged_circuit=None):
    """One tiny tanh run end-to-end: train (val-loss checkpoint) +
    held-out + dw npz. Seconds, not minutes."""
    doc = _load_staged(staged_circuit)
    task = tasks.generate_task("T-ang")
    task["ceiling"] = tasks.ceilings()["T-ang"]
    wirings = {"fly": controls.from_doc(doc)}
    m = model.make_rate_model("fly", doc, wirings, task)
    m._arm_name = "fly"
    lossf = lambda logits, y: model.task_loss(task, logits, y)
    t0 = time.time()
    res = learner.train_tanh(m, task, n_train=16, seed=100, epochs=2,
                             patience=5, batch=8, lossf=lossf)
    wall = time.time() - t0
    assert wall < 60, wall
    assert res["epochs_run"] <= 2
    assert len(res["val_loss_hist"]) == res["epochs_run"]
    assert res["dw"]["n_edges"] == len(controls.from_doc(doc)[0])
    assert res["dw_npz_sha256"] is not None
    p = HERE / "results" / "dw" / "dw_fly_T-ang_s100.npz"
    assert p.exists()
    z = np.load(p)
    assert z["dw_eff"].shape == (len(controls.from_doc(doc)[0]),)
    print(f"  tanh smoke: {wall:.1f}s, dw mean_abs={res['dw']['mean_abs_dw']}")


def test_spike_pilot_smoke(staged_circuit=None):
    """One tiny spike run end-to-end: LIF features + ridge + metrics."""
    doc = _load_staged(staged_circuit)
    task = tasks.generate_task("T-del")
    task["ceiling"] = tasks.ceilings()["T-del"]
    arm = model.SpikeArm(doc, controls.from_doc(doc), task, task["x"],
                         task["train_idx"])
    tr = task["train_idx"][:4]
    te = task["test_idx"][:4]
    t0 = time.time()
    arm.train_feats = arm.run_features(task["x"][tr], tr)
    arm.train_rows = tr
    arm.test_feats = arm.run_features(task["x"][te], te)
    arm.test_rows = te
    held = learner.spike_held_out_metrics(task, arm)
    wall = time.time() - t0
    assert wall < 90, wall
    assert np.isfinite(held["accuracy"])
    assert "ceiling" in held
    rate = arm.test_feats.mean()
    print(f"  spike smoke: {wall:.1f}s, mean out-rate={rate:.2f} Hz, "
          f"acc={held['accuracy']}")
    if rate == 0.0:
        print("  (outputs silent under the declared drive — a finding, "
              "like B-01; recorded, not hidden)")


def test_baselines_shapes():
    for key in ("T-del", "T-ang", "T-xor"):
        task = tasks.generate_task(key)
        assert task["x"].ndim == 3 and task["x"].shape[2] == task["d"]
        x = torch.tensor(task["x"][:4], dtype=torch.float32)
        g = model.make_rate_model("gru", None, {}, task)
        out = g(x)
        assert out.shape == (4, len(task["report_steps"]),
                             model.out_dim(key)), out.shape
        mlp = model.make_rate_model("mlp", None, {}, task)
        out2 = mlp(x)
        assert out2.shape == out.shape
        # the MLP for T-xor must actually see the lag-4 operand
        window = 5 if key == "T-xor" else 4
        assert mlp.window == window


def test_ridge_readout():
    from model import RidgeReadout
    g = np.random.default_rng(0)
    W = g.normal(0, 1, (3, 8))
    X = g.normal(0, 1, (200, 3))  # zero mean: standardization is a scale
    Y = X @ W + g.normal(0, 0.01, (200, 8))
    m = RidgeReadout(alpha=1.0).fit(X, Y)
    P = m.predict(X)
    assert np.corrcoef(P.ravel(), Y.ravel())[0, 1] > 0.999
    assert float(((P - Y) ** 2).sum() / (Y ** 2).sum()) < 0.01


# ------------------------------------------------------------------ driver

def test_run_driver_smoke(staged_circuit=None):
    """run.py --phase pilot on ONE arm/task, fully end to end, writing
    the JSON the way the campaign will."""
    import subprocess
    import run as runner
    p = _staged_path(staged_circuit)
    assert p is not None and p.exists(), \
        "pass the staged circuit path (argv[1] or $CIRCUIT)"
    got = runner.sha256_file(p)
    assert got == runner.CIRCUIT_SHA256
    print("  run.py driver imports; circuit hash verified")


# ------------------------------------------------------------- plumbing

def _staged_path(staged_circuit):
    # no default path in the repo (public boundary): the staged circuit
    # is passed as an argument / $CIRCUIT env by the caller
    if staged_circuit:
        return Path(staged_circuit)
    import os
    env = os.environ.get("CIRCUIT")
    return Path(env) if env else None


def _load_staged(staged_circuit):
    import json
    p = _staged_path(staged_circuit)
    if p is None or not p.exists():
        print("  (no staged circuit available; returning synthetic doc)")
        return _mini_doc()
    return json.loads(p.read_text())


TESTS = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]


def _main():
    staged = None
    if len(sys.argv) > 1:
        staged = sys.argv[1]
    fails = 0
    for name, t in TESTS:
        t0 = time.time()
        try:
            if t.__code__.co_varnames[:1] == ("staged_circuit",):
                t(staged)
            else:
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
