#!/bin/sh
# A-03 pre-registered campaign runner (design lane: NOT executed by the
# A-03 session — this is scripted here and run by the coordinator after
# the heavy lane, per the pre-registration in README.md).
#
#   CIRCUIT=<path to the staged flywire-fafb-olfactory-1536 circuit.json>
#   [PY=python] [SEEDS=100,101,102,103,104] [MAX_HOURS=16] run-all.sh
#
# Budget: 210 runs = 32 arm columns x 3 tasks x 5 seeds (pre-registered
# grid; the shrink ladder in README.md applies in order if the sizing
# projection overruns MAX_HOURS — edit MAIN in run.py, never here).
set -eu
cd "$(dirname "$0")"
PY=${PY:-python3}
MAX_HOURS=${MAX_HOURS:-16}
CIRCUIT=${CIRCUIT:?set CIRCUIT to the staged circuit.json (sha256-verified by run.py)}
SEEDS=${SEEDS:-100,101,102,103,104}

echo "== A-03 main grid (pre-registered; $MAX_HOURS-hour budget)"
$PY run.py --circuit "$CIRCUIT" --phase main --seeds "$SEEDS"
$PY run.py --circuit "$CIRCUIT" --phase summary
$PY run.py --circuit "$CIRCUIT" --phase manifest
echo "== done; results/ holds 210 per-run JSONs + summary.json + manifest.json"
