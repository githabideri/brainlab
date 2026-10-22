"""Driver for the worm tau-window experiment (pre-registered in
README.md; frozen before any run, 2026-10-22).

Grid: tau_syn in {40, 45, 55, 60, 75} ms, Model B (frozen v2
parameters), all-excitatory, measured + shuf 42/43/44, 5 seeds x
{rest, 500 ms ASH pulse} = 200 runs. Paired input
bg_seed = sim_seed*1000 + 1 (same train as the v3-sensitivity
batteries).

Writes results/tau<ms>.json per grid point and results/map.json —
the combined 9-point map (10/25/50/100 read from the
worm-v3-sensitivity results, 40/45/55/60/75 from this experiment)
with the two declared flags (dominance, contrast-edge).

Usage:  python3 src/run_tauwindow.py
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_SRC = os.path.join(HERE, "..", "worm-pilot", "src")
PARENT = os.path.join(HERE, "..", "worm-pilot")
sys.path.insert(0, PARENT_SRC)

from sim import WormNet, load_network, make_shuffled_exact  # noqa: E402
from run_campaign import COMMAND, motor_neuron  # noqa: E402

DATA = os.path.join(PARENT, "data")
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

SEEDS = [101, 102, 103, 104, 105]
SHUF = [42, 43, 44]
TAUS = [40, 45, 55, 60, 75]
VARIANT_IDX = 1
WINDOWS = [("pre", 4500, 5000), ("pulse", 5000, 5500),
           ("w0", 5500, 5750), ("w1", 5750, 6000),
           ("w2", 6000, 6500), ("w3", 6500, 7500), ("w4", 7500, 10500)]
WIN5 = ("win5", 5500, 10500)


def bg_seed(sim_seed):
    return sim_seed * 1000 + VARIANT_IDX


def GROUPS(net):
    idx = net["idx"]
    command = [idx[n] for n in COMMAND]
    motor = motor_neuron(net["names"])
    other = [i for i in range(net["n"])
             if i not in set(command) and i not in set(motor)]
    ash = [i for i in (idx.get("ASHL", -1), idx.get("ASHR", -1),
                       idx.get("ASJL", -1), idx.get("ASJR", -1))
           if 0 <= i < net["n"]]
    return {"command_pool": command, "body_wall_motors": motor,
            "other": other, "ash_ashj": ash}


def run_one(net, cfg, seed, cond, ash):
    w = WormNet(net, cfg, bg_seed(seed))
    if cond == "stim":
        w.run(cfg["duration_ms"], stim_ids=ash, stim_current=cfg["S"],
              stim_start_ms=cfg["stim_start_ms"],
              stim_dur_ms=cfg["stim_dur_ms"])
    else:
        w.run(cfg["duration_ms"])
    return w


def record(w, net, wname, seed, cond, cfg):
    n = net["n"]
    counts = np.array([len(w.spikes[i]) for i in range(n)])
    rate15 = counts / (cfg["duration_ms"] / 1000.0)
    rec = {"wiring": wname, "seed": seed, "cond": cond,
           "bg_seed": bg_seed(seed),
           "total_spikes": int(counts.sum()),
           "mean_rate_hz": float(rate15.mean()),
           "max_rate_hz": float(rate15.max()),
           "nan": bool(np.isnan(w.v).any()),
           "groups": {}}
    for gname, ids in GROUPS(net).items():
        if not ids:
            continue
        rec["groups"][gname] = {
            "rate_15s": float(rate15[ids].mean()),
            "windows": {win: float(np.mean(
                np.asarray([sum(1 for t in w.spikes[i]
                                 if a <= t < b) / ((b - a) / 1000.0)
                            for i in ids])))
                        for win, a, b in WINDOWS + [WIN5]}}
    return rec


def paired_contrasts(runs):
    bypair = {(r["wiring"], r["seed"]): r
              for r in runs if r["cond"] == "rest"}
    out = {}
    for r in runs:
        if r["cond"] != "stim":
            continue
        rest = bypair[(r["wiring"], r["seed"])]
        cell = out.setdefault(r["wiring"], {})
        for gname, g in r["groups"].items():
            rg = rest["groups"][gname]
            cell.setdefault(gname, {})
            for win, _a, _b in WINDOWS + [WIN5]:
                d = g["windows"][win] - rg["windows"][win]
                cell[gname].setdefault(win, []).append(d)
    return {w: {g: {win: {"mean": round(float(np.mean(v)), 6),
                          "per_seed": [round(x, 6) for x in v]}
                     for win, v in wins.items()}
                for g, wins in gs.items()}
            for w, gs in out.items()}


def paired_input_artifact(net, shuf42, cfg, tau):
    ash = GROUPS(net)["ash_ashj"]
    wa = run_one(net, cfg, SEEDS[0], "stim", ash)
    wb = run_one(shuf42, cfg, SEEDS[0], "stim", ash)
    assert wa.bg_events == wb.bg_events, "paired input violated"
    h = hashlib.sha256(json.dumps(wa.bg_events).encode()).hexdigest()
    print(f"[tau{tau}] paired input ok: {len(wa.bg_events)} events, "
          f"sha256 {h[:12]}...", flush=True)
    return {"sim_seed": SEEDS[0], "bg_seed": bg_seed(SEEDS[0]),
            "seed_rule": "bg_seed = sim_seed*1000 + 1 (never wiring)",
            "measured_vs_shuf42_bg_event_lists_identical": True,
            "events_sha256": h, "n_events": len(wa.bg_events)}


def run_point(tau):
    outp = os.path.join(RESULTS, f"tau{tau}.json")
    if os.path.exists(outp):
        print(f"[tau{tau}] exists, skipping", flush=True)
        return json.load(open(outp))
    t0 = time.time()
    base = json.load(open(os.path.join(PARENT,
                                       "config-50ms-v3-modelB.json")))
    cfg = dict(base)
    cfg["tau_syn"] = float(tau)
    cfg["substrate"] = (base.get("substrate", "") +
                        f" [tau-window derived: tau_syn {tau} ms]")
    cfgdir = os.path.join(HERE, "config")
    os.makedirs(cfgdir, exist_ok=True)
    json.dump(cfg, open(os.path.join(cfgdir, f"tau{tau}.json"), "w"),
              indent=1)
    net = load_network(DATA, cfg)
    shuf_nets, shuf_inv = {}, {}
    for s in SHUF:
        shuf_nets[s], shuf_inv[s] = make_shuffled_exact(net, cfg, s)
    ash = GROUPS(net)["ash_ashj"]
    art = paired_input_artifact(net, shuf_nets[SHUF[0]], cfg, tau)
    runs = []
    for wname, network in [("measured", net)] + \
                          [(f"shuf-{s}", shuf_nets[s]) for s in SHUF]:
        for seed in SEEDS:
            for cond in ("rest", "stim"):
                wt = time.time()
                w = run_one(network, cfg, seed, cond, ash)
                rec = record(w, network, wname, seed, cond, cfg)
                rec["wall_s"] = round(time.time() - wt, 2)
                runs.append(rec)
                print(f"[tau{tau}] {wname} seed={seed} {cond}: "
                      f"total={rec['total_spikes']} "
                      f"mean={rec['mean_rate_hz']:.2f}Hz "
                      f"({time.time() - wt:.1f}s, "
                      f"{time.time() - t0:.0f}s elapsed)", flush=True)
    out = {"tau_syn": tau,
           "bg_model": "B (forced propagation; historical v2 behaviour)",
           "signs": "all-excitatory (frozen)",
           "stimulus": "500 ms constant depolarization, frozen S",
           "config": cfg, "seeds": SEEDS, "shuffle_seeds": SHUF,
           "shuffle_invariants": {f"shuf-{s}": shuf_inv[s]
                                  for s in SHUF},
           "paired_input": art,
           "paired_contrast": paired_contrasts(runs),
           "runs": runs,
           "stable": all(r["max_rate_hz"] < 200 and not r["nan"]
                         for r in runs),
           "wall_s": round(time.time() - t0, 1)}
    with open(outp, "w") as f:
        json.dump(out, f, indent=1)
    print(f"[tau{tau}] wrote {os.path.relpath(outp, HERE)} "
          f"({len(runs)} runs, stable={out['stable']}, "
          f"{time.time() - t0:.0f}s)", flush=True)
    return out


def _flags(b):
    """The two declared flags (README) for one battery result."""
    rest = {}
    for r in b["runs"]:
        if r["cond"] == "rest":
            rest.setdefault(r["wiring"], []).append(r["mean_rate_hz"])
    rest = {w: float(np.mean(x)) for w, x in rest.items()}
    meas = rest.get("measured")
    sh = {w: r for w, r in rest.items() if w != "measured"}
    pc = b["paired_contrast"]
    mcp = (pc.get("measured", {}).get("command_pool", {})
             .get("win5", {}).get("mean"))
    shcp = {w: (c.get("command_pool", {}).get("win5", {}).get("mean"))
            for w, c in pc.items() if w != "measured"}
    return {
        "rest_hz": {w: round(v, 4) for w, v in sorted(rest.items())},
        "contrast_hz": {"measured": mcp,
                        **{w: v for w, v in sorted(shcp.items())}},
        "dominance": bool(meas is not None and all(meas > v
                                                   for v in sh.values())),
        "contrast_edge": bool(mcp is not None and all(
            (v is None or mcp > v) for v in shcp.values())),
        "cp_rest_hz": {w: round(float(np.mean([r['groups']['command_pool']['rate_15s']
                                               for r in b['runs']
                                               if r['wiring'] == w
                                               and r['cond'] == 'rest'])), 4)
                       for w in sorted(rest)},
    }


def build_map(new_points):
    """Combined 9-point map. 10/25/100 come from the frozen
    worm-v3-sensitivity B3 batteries, 50 from its B1."""
    sv = os.path.join(HERE, "..", "worm-v3-sensitivity", "results")
    src = {
        10.0: os.path.join(sv, "b3-tau10.json"),
        25.0: os.path.join(sv, "b3-tau25.json"),
        50.0: os.path.join(sv, "b1.json"),
        100.0: os.path.join(sv, "b3-tau100.json"),
    }
    for t, p in new_points.items():
        src[float(t)] = p
    grid = sorted(src)
    rows = {}
    for t in grid:
        b = (src[t] if isinstance(src[t], dict)
             else json.load(open(src[t])))
        rows[str(t)] = _flags(b)
    dom = [t for t in grid if rows[str(t)]["dominance"]]
    # maximal contiguous set over the combined grid containing 50
    window = []
    if 50.0 in dom:
        i = grid.index(50.0)
        lo = hi = i
        while lo > 0 and grid[lo - 1] in dom:
            lo -= 1
        while hi < len(grid) - 1 and grid[hi + 1] in dom:
            hi += 1
        window = [str(t) for t in grid[lo:hi + 1]]
    out = {"points": rows,
           "dominance_set": [str(t) for t in dom],
           "window": window,
           "window_definition":
               "maximal contiguous set of grid points (combined "
               "{10,25,40,45,50,55,60,75,100}) where the measured "
               "whole-animal rest rate exceeds all three shuffle "
               "rest rates; anchor 50 ms",
           "flags": {"dominance": "measured rest > all shuffles",
                     "contrast_edge": "measured command-pool win5 "
                                      "paired contrast > all shuffles"},
           "note": "exploratory regime map of the STATE effect; no "
                   "'wiring matters' claim — the control-wiring bar "
                   "(docs/evaluation.md §7) is unchanged",
           "source": {"10/25/50/100": "experiments/worm-v3-sensitivity"
                      "/results/ (frozen 2026-10-22)",
                      "40/45/55/60/75": "this experiment"}}
    p = os.path.join(RESULTS, "map.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1), flush=True)
    print(f"wrote {os.path.relpath(p, HERE)}", flush=True)


def main():
    pts = {}
    for t in TAUS:
        pts[t] = run_point(t)
    build_map(pts)


if __name__ == "__main__":
    main()
