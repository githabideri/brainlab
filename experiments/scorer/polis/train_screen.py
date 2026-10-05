#!/usr/bin/env python3
"""S2: train the scorer on the polis decision corpus and run the offline
screen (held-out val: accuracy vs the measured 2B models, damaging-choice
violations, and the shuffled-wiring control of the same training).

Usage:
    python3 train_screen.py [--corpus ./corpus] [--circuit ../circuit.json]
                            [--epochs 400] [--seed 0]

Writes `polis-screen.json`. The internal 20% split (deterministic) is the
only set used for early stopping; the val file is touched only at screen
time, once, per model.
"""
from __future__ import annotations

import argparse
import json
import time

import torch
from torch import nn

from scorer.circuit import load_circuit
from scorer.model import Scorer
from . import adapter

TASKS = {"mine": 7, "harvest": 7}
LLM_MODELS = ("2b", "2b-ft", "2b-ft2")


def load_corpus(path):
    train = [json.loads(l) for l in open(f"{path}/ft2-train.jsonl") if l.strip()]
    val = json.load(open(f"{path}/val.json"))
    baselines = {}
    for m in LLM_MODELS:
        for sl in ("valworld", "abstain"):
            rows = [json.loads(l) for l in open(f"{path}/{m}-{sl}.jsonl") if l.strip()]
            baselines[f"{m}/{sl}"] = rows  # abstain rows have id=null: join by position
    return train, val, baselines


def rows_to_model_rows(rows, vocab):
    return [{
        "x": adapter.encode(r["state"], r.get("mission", ""), vocab),
        "fam": adapter.head_family(r["options"]),
        "target": r["options"].index(r["oracle"]),
        "row": r,
    } for r in rows]


class FamilyTrainer:
    """A Scorer's rows mix head families (mine-list / harvest-list); this
    routes each row to its head for loss, eval and single-row choice."""

    def __init__(self, model: Scorer):
        self.model = model

    def scores(self, x: torch.Tensor, fams: list) -> dict:
        feats, _ = self.model.features(x)
        out = {}
        for fam in TASKS:
            idx = [j for j in range(len(x)) if fams[j] == fam]
            if idx:
                out[fam] = (idx, self.model.heads[fam](feats[idx]))
        return out

    def train_epoch(self, X, fams, y, opt, lossf, batch=32):
        self.model.train()
        for i in range(0, len(X), batch):
            b = slice(i, i + batch)
            scores = self.scores(X[b], fams[i + b])
            opt.zero_grad()
            loss = 0.0
            for fam, (idx, s) in scores.items():
                yb = torch.tensor([y[i + b][j] for j in idx], device=X.device)
                loss = loss + lossf(s, yb) * len(idx) / len(X[b])
            loss.backward()
            opt.step()

    def accuracy(self, X, fams, y) -> float:
        self.model.eval()
        with torch.no_grad():
            hits, n = 0, 0
            for fam, (idx, s) in self.scores(X, fams).items():
                c = s.argmax(-1)
                for j, yj in zip(idx, [y[i] for i in idx]):
                    hits += int(c[j] == yj)
                    n += 1
        return hits / max(1, n)

    def choose(self, row_x: list, fam: str) -> int:
        self.model.eval()
        with torch.no_grad():
            x = torch.tensor([row_x])
            feats, _ = self.model.features(x)
            return self.model.heads[fam](feats).argmax(-1).item()


def train_variant(variant, mtr, miv, circuit_path, state_dim, epochs, seed):
    torch.manual_seed(seed)
    model = Scorer(load_circuit(circuit_path), state_dim=state_dim, tasks=TASKS,
                   variant=variant, encoder_hidden=64, readout_hidden=32)
    t = FamilyTrainer(model)
    opt = torch.optim.Adam(model.trainable(), lr=2e-3)
    lossf = nn.CrossEntropyLoss()
    Xtr = torch.tensor([r["x"] for r in mtr])
    famtr = [r["fam"] for r in mtr]
    ytr = [r["target"] for r in mtr]
    Xiv = torch.tensor([r["x"] for r in miv])
    famiv = [r["fam"] for r in miv]
    yiv = [r["target"] for r in miv]

    best_acc, best_sd, stale = 0.0, None, 0
    for epoch in range(epochs):
        t.train_epoch(Xtr, famtr, ytr, opt, lossf)
        if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            acc = t.accuracy(Xiv, famiv, yiv)
            if acc > best_acc:
                best_acc, stale = acc, 0
                best_sd = {k: v.clone() for k, v in model.state_dict().items()}
            else:
                stale += 10
                if stale >= 200:
                    break
    if best_sd is not None:
        model.load_state_dict(best_sd)
    return model, best_acc


