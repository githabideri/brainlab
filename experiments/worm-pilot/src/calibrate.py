"""Setup-phase calibration (runs BEFORE the config is frozen).

For each declared variant (A: tau_syn = 5 ms, the lab convention,
primary; B: tau_syn = 50 ms, a physiological-range summation
variant — see README), a logged grid search chooses, in order:

  * alpha  — chemical gain (per sqrt-section): the largest value that
             keeps the rest run stable and below 20 Hz mean;
  * (lambda_bg, w_bg) — background drive: the stable grid point
             closest to a ~2 Hz sparse rest;
  * beta   — gap-junction conductance (1/ms per released EM section):
             set so the mean gap current at rest is 10% of the mean
             chemical synaptic current (the README's declared ratio);
  * S      — stimulus depolarization (mV) on ASHL/ASHR: smallest grid
             value giving >= 20 Hz ASH firing during the pulse.

Writes config-<tau>.json (frozen afterwards) and calibration-log.json.
"""
import json
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim import load_network, WormNet  # noqa: E402

DATA = os.path.join(HERE, "..", "data")
PROVISIONAL_BETA = 0.001  # grid-phase placeholder (see below)
VARIANTS = {"5ms": 5.0, "50ms": 50.0}


def base_cfg(tau_syn):
    return {"dt": 1.0, "tau_m": 20.0, "tau_syn": tau_syn,
            "v0": -52.0, "v_th": -45.0, "v_rst": -52.0,
            "refractory_ms": 2.2, "delay_ms": 1.8, "delay_steps": 2,
            "lambda_bg": 1.0, "w_bg": 0.5,
            "duration_ms": 15000,
            "stim_start_ms": 5000, "stim_dur_ms": 500,
            "stim_ids": ["ASHL", "ASHR"]}


def rest_stats(net, cfg):
    w = WormNet(net, cfg, 0)
    w.run(cfg["duration_ms"])
    rates = np.array([len(w.spikes[i]) for i in range(net["n"])]) \
        / (cfg["duration_ms"] / 1000.0)
    return {"mean_hz": float(rates.mean()), "max_hz": float(rates.max()),
            "nan": bool(np.isnan(w.v).any()), "net": w,
            "mean_g_mV": w.mean_g}


