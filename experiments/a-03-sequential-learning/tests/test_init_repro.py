"""A-03 init-reproducibility regression tests (review round 4, 2026-10-13).

The round-4 review of 787bc3a found that `run_rate()` constructed the
tanh/GRU/MLP model BEFORE `train_tanh()` called `torch.manual_seed`,
so the recorded run seed controlled training shuffles but NOT initial
parameters — and the tanh-fly T-del reruns (0.469 / 0.250 / 0.438 on
nominally identical runs) are a concrete possible consequence. These
tests pin the fixed protocol on the synthetic mini-circuit (no staged
dependency; seconds per test):

  1. two same-seed executions -> identical full state-dict hash AND
     identical held-out metrics (bit-identical rerun);
  2. matched fly / degree architectures with the same seed -> identical
     initial neural-network parameters (clean same-initialization
     comparison between the biological wiring and its control);
  3. different seeds -> different initial parameters (sanity).

Run:  python tests/test_init_repro.py
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).parent))

import controls  # noqa: E402
import learner  # noqa: E402
import model  # noqa: E402
import run  # noqa: E402
import tasks  # noqa: E402
import test_a03  # noqa: E402  (reuses its _mini_doc)

N_TRAIN = 32
N_TEST = 32
EPOCHS = 6
PATIENCE = 4
BATCH = 8


def _task(key: str) -> dict:
    t = tasks.generate_task(key)
    t["ceiling"] = tasks.ceilings()[key]
    return t


def _build(arm: str, doc, wirings, task, seed):
    """Exactly what run_rate now does: seed BEFORE construction.
    (wirings: the 3-tuple form from run.build_wirings)"""
    torch.manual_seed(seed)
    return model.make_rate_model(arm, doc, wirings, task)


def _param_sha256(m: torch.nn.Module) -> str:
    """Hash of the neural-network PARAMETERS only (nn.Parameter);
    edge buffers (source/target/sign/initial_weight) are wiring data,
    not initialized parameters, and legitimately differ between
    matched wirings."""
    h = hashlib.sha256()
    params = dict(m.named_parameters())
    for k in sorted(params):
        h.update(k.encode())
        h.update(params[k].detach().numpy().tobytes())
    return h.hexdigest()


def _run_once(arm, doc, wirings, task, seed):
    m = _build(arm, doc, wirings, task, seed)
    init = _param_sha256(m)
    lossf = lambda logits, y: model.task_loss(task, logits, y)
    res = learner.train_tanh(m, task, N_TRAIN, seed, EPOCHS, PATIENCE,
                             BATCH, lossf)
    te_idx = task["test_idx"][:N_TEST]
    Xte = torch.tensor(task["x"][te_idx], dtype=torch.float32)
    m.eval()
    with torch.no_grad():
        ho = learner.held_out_metrics(task, m(Xte).numpy(), te_idx)
    return init, run.weights_sha256(m), ho, res


def _wirings(doc):
    # only the two wirings these tests need (the full control set can
    # have empty swap pools on the tiny 60-edge mini doc)
    n = len(doc["neurons"])
    return {"fly": controls.from_doc(doc),
            "degree": controls.make_degree(doc, n, 0)[:3]}


def test_same_seed_bitidentical_rerun():
    doc = test_a03._mini_doc()
    wirings = _wirings(doc)
    task = _task("T-del")
    a = _run_once("tanh-fly", doc, wirings, task, 777)
    b = _run_once("tanh-fly", doc, wirings, task, 777)
    assert a[0] == b[0], "init parameter hash differs across same-seed runs"
    assert a[1] == b[1], "final state-dict hash differs across same-seed runs"
    assert a[2] == b[2], f"held-out metrics differ: {a[2]} vs {b[2]}"
    assert a[3]["val_loss_best"] == b[3]["val_loss_best"]


def test_matched_wirings_same_seed_same_init():
    doc = test_a03._mini_doc()
    wirings = _wirings(doc)
    task = _task("T-ang")
    mf = _build("tanh-fly", doc, wirings, task, 555)
    md = _build("tanh-degree", doc, wirings, task, 555)
    assert _param_sha256(mf) == _param_sha256(md), (
        "matched fly/degree tanh models with the same seed must start "
        "from identical initial parameters")


def test_different_seed_different_init():
    doc = test_a03._mini_doc()
    wirings = _wirings(doc)
    task = _task("T-del")
    a = _build("tanh-fly", doc, wirings, task, 555)
    b = _build("tanh-fly", doc, wirings, task, 556)
    assert _param_sha256(a) != _param_sha256(b)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)
           and not isinstance(v, type(sys))]
    failed = 0
    for fn in fns:
        t0 = time.time()
        try:
            fn()
            print(f"PASS {fn.__name__}  ({time.time() - t0:.1f}s)")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
