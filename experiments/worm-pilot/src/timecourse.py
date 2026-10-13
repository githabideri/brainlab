"""Time-resolved response around the ASH pulse (review round 4, 2026-10-13).

The 5-s post-stimulus average of the 80-run campaign could obscure a
brief sensorimotor response. This script re-runs the 50 ms variant
subset (4 wirings x 5 seeds x rest/stim = 40 runs, same frozen config,
same paired-input seed rule as the campaign) and records per-group
firing rates in short windows:

    pre   : [4500, 5000)   1 s before the pulse (paired baseline)
    pulse : [5000, 5500)   during the 500 ms pulse
    w0    : [5500, 5750)   first 250 ms after
    w1    : [5750, 6000)
    w2    : [6000, 6500)
    w3    : [6500, 7500)
    w4    : [7500, 10500)  rest of the declared 5-s window

Paired contrast per window = stim-run rate - paired rest-run rate
(same wiring, seed, bg seed). Writes data/timecourse-50ms-<tag>.json
(append-only; the frozen campaign results are untouched).

Usage:  python src/timecourse.py [tag]   (default tag: v3)
"""
import json
import os
import time as time_mod

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

import sys
sys.path.insert(0, os.path.join(HERE, "src"))

from run_campaign import (COMMAND, bg_seed, motor_neuron)  # noqa: E402
from sim import WormNet, load_network, make_shuffled_exact  # noqa: E402

VARIANT = "50ms"
VARIANT_IDX = 1  # bg_seed = sim_seed*1000 + variant_idx (as in campaign)


def win_rates(spikes, a, b):
    """Per-neuron rate (Hz) inside [a, b). spikes: {neuron: [times]}."""
    return [sum(1 for t in spikes[i] if a <= t < b) / ((b - a) / 1000.0)
            for i in sorted(spikes)]


def main(tag="v3"):
    cfg = json.load(open(os.path.join(HERE, f"config-{VARIANT}.json")))
    t0p, d = cfg["stim_start_ms"], cfg["stim_dur_ms"]
    t1 = t0p + d
    WINDOWS = [("pre", t0p - 500, t0p), ("pulse", t0p, t1),
               ("w0", t1, t1 + 250), ("w1", t1 + 250, t1 + 500),
               ("w2", t1 + 500, t1 + 1000), ("w3", t1 + 1000, t1 + 2000),
               ("w4", t1 + 2000, t1 + 5000)]
    net = load_network(DATA, cfg)
    shuf_seeds = cfg.get("shuffle_seeds", [42, 43, 44])
    shuf_nets = {s: make_shuffled_exact(net, cfg, s)[0] for s in shuf_seeds}
    idx = net["idx"]
    ash = [idx[n] for n in cfg["stim_ids"]]
    command = [idx[n] for n in COMMAND]
    motor = motor_neuron(net["names"])
    other = [i for i in range(net["n"])
             if i not in set(command) and i not in set(motor)]
    groups = {"command_pool": command, "body_wall_motors": motor,
              "other": other,
              "ash_ashj": [i for i in (idx.get("ASHL", -1), idx.get("ASHR", -1),
                                       idx.get("ASJL", -1), idx.get("ASJR", -1))
                           if 0 <= i < net["n"]]}
    groups = {k: [i for i in v if 0 <= i < net["n"]] for k, v in groups.items()}
    DUR = cfg["duration_ms"]
    wirings = [("measured", net)] + \
              [(f"shuf-{s}", shuf_nets[s]) for s in shuf_seeds]

    out = {"variant": VARIANT,
           "substrate": cfg.get("substrate", "v2-dual-electrical"),
           "bg_model": ("B (forced propagation; historical v2 behaviour)"
                        if cfg.get("bg_propagate", False)
                        else "A (pure external current; only threshold-"
                             "crossing spikes propagate; default)"),
           "windows": {w[0]: [w[1], w[2]] for w in WINDOWS},
           "paired_contrast_definition":
               "stim-run window rate - paired rest-run rate, same "
               "(wiring, sim seed, bg seed)",
           "runs": []}
    t0 = time_mod.time()
    for wname, network in wirings:
        for seed in cfg["seeds"]:
            for cond in ("rest", "stim"):
                w = WormNet(network, cfg, bg_seed(seed, VARIANT_IDX))
                if cond == "stim":
                    w.run(DUR, stim_ids=ash, stim_current=cfg["S"],
                          stim_start_ms=cfg["stim_start_ms"],
                          stim_dur_ms=cfg["stim_dur_ms"])
                else:
                    w.run(DUR)
                rec = {"wiring": wname, "seed": seed, "cond": cond,
                       "bg_seed": bg_seed(seed, VARIANT_IDX),
                       "bg_model": out["bg_model"],
                       "substrate": out["substrate"],
                       "groups": {}}
                for gname, ids in groups.items():
                    if not ids:
                        continue
                    per_win = {win: win_rates(w.spikes, a, b)
                               for (win, a, b) in WINDOWS}
                    rec["groups"][gname] = {
                        win: [round(float(np.mean(np.asarray(rrates)[ids])), 6)]
                        for win, rrates in per_win.items()}
                out["runs"].append(rec)
                print(f"{wname} seed={seed} {cond}: done "
                      f"({time_mod.time() - t0:.0f}s total)", flush=True)

    # paired contrasts per window/group/wiring
    bypair = {(r["wiring"], r["seed"]): r
              for r in out["runs"] if r["cond"] == "rest"}
    contrast = {}
    for r in out["runs"]:
        if r["cond"] != "stim":
            continue
        rest = bypair[(r["wiring"], r["seed"])]
        for gname in r["groups"]:
            cell = contrast.setdefault(gname, {}) \
                               .setdefault(r["wiring"], {})
            for (win, a, b) in WINDOWS:
                d = r["groups"][gname][win][0] - \
                    rest["groups"][gname][win][0]
                cell.setdefault(win, []).append(d)
    for gname in contrast:
        for wname in contrast[gname]:
            contrast[gname][wname] = {
                win: {"mean": round(float(np.mean(v)), 6),
                      "per_seed": [round(x, 6) for x in v]}
                for win, v in contrast[gname][wname].items()}
    out["paired_contrast"] = contrast

    p = os.path.join(DATA, f"timecourse-50ms-{tag}.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {os.path.relpath(p, HERE)} (bg_model={out['bg_model']})")
    cp = contrast.get("command_pool", {})
    for wname in sorted(cp):
        line = ", ".join(f"{win} {cp[wname][win]['mean']:+.4f}"
                         for win, _a, _b in WINDOWS
                         if win in cp[wname])
        print(f"command_pool {wname}: {line}")


if __name__ == "__main__":
    import sys as _s
    main(_s.argv[1] if len(_s.argv) > 1 else "v3")
