"""2026-10-13 re-run campaign (supersedes the 2026-10-12 v1 grid; the
v1 results.json stays frozen in git).

Grid: 2 declared variants (5 ms tau_syn primary, 50 ms tau_syn
EXPLORATORY — the variant was selected post-hoc, see README/report
addendum) x 4 wirings (measured + 3 INDEPENDENT exact-invariant
shuffle graphs, seeds 42/43/44) x 5 simulation seeds x 2 conditions
(rest / 500 ms ASH depolarization at t = 5.0-5.5 s) = 80 runs.

Paired input (review requirement 3): the per-neuron Poisson background
is the only stochastic input; its rng is seeded with
    bg_seed = sim_seed * 1000 + variant_idx
— a function of the simulation seed and the variant ONLY, never of
the wiring. For any (sim_seed, variant) the measured wiring and every
shuffle therefore see the identical input train, and the only
difference between their runs is the wiring itself. The ASH stimulus
is a constant depolarization (identical across wirings by
construction). One paired example per variant is dumped as an
artifact (data/paired-stim-example-<variant>.json): the measured and
the shuf-42 background event lists, asserted byte-identical, with
sha256.

Primary metric (review requirement 4): the stim-rest DELTA, per wiring
and seed and group: delta_hz = stim-window rate (5 s after the pulse)
minus rest rate (whole 15 s); response index = delta / rest where
rest >= 0.1 Hz. Headline table: measured vs each of the 3 shuffles on
the delta, with the spread ACROSS the 3 independent graphs reported
explicitly (v1's single shared graph confounded graph and seed
variability).

Writes results-exact.json (frozen afterwards). Reads the FROZEN
config-<variant>.json; no parameter is tuned here.
"""
import hashlib
import json
import os
import sys
import time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim import load_network, WormNet, make_shuffled_exact  # noqa: E402

DATA = os.path.join(HERE, "..", "data")
VARIANTS = ["5ms", "50ms"]

COMMAND = ["AVAR", "AVAL", "AVBL", "AVBR", "AVDR", "AVDL", "AVJL", "AVJR"]


def motor_neuron(names):
    keep = []
    for i, nm in enumerate(names):
        if nm in ("PDA", "PDB", "DVA", "DVB") or nm.startswith(
                ("DA0", "DB0", "DD0", "VA0", "VB0", "VD0", "AS0", "VC0",
                 "DA1", "DB1", "DD1", "VA1", "VB1", "VD1", "VC1")):
            keep.append(i)
    return keep


def bg_seed(sim_seed, variant_idx):
    """Paired-input seeding rule: f(sim_seed, variant) only, never
    the wiring (declared in the module docstring)."""
    return sim_seed * 1000 + variant_idx


