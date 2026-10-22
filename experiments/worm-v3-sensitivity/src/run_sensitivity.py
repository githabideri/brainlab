"""Driver for the worm v3-sensitivity experiment (pre-registered in
README.md; frozen before any run, 2026-10-22).

Batteries (5 seeds x {rest, 500 ms ASH pulse at t = 5.0-5.5 s},
paired input bg_seed = sim_seed*1000 + 1, byte-identical across all
wirings of a battery):

  B1   Model B (bg_propagate=True),  tau_syn 50 ms,  all-excitatory,
       constant depolarization;  measured + 11 shuffles (42-52)
  B1a  Model A (bg_propagate=False), tau_syn 50 ms,  all-excitatory,
       constant depolarization;  measured + 11 shuffles (42-52)
  B2   Model B, 50 ms, SIGNED (GAD-synthesizing presynaptic ->
       negative weight; data/gabaergic-herm.json); measured + shuf 42/43/44
  B3   Model B, tau_syn in {10, 25, 100} ms, all-excitatory,
       constant depolarization; measured + shuf 42/43/44
  B4   Model B, 50 ms, all-excitatory, TRAPEZOID stimulus (100 ms
       rise / 300 ms plateau at frozen S / 100 ms fall);
       measured + shuf 42/43/44

Nothing in ../worm-pilot/ is modified: the frozen sim.py / configs /
data are imported and read; B3's derived configs are written to
this experiment's config/.

Writes results/b1.json, b1a.json, b2.json, b3.json, b4.json and
results/verdicts.json (S1-S4 stop rules evaluated by code).

Usage:  python src/run_sensitivity.py [battery ...]
        (default: all; each battery is resumable: a battery whose
        results file already exists is skipped)
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

SEEDS = [101, 102, 103, 104, 105]          # frozen pilot seeds
SHUF_11 = list(range(42, 53))             # 42/43/44 frozen + 45-52 new
SHUF_3 = [42, 43, 44]
VARIANT_IDX = 1                           # pilot rule: 1 == 50 ms family

WINDOWS = [("pre", 4500, 5000), ("pulse", 5000, 5500),
           ("w0", 5500, 5750), ("w1", 5750, 6000),
           ("w2", 6000, 6500), ("w3", 6500, 7500), ("w4", 7500, 10500)]
WIN5 = ("win5", 5500, 10500)              # the declared 5-s window


def bg_seed(sim_seed):
    """Paired-input seeding rule (frozen): f(sim seed, variant) only,
    never the wiring/sign/timescale."""
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


def apply_signs(net):
    """B2: negative weight on chemical edges whose presynaptic neuron
    is a GAD-synthesizing (unc-25-positive) cell (data/ file).
    Magnitudes unchanged; everything else stays excitatory."""
    gaba = set(json.load(open(os.path.join(HERE, "data",
                                           "gabaergic-herm.json")))
               ["in_300_neuron_network"]["present"])
    names = net["names"]
    mask = np.array([names[i] in gaba for i in net["c_src"]])
    out = dict(net)
    out["c_w"] = np.where(mask, -net["c_w"], net["c_w"])
    return out, int(mask.sum())


def run_trapezoid(net, cfg, seed, ash):
    """B4: the pilot's exact step, with the stimulus current shaped as
    a declared trapezoid (100 ms rise, 300 ms plateau at frozen S,
    100 ms fall) instead of a step. Only the per-step current differs
    from the frozen model; no other parameter is touched."""
    w = WormNet(net, cfg, seed)
    dt = cfg["dt"]
    t0 = cfg["stim_start_ms"]
    S = cfg["S"]
    w._reset()
    w.stim_ids = np.asarray(ash, dtype=np.int64)
    w.t_stim_current = 0.0
    w.t_stim_start = t0
    w.t_stim_dur = 500.0
    for _ in range(int(cfg["duration_ms"] // dt)):
        t = w.t + dt
        if t0 <= t < t0 + 100:
            w.t_stim_current = S * (t - t0) / 100.0
        elif t0 + 100 <= t < t0 + 300:
            w.t_stim_current = S
        elif t0 + 300 <= t < t0 + 400:
            w.t_stim_current = S * (t0 + 400 - t) / 100.0
        else:
            w.t_stim_current = 0.0
        w.step()
    return w


def run_one(net, cfg, seed, cond, ash, trap=False):
    if trap and cond == "stim":
        return run_trapezoid(net, cfg, seed, ash)
    w = WormNet(net, cfg, bg_seed(seed))
    if cond == "stim":
        w.run(cfg["duration_ms"], stim_ids=ash, stim_current=cfg["S"],
              stim_start_ms=cfg["stim_start_ms"],
              stim_dur_ms=cfg["stim_dur_ms"])
    else:
        w.run(cfg["duration_ms"])
    return w


def record(w, net, wname, seed, cond, cfg, extra):
    n = net["n"]
    counts = np.array([len(w.spikes[i]) for i in range(n)])
    rate15 = counts / (cfg["duration_ms"] / 1000.0)
    rec = {"wiring": wname, "seed": seed, "cond": cond,
           "bg_seed": bg_seed(seed),
           "total_spikes": int(counts.sum()),
           "mean_rate_hz": float(rate15.mean()),
           "max_rate_hz": float(rate15.max()),
           "nan": bool(np.isnan(w.v).any()),
           **extra}
    for gname, ids in GROUPS(net).items():
        if not ids:
            continue
        rec.setdefault("groups", {})[gname] = {
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
            for win, a, b in WINDOWS + [WIN5]:
                d = g["windows"][win] - rg["windows"][win]
                cell[gname].setdefault(win, []).append(d)
    return {w: {g: {win: {"mean": round(float(np.mean(v)), 6),
                          "per_seed": [round(x, 6) for x in v]}
                     for win, v in wins.items()}
                for g, wins in gs.items()}
            for w, gs in out.items()}


def paired_input_artifact(net, shuf42, cfg, bid, extra):
    """One measured-vs-shuf-42 background event pair (seed 101, stim
    run), asserted byte-identical; sha256 recorded."""
    t0 = time.time()
    ash = GROUPS(net)["ash_ashj"]
    wa = run_one(net, cfg, SEEDS[0], "stim", ash)
    wb = run_one(shuf42, cfg, SEEDS[0], "stim", ash)
    assert wa.bg_events == wb.bg_events, \
        f"paired input violated in {bid}: bg event lists differ"
    h = hashlib.sha256(json.dumps(wa.bg_events).encode()).hexdigest()
    art = {"battery": bid, "sim_seed": SEEDS[0], "bg_seed": bg_seed(SEEDS[0]),
           "seed_rule": "bg_seed = sim_seed*1000 + 1 (never wiring/sign/"
                        "timescale/stimulus)",
           "substrate": cfg.get("substrate"),
           "bg_model": ("B (forced propagation; historical v2 behaviour)"
                        if cfg.get("bg_propagate", False) else
                        "A (pure external current; default)"),
           "n_neurons": net["n"],
           "measured_vs_shuf42_bg_event_lists_identical": True,
           "events_sha256": h, "n_events": len(wa.bg_events), **extra}
    print(f"[{bid}] paired input ok: {len(wa.bg_events)} bg events, "
          f"sha256 {h[:12]}... ({time.time() - t0:.1f}s)", flush=True)
    return art


def run_battery(bid, cfg, shuf_seeds, sign=False, trap=False,
                label=None):
    t0 = time.time()
    outp = os.path.join(RESULTS, f"{bid}.json")
    if os.path.exists(outp):
        print(f"[{bid}] results exist, skipping", flush=True)
        return json.load(open(outp))
    net = load_network(DATA, cfg)
    n_flipped = 0
    if sign:
        net, n_flipped = apply_signs(net)
    shuf_nets, shuf_inv = {}, {}
    for s in shuf_seeds:
        shuf_nets[s], shuf_inv[s] = make_shuffled_exact(net, cfg, s)
    g = GROUPS(net)
    ash = g["ash_ashj"]
    cfgB = dict(cfg)
    extra = {"label": label or bid,
             "bg_model": ("B (forced propagation; historical v2 behaviour)"
                          if cfg.get("bg_propagate", False) else
                          "A (pure external current; default)"),
             "substrate": "v3-canonical-electrical (frozen worm-pilot "
                          "data); parameters = frozen v2 values",
             "signs": ("GAD-synthesizing presynaptic -> negative "
                       f"({n_flipped} of {net['n_chem']} chemical edges "
                       "flipped; source: Gendrel/Atlas/Hobert 2016 "
                       "eLife 17686 Table 1)" if sign
                       else "all-excitatory (frozen)"),
             "stimulus": ("trapezoid 100/300/100 ms, peak = frozen S"
                          if trap else
                          "500 ms constant depolarization, frozen S"),
             "tau_syn": cfg["tau_syn"]}
    art = paired_input_artifact(net, shuf_nets[shuf_seeds[0]], cfg,
                                bid, extra)
    runs = []
    for wname, network in [("measured", net)] + \
                          [(f"shuf-{s}", shuf_nets[s]) for s in shuf_seeds]:
        for seed in SEEDS:
            for cond in ("rest", "stim"):
                wt = time.time()
                w = run_one(network, cfg, seed, cond, ash, trap=trap)
                rec = record(w, network, wname, seed, cond, cfg,
                             {"wall_s": round(time.time() - wt, 2),
                              "n_flipped": n_flipped})
                runs.append(rec)
                print(f"[{bid}] {wname} seed={seed} {cond}: "
                      f"total={rec['total_spikes']} "
                      f"mean={rec['mean_rate_hz']:.2f}Hz "
                      f"max={rec['max_rate_hz']:.1f}Hz "
                      f"({time.time() - wt:.1f}s, "
                      f"{time.time() - t0:.0f}s elapsed)", flush=True)
    out = {"battery": bid, **extra, "config": cfg,
           "seeds": SEEDS, "shuffle_seeds": shuf_seeds,
           "shuffle_invariants": {f"shuf-{s}": shuf_inv[s]
                                  for s in shuf_seeds},
           "paired_input": art,
           "paired_contrast": paired_contrasts(runs),
           "runs": runs,
           "stable": all(r["max_rate_hz"] < 200 and not r["nan"]
                         for r in runs),
           "wall_s": round(time.time() - t0, 1)}
    with open(outp, "w") as f:
        json.dump(out, f, indent=1)
    print(f"[{bid}] wrote {os.path.relpath(outp, HERE)} "
          f"({len(runs)} runs, stable={out['stable']}, "
          f"{time.time() - t0:.0f}s)", flush=True)
    return out


def cfg_parent(name):
    return json.load(open(os.path.join(PARENT, name)))


def main(batteries=None):
    wanted = set(batteries) if batteries else \
        {"b1", "b1a", "b2", "b3", "b4"}
    cfgA = cfg_parent("config-50ms.json")            # Model A
    cfgB = cfg_parent("config-50ms-v3-modelB.json")  # Model B
    res = {}
    if "b1" in wanted:
        res["b1"] = run_battery("b1", cfgB, SHUF_11,
                                label="Model B, 50 ms, all-excitatory, "
                                      "constant stim, 11 shuffles")
    if "b1a" in wanted:
        res["b1a"] = run_battery("b1a", cfgA, SHUF_11,
                                 label="Model A, 50 ms, all-excitatory, "
                                       "constant stim, 11 shuffles")
    if "b2" in wanted:
        res["b2"] = run_battery("b2", cfgB, SHUF_3, sign=True,
                                label="Model B, 50 ms, SIGNED "
                                      "(GAD-synthesizing presynaptic "
                                      "inhibitory), 3 shuffles")
    if "b3" in wanted:
        cfgdir = os.path.join(HERE, "config")
        os.makedirs(cfgdir, exist_ok=True)
        for tau in (10, 25, 100):
            c = dict(cfgB)
            c["tau_syn"] = float(tau)
            c["substrate"] = (c.get("substrate", "") +
                              f" [B3 derived: tau_syn {tau} ms]")
            p = os.path.join(cfgdir, f"b3-tau{tau}.json")
            json.dump(c, open(p, "w"), indent=1)
            res[f"b3-tau{tau}"] = run_battery(f"b3-tau{tau}", c, SHUF_3,
                                              label=f"Model B, tau "
                                                    f"{tau} ms, "
                                                    f"all-excitatory")
    if "b4" in wanted:
        res["b4"] = run_battery("b4", cfgB, SHUF_3, trap=True,
                                label="Model B, 50 ms, all-excitatory, "
                                      "trapezoid stimulus")
    analyze(res, wanted)


def analyze(res, wanted):
    """S1-S4 stop rules (pre-registered in README.md), evaluated by
    code, before any interpretation. `res` maps battery key -> battery
    result dict."""
    v = {"stop_rules": {}, "overall": {}}

    def rest_table(key):
        """(wiring, whole-animal rest mean) over seeds, from a battery."""
        if key not in res:
            return None
        tbl = {}
        for r in res[key]["runs"]:
            if r["cond"] == "rest":
                tbl.setdefault(r["wiring"], []).append(r["mean_rate_hz"])
        return {w: float(np.mean(x)) for w, x in tbl.items()}

    # S1: is the resting state wiring-specific? (B1 = Model B, 50 ms)
    if "b1" in wanted:
        rt = rest_table("b1")
        meas = rt["measured"]
        shufs = {w: r for w, r in rt.items() if w != "measured"}
        active = sorted(w for w, r in shufs.items()
                        if r >= 0.75 * meas)
        s1 = {"measured_rest_hz": round(meas, 4),
              "shuffle_rest_hz": {w: round(r, 4)
                                  for w, r in sorted(shufs.items())},
              "n_shuffles_at_or_above_0p75_measured": len(active),
              "active_shuffles": active,
              "verdict": ("NOT wiring-specific (>=3 of 11 shuffles in "
                          "the active basin; all-excitatory bifurcation-"
                          "neighbourhood artifact)"
                          if len(active) >= 3 else
                          "wiring-specificity stands (<=2 of 11)")}
        cp = {}
        for r in res["b1"]["runs"]:
            if r["cond"] == "rest":
                cp.setdefault(r["wiring"], []).append(
                    r["groups"]["command_pool"]["rate_15s"])
        s1["command_pool_rest_hz"] = {
            w: round(float(np.mean(x)), 4) for w, x in sorted(cp.items())}
        v["stop_rules"]["S1_resting_state"] = s1

    # S2: do signs change the picture? (B2)
    if "b2" in wanted:
        b = res["b2"]
        cp = b["paired_contrast"].get("command_pool", {})
        meas = cp.get("measured", {}).get("win5", {})
        sh_means = {w: c.get("win5", {}).get("mean")
                    for w, c in cp.items() if w != "measured"}
        s2 = {
            "measured_signed_contrast_win5_hz": meas.get("mean"),
            "measured_signed_per_seed": meas.get("per_seed"),
            "signed_shuffle_contrasts_win5_hz": sh_means,
            "rest_table": {w: round(vv, 4) for w, vv in
                           sorted((rest_table("b2") or {}).items())},
        }
        m = meas.get("mean")
        ps = meas.get("per_seed") or []
        s2["pass"] = bool(m is not None and m > 0.5 and
                          all(x > 0 for x in ps) and
                          all(v is not None and m > v
                              for v in sh_means.values()))
        v["stop_rules"]["S2_signs"] = s2

    # S3: timescale map (exploratory; no pass/fail). Model B only.
    taus = {}
    if "b1" in wanted:
        taus[50.0] = "b1"
    for key, tau in (("b3-tau10", 10.0), ("b3-tau25", 25.0),
                     ("b3-tau100", 100.0)):
        if key in res:
            taus[tau] = key
    if taus:
        s3 = {}
        for tau in sorted(taus):
            b = res[taus[tau]]
            cp = b["paired_contrast"].get("command_pool", {})
            mo = b["paired_contrast"].get("body_wall_motors", {})
            rt = rest_table(taus[tau]) or {}
            s3[str(tau)] = {
                "command_pool_contrast": {
                    w: c.get("win5", {}).get("mean")
                    for w, c in cp.items()},
                "motor_contrast": {
                    w: c.get("win5", {}).get("mean")
                    for w, c in mo.items()},
                "rest_hz": {w: round(x, 4) for w, x in sorted(rt.items())},
            }
        v["stop_rules"]["S3_timescale_map"] = s3

    # S4: graded stimulus (exploratory; no pass/fail)
    if "b1" in wanted and "b4" in wanted:
        s4 = {}
        for label, b in (("step", res["b1"]), ("trapezoid", res["b4"])):
            cp = b["paired_contrast"].get("command_pool", {})
            s4[label] = {w: c.get("win5", {}).get("mean")
                         for w, c in cp.items()}
        v["stop_rules"]["S4_graded_stimulus"] = s4

    # Overall verdict (control-wiring bar): measured command-pool win5
    # paired contrast > 0.5 Hz, all 5 seeds positive, beats ALL of its
    # battery's shuffles — in any battery.
    hits = []
    for key, b in res.items():
        cp = b["paired_contrast"].get("command_pool", {}).get("measured")
        if not cp:
            continue
        m, ps = cp["win5"].get("mean"), cp["win5"].get("per_seed", [])
        if m is None or m <= 0.5 or not ps or not all(x > 0 for x in ps):
            continue
        sh_max = max((c["win5"].get("mean") or 0.0)
                     for w, c in b["paired_contrast"]["command_pool"].items()
                     if w != "measured")
        if m > sh_max:
            hits.append({"battery": key, "contrast_hz": m,
                         "per_seed": ps})
    v["overall"] = {
        "wiring_matters_pass": bool(hits),
        "passing_cells": hits,
        "rule": "measured command-pool win5 paired contrast > 0.5 Hz "
                "(seed mean), positive in all 5 seeds, exceeding all "
                "matched shuffles, in at least one battery",
    }
    p = os.path.join(RESULTS, "verdicts.json")
    with open(p, "w") as f:
        json.dump(v, f, indent=1)
    print(json.dumps(v, indent=1), flush=True)
    print(f"wrote {os.path.relpath(p, HERE)}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
