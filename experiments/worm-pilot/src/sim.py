"""LIF spiking network of the measured C. elegans (herm) connectome with
shared-conductance gap junctions.

Model conventions: the lab LIF of experiments/b-01-internal-compass/lif.py
(tau_m = 20 ms, V_th = -45 mV, V_0 = V_rst = -52 mV, refractory 2.2 ms,
dt = 1 ms, single-exponential synaptic current with constant 1.8 ms
delay), with two declared deviations (see README):
  1. gap junctions modelled as linear shared conductance, as in the
     Cook 2019 treatment of the symmetric/asymmetric sheets:
     dV/dt = -(V - T)/tau_m + sum_j g_j (v_j - V), with per-neuron
     effective time constant 1/a, a = 1/tau_m + G_i. Solved exactly per
     step (unconditionally stable); with no junctions this reduces to
     lif.py's exact exponential form;
  2. the stimulus is a constant depolarization offset on the ASH
     receptors (a receptor potential), not a spike train.

Chemical synapses: all-positive weights w = alpha * sqrt(section count)
(the released data carry no signs — see circuits/c-elegans-substrate.md).
"""
import json
import numpy as np


def load_network(data_dir, cfg):
    neurons = json.load(open(f"{data_dir}/c-elegans-neurons-herm.json"))
    edges = json.load(open(f"{data_dir}/c-elegans-edges-herm.json"))
    idx = {n: i for i, n in enumerate(neurons)}
    n = len(neurons)

    # chemical: directed, positive weights
    chem = [e for e in edges if e["kind"] == "chem"
            and e["pre"] in idx and e["post"] in idx]
    csrc = np.array([idx[e["pre"]] for e in chem], dtype=np.int64)
    cdst = np.array([idx[e["post"]] for e in chem], dtype=np.int64)
    cw = np.array([e["w"] for e in chem], dtype=np.float64)
    c_w = cfg["alpha"] * np.sqrt(cw)
    o = np.argsort(csrc, kind="stable")
    csrc, cdst, c_w = csrc[o], cdst[o], c_w[o]
    u_src, counts = np.unique(csrc, return_counts=True)
    u_start = np.concatenate([[0], np.cumsum(counts)])

    # gap junctions. Symmetric sheets: undirected pairs (a, b, g).
    # Asymmetric sheets: directed (s -> d, g).
    sym_pairs, asym_pairs = [], []
    for e in edges:
        if e["kind"] == "gap_sym" and e["pre"] in idx and e["post"] in idx:
            a, b = idx[e["pre"]], idx[e["post"]]
            sym_pairs.append((min(a, b), max(a, b), float(e["w"]) * cfg["beta"]))
        elif e["kind"] == "gap_asym" and e["pre"] in idx and e["post"] in idx:
            asym_pairs.append((idx[e["pre"]], idx[e["post"]],
                               float(e["w"]) * cfg["beta"]))
    gs = np.array([x for p in sym_pairs for x in (p[0], p[1])] +
                  [p[0] for p in asym_pairs], dtype=np.int64)
    gd = np.array([x for p in sym_pairs for x in (p[1], p[0])] +
                  [p[1] for p in asym_pairs], dtype=np.int64)
    gw = np.array([w for p in sym_pairs for w in (p[2], p[2])] +
                  [p[2] for p in asym_pairs], dtype=np.float64)

    return {"n": n, "names": neurons, "idx": idx,
            "c_src": csrc, "c_dst": cdst, "c_w": c_w,
            "u_src": u_src, "u_start": u_start,
            "g_src": gs, "g_dst": gd, "g_w": gw,
            "g_sym_pairs": sym_pairs, "g_asym_pairs": asym_pairs,
            "n_chem": len(chem), "n_gap_pairs": len(sym_pairs)}