def run_variant(name, variant_idx):
    cfg = json.load(open(os.path.join(HERE, "..", f"config-{name}.json")))
    net = load_network(DATA, cfg)
    shuf_seeds = cfg.get("shuffle_seeds", [42, 43, 44])
    shuf_nets = {}
    shuf_inv = {}
    for s in shuf_seeds:
        shuf_nets[s], shuf_inv[s] = make_shuffled_exact(net, cfg, s)
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

    W1 = cfg["stim_start_ms"] + cfg["stim_dur_ms"]
    DUR = cfg["duration_ms"]
    wirings = [("measured", net)] + \
              [(f"shuf-{s}", shuf_nets[s]) for s in shuf_seeds]
    out = {"config": cfg, "runs": [], "summary": {},
           "shuffle_invariants": {f"shuf-{s}": shuf_inv[s]
                                  for s in shuf_seeds}}

    # --- paired-input example artifact (one per variant) -------------
    s0 = cfg["seeds"][0]
    seedA = bg_seed(s0, variant_idx)
    wA = WormNet(net, cfg, seedA)
    wA.run(DUR, stim_ids=ash, stim_current=cfg["S"],
           stim_start_ms=cfg["stim_start_ms"],
           stim_dur_ms=cfg["stim_dur_ms"])
    wB = WormNet(shuf_nets[shuf_seeds[0]], cfg, seedA)
    wB.run(DUR, stim_ids=ash, stim_current=cfg["S"],
           stim_start_ms=cfg["stim_start_ms"],
           stim_dur_ms=cfg["stim_dur_ms"])
    evA, evB = wA.bg_events, wB.bg_events
    assert evA == evB, "paired input violated: bg event lists differ"
    h = hashlib.sha256(json.dumps(evA).encode()).hexdigest()
    art = {
        "variant": name, "sim_seed": s0, "bg_seed": seedA,
        "seed_rule": "bg_seed = sim_seed*1000 + variant_idx (never wiring)",
        "n_neurons": net["n"],
        "background": f"per-neuron Bernoulli per 1 ms step, p = "
                      f"lambda_bg*dt/1000, lambda_bg = {cfg['lambda_bg']}",
        "stimulus": "500 ms constant depolarization on ASHL/ASHR at "
                    "t=5.0-5.5 s (identical across wirings by construction)",
        "measured_vs_shuf42_bg_event_lists_identical": True,
        "events_sha256": h,
        "events": [[t, ids] for t, ids in evA],
    }
    p = os.path.join(DATA, f"paired-stim-example-{name}.json")
    with open(p, "w") as f:
        json.dump(art, f, indent=1)
    out["paired_stim_artifact"] = {"file": os.path.relpath(p, HERE),
                                   "events_sha256": h,
                                   "n_events": len(evA)}
    print(f"[{name}] paired-stim artifact: {len(evA)} bg events, "
          f"sha256 {h[:12]}… (measured == shuf-42, same sim seed+variant)",
          flush=True)

    for wname, network in wirings:
        for seed in cfg["seeds"]:
            for cond in ("rest", "stim"):
                t0 = time.time()
                w = WormNet(network, cfg, bg_seed(seed, variant_idx))
                if cond == "stim":
                    w.run(DUR, stim_ids=ash, stim_current=cfg["S"],
                          stim_start_ms=cfg["stim_start_ms"],
                          stim_dur_ms=cfg["stim_dur_ms"])
                else:
                    w.run(DUR)
                dt_wall = time.time() - t0
                counts = np.array([len(w.spikes[i]) for i in range(net["n"])])
                rest_rate = counts / (DUR / 1000.0)
                win = np.array(
                    [sum(1 for t in w.spikes[i] if W1 <= t < W1 + 5000)
                     for i in range(net["n"])])
                win_rate = win / 5.0
                rec = {"wiring": wname, "seed": seed, "cond": cond,
                       "bg_seed": bg_seed(seed, variant_idx),
                       "total_spikes": int(counts.sum()),
                       "mean_rate_hz": float(rest_rate.mean()),
                       "max_rate_hz": float(rest_rate.max()),
                       "nan": bool(np.isnan(w.v).any()),
                       "wall_s": round(dt_wall, 2),
                       "groups": {}}
                for gname, ids in groups.items():
                    if not ids:
                        continue
                    gr = float(rest_rate[ids].mean())
                    wr = float(win_rate[ids].mean())
                    rec["groups"][gname] = {
                        "rest_hz": gr,
                        "stim_window_hz": wr,
                        "delta_hz": wr - gr,
                        "n": len(ids),
                    }
                out["runs"].append(rec)
                print(f"[{name}] {wname} seed={seed} {cond}: "
                      f"total={rec['total_spikes']} "
                      f"mean={rec['mean_rate_hz']:.2f}Hz "
                      f"max={rec['max_rate_hz']:.1f}Hz ({dt_wall:.1f}s)",
                      flush=True)

    # --- primary metric: stim-rest deltas ----------------------------
    for wiring, _ in wirings:
        for gname in groups:
            dvals, rvals = [], []
            for r in out["runs"]:
                if r["wiring"] != wiring or r["cond"] != "stim":
                    continue
                g = r["groups"].get(gname)
                if not g:
                    continue
                dvals.append(g["delta_hz"])
                if g["rest_hz"] >= 0.1:
                    rvals.append(g["delta_hz"] / g["rest_hz"])
            out["summary"][f"{wiring}/{gname}"] = {
                "n_seeds": len(dvals),
                "rest_hz_mean": None,  # filled below from rest runs
                "stim_window_hz_mean":
                    float(np.mean([r["groups"][gname]["stim_window_hz"]
                                   for r in out["runs"]
                                   if r["wiring"] == wiring
                                   and r["cond"] == "stim"
                                   and gname in r["groups"]]))
                    if dvals else None,
                "delta_hz_values": dvals,
                "delta_hz_mean": float(np.mean(dvals)) if dvals else None,
                "delta_hz_sd": float(np.std(dvals)) if dvals else None,
                "response_index_values": rvals,
                "response_index_mean": float(np.mean(rvals)) if rvals
                else None,
            }
            rest_runs = [r for r in out["runs"]
                         if r["wiring"] == wiring and r["cond"] == "rest"]
            if rest_runs and gname in rest_runs[0]["groups"]:
                out["summary"][f"{wiring}/{gname}"]["rest_hz_mean"] = \
                    float(np.mean([r["groups"][gname]["rest_hz"]
                                   for r in rest_runs]))
    # headline: measured vs each shuffle on the delta, with the spread
    # ACROSS the 3 independent shuffle graphs reported explicitly
    head = {}
    for gname in groups:
        m = out["summary"].get(f"measured/{gname}", {})
        sh = [out["summary"].get(f"shuf-{s}/{gname}", {})
              for s in shuf_seeds]
        sh_means = [x.get("delta_hz_mean") for x in sh]
        head[gname] = {
            "measured_delta_mean_hz": m.get("delta_hz_mean"),
            "measured_delta_sd_hz": m.get("delta_hz_sd"),
            "shuffle_deltas_mean_hz": sh_means,
            "shuffle_deltas_spread_across_graphs_hz":
                (float(np.std(sh_means)) if all(x is not None for x in sh_means)
                 else None),
            "measured_beats_all_shuffles":
                (m.get("delta_hz_mean") is not None
                 and all(x is not None for x in sh_means)
                 and m["delta_hz_mean"] > max(sh_means)),
        }
    out["headline"] = head
    out["verdicts"] = {
        "stable": all(r["max_rate_hz"] < 200 and not r["nan"]
                      for r in out["runs"]),
        "routed_command_pool":
            head["command_pool"]["measured_delta_mean_hz"] is not None
            and head["command_pool"]["measured_delta_mean_hz"] > 0.5
            and head["command_pool"]["measured_beats_all_shuffles"],
        "routed_motors":
            head["body_wall_motors"]["measured_delta_mean_hz"] is not None
            and head["body_wall_motors"]["measured_delta_mean_hz"] > 0.5
            and head["body_wall_motors"]["measured_beats_all_shuffles"],
    }
    return out


def main():
    results = {}
    for idx, name in enumerate(VARIANTS):
        results[name] = run_variant(name, idx)
        print(json.dumps({name: results[name]["verdicts"],
                          "headline": results[name]["headline"]}, indent=1))
    with open(os.path.join(HERE, "..", "results-exact.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("results-exact.json written (v1 results.json untouched)")


if __name__ == "__main__":
    main()