def calibrate_variant(tau_syn):
    log = {"alpha_grid": {}, "bg_grid": {}, "stim_grid": {},
           "selected": {}, "provisional_beta_for_grid": PROVISIONAL_BETA}

    # --- stage 1: alpha (gap at a small provisional value, so the
    # grid measures the chemical dynamics)
    candidates = []
    for alpha in [0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4]:
        cfg = {**base_cfg(tau_syn), "alpha": alpha,
               "beta": PROVISIONAL_BETA}
        net = load_network(DATA, cfg)
        st = rest_stats(net, cfg)
        entry = {k: st[k] for k in ("mean_hz", "max_hz", "mean_g_mV", "nan")}
        log["alpha_grid"][alpha] = entry
        if not entry["nan"] and entry["mean_hz"] < 20 \
                and entry["max_hz"] < 100:
            candidates.append((alpha, entry))
        if entry["max_hz"] > 100:
            break
    if candidates:
        alpha, aentry = max(candidates, key=lambda c: c[0])
    else:
        item = min(log["alpha_grid"].items(),
                   key=lambda kv: abs(kv[1]["mean_hz"] - 2.0))
        alpha, aentry = item[0], item[1]
        log["selected"]["alpha_note"] = "no stable candidate; closest to 2 Hz"
    log["selected"]["alpha"] = alpha
    log["selected"]["alpha_entry"] = aentry

    # --- stage 2: background drive (stable point closest to ~2 Hz)
    cfgB = {**base_cfg(tau_syn), "alpha": alpha, "beta": PROVISIONAL_BETA}
    netB = load_network(DATA, cfgB)
    bg_best, bg_dist = None, 1e9
    for lam in [1, 2, 3, 4]:
        for wbg in [5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0]:
            cfgb = {**cfgB, "lambda_bg": lam, "w_bg": wbg}
            st = rest_stats(netB, cfgb)
            entry = {k: st[k] for k in ("mean_hz", "max_hz", "nan")}
            log["bg_grid"][f"{lam}/{wbg}"] = entry
            if entry["nan"] or entry["max_hz"] > 50:
                continue
            d = abs(entry["mean_hz"] - 2.0)
            if d < bg_dist:
                bg_best, bg_dist = (lam, wbg), d
    if bg_best is None:
        bg_best = (2, 5.0)
        log["selected"]["bg_note"] = (
            "no stable bg candidate within the grid; "
            "using the closest stable low point")
    log["selected"]["lambda_bg"] = bg_best[0]
    log["selected"]["w_bg"] = bg_best[1]
    cfgB = {**cfgB, "lambda_bg": bg_best[0], "w_bg": bg_best[1]}

    # --- stage 3: beta (10% of the mean chemical current at rest)
    netA = load_network(DATA, cfgB)
    netA1 = load_network(DATA, {**cfgB, "beta": 1.0})
    w = WormNet(netA, cfgB, 0)
    w.run(cfg["duration_ms"])
    mean_chem_current = w.mean_g / cfgB["tau_syn"]
    dv = np.abs(w.v[netA["g_src"]] - w.v[netA["g_dst"]])
    mean_gap_per_beta = float(np.mean(netA1["g_w"]) * np.mean(dv))
    beta = 0.1 * max(mean_chem_current, 1e-9) / max(mean_gap_per_beta, 1e-9)
    log["selected"]["beta"] = beta
    log["selected"]["mean_chem_current_mV_per_ms"] = mean_chem_current
    log["selected"]["mean_gap_current_per_unit_beta"] = mean_gap_per_beta

    # --- stage 4: stimulus (smallest S giving >= 20 Hz ASH)
    cfgA = {**cfgB, "beta": beta}
    netA = load_network(DATA, cfgA)
    idx = netA["idx"]
    ash = [idx["ASHL"], idx["ASHR"]]
    S_chosen = None
    for S in [4, 6, 8, 10, 12, 16, 20, 24, 28]:
        cfgS = {**cfgA, "S": S}
        w = WormNet(netA, cfgS, 0)
        w.run(cfg["duration_ms"], stim_ids=ash, stim_current=S,
              stim_start_ms=cfg["stim_start_ms"],
              stim_dur_ms=cfg["stim_dur_ms"])
        t0, t1 = cfg["stim_start_ms"], cfg["stim_start_ms"] + cfg["stim_dur_ms"]
        n_s = sum(len([t for t in w.spikes[i] if t0 <= t < t1]) for i in ash)
        rate = n_s / 0.5 / 2.0
        log["stim_grid"][S] = rate
        if rate >= 20.0:
            S_chosen = S
            break
    if S_chosen is None:
        S_chosen = 28
        log["selected"]["stim_note"] = "grid did not reach 20 Hz; S capped"
    log["selected"]["S"] = S_chosen

    frozen = {**base_cfg(tau_syn), "alpha": alpha, "beta": beta,
              "S": S_chosen, "lambda_bg": bg_best[0], "w_bg": bg_best[1],
              "seeds": [101, 102, 103, 104, 105], "shuffle_seed": 7}
    return frozen, log


def main():
    all_logs = {}
    for name, tau in VARIANTS.items():
        frozen, log = calibrate_variant(tau)
        all_logs[name] = log
        path = os.path.join(HERE, "..", f"config-{name}.json")
        with open(path, "w") as f:
            json.dump(frozen, f, indent=1)
        sel = log["selected"]
        print(f"[{name}] alpha={sel['alpha']} lambda_bg={sel['lambda_bg']} "
              f"w_bg={sel['w_bg']} beta={sel['beta']:.5f} S={sel['S']}",
              flush=True)
    with open(os.path.join(HERE, "..", "calibration-log.json"), "w") as f:
        json.dump(all_logs, f, indent=1)
    print("calibration done; config-5ms.json + config-50ms.json frozen")


if __name__ == "__main__":
    main()
