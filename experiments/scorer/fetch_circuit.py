#!/usr/bin/env python3
"""Fetch a circuit file by dataset reference and verify its hash.

Circuits are referenced by dataset + hash in circuits/ and never stored in
this repo. Usage:
    python3 fetch_circuit.py <url> <sha256> -o <dest>
"""
import argparse
import hashlib
import sys
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url")
    ap.add_argument("sha256")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    tmp = args.out + ".part"
    urllib.request.urlretrieve(args.url, tmp)
    digest = hashlib.sha256(open(tmp, "rb").read()).hexdigest()
    if digest != args.sha256:
        sys.exit(f"hash mismatch: got {digest}, want {args.sha256}")
    import os
    os.replace(tmp, args.out)
    print(f"fetched {args.out} ({digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
