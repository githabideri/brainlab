"""Round-5 minimal re-run driver (2026-10-13, review round 5).

Re-measures the ASH nociception question on the CORRECTED substrate:

  1. v3 canonical electrical graph + background Model A (default,
     pure external current): BOTH variants (5 ms + 50 ms), 4 wirings
     x 5 seeds x rest/stim = 80 runs -> results-v3-canonical.json
  2. v3 canonical electrical graph + background Model B (historical
     forced propagation), 50 ms variant only: 40 runs ->
     results-v3-modelB-50ms.json
  3. 50 ms Model A time course (paired-input windows): 40 runs ->
     data/timecourse-50ms-v3.json

The scientific question (review round 5): do the round-4 findings —
+0.090 Hz 5-s paired contrast (5 ms variant) and +1.75 Hz during-
pulse contrast (50 ms variant) — SURVIVE the two P0 substrate
corrections? If they disappear, the honest report is that the
round-4 positive was a substrate artifact. No new gains/timescales
are introduced; parameters are the frozen v2 values (config-*.json).

Frozen v2 artifacts (results-exact.json, data/timecourse-50ms.json,
data/paired-stim-effect.json, config-*-v2-dual-electrical.json) are
NOT touched.

Usage:  python src/run_v3.py
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, os.path.join(HERE, "src"))

import run_campaign as rc  # noqa: E402
import timecourse as tc  # noqa: E402


def main():
    # 1) canonical substrate, Model A, both variants
    res = {}
    for idx, name in enumerate(rc.VARIANTS):
        res[name] = rc.run_variant(name, idx, tag="v3")
        print(json.dumps({name: res[name]["verdicts"],
                          "headline": res[name]["headline"]}, indent=1),
              flush=True)
    p = os.path.join(HERE, "results-v3-canonical.json")
    with open(p, "w") as f:
        json.dump(res, f, indent=1)
    print(f"wrote {os.path.relpath(p, HERE)}")

    # 2) canonical substrate, Model B, 50 ms only (dependency check)
    resB = {"50ms": rc.run_variant("50ms", 1, tag="v3-modelB",
                                   cfg_name="50ms-v3-modelB")}
    p = os.path.join(HERE, "results-v3-modelB-50ms.json")
    with open(p, "w") as f:
        json.dump(resB, f, indent=1)
    print(f"wrote {os.path.relpath(p, HERE)}")

    # 3) 50 ms time course on the canonical substrate (Model A)
    tc.main("v3")


if __name__ == "__main__":
    main()
