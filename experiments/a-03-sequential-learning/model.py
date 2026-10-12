"""A-03 model arms.

tanh   TanhSeq — the A-02 architecture run as a sequence: encoder ->
       sensory drive -> SeqCircuit (persistent hidden state, 4 internal
       propagation steps per input step) -> LayerNorm readout over the
       384 output nodes -> per-task head. Report steps declared per
       task; outputs are only taken at those steps (loss is computed on
       them).
gru    conventional recurrent baseline: one GRU layer (128 hidden).
mlp    conventional feedforward baseline on a window of the last W steps
       (W = 4 for T-del/T-ang, 5 for T-xor so it can see both XOR
       operands) — the declared no-long-memory comparator.
spike  the same graph under B-01's Shiu-2024 LIF (lif.py, verbatim):
       circuit FROZEN (B-01 treatment); fixed declared Poisson drive to
       the 256 sensory nodes; the only learned object is a linear ridge
       readout on output-node rates. Delta-w is zero by construction.

Spike-arm efficacy & drive declarations (pilot-verified 2026-10-12; see
the README "Sizing outcome" section and the report):
  * the per-target-normalized 0.275 mV mapping (B-01's constants
    applied to the signed atlas) is DYNAMICALLY INERT on this circuit:
    measured max g over a full trial = 0.045 mV, zero spikes anywhere
    (the flywire signed weights are small integers; per-target
    normalization across ~28 inputs crushes each edge to ~0.01 mV).
  * declared mapping actually used: B-01's efficacy *regime* —
    sign x min(log1p|w|, c) x k with the p95 per-edge effect scaled to
    4.7 mV (B-01's own capped maximum: min(PSD, p95=17) x 0.275 mV).
  * tonic 10 mV on the 384 output nodes (the 4 mV declared in the
    pre-registration leaves v at −48 mV, below the −45 mV threshold:
    the readout population cannot fire at all; 10 mV puts the
    equilibrium at −42 mV, a live ~refractory-limited population whose
    rate is modulated by the network's synaptic input; the ridge
    standardization removes the baseline). The per-trial LIF state
    reset is a fresh construction (the verbatim lif.py `reset()` has a
    latent fill_-with-1-d-bug; B-01's single-session run never called
    it — handed to B-02 Stage 1 as a logged finding).
  * the LIF loop runs single-threaded (measured 10x faster than the
    4-thread setting on these 1,536-element kernels; the tanh arm keeps
    4 threads).
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

import lif
import tasks
from circuit import SeqCircuit

# ---------------------------------------------------------------- tanh


def _head(n_in: int, n_out: int) -> nn.Linear:
    h = nn.Linear(n_in, n_out)
    nn.init.orthogonal_(h.weight, 0.01)
    nn.init.zeros_(h.bias)
    return h


class TanhSeq(nn.Module):
    def __init__(self, doc: dict, src, tgt, w, d_in: int, out_dim: int,
                 report_steps: tuple, enabled: bool = True,
                 n_prop: int = 2):
        super().__init__()
        # n_prop = 2: declared A-03 sizing revision (see circuit.py header)
        self.circuit = SeqCircuit(doc, src, tgt, w, enabled=enabled,
                                  n_prop=n_prop)
        n_sens, n_out = len(self.circuit.sensory), len(self.circuit.outputs)
        self.report_steps = tuple(report_steps)
        self.encoder = nn.Sequential(
            nn.Linear(d_in, 256), nn.ELU(),
            nn.Linear(256, 256), nn.ELU(),
            nn.LayerNorm(256),
        )
        self.drive = nn.Linear(256, n_sens)
        self.readout = nn.LayerNorm(n_out, eps=1e-6)
        self.head = _head(n_out, out_dim)

    def forward(self, xs: torch.Tensor) -> torch.Tensor:
        """xs: (B, T, d). Returns (B, R, out_dim) at the report steps."""
        B = xs.shape[0]
        dev = xs.device
        h = self.circuit.initial(B, dev)
        outs = []
        for t in range(xs.shape[1]):
            e = self.encoder(xs[:, t])
            d = self.circuit.initial(B, dev)
            d.index_copy_(1, self.circuit.sensory, self.drive(e))
            h = self.circuit.step_persistent(h, d)
            if t in self.report_steps:
                outs.append(self.head(self.readout(h[:, self.circuit.outputs])))
        return torch.stack(outs, dim=1)

    def trainable(self):
        return ([p for m in (self.encoder, self.drive, self.readout, self.head)
                 for p in m.parameters()]
                + self.circuit.trainable())


class GRUBaseline(nn.Module):
    """1 GRU layer, 128 hidden, head applied at the report steps."""

    def __init__(self, d_in: int, out_dim: int, report_steps: tuple, hidden: int = 128):
        super().__init__()
        self.report_steps = tuple(report_steps)
        self.rnn = nn.GRU(d_in, hidden, batch_first=True)
        self.head = _head(hidden, out_dim)

    def forward(self, xs):
        out, _ = self.rnn(xs)
        idx = torch.tensor(self.report_steps, device=xs.device)
        return self.head(out[:, idx])

    def trainable(self):
        return list(self.parameters())


class MLPCascade(nn.Module):
    """Feedforward on the window of the last W steps ending at each
    report step. W = len(report_window) (4; 5 for T-xor)."""

    def __init__(self, d_in: int, out_dim: int, report_steps: tuple, window: int):
        super().__init__()
        self.report_steps = tuple(report_steps)
        self.window = window
        self.net = nn.Sequential(nn.Linear(window * d_in, 256), nn.ReLU(),
                                 nn.Linear(256, 256), nn.ReLU())
        self.head = _head(256, out_dim)

    def forward(self, xs):
        outs = []
        for t in self.report_steps:
            w = xs[:, max(0, t - self.window + 1):t + 1]
            outs.append(self.head(self.net(w.reshape(w.shape[0], -1))))
        return torch.stack(outs, dim=1)

    def trainable(self):
        return list(self.parameters())


def out_dim(task_key: str) -> int:
    return {"T-del": 4, "T-ang": 2, "T-xor": 1}[task_key]


def make_rate_model(arm: str, doc: dict, wirings: dict, task: dict):
    if arm == "gru":
        return GRUBaseline(task["d"], out_dim(task["key"]), task["report_steps"])
    if arm == "mlp":
        window = 5 if task["key"] == "T-xor" else 4
        return MLPCascade(task["d"], out_dim(task["key"]), task["report_steps"], window)
    src, tgt, w = wirings[arm]
    return TanhSeq(doc, src, tgt, w, task["d"], out_dim(task["key"]),
                   task["report_steps"], enabled=len(src) > 0)


def loss_fn(task: dict) -> nn.Module:
    if task["kind"] == "class":
        return nn.CrossEntropyLoss()
    if task["kind"] == "binary":
        return nn.BCEWithLogitsLoss()
    return nn.MSELoss()


def task_loss(task: dict, logits: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """logits: (B, R, out_dim); y: (B, out_dim) for class/reg (R=1 tasks)
    or (B, R) for binary. Returns the mean over report steps."""
    if task["kind"] == "class":
        return nn.functional.cross_entropy(logits[:, 0], y)
    if task["kind"] == "binary":
        return nn.functional.binary_cross_entropy_with_logits(logits[:, :, 0], y)
    return nn.functional.mse_loss(logits[:, 0], y)


# ---------------------------------------------------------------- spike

W_X_SEED_OFFSET = 5000
R0 = 2.0        # Hz, per sensory node (declared)
RMAX = 48.0     # Hz, max stimulus-driven rate (declared)
TONIC_OUT = 10.0  # mV steady-state offset on the 384 output nodes (declared)
EFFECT_P95_MV = 4.7  # B-01's capped per-edge maximum (min(PSD,p95=17) x 0.275)
STEP_MS = 100    # one task step = 100 ms of LIF
WINDOW_MS = 200  # readout window ending at the report step


def w_x_projection(task: dict) -> np.ndarray:
    """Fixed master-seed input projection d -> 256 sensory nodes (the
    declared input encoding of the spike arm)."""
    spec = task["spec"]
    g = np.random.default_rng(tasks.MASTER_SEED + W_X_SEED_OFFSET
                              + tasks.TASKS.index(spec))
    return (g.normal(0.0, 1.0 / np.sqrt(task["d"]),
                     (task["d"], 256))).astype(np.float32)


def lif_weights(doc: dict, src, tgt, w):
    """Declared efficacy rule for the spike arm (pilot-verified):
    sign x min(log1p|w|, c) x k, with the p95 per-edge effect scaled to
    4.7 mV — B-01's own capped maximum (min(PSD, p95=17) x 0.275 mV).
    The per-target-normalized 0.275 mV variant is dynamically inert on
    this circuit (measured; see module docstring)."""
    mag = np.log1p(np.abs(w))
    c = np.percentile(mag, 95)
    k = EFFECT_P95_MV / c
    return (np.sign(w) * np.minimum(mag, c) * k).astype(np.float32)


class SpikeArm:
    """Frozen LIF circuit (B-01 treatment) + declared Poisson drive +
    ridge readout on output-node rates. The only learned object is the
    ridge.

    Per-trial state reset is done by *re-instantiating* the LIFNet
    (constructor initial state = B-01's initial state, byte-identical
    lif.py). The verbatim lif.py's `reset()` method has a latent bug
    (`fill_` called with a 1-d value tensor — it would raise on any
    call); B-01's single-session run never called it. A-03 therefore
    does not call it either; the defect is handed to B-02 Stage 1 as a
    logged finding (see the report)."""

    def __init__(self, doc: dict, wiring: tuple, task: dict,
                 X_all: np.ndarray, train_idx: np.ndarray):
        src, tgt, w = wiring
        self._src = src
        self._tgt = tgt
        self._w = lif_weights(doc, src, tgt, w)
        self._n = len(doc["neurons"])
        self._tonic = self._tonic_arr(doc)
        self.lif = self._new_lif()
        self.outputs = np.array(
            [i for i, n in enumerate(doc["neurons"]) if n["group"] in (19, 23)])
        self.pos = np.full(len(doc["neurons"]), -1, dtype=np.int64)
        self.pos[self.outputs] = np.arange(len(self.outputs))
        self.Wx = w_x_projection(task)
        self.task = task
        # per-(step, sensory-node) min/max of the encoded input over the
        # training fold (declared normalization of the Poisson drive)
        Xf = X_all.reshape(-1, X_all.shape[-1])
        Z = (Xf @ self.Wx).reshape(X_all.shape[0], X_all.shape[1],
                                   self.Wx.shape[1])  # (N, T, 256)
        zt = Z[train_idx]
        self.m = zt.min(axis=0)                   # (T, 256)
        self.M = np.maximum(zt.max(axis=0), self.m + 1e-6)

    def _new_lif(self):
        return lif.LIFNet(self._src, self._tgt, self._w, self._n,
                          tonic=self._tonic)

    @staticmethod
    def _tonic_arr(doc):
        tonic = np.zeros(len(doc["neurons"]))
        for i, n in enumerate(doc["neurons"]):
            if n["group"] in (19, 23):
                tonic[i] = TONIC_OUT
        return tonic

    def run_features(self, X: np.ndarray, rows: np.ndarray) -> np.ndarray:
        """X: (n_trials, T, d); rows: the trial indices of X in the
        master order (retained so the ridge targets align row-wise).
        Returns features (n_trials, R, 384): output-node spike rates
        (Hz) over the window ending at each report step."""
        self.feat_rows = rows  # caller also sets train_rows/test_rows
        rep = self.task["report_steps"]
        window_steps = WINDOW_MS // STEP_MS
        feats = np.zeros((len(X), len(rep), len(self.outputs)), dtype=np.float32)
        prev_threads = torch.get_num_threads()
        torch.set_num_threads(1)  # declared: 10x faster on these kernels
        try:
            for i, x in enumerate(X):
                net = self._new_lif()  # per-trial reset = fresh construction
                step_counts = []
                for s in range(x.shape[0]):
                    z = x[s] @ self.Wx
                    u = np.clip((z - self.m[s]) / (self.M[s] - self.m[s]),
                                0.0, 1.0)
                    lam = torch.tensor(((R0 + RMAX * u).astype(np.float32))
                                       / 1000.0)  # per ms
                    cnt = np.zeros(len(self.outputs), dtype=np.float64)
                    for _ in range(STEP_MS):
                        c = torch.poisson(lam)
                        k = int(c.sum())
                        if k > 0:
                            sp = net.step((c.nonzero().flatten().to(torch.int64),
                                           c[c > 0].to(torch.int64)))
                        else:
                            sp = net.step()
                        if sp is not None:
                            oi = self.pos[sp.numpy()]
                            oi = oi[oi >= 0]
                            if len(oi):
                                cnt += np.bincount(oi, minlength=len(self.outputs))
                    step_counts.append(cnt)
                for j, s in enumerate(rep):
                    lo = max(0, s + 1 - window_steps)
                    wcnt = sum(step_counts[k] for k in range(lo, s + 1))
                    feats[i, j] = wcnt / (WINDOW_MS / 1000.0)
        finally:
            torch.set_num_threads(prev_threads)
        return feats


# ---------------------------------------------------------------- ridge

class RidgeReadout:
    """Plain linear ridge (alpha = 1.0, no tuning): standardize the
    features with the fit-set statistics, fit [X, 1]."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.mu = None
        self.sd = None
        self.beta = None

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "RidgeReadout":
        self.mu = X.mean(0)
        self.sd = np.maximum(X.std(0), 1e-8)
        Xs = (X - self.mu) / self.sd
        A = np.hstack([Xs, np.ones((len(X), 1))])
        B = A.T @ A
        B.flat[:: A.shape[1] + 1] += 0.0  # no penalty on the bias
        B.flat[:: A.shape[1] + 1] -= 0.0
        reg = self.alpha * np.eye(A.shape[1])
        reg[-1, -1] = 0.0
        self.beta = np.linalg.solve(B + reg, A.T @ Y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        Xs = (X - self.mu) / self.sd
        return np.hstack([Xs, np.ones((len(X), 1))]) @ self.beta
