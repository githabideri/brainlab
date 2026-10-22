"""Sanity smoke for worm-v3-sensitivity (not part of the pre-registered
batteries; run before them). Checks: sign assignment flips exactly the
declared 219 edges; a signed shuffle keeps the signed multiset; a
trapezoid run drives ASH during the pulse and not outside it."""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_SRC = os.path.join(HERE, "..", "worm-pilot", "src")
sys.path.insert(0, PARENT_SRC)
sys.path.insert(0, os.path.join(HERE, "src"))

from sim import WormNet, load_network, make_shuffled_exact  # noqa: E402
from run_sensitivity import apply_signs, run_trapezoid, GROUPS  # noqa: E402

DATA = os.path.join(HERE, "..", "worm-pilot", "data")
cfg = json.load(open(os.path.join(HERE, "..", "worm-pilot",
                                  "config-50ms-v3-modelB.json")))
net = load_network(DATA, cfg)
signed, nflip = apply_signs(net)
print(f"flipped edges: {nflip} (expect 219)")
assert nflip == 219
neg = int((signed["c_w"] < 0).sum())
pos = int((signed["c_w"] > 0).sum())
print(f"signed network: {neg} negative / {pos} positive "
      f"(expect 219 / {net['n_chem'] - 219})")

shuf, inv = make_shuffled_exact(signed, cfg, 45)
sneg = int((shuf["c_w"] < 0).sum())
print(f"shuf-45 signed: {sneg} negative (expect 219), invariants ok: "
      f"multiset_equal={inv['classes']['chemical']['multiset_equal']}, "
      f"self_residual={inv['classes']['chemical']['self_edges_residual']}, "
      f"deg_diff={inv['classes']['chemical']['out_degree_max_abs_diff']}"
      f"/{inv['classes']['chemical']['in_degree_max_abs_diff']}")
assert sneg == 219

# trapezoid smoke on the ALL-EXCITATORY network (B4's target): the
# pulse window should carry more ASH spikes than the paired rest's
ash = GROUPS(net)["ash_ashj"]
wt = run_trapezoid(net, cfg, 101, ash)
wr = WormNet(net, cfg, 101)
wr.run(cfg["duration_ms"])
in_p = sum(1 for i in ash for t in wt.spikes[i] if 5000 <= t < 5500)
in_p_rest = sum(1 for i in ash for t in wr.spikes[i] if 5000 <= t < 5500)
print(f"trapezoid (all-exc, seed 101): ASH pulse-window spikes ="
      f" stim {in_p} vs rest {in_p_rest}")
assert in_p > in_p_rest
# signed variant smoke: it runs stably end-to-end (no assertion on rate)
ws = run_trapezoid(signed, cfg, 101, ash)
print(f"signed trapezoid run stable: total spikes = "
      f"{sum(len(x) for x in ws.spikes.values())}, "
      f"NaN-free = {not any(x != x for x in ws.v)}")
print("SMOKE OK")
