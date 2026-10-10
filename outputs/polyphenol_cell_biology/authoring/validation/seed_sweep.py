#!/usr/bin/env python3
"""Multi-seed robustness sweep (PRIVATE authoring tool).

For each seed: regenerate the whole dataset, run the reference analysis on it, and
record the eight classifications plus the distance of every graded quantity from
its nearest classification boundary. Reports the MINIMUM margin seen across all
seeds, which is the number that decides whether the benchmark's conclusions are
stable.

Also records same-seed byte reproducibility.

    python3 seed_sweep.py --seeds 20261010 7 101 20240229 31337 555 --workdir /tmp/x
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "generator"
REF = ROOT / "reference"

THETA = 0.15
INPUT_FILES = ["compounds.csv", "cell_models.csv", "sample_manifest.csv",
               "viability_readouts.csv", "oxidative_stress_readouts.csv",
               "qpcr_ct_values.csv", "exposure_measurements.csv",
               "assay_controls.csv"]

EXPECTED = {
    "PP01": ("not_protected", "not_assessable", "none"),
    "PP02": ("protected", "nrf2_dependent", "none"),
    "PP03": ("protected", "not_nrf2_dependent", "none"),
    "PP04": ("not_protected", "not_assessable", "mtt;ros"),
    "PP05": ("protected", "not_nrf2_dependent", "none"),
    "PP06": ("protected", "nrf2_dependent", "ros"),
    "PP07": ("not_protected", "not_assessable", "none"),
    "PP08": ("protected", "indeterminate", "none"),
}
EXPECTED_PRIMARY = {"PP01": 100.0, "PP02": 50.0, "PP03": 10.0, "PP04": 300.0,
                    "PP05": 100.0, "PP06": 100.0, "PP07": 10.0, "PP08": 50.0}
EXPECTED_MATCHED = {"PP01": 100.0, "PP02": 50.0, "PP03": 50.0, "PP04": 300.0,
                    "PP05": 100.0, "PP06": 100.0, "PP07": 10.0, "PP08": None}


def gen(seed: int, out: pathlib.Path) -> None:
    subprocess.run([sys.executable, "generate_dataset.py", "--seed", str(seed),
                    "--out", str(out)], cwd=GEN, check=True,
                   stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "make_data_dictionary.py", "--data", str(out)],
                   cwd=GEN, check=True, stdout=subprocess.DEVNULL)
    for f in ("study_specification.json", "output_schema.json"):
        shutil.copy(ROOT / "data" / f, out / f)


def run_ref(data: pathlib.Path, out: pathlib.Path) -> list[dict]:
    subprocess.run([sys.executable, "reference_analysis.py", "--data", str(data),
                    "--out", str(out)], cwd=REF, check=True,
                   stdout=subprocess.DEVNULL)
    with open(out, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(s):
    return None if s.strip() in ("", "NA") else float(s)


def margins(row: dict) -> dict:
    """Distance from each decision boundary; positive means the correct side."""
    out = {}
    lo = num(row["protection_index_wt_ci_low"])
    hi = num(row["protection_index_wt_ci_high"])
    if row["protection_status"] == "protected":
        out["protection"] = lo - THETA
    elif row["protection_status"] == "not_protected":
        out["protection"] = THETA - hi
    else:
        out["protection"] = -abs(min(lo - THETA, THETA - hi))
    dlo, dhi = num(row["nrf2_dependence_contrast_ci_low"]), num(row["nrf2_dependence_contrast_ci_high"])
    st = row["nrf2_dependence_status"]
    if st == "nrf2_dependent" and dlo is not None:
        out["dependence"] = dlo - THETA
    elif st == "not_nrf2_dependent" and dhi is not None:
        out["dependence"] = THETA - dhi
    else:
        out["dependence"] = float("inf")   # structural, not interval-based
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--keep-first", action="store_true")
    args = ap.parse_args(argv)
    wd = pathlib.Path(args.workdir)
    wd.mkdir(parents=True, exist_ok=True)

    report = {"seeds": {}, "same_seed_reproducible": None,
              "all_classifications_stable": True, "min_margins": {}}
    baseline_hashes = None
    worst = {}

    for seed in args.seeds:
        d = wd / f"seed_{seed}"
        if d.exists():
            shutil.rmtree(d)
        gen(seed, d)
        hashes = {f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in INPUT_FILES}
        if baseline_hashes is None and seed == args.seeds[0]:
            baseline_hashes = hashes
        rows = run_ref(d, wd / f"results_seed_{seed}.csv")
        entry = {"compounds": {}}
        for r in rows:
            cid = r["compound_id"]
            got = (r["protection_status"], r["nrf2_dependence_status"],
                   r["interference_flags"])
            ok = got == EXPECTED[cid]
            pconc = num(r["primary_concentration_um"])
            mconc = num(r["exposure_matched_ko_concentration_um"])
            conc_ok = (pconc == EXPECTED_PRIMARY[cid]) and (mconc == EXPECTED_MATCHED[cid])
            m = margins(r)
            entry["compounds"][cid] = {
                "statuses": got, "expected": EXPECTED[cid], "statuses_match": ok,
                "primary_conc": pconc, "matched_conc": mconc,
                "concentrations_match": conc_ok,
                "pi_wt": num(r["protection_index_wt"]),
                "contrast": num(r["nrf2_dependence_contrast"]),
                "margin_protection": round(m["protection"], 4),
                "margin_dependence": (None if m["dependence"] == float("inf")
                                      else round(m["dependence"], 4)),
            }
            if not ok or not conc_ok:
                report["all_classifications_stable"] = False
            for k in ("protection", "dependence"):
                if m[k] != float("inf"):
                    key = f"{cid}:{k}"
                    worst[key] = min(worst.get(key, 9e9), m[k])
        report["seeds"][str(seed)] = entry
        if not args.keep_first or seed != args.seeds[0]:
            shutil.rmtree(d)

    # same-seed byte reproducibility
    s0 = args.seeds[0]
    d2 = wd / f"repro_{s0}"
    if d2.exists():
        shutil.rmtree(d2)
    gen(s0, d2)
    h2 = {f: hashlib.sha256((d2 / f).read_bytes()).hexdigest() for f in INPUT_FILES}
    report["same_seed_reproducible"] = (h2 == baseline_hashes)
    report["same_seed_mismatches"] = [f for f in INPUT_FILES
                                      if h2[f] != baseline_hashes[f]]
    shutil.rmtree(d2)

    report["min_margins"] = {k: round(v, 4) for k, v in sorted(worst.items())}
    report["smallest_margin_overall"] = min(worst.values()) if worst else None

    out = ROOT / "validation" / "seed_sweep_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"same-seed byte reproducible : {report['same_seed_reproducible']}")
    print(f"all classifications stable  : {report['all_classifications_stable']}")
    print(f"smallest margin overall     : {report['smallest_margin_overall']}")
    print("\nper-compound worst-case margin across seeds "
          "(positive = correct side of the boundary):")
    for k, v in report["min_margins"].items():
        flag = "  <-- TIGHT" if v < 0.03 else ("  <-- FAIL" if v < 0 else "")
        print(f"  {k:30s} {v:+.4f}{flag}")
    if not report["all_classifications_stable"]:
        print("\nUNSTABLE classifications:")
        for seed, e in report["seeds"].items():
            for cid, c in e["compounds"].items():
                if not c["statuses_match"]:
                    print(f"  seed {seed} {cid}: got {c['statuses']} "
                          f"expected {c['expected']}")
                elif not c["concentrations_match"]:
                    print(f"  seed {seed} {cid}: conc drift primary="
                          f"{c['primary_conc']} matched={c['matched_conc']}")
    print(f"\nwrote {out}")
    return 0 if report["all_classifications_stable"] and report["same_seed_reproducible"] else 1


if __name__ == "__main__":
    sys.exit(main())
