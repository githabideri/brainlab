"""Final campaign: per declared variant (5 ms / 50 ms tau_syn),
5 seeds x 2 wirings (measured / shuffled) x 2 conditions (rest /
stim) = 20 runs. Writes results.json.

Reads the FROZEN config-<variant>.json; no parameter is tuned here.

Readout (README): rest rate = mean Hz over the whole 15 s; stimulus
response = mean Hz in the window [5.5, 10.5] s after the 500 ms pulse
at t=5 s.
"""
import json
import os
import sys
import time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim import load_network, WormNet, make_shuffled  # noqa: E402

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


def run_variant(name):
    cfg = json.load(open(os.path.join(HERE, "..", f"config-{name}.json")))
    net = load_network(DATA, cfg)
    shuf = make_shuffled(net, cfg, cfg["shuffle_seed"])
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
    out = {"config": cfg, "runs": [], "summary": {}}

    for wiring, network in (("measured", net), ("shuffled", shuf)):
        for seed in cfg["seeds"]:
            for cond in ("rest", "stim"):
                t0 = time.time()
                w = WormNet(network, cfg, seed)
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
                rec = {"wiring": wiring, "seed": seed, "cond": cond,
                       "total_spikes": int(counts.sum()),
                       "mean_rate_hz": float(rest_rate.mean()),
                       "max_rate_hz": float(rest_rate.max()),
                       "nan": bool(np.isnan(w.v).any()),
                       "wall_s": round(dt_wall, 2),
                       "groups": {}}
                for gname, ids in groups.items():
                    if not ids:
                        continue
                    gr = rest_rate[ids]
                    wr = win_rate[ids]
                    rec["groups"][gname] = {
                        "rest_hz": float(gr.mean()),
                        "stim_window_hz": float(wr.mean()),
                        "n": len(ids),
                    }
                out["runs"].append(rec)
                print(f"[{name}] {wiring} seed={seed} {cond}: "
                      f"total={rec['total_spikes']} "
                      f"mean={rec['mean_rate_hz']:.2f}Hz "
                      f"max={rec['max_rate_hz']:.1f}Hz ({dt_wall:.1f}s)",
                      flush=True)

    # --- summary. Primary metric: post-stim group rate (Hz) per wiring,
    # mean +- SD over seeds. Secondary: response index where the rest
    # rate is >= 0.1 Hz (undefined for a sparse-silent rest).
    for wiring in ("measured", "shuffled"):
        for gname in groups:
            vals, ri = [], []
            for r in out["runs"]:
                if r["wiring"] != wiring or r["cond"] != "stim":
                    continue
                g = r["groups"].get(gname)
                if not g:
                    continue
                vals.append(g["stim_window_hz"])
                rest = [x for x in out["runs"]
                        if x["wiring"] == wiring and x["cond"] == "rest"
                        and x["seed"] == r["seed"]]
                rg = rest[0]["groups"].get(gname) if rest else None
                if rg and rg["rest_hz"] >= 0.1:
                    ri.append((g["stim_window_hz"] - rg["rest_hz"])
                              / rg["rest_hz"])
            out["summary"][f"{wiring}/{gname}"] = {
                "n_seeds": len(vals),
                "poststim_hz_mean": float(np.mean(vals)) if vals else None,
                "poststim_hz_sd": float(np.std(vals)) if vals else None,
                "poststim_hz_values": vals,
                "response_index_values": ri,
                "response_index_mean": float(np.mean(ri)) if ri else None,
            }
    m = out["summary"].get("measured/command_pool", {})
    s = out["summary"].get("shuffled/command_pool", {})
    mm = out["summary"].get("measured/body_wall_motors", {})
    sm = out["summary"].get("shuffled/body_wall_motors", {})

    def beats(a, b):
        av, bv = a.get("poststim_hz_mean"), b.get("poststim_hz_mean")
        if av is None or bv is None:
            return False
        return av > 0.5 and av > bv and av > (a.get("poststim_hz_sd") or 0)

    out["verdicts"] = {
        "stable": all(r["max_rate_hz"] < 200 and not r["nan"]
                      for r in out["runs"]),
        "routed_command_pool": beats(m, s),
        "routed_motors": beats(mm, sm),
        "wiring_matters_command_pool": beats(m, s),
        "wiring_matters_motors": beats(mm, sm),
    }
    return out


def main():
    results = {}
    for name in VARIANTS:
        results[name] = run_variant(name)
        print(json.dumps({name: results[name]["verdicts"]}, indent=1))
    with open(os.path.join(HERE, "..", "results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("results.json written")


if __name__ == "__main__":
    main()