def screen(t: FamilyTrainer, mval, baselines):
    """Held-out val, once: accuracy per model + damaging-choice violations.

    val = 96 valworld rows (joined to the baselines by id) + 45 abstain rows
    (stuck-situation rows, oracle=wait; id=null everywhere, joined by
    position; oracle agreement checked at load).
    """
    acc = {f"scorer-{t.model.circuit.variant}": [0, 0], **{m: [0, 0] for m in LLM_MODELS}}
    viol = {k: [] for k in acc}
    slices = {"valworld": 0, "abstain": 0}
    abstain_idx = 0
    oracle_mismatch = 0
    for v in mval:
        r = v["row"]
        rid = r.get("id")
        label = rid or f"abstain-{abstain_idx}"
        task = adapter.parse_state(r["state"]).get("task", "")
        sl = "abstain" if (r.get("family") == "abstain" or adapter.mission_class(task) == "other") else "valworld"
        slices[sl] += 1
        key = f"scorer-{t.model.circuit.variant}"
        choice = r["options"][t.choose(v["x"], v["fam"])]
        acc[key][0] += int(choice == r["oracle"])
        acc[key][1] += 1
        for rule in adapter.violations(r["state"], choice):
            viol[key].append({"row": label, "rule": rule})
        for m in LLM_MODELS:
            if sl == "abstain":
                b = baselines[f"{m}/abstain"][abstain_idx] if abstain_idx < len(baselines[f"{m}/abstain"]) else None
                if b is not None and b.get("oracle") != r["oracle"]:
                    oracle_mismatch += 1
                abstain_idx += 1
            else:
                b = next((x for x in baselines[f"{m}/valworld"] if x["row"] == rid), None)
            if b is None:
                continue
            acc[m][0] += int(b["choice"] == r["oracle"])
            acc[m][1] += 1
            for rule in adapter.violations(r["state"], b["choice"]):
                viol[m].append({"row": label, "rule": rule})
    fmt = lambda a: round(100 * a[0] / a[1], 2) if a[1] else None
    return {
        "n": len(mval),
        "slices": slices,
        "abstain_oracle_mismatches": oracle_mismatch,
        "accuracy_pct": {k: fmt(v) for k, v in acc.items()},
        "violations": {k: {"n": len(v),
                           "rules": sorted({x["rule"] for x in v}),
                           "rows": sorted({x["row"] for x in v})}
                       for k, v in viol.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default="./corpus")
    ap.add_argument("--circuit", default="../circuit.json")
    ap.add_argument("--epochs", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="polis-screen.json")
    args = ap.parse_args()

    train, val, baselines = load_corpus(args.corpus)
    vocab = adapter.build_vocab(train)
    state_dim = adapter.state_dim(vocab)
    with open("vocab.json", "w") as f:
        json.dump({k: list(v) for k, v in vocab.items()}, f, indent=1)
    print(f"vocab: item={len(vocab['item'])} since={len(vocab['since'])} "
          f"last={len(vocab['last'])} state_dim={state_dim}", flush=True)

    mtr = rows_to_model_rows(train, vocab)
    mval = rows_to_model_rows(val, vocab)
    g = torch.Generator().manual_seed(args.seed)
    perm = torch.randperm(len(mtr), generator=g).tolist()
    n_iv = len(mtr) // 5
    iv_set = set(perm[:n_iv])
    mrows_tr = [r for j, r in enumerate(mtr) if j not in iv_set]
    mrows_iv = [r for j, r in enumerate(mtr) if j in iv_set]
    print(f"split: train={len(mrows_tr)} internal-val={len(mrows_iv)} screen-val={len(mval)}", flush=True)

    t0 = time.time()
    runs = []
    for variant in ("fly", "shuffled"):
        model, best_acc = train_variant(variant, mrows_tr, mrows_iv,
                                        args.circuit, state_dim, args.epochs, args.seed)
        res = {"variant": variant, "internal_val_acc": round(best_acc, 4),
               "val": screen(FamilyTrainer(model), mval, baselines)}
        runs.append(res)
        print(json.dumps(res, indent=1), flush=True)
    report = {"corpus": args.corpus, "seed": args.seed, "state_dim": state_dim,
              "wall_s": round(time.time() - t0, 1), "runs": runs}
    with open(args.out, "w") as f:
        json.dump(report, f, indent=1)
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
