"""A-03 learner: the A-02 checkpoint flaw, closed.

Checkpoint rule: keep the state with the best (lowest) internal-val
LOSS — never accuracy (the A-02 review's first flag: val-accuracy
checkpointing on near-saturated tasks keeps the FIRST model to reach
the accuracy maximum and discards later learning). Patience is counted
on val-loss. The full per-epoch train/val loss trajectories are
recorded in every run.

`pick_checkpoint` is a pure function of the recorded val-loss series
so the rule is unit-testable in isolation, including the exact
A-02 failure shape (accuracy plateaus early, loss keeps improving).
"""
from __future__ import annotations

import copy
import hashlib
import time
from pathlib import Path

import numpy as np
import torch

from circuit import dw_stats

EPS = 1e-9  # an improvement must beat the best by more than this


def pick_checkpoint(val_losses, patience: int, epoch_cap: int):
    """Return (best_epoch, stop_epoch) for a val-loss series.

    best_epoch: argmin of the val-loss series up to and including the
    stop point (first minimum wins ties — same epsilon convention as
    A-01/A-02, mirrored for the loss). stop_epoch: last epoch
    simulated; the loop stops after `patience` epochs without an
    improvement, or at the epoch cap.

    A-02 failure shape, in the accuracy metric: val-acc
    [0.5, 0.998, 0.998, 0.998, ...] with the loss still falling —
    argmax(accuracy) = epoch 1 forever, and every later learning is
    discarded. On the loss metric this rule keeps following the
    falling loss: that is the fix.
    """
    n = len(val_losses)
    stop = n - 1
    best_so_far, bad = float("inf"), 0
    for i, v in enumerate(val_losses):
        if v < best_so_far - EPS:
            best_so_far, bad = v, 0
        else:
            bad += 1
            if bad >= patience:
                stop = i
                break
    stop = min(stop, epoch_cap - 1)
    best = min(range(stop + 1), key=lambda i: val_losses[i])
    return best, stop


