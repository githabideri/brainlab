#!/usr/bin/env python3
"""Control comparison driver: fly vs shuffled vs disconnected FlyWire wiring,
same sugar-GRN stimulus, same AlphaLIF model, same budget.

Imports the reference toolkit (eonsystemspbc/fly-brain) for the circuit
loader, the Shiu et al. AlphaLIF model, and the `sugar` experiment table,
so the `fly` variant is bit-identical to the toolkit's own circuit.

Usage:
  python run_control.py --out /var/brainlab/runs/<campaign>/control \
      [--seeds 5] [--pre 0.5] [--stim 1.0] [--post 1.0] [--shuf-seed-base 20261004]

Outputs into --out:
  manifest.json                 seeds, circuit hash, toolkit commit, versions
  <variant>_seed<i>.json        per-run readout (see README)
  <variant>_seed<i>.rates.npy   per-neuron rate vector (spikes/s), for
                                post-hoc cross-variant correlation
  summary.json                  pairwise comparisons + aggregates
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import torch


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- toolkit ---
FLYBRAIN = Path(os.environ.get("FLYBRAIN_DIR", "/opt/fly-brain"))
sys.path.insert(0, str(FLYBRAIN / "code"))

log(f"importing toolkit from {FLYBRAIN}")
from benchmark import get_experiment, path_comp, path_con, path_wt  # noqa: E402
from run_pytorch import DT, MODEL_PARAMS, TorchModel, get_weights, get_hash_tables  # noqa: E402

# ---------------------------------------------------------------- helpers ---


def sha256_16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def tool_commit():
    try:
        return subprocess.run(
            ["git", "-C", str(FLYBRAIN), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def to_csr(w):
    return w.to_sparse_csr() if hasattr(w, "to_sparse_csr") else w


def build_shuffled(presyn, postsyn, weights, n, candidates, shuf_seed):
    """Keep source+weight of every edge; re-sample the target uniformly from
    neurons that have >=1 input, no duplicate (src,dst) per source.
    Returns (presyn, new_postsyn, weights) in presyn-sorted order."""
    log(f"shuffling {len(presyn)} edges (seed {shuf_seed})")
    rng = np.random.RandomState(shuf_seed)
    cands = np.asarray(candidates, dtype=np.int64)
    order = np.argsort(presyn, kind="stable")
    src_sorted = presyn[order]
    w_sorted = weights[order]
    src_vals, starts = np.unique(src_sorted, return_index=True)
    ends = np.append(starts[1:], len(src_sorted))
    new_postsyn = np.empty_like(presyn)
    for i, src in enumerate(src_vals):
        s, e = int(starts[i]), int(ends[i])
        k = e - s
        if k == 0:
            continue
        tries = min(k * 4 + 64, len(cands))
        if tries < k:
            tries = k
        pick = (rng.choice(len(cands), size=tries, replace=False)
                if tries < len(cands)
                else rng.integers(0, len(cands), size=tries))
        targets = cands[pick]
        _, first = np.unique(targets, return_index=True)
        first = np.sort(first)[:k]
        if len(first) < k:
            extra = rng.choice(len(cands), size=k - len(first), replace=True)
            first = np.concatenate([first, extra])[:k]
        new_postsyn[order[s:e]] = targets[np.sort(first)]
    return presyn, new_postsyn, w_sorted


def run_variant(name, weights, exc_idx, n, seed, pre, stim, post, out):
    torch.manual_seed(seed)
    # DT is in ms; the protocol times are in seconds
    pre_steps = int(round(pre * 1000 / DT))
    stim_steps = int(round(stim * 1000 / DT))
    post_steps = int(round(post * 1000 / DT))
    total = pre_steps + stim_steps + post_steps

    model = TorchModel(1, n, DT, MODEL_PARAMS, weights,
                       exc_indices=exc_idx, device="cpu")
    conductance, delay_buffer, spikes, v, refrac = model.state_init()

    rates = torch.zeros(1, n, device="cpu")
    total_count = torch.zeros(n, dtype=torch.long)
    post_count = torch.zeros(n, dtype=torch.long)
    t0 = time.time()
    with torch.no_grad():
        for step in range(total):
            rates.zero_()
            if pre_steps <= step < pre_steps + stim_steps:
                rates[0, exc_idx] = 200.0
            out_state = model(rates, conductance, delay_buffer, spikes, v, refrac)
            conductance, delay_buffer, spikes, v, refrac = out_state
            total_count += (spikes[0] > 0).long()
            if step >= pre_steps + stim_steps:
                post_count += (spikes[0] > 0).long()
    wall = time.time() - t0

    dur = pre + stim + post
    rate = total_count.float() / dur            # spikes per second
    post_rate = post_count.float() / post       # spikes/s, offset window
    active = int((rate > 1.0).sum())
    top50 = torch.topk(total_count, 50)
    np.save(out / f"{name}_seed{seed}.rates.npy",
            rate.numpy().astype(np.float32))
    np.save(out / f"{name}_seed{seed}.postrates.npy",
            post_rate.numpy().astype(np.float32))
    return {
        "variant": name,
        "seed": seed,
        "wall_s": round(wall, 1),
        "total_spikes": int(total_count.sum()),
        "post_offset_spikes": int(post_count.sum()),
        "active_neurons_gt1Hz": active,
        "rate_mean": round(float(rate.mean()), 4),
        "rate_median": round(float(rate.median()), 4),
        "rate_p90": round(float(torch.quantile(rate, 0.90)), 4),
        "top50_indices": [int(i) for i in top50.indices.tolist()],
        "top50_counts": [int(c) for c in top50.values.tolist()],
    }


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = pd.Series(a).rank().to_numpy(dtype=np.float64)
    rb = pd.Series(b).rank().to_numpy(dtype=np.float64)
    ra = (ra - ra.mean()) / (ra.std() + 1e-12)
    rb = (rb - rb.mean()) / (rb.std() + 1e-12)
    return float(np.dot(ra, rb) / len(ra))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--pre", type=float, default=0.5)
    ap.add_argument("--stim", type=float, default=1.0)
    ap.add_argument("--post", type=float, default=1.0)
    ap.add_argument("--shuf-seed-base", type=int, default=20261004)
    ap.add_argument("--variants", default="fly,shuffled,disconnected")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    exp = get_experiment("sugar")
    log(f"experiment: {exp['name']} — {len(exp['neu_exc'])} neurons @ "
        f"{exp['stim_rate']} Hz")

    flyid2i, _ = get_hash_tables(str(path_comp))
    exc_idx = [flyid2i[int(nid)] for nid in exp["neu_exc"]]
    n = pd.read_csv(path_comp).shape[0]   # exactly the toolkit's num_neurons
    log(f"neurons: {n}")

    manifest = {
        "experiment": "control-comparison",
        "circuit_parquet_sha256_16": sha256_16(str(path_con)),
        "circuit_csv_sha256_16": sha256_16(str(path_comp)),
        "toolkit_commit": tool_commit(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "nproc": os.cpu_count(),
        "model_params": MODEL_PARAMS,
        "dt_ms": DT,
        "stimulus": {"experiment": "sugar", "n_stimulated": len(exc_idx),
                     "rate_hz": exp["stim_rate"], "pre_s": args.pre,
                     "stim_s": args.stim, "post_s": args.post},
        "stim_seeds": list(range(100, 100 + args.seeds)),
        "shuffled_seed_base": args.shuf_seed_base,
        "variants": args.variants.split(","),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    log("loading fly weights (COO for shuffling, CSR for the model; "
        "cached pkl reused if present)")
    w_coo = get_weights(str(path_con), str(path_comp), str(path_wt),
                        csr=False).coalesce()
    idx = w_coo.indices()
    postsyn, presyn = idx[0].numpy(), idx[1].numpy()
    vals = w_coo.values().numpy()
    log(f"edges: {len(presyn)}")
    w_csr = to_csr(w_coo)

    has_input = np.unique(presyn)  # neurons with >=1 input = targets
    log(f"shuffling candidate targets: {len(has_input)} neurons")

    # expected Poisson spikes in the stim window: n_stim × stim_steps × p,
    # p = rate(Hz) × dt(s). Any run returning far below this is a protocol
    # bug (e.g. a units mix-up in the step counts), not a result.
    expected_poisson = len(exc_idx) * int(round(args.stim * 1000 / DT)) \
        * (exp["stim_rate"] * DT / 1000.0)
    log(f"expected Poisson stim spikes ≈ {expected_poisson:.0f}")

    variants = {"fly": w_csr}
    if "shuffled" in args.variants:
        sp, sp2, sv = build_shuffled(presyn, postsyn, vals, n, has_input,
                                     args.shuf_seed_base)
        ws = torch.sparse_coo_tensor(
            torch.tensor([sp2, sp]),
            torch.tensor(sv, dtype=torch.float32), (n, n)).coalesce()
        variants["shuffled"] = to_csr(ws)
        log("shuffled built")
    if "disconnected" in args.variants:
        wd = torch.sparse_coo_tensor(
            torch.tensor([[], []], dtype=torch.int64),
            torch.tensor([], dtype=torch.float32), (n, n)).coalesce()
        variants["disconnected"] = to_csr(wd)
        log("disconnected built")

    names = list(variants)
    seeds = manifest["stim_seeds"]
    results = {}
    for name in names:
        for seed in seeds:
            tag = f"{name}_seed{seed}"
            res = out / f"{tag}.json"
            if res.exists():
                log(f"{tag}: exists, skipping")
                results[tag] = json.loads(res.read_text())
                continue
            log(f"running {tag} ...")
            try:
                r = run_variant(name, variants[name], exc_idx, n, seed,
                                args.pre, args.stim, args.post, out)
            except Exception as e:
                log(f"{tag} FAILED: {e!r}")
                (out / f"{tag}.error.txt").write_text(
                    repr(e) + "\n" + traceback.format_exc())
                continue
            results[tag] = r
            res.write_text(json.dumps(r, indent=2))
            if r["total_spikes"] < 0.5 * expected_poisson:
                log(f"WARNING {tag}: {r['total_spikes']} spikes is far below "
                    f"the expected ~{expected_poisson:.0f} Poisson stim spikes — "
                    f"treat as a protocol bug, not a result")
            log(f"{tag} done: {r['total_spikes']} spikes "
                f"({r['active_neurons_gt1Hz']} active) in {r['wall_s']}s wall")

    # ------------------------------------------------------------- summary --
    summary = {"manifest_file": "manifest.json", "pairwise": {},
               "aggregates": {}}
    for seed in seeds:
        row = {}
        got = {}
        for v in names:
            tag = f"{v}_seed{seed}"
            if tag in results and "total_spikes" in results[tag]:
                got[v] = results[tag]
        keys = list(got)
        for ai, a in enumerate(keys):
            for b in keys[ai + 1:]:
                entry = {
                    "jaccard_top50": round(
                        len(set(got[a]["top50_indices"])
                             & set(got[b]["top50_indices"]))
                        / max(1, len(set(got[a]["top50_indices"])
                                    | set(got[b]["top50_indices"]))), 4),
                    "total_spike_ratio_b_over_a": round(
                        got[b]["total_spikes"] /
                        max(1, got[a]["total_spikes"]), 4),
                }
                fa = out / f"{a}_seed{seed}.rates.npy"
                fb = out / f"{b}_seed{seed}.rates.npy"
                if fa.exists() and fb.exists():
                    entry["spearman_rates"] = round(
                        spearman(np.load(fa), np.load(fb)), 4)
                row[f"{a}_vs_{b}"] = entry
        summary["pairwise"][f"seed_{seed}"] = row
    for v in names:
        ts = [results[f"{v}_seed{s}"]["total_spikes"] for s in seeds
              if f"{v}_seed{s}" in results
              and "total_spikes" in results[f"{v}_seed{s}"]]
        if ts:
            summary["aggregates"][v] = {
                "total_spikes_mean": round(float(np.mean(ts)), 1),
                "total_spikes_sd": round(float(np.std(ts)), 1),
                "runs_completed": len(ts),
            }
    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    log(f"summary written: {out / 'summary.json'}")

    failed = 0
    for v in names:
        for s in seeds:
            tag = f"{v}_seed{s}"
            if tag not in results or "total_spikes" not in results.get(tag, {}):
                failed += 1
    log(f"campaign result: {failed} missing (variant,seed) runs")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
