#!/usr/bin/env python3
"""Runs every shortcut analysis against the final dataset, submits each result to the
verifier, and records honestly what the verifier does and does not catch.

For each shortcut it records:
  * the submitted result table,
  * which of its scientific conclusions are wrong (compared against the expected
    results, which the shortcuts never see),
  * which verifier checks detect those errors,
  * and any case where the shortcut still produces a valid result.

A verifier cannot reject an incorrect internal method that happens to produce fully
valid outputs. Where that happens, this script reports it as such instead of
pretending otherwise.

    python3 shortcut_runner.py --workdir /tmp/sc
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VERIFIER = ROOT / "verifier" / "verify_results.py"
EXPECTED = ROOT / "validation" / "expected_results.csv"
SHORTCUT_DIR = ROOT / "shortcuts"

STATUS_COLS = ["protection_status", "nrf2_dependence_status", "interference_flags"]
GRADED_NUMERIC = ["primary_concentration_um", "wt_primary_exposure_pmol_per_1e6_cells",
                  "exposure_matched_ko_concentration_um", "protection_index_wt",
                  "protection_index_wt_ci_low", "protection_index_wt_ci_high",
                  "protection_index_ko_primary_conc",
                  "protection_index_ko_exposure_matched", "protection_index_rescue",
                  "nrf2_dependence_contrast", "nrf2_dependence_contrast_ci_low",
                  "nrf2_dependence_contrast_ci_high"]


def load(p: pathlib.Path) -> dict:
    return {r["compound_id"]: r for r in
            csv.DictReader(p.read_text(encoding="utf-8").splitlines())}


def compare_science(got: dict, want: dict) -> dict:
    """Which scientific conclusions differ, independent of formatting."""
    wrong_status, wrong_numeric = [], []
    for cid in sorted(want):
        if cid not in got:
            wrong_status.append(f"{cid}: row absent")
            continue
        for c in STATUS_COLS:
            g, w = got[cid].get(c, "").strip(), want[cid][c].strip()
            if c == "interference_flags":
                gs = set(filter(None, g.split(";"))) - {"none"}
                ws = set(filter(None, w.split(";"))) - {"none"}
                if gs != ws:
                    wrong_status.append(f"{cid}.{c}: said '{g}', correct '{w}'")
            elif g != w:
                wrong_status.append(f"{cid}.{c}: said '{g}', correct '{w}'")
        for c in GRADED_NUMERIC:
            g, w = got[cid].get(c, "").strip(), want[cid][c].strip()
            if g == w:
                continue
            if "NA" in (g, w):
                wrong_numeric.append(f"{cid}.{c}: said '{g}', correct '{w}'")
                continue
            try:
                gf, wf = float(g), float(w)
            except ValueError:
                wrong_numeric.append(f"{cid}.{c}: unparseable '{g}'")
                continue
            tolerance = {"primary_concentration_um": 0.0,
                         "exposure_matched_ko_concentration_um": 0.0}.get(c, 0.005)
            if c == "wt_primary_exposure_pmol_per_1e6_cells":
                if abs(gf - wf) > 0.01 * abs(wf):
                    wrong_numeric.append(f"{cid}.{c}: said {gf:.4g}, correct {wf:.4g}")
            elif abs(gf - wf) > tolerance + 1e-12:
                wrong_numeric.append(f"{cid}.{c}: said {gf:.4f}, correct {wf:.4f}")
    return {"wrong_conclusions": wrong_status, "wrong_numbers": wrong_numeric}


def run_verifier(results: pathlib.Path, jsonp: pathlib.Path):
    r = subprocess.run([sys.executable, str(VERIFIER), "--results", str(results),
                        "--data", str(DATA), "--expected", str(EXPECTED),
                        "--json", str(jsonp), "--quiet"],
                       capture_output=True, text=True)
    rep = json.loads(jsonp.read_text()) if jsonp.exists() else {}
    failed = [c["check"] for c in rep.get("checks", []) if c["status"] == "FAIL"]
    return r.returncode, failed, rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args(argv)
    wd = pathlib.Path(args.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    want = load(EXPECTED)

    scripts = sorted(SHORTCUT_DIR.glob("shortcut_*.py"))
    if not scripts:
        print("no shortcut scripts found", file=sys.stderr)
        return 1

    records = []
    for s in scripts:
        key = s.stem
        out = wd / f"{key}.csv"
        run = subprocess.run([sys.executable, str(s), "--data", str(DATA),
                              "--out", str(out)], capture_output=True, text=True)
        rec = {"shortcut": key, "script": s.name,
               "ran_successfully": run.returncode == 0,
               "stderr_tail": run.stderr[-800:] if run.returncode != 0 else ""}
        if run.returncode != 0 or not out.is_file():
            rec.update({"verifier_exit": None, "verifier_checks_failed": [],
                        "wrong_conclusions": ["shortcut failed to run"],
                        "wrong_numbers": [], "verdict": "shortcut_did_not_produce_output"})
            records.append(rec)
            continue

        got = load(out)
        sci = compare_science(got, want)
        rc, failed, _rep = run_verifier(out, wd / f"{key}.verify.json")
        rec.update({
            "verifier_exit": rc,
            "verifier_rejected": rc != 0,
            "verifier_checks_failed": failed,
            "n_wrong_conclusions": len(sci["wrong_conclusions"]),
            "wrong_conclusions": sci["wrong_conclusions"],
            "n_wrong_numbers": len(sci["wrong_numbers"]),
            "wrong_numbers": sci["wrong_numbers"][:40],
            "statuses_submitted": {cid: {c: got[cid].get(c, "") for c in STATUS_COLS}
                                   for cid in sorted(got)},
        })
        if sci["wrong_conclusions"] and rc != 0:
            rec["verdict"] = "wrong_science_and_rejected"
        elif sci["wrong_conclusions"] and rc == 0:
            rec["verdict"] = "WRONG_SCIENCE_BUT_ACCEPTED"
        elif not sci["wrong_conclusions"] and rc == 0:
            rec["verdict"] = "correct_conclusions_and_accepted"
        else:
            rec["verdict"] = "correct_conclusions_but_rejected"
        records.append(rec)

    report = {
        "n_shortcuts": len(records),
        "any_wrong_science_accepted": any(
            r["verdict"] == "WRONG_SCIENCE_BUT_ACCEPTED" for r in records),
        "shortcuts": records,
    }
    outp = ROOT / "validation" / "shortcut_report.json"
    outp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"{'shortcut':44s} {'verifier':>9s} {'wrong concl':>12s} "
          f"{'wrong nums':>11s}  verdict")
    for r in records:
        print(f"  {r['shortcut']:42s} "
              f"{('REJECT' if r.get('verifier_rejected') else 'accept'):>9s} "
              f"{r.get('n_wrong_conclusions', '-'):>12} "
              f"{r.get('n_wrong_numbers', '-'):>11}  {r['verdict']}")
    print()
    for r in records:
        print(f"-- {r['shortcut']}")
        print(f"   checks that fired: {', '.join(r['verifier_checks_failed']) or 'none'}")
        for w in r.get("wrong_conclusions", [])[:10]:
            print(f"   wrong: {w}")
        if r.get("n_wrong_conclusions", 0) > 10:
            print(f"   ... and {r['n_wrong_conclusions'] - 10} more")
    print(f"\nwrote {outp}")
    if report["any_wrong_science_accepted"]:
        print("\nNOTE: at least one shortcut produced wrong science that the verifier "
              "could not reject. This is reported, not hidden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