class WormNet:
    def __init__(self, net, cfg, seed):
        self.net = net
        self.cfg = cfg
        self.n = net["n"]
        self.rng = np.random.default_rng(seed)
        self.exp_tau = np.exp(-cfg["dt"] / cfg["tau_syn"])
        # effective membrane time constant per neuron: the gap-junction
        # conductance adds in parallel to the leak, so tau_eff = 1/a with
        # a = 1/tau_m + G_i. Precompute the exact per-step factors.
        G = np.zeros(self.n)
        np.add.at(G, net["g_dst"], net["g_w"])
        self.a = 1.0 / cfg["tau_m"] + G
        self.exp_a = np.exp(-self.a * cfg["dt"])
        self._reset()

    def _reset(self):
        self.v = np.full(self.n, self.cfg["v0"])
        self.g = np.zeros(self.n)
        self.ref = np.zeros(self.n)
        self.queue = [np.zeros(0, dtype=np.int64)
                      for _ in range(self.cfg["delay_steps"])]
        self.t = 0.0
        self.t_stim_left = 0.0
        self.t_stim_start = None
        self.t_stim_dur = None
        self.stim_ids = np.zeros(0, dtype=np.int64)
        self.t_stim_current = 0.0
        self.spikes = {i: [] for i in range(self.n)}
        self.g_sum = 0.0
        self.g_samples = 0
        self._step_count = 0

    @property
    def mean_g(self):
        return self.g_sum / max(1, self.g_samples)

    def _deliver(self, ids):
        if len(ids) == 0:
            return
        ids, cnt = np.unique(ids, return_counts=True)
        j = np.searchsorted(self.net["u_src"], ids)
        safe = np.minimum(j, len(self.net["u_src"]) - 1)
        valid = (j < len(self.net["u_src"])) & (self.net["u_src"][safe] == ids)
        ids, cnt, j = ids[valid], cnt[valid], j[valid]
        if len(j) == 0:
            return
        s = self.net["u_start"][j]
        e = self.net["u_start"][j + 1]
        sizes = e - s
        total = int(sizes.sum())
        base = np.repeat(s, sizes)
        starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
        pos = base + (np.arange(total) - np.repeat(starts, sizes))
        np.add.at(self.g, self.net["c_dst"][pos],
                  self.net["c_w"][pos] * np.repeat(cnt, sizes))

    def step(self):
        """One dt-ms step. Returns the ids that spiked.

        Membrane: dV/dt = -(V - T)/tau_m + sum_j g_j (v_j - V), with
        T = v0 + g + I_stim (the lab LIF target-shift convention of
        lif.py, so the chemical part reduces to its exact form when the
        neuron has no gap junctions). Solved exactly per step:
        V' = B/a + (V - B/a) * exp(-a*dt) — unconditionally stable.
        """
        cfg = self.cfg
        self.t += cfg["dt"]
        # 1. deliver delayed internal spikes
        self._deliver(self.queue.pop(0))
        # 2. background Poisson drive (external spikes, same delay)
        bg = self.rng.binomial(1, cfg["lambda_bg"] * cfg["dt"] / 1000.0, self.n)
        bg_ids = np.nonzero(bg)[0]
        if len(bg_ids) > 0:
            np.add.at(self.g, bg_ids, cfg["w_bg"])
        # 3. target offset (synaptic current decayed with tau_syn)
        T = cfg["v0"] + self.g
        if self.t_stim_start is not None and \
                self.t_stim_start <= self.t < self.t_stim_start + self.t_stim_dur:
            T = T.copy()
            T[self.stim_ids] += self.t_stim_current
            if self.t >= self.t_stim_start + self.t_stim_dur:
                self.t_stim_start = None  # done
        # 4. gap-junction weighted inputs
        wv = np.zeros(self.n)
        if len(self.net["g_src"]) > 0:
            np.add.at(wv, self.net["g_dst"],
                      self.net["g_w"] * self.v[self.net["g_src"]])
        # 5. exact membrane update
        a = self.a
        target = (T / cfg["tau_m"] + wv) / a
        self.v = target + (self.v - target) * self.exp_a
        # 6. synaptic-current decay (after use, as in lif.py)
        self.g *= self.exp_tau
        # 7. refractory
        self.ref = np.maximum(self.ref - cfg["dt"], 0.0)
        # 8. threshold
        spiked = np.nonzero((self.v > self.cfg["v_th"]) & (self.ref <= 0))[0]
        if len(spiked) > 0:
            self.v[spiked] = self.cfg["v_rst"]
            self.g[spiked] = 0.0
            self.ref[spiked] = cfg["refractory_ms"]
            for i in spiked:
                self.spikes[i].append(self.t)
        # 9. queue internal + external events together (fixed delay)
        if len(bg_ids) > 0:
            self.queue.append(np.concatenate([spiked, bg_ids]))
        else:
            self.queue.append(spiked)
        # diagnostics
        if self._step_count % 10 == 0:
            self.g_sum += float(self.g.mean())
            self.g_samples += 1
        self._step_count += 1
        return spiked

    def run(self, duration_ms, stim_ids=(), stim_current=0.0,
            stim_start_ms=0.0, stim_dur_ms=0.0):
        self._reset()
        self.stim_ids = np.asarray(stim_ids, dtype=np.int64)
        self.t_stim_current = stim_current
        if len(self.stim_ids) > 0 and stim_current > 0:
            self.t_stim_start = stim_start_ms
            self.t_stim_dur = stim_dur_ms
        for _ in range(int(duration_ms // self.cfg["dt"])):
            self.step()
        return self


def make_shuffled(net, cfg, seed):
    """Degree-matched random wiring (configuration model).

    Same edge counts, same out-degree per pre and in-degree per post,
    same weight multiset (reassigned randomly); self-edges and
    duplicate pairs rejected (a few edges may drop; counted). Chemical
    and gap junctions are shuffled independently; all gap junctions are
    treated as undirected pairs for the shuffle (the pilot's declared
    simplification — see README).
    """
    rng = np.random.default_rng(seed)
    n = net["n"]
    shuf = dict(net)

    # chemical multigraph: exact degree marginals, shuffled partner
    # assignment; self-loops dropped and counted; parallel edges kept
    # (they exist in the real data).
    out = np.zeros(n, dtype=int)
    inn = np.zeros(n, dtype=int)
    for s, d in zip(net["c_src"], net["c_dst"]):
        out[s] += 1
        inn[d] += 1
    pres = np.repeat(np.arange(n), out)
    post_pool = np.repeat(np.arange(n), inn)
    rng.shuffle(post_pool)
    new_s, new_d = [], []
    n_self = 0
    for s, d in zip(pres, post_pool):
        if s == d:
            n_self += 1
            continue
        new_s.append(s); new_d.append(d)
    ws = np.array(net["c_w"], dtype=np.float64)
    rng.shuffle(ws)
    new_w = np.array([ws[i % len(ws)] for i in range(len(new_s))])
    new_s = np.array(new_s, dtype=np.int64)
    new_d = np.array(new_d, dtype=np.int64)
    o = np.argsort(new_s, kind="stable")
    u_src, counts = np.unique(new_s, return_counts=True)
    shuf["c_src"], shuf["c_dst"], shuf["c_w"] = new_s[o], new_d[o], new_w[o]
    shuf["u_src"], shuf["u_start"] = u_src, np.concatenate([[0], np.cumsum(counts)])
    shuf["n_chem"] = len(new_s)
    shuf["n_chem_self_dropped"] = n_self

    # gap junctions as undirected pairs (declared simplification: the
    # asymmetric sheets are treated as undirected for the control);
    # multiple junctions per pair are merged by max (as in the release
    # matrices). Configuration model: the pool of 2*k endpoint slots is
    # shuffled and consecutive slots are paired until k distinct
    # non-self pairs are built, so the shuffled wiring has the same
    # pair count, degree marginals and weight multiset.
    pairw = {}
    for a, b, w in net["g_sym_pairs"] + net["g_asym_pairs"]:
        a, b = int(min(a, b)), int(max(a, b))
        pairw[(a, b)] = max(pairw.get((a, b), 0.0), w)
    items = list(pairw.items())
    k = len(items)
    deg = np.zeros(n, dtype=int)
    for (a, b), _ in items:
        deg[a] += 1
        deg[b] += 1
    pool = np.repeat(np.arange(n), np.maximum(deg, 0))
    rng.shuffle(pool)
    ws = np.array([w for _, w in items], dtype=np.float64)
    rng.shuffle(ws)
    accepted, used, pi = [], set(), 0
    while len(accepted) < k and pi + 1 < len(pool):
        a, b = int(pool[pi]), int(pool[pi + 1])
        pi += 2
        if a == b or (a, b) in used or (b, a) in used:
            continue
        used.add((a, b))
        accepted.append((a, b, ws[len(accepted)] % len(ws)))
    new_gs = np.array([a for a, b, _ in accepted], dtype=np.int64)
    new_gd = np.array([b for a, b, _ in accepted], dtype=np.int64)
    new_gw = np.array([w for _, _, w in accepted], dtype=np.float64)
    shuf["g_src"] = np.concatenate([new_gs, new_gd])
    shuf["g_dst"] = np.concatenate([new_gd, new_gs])
    shuf["g_w"] = np.concatenate([new_gw, new_gw])
    shuf["n_gap_pairs"] = len(new_gs)
    shuf["n_gap_pairs_input"] = k
    return shuf
