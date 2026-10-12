#!/bin/bash
# B-01: run all pre-registered (variant, seed) sessions sequentially.
set -u
PY=/root/homelab/temp/brainlab/venv/bin/python
cd "$(dirname "$0")"
for variant in bio ring shuffle; do
  for seed in 0 1 2 3 4; do
    out="results/${variant}-seed${seed}.json"
    if [ -s "$out" ]; then echo "skip $out (exists)"; continue; fi
    echo "=== $variant seed $seed ==="
    "$PY" run.py --variant "$variant" --seed "$seed" > "results/${variant}-seed${seed}.log" 2>&1
    echo "rc=$? $variant seed $seed"
  done
done
echo "ALL DONE $(date)"
