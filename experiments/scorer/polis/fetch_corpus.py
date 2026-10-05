#!/usr/bin/env python3
"""Fetch the polis decision corpus (public repo) by sha256 into ./corpus/.

Usage: python3 fetch_corpus.py [--base https://raw.githubusercontent.com/githabideri/polis/main]
"""
import hashlib
import os
import sys
import urllib.request

BASE_DEFAULT = "https://raw.githubusercontent.com/githabideri/polis/main"
FILES = {
    "ft2-train.jsonl":        ("data/ft2-rows-2026-09-26/train.jsonl", "605e8e31739511aef0b7205e3aa87ee83f5b31b92d5578de58e33ab015f59b09"),
    "val.json":               ("data/ft2-rows-2026-09-26/val.json", "2e68be9044791f7927c3915212ce0f02944e33804c2f861ea4cedddb86037dd3"),
    "ab-summary.json":        ("data/ft2-ab/summary.json", "a3ae962cd24341a458adf200eec60c838461e6bc3895a153fb83f52e4f6d74c5"),
    "2b-valworld.jsonl":      ("data/ft2-ab/qwen35-decider-2b-valworld.jsonl", "a83a9c18b946477480c47beb5853749a2edd8fd1db4bc2af0eee578447be0042"),
    "2b-ft-valworld.jsonl":   ("data/ft2-ab/qwen35-decider-2b-ft-valworld.jsonl", "dabcdc6f2a4443ac9db0931d0bee25ed45db4348f164f476603aac830ea42e1b"),
    "2b-ft2-valworld.jsonl":  ("data/ft2-ab/qwen35-decider-2b-ft2-valworld.jsonl", "29e9dd0b0e64c6bd1f7c5c24d44c61e557b5e7ee7558fb7806db6e2d630279d7"),
    "2b-abstain.jsonl":       ("data/ft2-ab/qwen35-decider-2b-abstain.jsonl", "3f47b4212dd088b480416d60207766748647d5e6822cefd403818f39e1012325"),
    "2b-ft-abstain.jsonl":    ("data/ft2-ab/qwen35-decider-2b-ft-abstain.jsonl", "7c3504e581ca4b5d1e63b7cdb5a05aeeefcd40649410fabc13ce51acf04af50b"),
    "2b-ft2-abstain.jsonl":   ("data/ft2-ab/qwen35-decider-2b-ft2-abstain.jsonl", "22f388c43da3290d91d574ad21ca964277329ac7108a95c0555349886a7e379f"),
}


def main() -> int:
    base = BASE_DEFAULT
    for k, arg in enumerate(sys.argv[1:]):
        if arg == "--base" and k + 1 < len(sys.argv) - 1:
            base = sys.argv[k + 2]
    os.makedirs("corpus", exist_ok=True)
    for name, (path, sha) in FILES.items():
        dest = f"corpus/{name}"
        if os.path.exists(dest) and hashlib.sha256(open(dest, "rb").read()).hexdigest() == sha:
            continue
        tmp = dest + ".part"
        urllib.request.urlretrieve(f"{base}/{path}", tmp)
        got = hashlib.sha256(open(tmp, "rb").read()).hexdigest()
        if got != sha:
            os.unlink(tmp)
            sys.exit(f"hash mismatch for {name}: {got}")
        os.replace(tmp, dest)
        print(f"fetched {name}")
    print("corpus complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