def _val_split(task: dict, n_train: int, seed: int):
    """Internal val = 10% of the (prefix) training fold, split by the
    run seed — never the held-out test fold."""
    tr = task["train_order"][:n_train]
    g = np.random.default_rng(seed)
    sh = g.permutation(len(tr))
    n_val = max(1, len(tr) // 10)
    val_idx, tr_idx = tr[sh[:n_val]], tr[sh[n_val:]]
    return tr_idx, val_idx


def held_out_metrics(task: dict, y_pred_logits: np.ndarray, rows=None) -> dict:
    """Per-task held-out metrics. y_pred_logits: (n, R, out_dim)
    (R = 1 for T-del / T-ang) for the trials named by `rows` (the held-
    out fold, or a prefix of it in the pilot). T-ang logits are
    (sin, cos) predictions: metric is circular RMCE (deg) + R^2 on
    (sin, cos)."""
    y = task["y"][rows] if rows is not None else task["y"]
    ceil = task["ceiling"]
    if task["kind"] == "class":
        pred = y_pred_logits[:, 0].argmax(1)
        acc = float((pred == y).mean())
        logits = y_pred_logits[:, 0]
        p = np.clip(np.exp(logits - logits.max(1, keepdims=True)), 1e-12, 1.0)
        p /= p.sum(1, keepdims=True)
        nll = float(-np.log(p[np.arange(len(y)), y]).mean())
        eff = (acc - ceil["chance"]) / (ceil["ceiling"] - ceil["chance"])
        return dict(accuracy=round(acc, 4), nll=round(nll, 4),
                    ceiling=round(ceil["ceiling"], 4), chance=ceil["chance"],
                    efficiency=round(eff, 4))
    if task["kind"] == "binary":
        p = 1.0 / (1.0 + np.exp(-y_pred_logits[:, :, 0]))
        pred = (p > 0.5).astype(np.int64)
        acc = float((pred == y.astype(np.int64)).mean())
        eps = 1e-12
        nll = float(-(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)).mean())
        eff = (acc - ceil["chance"]) / (ceil["ceiling"] - ceil["chance"])
        return dict(accuracy=round(acc, 4), nll=round(nll, 4),
                    ceiling=round(ceil["ceiling"], 4), chance=ceil["chance"],
                    efficiency=round(eff, 4))
    # reg: (sin, cos)
    sc = y_pred_logits[:, 0]
    ang = np.degrees(np.arctan2(sc[:, 0], sc[:, 1])) % 360.0
    H = task["extra"]["H"]
    H = H[rows] if rows is not None else H
    err = np.abs((ang - H + 180.0) % 360.0 - 180.0)
    rmce = float(err.mean())
    ss_res = float(((sc - y) ** 2).sum())
    ss_tot = float(((y - y.mean(0)) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    eff = ceil["ceiling"] / rmce if rmce > 0 else 99.0
    return dict(rmce_deg=round(rmce, 3), r2=round(r2, 4),
                ceiling=round(ceil["ceiling"], 3), chance=round(ceil["chance"], 3),
                efficiency=round(min(eff, 99.0), 4))


def _Y_rows(task: dict, y, r: int) -> np.ndarray:
    """Targets aligned to (n, out_dim) for report step r (ridge input);
    y is the slice of the master target array for the relevant trials.
    class: one-hot; binary: the scalar at step r; reg (R = 1): (sin, cos)."""
    if task["kind"] == "class":
        return np.stack([np.eye(task["spec"]["K"])[c] for c in y], 0)
    if task["kind"] == "binary":
        return y[:, r][:, None]
    return y


def spike_held_out_metrics(task: dict, arm) -> dict:
    """Spike arm: ridge readout (alpha = 1.0, no tuning) fit on the
    first 80% of the training features (fixed prefix — declared),
    evaluated on the held-out fold.

    LEAK-FREE (2026-10-13 fix, review P0): the fit set is the declared
    training prefix ONLY — `Xtr[:n_fit, r]` with the matching training
    targets. The v1 version also passed the held-out features AND
    their true labels into `fit()` and then evaluated on those same
    rows (direct train/test contamination; that is what produced the
    pilot's 1.000 / 0.05 deg / R^2 = 1.0). Held-out labels are used
    only inside `held_out_metrics()`, after prediction."""
    from model import RidgeReadout

    Xtr, Xte = arm.train_feats, arm.test_feats
    n_fit = max(1, int(0.8 * len(Xtr)))
    y_all = task["y"]
    R = len(arm.task["report_steps"])
    outs = []
    for r in range(R):
        m = RidgeReadout(alpha=1.0).fit(
            Xtr[:n_fit, r],
            _Y_rows(task, y_all[arm.train_rows][:n_fit], r))
        outs.append(m.predict(Xte[:, r]))
    logits = np.stack(outs, 1)
    return held_out_metrics(task, logits, arm.test_rows)


def train_tanh(model, task: dict, n_train: int, seed: int, epochs: int,
               patience: int, batch: int, lossf, version: str = "v1") -> dict:
    """One tanh/baseline run: Adam, val-LOSS checkpointing, full loss
    trajectories, Δw recorded. The held-out fold is NOT evaluated here
    (review round 4: the single final evaluation lives in the caller's
    result path, run_rate)."""
    tr_idx, val_idx = _val_split(task, n_train, seed)
    X = torch.tensor(task["x"], dtype=torch.float32)
    if task["kind"] == "class":
        Y = torch.tensor(task["y"], dtype=torch.long)
    else:
        Y = torch.tensor(task["y"].astype(np.float32), dtype=torch.float32)
    xtr, ytr = X[tr_idx], Y[tr_idx]
    xval, yval = X[val_idx], Y[val_idx]

    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.trainable(), lr=2.5e-3)
    g = torch.Generator().manual_seed(seed)
    tr_losses, val_losses = [], []
    best, bad, best_state = float("inf"), 0, copy.deepcopy(model.state_dict())
    epochs_run = 0
    t0 = time.time()
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(len(xtr), generator=g)
        for i in range(0, len(xtr), batch):
            b = perm[i:i + batch]
            opt.zero_grad()
            lossf(model(xtr[b]), ytr[b]).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            tr_loss = float(lossf(model(xtr), ytr))
            val_loss = float(lossf(model(xval), yval))
        tr_losses.append(tr_loss)
        val_losses.append(val_loss)
        epochs_run = epoch + 1
        if val_loss < best - EPS:
            best, bad, best_state = val_loss, 0, copy.deepcopy(model.state_dict())
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    wall = time.time() - t0

    # (held-out evaluation deliberately absent here; see docstring)
    res = {
        "epochs_run": int(epochs_run),
        "early_stopped": epochs_run < epochs,
        "val_loss_best": round(best, 6),
        "train_loss_first": round(tr_losses[0], 6),
        "train_loss_last": round(tr_losses[-1], 6),
        "train_loss_hist": [round(v, 6) for v in tr_losses],
        "val_loss_hist": [round(v, 6) for v in val_losses],
        "wall_s": round(wall, 1),
    }

    circuit = getattr(model, "circuit", None)
    if circuit is not None:
        # Δw: the mandatory pre/post wiring-change record. The initial
        # state is the zero-init convention, so "pre" is known exactly
        # (no need to capture it at t=0).
        rec = circuit.dw_record()
        if rec["dw_eff"].size:
            # version-tagged: repeat runs must not overwrite previous
            # draws' raw arrays (review round 4)
            npz = Path(_dw_dir(version)) / (
                f"dw_{getattr(model, '_arm_name', 'tanh')}_{task['key']}_s{seed}.npz")
            np.savez(npz, **{k: np.ascontiguousarray(v, dtype=np.float32)
                             for k, v in rec.items()})
            res["dw_npz_sha256"] = _npz_sha256(npz)
        res["dw"] = dw_stats(rec) if rec["dw_eff"].size else {"n_edges": 0}
    return res


def _dw_dir(version: str = "v1"):
    d = Path(__file__).parent / "results" / "dw" / version
    d.mkdir(parents=True, exist_ok=True)
    return d


def _npz_sha256(p: Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
