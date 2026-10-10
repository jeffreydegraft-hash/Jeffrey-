#!/usr/bin/env python3
"""Standalone clean-room check: extract solver_inputs.zip into an empty directory and
run the reference analysis and the verifier against the extracted copy alone.

This is the check that proves the reference solution can be reconstructed from the
delivered archive without any other file from the package.

    python3 clean_room_test.py --zip ../../outputs/polyphenol_cell_biology/solver_inputs.zip \
        --reference ../reference/reference_analysis.py \
        --verifier ../verifier/verify_results.py \
        --expected expected_results.csv --workdir /tmp/cr
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import zipfile


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--verifier", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--workdir", required=True)
    a = ap.parse_args(argv)

    d = pathlib.Path(a.workdir) / "clean_room"
    if d.exists():
        shutil.rmtree(d)
    (d / "data").mkdir(parents=True)

    with zipfile.ZipFile(a.zip) as zf:
        bad = zf.testzip()
        if bad is not None:
            print(f"FAIL archive is corrupt at {bad}")
            return 1
        zf.extractall(d / "data")
    files = sorted(p.name for p in (d / "data").iterdir())
    print(f"extracted {len(files)} files: {files}")

    res = d / "results.csv"
    r1 = subprocess.run([sys.executable, a.reference, "--data", str(d / "data"),
                         "--out", str(res)], capture_output=True, text=True)
    print(f"reference analysis exit = {r1.returncode}")
    if r1.returncode != 0:
        print(r1.stderr[-3000:])
        return 1
    r2 = subprocess.run([sys.executable, a.verifier, "--results", str(res),
                         "--data", str(d / "data"), "--expected", a.expected],
                        capture_output=True, text=True)
    print(r2.stdout[-3000:])
    print(f"verifier exit = {r2.returncode}")
    return r2.returncode


if __name__ == "__main__":
    sys.exit(main())
