"""Background-drive semantics test (review round 5, 2026-10-13).

The v2 simulation had a second, unlabelled behaviour: every background
Poisson event was not only an external current injection (w_bg) but
was ALSO enqueued as a presynaptic event, so it propagated through the
neuron's chemical output fan-out even when the neuron never crossed
threshold. Round 5 labels the two models explicitly:

  * Model A (default, cfg["bg_propagate"] = False): pure external
    current; only genuine threshold-crossing spikes propagate.
  * Model B (cfg["bg_propagate"] = True; historical v2 behaviour):
    background events also propagate as forced presynaptic events.

This test builds a minimal 2-neuron network (0 -> 1 chemical, weight
chosen so one delivered event is sufficient to bring 1 to threshold;
no background current, w_bg = 0; lambda_bg = 1000 so that with p =
lambda_bg*dt/1000 = 1 EVERY neuron gets a background event EVERY step)
and asserts:

  1. Model A: neuron 1 never spikes (the background events at neuron
     0 do NOT propagate), and neuron 0 itself never spikes either
     (w_bg = 0) — total spikes 0.
  2. Model B: neuron 1 DOES spike (the forced propagation delivers
     real chemical current), with neuron 0 itself still silent.
  3. the background event trains are byte-identical across the two
     models for the same seed (the paired-input guarantee is
     model-independent: the Poisson draws do not depend on the
     propagation choice).

Run:  python src/test_bg_models.py
Exit 0 = all checks hold; non-zero = a check failed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

from sim import WormNet  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(f"  [{'ok' if cond else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def mini_net():
    """2 neurons: 0 -> 1 chemical (raw w = 1, alpha = 20 -> 20 mV of
    synaptic current: enough to push neuron 1 from -52 to -45, above
    threshold -45... v0 + g = -32 > -45). No gap junctions."""
    n = 2
    c_src = np.array([0], dtype=np.int64)
    c_dst = np.array([1], dtype=np.int64)
    c_w = np.array([20.0])
    u_src, counts = np.unique(c_src, return_counts=True)
    return {"n": n, "names": ["A", "B"], "idx": {"A": 0, "B": 1},
            "c_src": c_src, "c_dst": c_dst, "c_w": c_w,
            "u_src": u_src, "u_start": np.concatenate([[0], np.cumsum(counts)]),
            "g_src": np.zeros(0, dtype=np.int64),
            "g_dst": np.zeros(0, dtype=np.int64),
            "g_w": np.zeros(0),
            "g_pairs": [], "n_chem": 1, "n_gap_pairs": 0}


def mini_cfg(bg_propagate):
    return {"dt": 1.0, "tau_m": 20.0, "tau_syn": 100.0,
            "v0": -52.0, "v_th": -45.0, "v_rst": -52.0,
            "refractory_ms": 2.2, "delay_ms": 1.8, "delay_steps": 2,
            "lambda_bg": 1000.0,   # p = 1.0: every neuron, every step
            "w_bg": 0.0,           # no external current (isolate the
                                   # propagation channel)
            "bg_propagate": bg_propagate}


def run_model(model):
    w = WormNet(mini_net(), mini_cfg(model), seed=7)
    w.run(500)
    return w


def main():
    print("background-drive models (review round 5)")
    wa = run_model(False)
    wb = run_model(True)
    na = sum(len(v) for v in wa.spikes.values())
    nb = sum(len(v) for v in wb.spikes.values())
    print(f"  model A spikes: neuron0={len(wa.spikes[0])}, "
          f"neuron1={len(wa.spikes[1])} (total {na})")
    print(f"  model B spikes: neuron0={len(wb.spikes[0])}, "
          f"neuron1={len(wb.spikes[1])} (total {nb})")
    check("model A: no background propagation — zero spikes",
          na == 0 and len(wa.spikes[1]) == 0)
    check("model A: neuron 0 never fires (w_bg = 0, no self-injection)",
          len(wa.spikes[0]) == 0)
    check("model B: forced propagation delivers real chemical current "
          "— neuron 1 spikes",
          nb > 0 and len(wb.spikes[1]) > 0)
    check("model B: the source neuron 0 itself still never fires",
          len(wb.spikes[0]) == 0)
    check("paired-input: background event trains byte-identical across "
          "models (same seed)",
          wa.bg_events == wb.bg_events)
    check("paired-input: trains are non-empty (p = 1 per step)",
          len(wa.bg_events) > 0 and len(wa.bg_events[0][1]) == 2)


if __name__ == "__main__":
    main()
    if FAILS:
        print(f"\n{len(FAILS)} check(s) FAILED: {FAILS}")
        sys.exit(1)
    print("\nall background-model checks hold")
