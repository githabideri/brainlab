"""The polis 8-line state -> fixed feature vector (closed vocab, no text in the net).

The 8-line text is the byte-frozen reflex prompt of the r2 contract
(task / phase / facts / carrying / items / since_last_step / last_action /
proposed action). The adapter parses it deterministically; every string
field maps onto a frozen vocabulary built from the TRAIN corpus only (the
val set's unseen values fall into the `other` bucket — no leakage).

The vector feeds the Scorer's learned encoder; the head family is chosen
by the row's candidate tuple (mine-list vs harvest-list).
"""
from __future__ import annotations

import re

MISSIONS = ("mine", "harvest", "build")
PHASES = ("travel", "mine", "pickup", "return", "done", "build", "harvest")
ACTIONS = ("goto_target", "mine_target", "harvest_target", "pickup_item",
           "place_block", "give_tool", "goto_base", "wait")


def parse_state(state: str) -> dict:
    f = {}
    for line in state.split("\n"):
        if line.startswith("task: "):
            f["task"] = line[6:]
        elif line.startswith("current phase: "):
            f["phase"] = line[15:]
        elif line.startswith("facts: "):
            body = line[7:]
            m = re.search(r"near_target=(\w+)", body)
            f["near_t"] = m.group(1) == "yes" if m else False
            m = re.search(r"near_base=(\w+)", body)
            f["near_b"] = m.group(1) == "yes" if m else False
            # fixture label varies by mission (marker_present / crop_present);
            # the presence flag is what matters
            m2 = re.search(r", (\w+_present)=(yes|no)$", body)
            f["fixture"] = m2.group(2) == "yes" if m2 else False
        elif line.startswith("carrying: "):
            body = line[10:]
            f["carrying"] = [] if body == "empty" else body.split(", ")
        elif line.startswith("items: "):
            body = line[7:]
            f["items"] = [] if body == "none" else body.split(", ")
        elif line.startswith("since_last_step: "):
            f["since"] = line[17:]
        elif line.startswith("last_action: "):
            f["last_raw"] = line[15:]
        elif line.startswith("proposed action: "):
            f["proposal"] = line[17:]
    return f


def normalize_last(raw: str) -> str:
    """Collapse the dynamic item specifics out of the last-action messages."""
    s = raw
    s = re.sub(r"picked \d+x \S+", "picked", s)
    s = re.sub(r"dropped \d+x game:pickaxe-\w+", "dropped-pickaxe", s)
    s = re.sub(r"dropped \d+x \S+", "dropped", s)
    s = re.sub(r"harvested \S+ with collection", "harvested-collected", s)
    s = re.sub(r"harvested \S+", "harvested", s)
    s = re.sub(r"Tool required: block needs tier \d+", "tool-required", s)
    return s


def _vocab(rows, get) -> tuple:
    seen = []
    for r in rows:
        v = get(r)
        if isinstance(v, list):
            for x in v:
                if x not in seen:
                    seen.append(x)
        elif v and v not in seen:
            seen.append(v)
    return tuple(sorted(seen))


def build_vocab(train_rows: list) -> dict:
    """Frozen closed sets from the train corpus only."""
    parsed = [parse_state(r["state"]) for r in train_rows]
    vocab = {
        "mission": MISSIONS,
        "phase": PHASES,
        "item": _vocab(train_rows, lambda r: parse_state(r["state"]).get("carrying", []))
              + _vocab(train_rows, lambda r: parse_state(r["state"]).get("items", [])),
        "since": _vocab(parsed, lambda r: r.get("since", "")),
        "last": _vocab(parsed, lambda r: normalize_last(r.get("last_raw", ""))),
    }
    vocab["item"] = tuple(sorted(set(vocab["item"])))
    vocab["since"] = tuple(sorted(set(vocab["since"])))
    vocab["last"] = tuple(sorted(set(vocab["last"])))
    vocab["action"] = ACTIONS
    return vocab


def mission_class(task: str) -> str:
    """The task line is the primary mission signal: some corpus rows carry a
    truncated `mission` field (a generator bug), but the task text is intact
    and matches the r2 contract templates."""
    t = (task or "").strip()
    if t.startswith("mine the"):
        return "mine"
    if t.startswith("harvest the"):
        return "harvest"
    if t.startswith("place a block") or t.startswith("build"):
        return "build"
    return "other"


def head_family(options: list) -> str:
    if "mine_target" in options:
        return "mine"
    if "harvest_target" in options:
        return "harvest"
    raise ValueError(f"unknown options tuple: {options}")


def encode(state: str, mission: str, vocab: dict) -> list:
    """One 8-line state -> feature vector (closed one-hot + booleans + counts)."""
    f = parse_state(state)
    mcls = mission_class(f.get("task", "")) if f.get("task") else (mission if mission in MISSIONS else "other")
    v = []
    def oh(value, table):
        for t in table:
            v.append(1.0 if value == t else 0.0)
    oh(mcls, list(vocab["mission"]) + ["other"])
    ph = f.get("phase", "")
    oh(ph if ph in PHASES else "other", list(vocab["phase"]) + ["other"])
    v.append(1.0 if f.get("near_t") else 0.0)
    v.append(1.0 if f.get("near_b") else 0.0)
    v.append(1.0 if f.get("fixture") else 0.0)
    def item_block(items):
        for it in vocab["item"]:
            v.append(1.0 if it in items else 0.0)
        v.append(1.0 if len(items) == 0 else 0.0)  # none/empty
    item_block(f.get("carrying", []))
    v.append(float(len(f.get("carrying", []))))
    item_block(f.get("items", []))
    v.append(float(len(f.get("items", []))))
    oh(f.get("since", ""), list(vocab["since"]) + ["other"])
    oh(normalize_last(f.get("last_raw", "")), list(vocab["last"]) + ["other"])
    oh(f.get("proposal", ""), list(vocab["action"]) + ["other"])
    return v


def state_dim(vocab: dict) -> int:
    return (len(MISSIONS) + 1) + (len(PHASES) + 1) + 3 + \
           (len(vocab["item"]) + 1 + 1) + (len(vocab["item"]) + 1 + 1) + \
           (len(vocab["since"]) + 1) + (len(vocab["last"]) + 1) + (len(ACTIONS) + 1)


def violations(state: str, choice: str) -> list:
    """The judge-rule 'no' conditions, made checkable: a choice contradicts
    a fact the state itself asserts (missing tool / missing fixture / nothing
    to pick up / tool already held). These are the *damaging* class for the
    offline screen."""
    f = parse_state(state)
    out = []
    carrying = f.get("carrying", [])
    has_pickaxe = any("pickaxe" in c for c in carrying)
    if choice == "mine_target" and not has_pickaxe:
        out.append("mine-without-pickaxe")
    if choice == "give_tool" and has_pickaxe:
        out.append("give-tool-already-held")
    if choice == "harvest_target" and not f.get("fixture"):
        out.append("harvest-missing-crop")
    if choice == "pickup_item" and not f.get("items"):
        out.append("pickup-nothing")
    return out
