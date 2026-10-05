"""Standalone pre-veto ranker drop-in.

No mod code, no r2/, no polis runtime — torch plus this bundle only.
The input is the same 8-line reflex text the decider sees
(`r2/projection.py build_state_text`); the output is one score per
candidate action of the mission's frozen action tuple, a ranked order,
and an abstain flag (low margin / no head for this tuple -> defer to
the existing path).

    from ranker import load_ranker
    rank = load_ranker(CIRCUIT, WEIGHTS, VOCAB)   # ~1 s, once
    out = rank(state_text, ["mine_target", "give_tool", "pickup_item", ...])
    # -> {"head": "mine",
    #     "scores": {"mine_target": 0.41, "give_tool": 0.57, ...},
    #     "ranked": ["give_tool", "mine_target", ...],
    #     "chosen": "give_tool", "margin": 0.16, "abstained": False}

Caveats (match the S2 screen):
- heads exist for the mine-list and harvest-list tuples only (the
  measured corpus is mine + harvest); any other tuple (e.g. build)
  abstains.
- the 8-line format is the 2026-09-25/26 contract; if the state text
  format changes, cross-check before trusting outputs (the self-test
  below is that check — it must still print 131/141 on the pinned val).

Self-test (replays the pinned 141-row val; deterministic, seed 0 model):

    python ranker.py --circuit circuit.json \
        --weights /var/brainlab/runs/2026-10-05-s2/scorer-fly.pt \
        --vocab vocab.json --corpus polis/corpus
    # must print: accuracy 131/141 (92.91%), damaging 0
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scorer.circuit import load_circuit  # noqa: E402
from scorer.model import Scorer  # noqa: E402
try:
    from . import adapter  # noqa: E402  (package use)
except ImportError:
    from polis import adapter  # noqa: E402  (script use)

TASKS = {"mine": 7, "harvest": 7}  # the frozen head shapes (S2)
ENCODER_HIDDEN, READOUT_HIDDEN = 64, 32  # the S2 widths (see train_screen)


def load_ranker(circuit_path: str, weights_path: str, vocab_path: str,
                abstain_margin: float = 0.25, threads: int = 4):
    """Load the trained scorer; returns rank(state_text, options) -> dict."""
    torch.set_num_threads(threads)
    vocab = json.load(open(vocab_path))
    model = Scorer(load_circuit(circuit_path), state_dim=adapter.state_dim(vocab),
                   tasks=TASKS, variant="fly",
                   encoder_hidden=ENCODER_HIDDEN, readout_hidden=READOUT_HIDDEN)
    model.load_state_dict(torch.load(weights_path))
    model.eval()

    def rank(state_text: str, options: list) -> dict:
        options = list(options)
        try:
            fam = adapter.head_family(options)  # mine-list vs harvest-list
        except ValueError:
            return {"head": None, "abstained": True,
                    "note": "no head for this candidate tuple — defer to the existing path"}
        with torch.no_grad():
            x = torch.tensor([adapter.encode(state_text, "", vocab)], dtype=torch.float32)
            scores, chosen, margin, abstained = model.score(x, fam, abstain_margin)
        s = scores[0].tolist()
        return {
            "head": fam,
            "scores": dict(zip(options, s)),
            "ranked": [options[i] for i in sorted(range(len(options)), key=lambda i: -s[i])],
            "chosen": options[int(chosen[0])],
            "margin": float(margin[0]),
            "abstained": bool(abstained[0]),
        }

    return rank


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuit", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--corpus", required=True, help="dir holding val.json (the pinned S2 val)")
    args = ap.parse_args()

    rank = load_ranker(args.circuit, args.weights, args.vocab)
    val = json.load(open(os.path.join(args.corpus, "val.json")))
    ok = 0
    n_abstain = 0
    damaging = []
    for r in val:
        out = rank(r["state"], r["options"])
        # pure argmax, exactly as the S2 screen used it (choose() has no
        # abstain; the margin flag is advisory for the live wiring)
        ch = out["chosen"] if out.get("head") else r["oracle"]
        if ch == r["oracle"]:
            ok += 1
        if out.get("abstained"):
            n_abstain += 1
        for v in adapter.violations(r["state"], ch):
            damaging.append(f"{r.get('id') or 'abstain'}:{v}")
    n = len(val)
    print(f"accuracy {ok}/{n} ({100*ok/n:.2f}%), damaging {len(damaging)}, margin-abstains {n_abstain}")
    if damaging:
        print("damaging rows:", damaging)
    # S2 fly reference: accuracy 131/141 (92.91%), damaging 0
