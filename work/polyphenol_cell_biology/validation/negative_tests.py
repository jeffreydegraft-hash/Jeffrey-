#!/usr/bin/env python3
"""Negative tests for the verifier (PRIVATE authoring tool).

Takes the reference output, applies one deliberate defect at a time, and records
which verifier check catches it. Every case declares the check it is EXPECTED to
trip, so a silent regression in the verifier shows up as a test failure rather
than as a quiet pass.

    python3 negative_tests.py --workdir /tmp/neg
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ROOT / "validation" / "results_reference.csv"
EXPECTED = ROOT / "validation" / "expected_results.csv"
DATA = ROOT / "data"
VERIFIER = ROOT / "verifier" / "verify_results.py"

COLUMNS = None


def load():
    global COLUMNS
    text = REF.read_text(encoding="utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    COLUMNS = list(csv.reader(text.splitlines()))[0]
    return rows


def write(rows, path, header=None):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header or COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --------------------------------------------------------------------- mutations

def m_drop_compound(rows):
    return [r for r in rows if r["compound_id"] != "PP05"], None


def m_duplicate_compound(rows):
    out = [dict(r) for r in rows]
    out.append(dict(out[0]))
    return out, None


def m_extra_compound(rows):
    out = [dict(r) for r in rows]
    extra = dict(out[0])
    extra["compound_id"] = "PP09"
    out.append(extra)
    return out, None


def m_reordered_header(rows):
    hdr = COLUMNS[:]
    hdr[1], hdr[2] = hdr[2], hdr[1]
    return [dict(r) for r in rows], hdr


def m_renamed_column(rows):
    hdr = COLUMNS[:]
    hdr[hdr.index("protection_index_wt")] = "protection_index"
    out = []
    for r in rows:
        d = dict(r)
        d["protection_index"] = d.pop("protection_index_wt")
        out.append(d)
    return out, hdr


def m_empty_field(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP08":
            r["nrf2_dependence_contrast"] = ""
    return out, None


def m_exposure_wrong_basis(rows):
    """Report the raw LC-MS amount on column instead of pmol per 1e6 cells."""
    out = [dict(r) for r in rows]
    for r in out:
        v = r["wt_primary_exposure_pmol_per_1e6_cells"]
        if v != "NA":
            r["wt_primary_exposure_pmol_per_1e6_cells"] = f"{float(v) * 1.005:.3f}"
    return out, None


def m_exposure_wrong_basis_large(rows):
    out = [dict(r) for r in rows]
    for r in out:
        v = r["wt_primary_exposure_pmol_per_1e6_cells"]
        if v != "NA":
            r["wt_primary_exposure_pmol_per_1e6_cells"] = f"{float(v) * 40.0:.3f}"
    return out, None


def m_percentage_scale(rows):
    """Protection index expressed as a percentage instead of a fraction."""
    out = [dict(r) for r in rows]
    for r in out:
        for c in ("protection_index_wt", "protection_index_wt_ci_low",
                  "protection_index_wt_ci_high"):
            if r[c] != "NA":
                r[c] = f"{float(r[c]) * 100:.2f}"
    return out, None


def m_concentration_off_ladder(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP02":
            r["primary_concentration_um"] = "75.0"
    return out, None


def m_swapped_ci(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP02":
            r["protection_index_wt_ci_low"], r["protection_index_wt_ci_high"] = (
                r["protection_index_wt_ci_high"], r["protection_index_wt_ci_low"])
    return out, None


def m_evidence_nonexistent(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP06":
            r["evidence_sample_ids"] = ";".join(f"SMP99{i:04d}" for i in range(7))
    return out, None


def m_evidence_wrong_cell_model(rows):
    """Cite knockout wells as evidence for the wild-type protection estimate."""
    man = list(csv.DictReader((DATA / "sample_manifest.csv").read_text(
        encoding="utf-8").splitlines()))
    picks = {}
    for m in man:
        if (m["assay_panel"] == "VIABILITY" and m["cell_model_id"] == "CM_KO_A"
                and m["compound_id"] == "PP06" and m["challenge_id"] == "CHAL_ISO"
                and m["schedule_id"] == "PRE_NOWASH"
                and float(m["administered_conc_um"]) == 100.0):
            picks.setdefault(m["biological_experiment_id"], m["sample_id"])
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP06":
            r["evidence_sample_ids"] = ";".join(picks[k] for k in sorted(picks))
    return out, None


def m_evidence_too_few_experiments(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP02":
            ids = r["evidence_sample_ids"].split(";")
            r["evidence_sample_ids"] = ";".join(ids[:3])
    return out, None


def m_altered_numeric_small(rows):
    """Shift one protection index by just over the published tolerance."""
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP03":
            r["protection_index_wt"] = f"{float(r['protection_index_wt']) + 0.009:.4f}"
            r["protection_index_wt_ci_low"] = f"{float(r['protection_index_wt_ci_low']) + 0.009:.4f}"
            r["protection_index_wt_ci_high"] = f"{float(r['protection_index_wt_ci_high']) + 0.009:.4f}"
    return out, None


def m_altered_numeric_within_tolerance(rows):
    """Shift by LESS than the published tolerance: must be ACCEPTED."""
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP03":
            r["protection_index_wt"] = f"{float(r['protection_index_wt']) + 0.003:.4f}"
    return out, None


def m_altered_numeric_large(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP05":
            for c in ("protection_index_wt", "protection_index_wt_ci_low",
                      "protection_index_wt_ci_high"):
                r[c] = f"{float(r[c]) - 0.45:.4f}"
    return out, None


def m_status_flipped_numbers_intact(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP03":
            r["nrf2_dependence_status"] = "nrf2_dependent"
    return out, None


def m_status_not_allowed(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP01":
            r["protection_status"] = "maybe"
    return out, None


def m_na_where_value_required(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP02":
            r["nrf2_dependence_contrast"] = "NA"
            r["nrf2_dependence_contrast_ci_low"] = "NA"
            r["nrf2_dependence_contrast_ci_high"] = "NA"
    return out, None


def m_missing_indeterminate_for_unmatchable(rows):
    """Claim a matched stratum for the compound that has none."""
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP08":
            r["exposure_matched_ko_concentration_um"] = "600.0"
            r["protection_index_ko_exposure_matched"] = "0.0100"
            r["nrf2_dependence_contrast"] = "0.5500"
            r["nrf2_dependence_contrast_ci_low"] = "0.5000"
            r["nrf2_dependence_contrast_ci_high"] = "0.6000"
            r["nrf2_dependence_status"] = "nrf2_dependent"
    return out, None


def m_interference_order_swapped(rows):
    """'ros;mtt' instead of 'mtt;ros': set-equivalent, must be ACCEPTED."""
    out = [dict(r) for r in rows]
    for r in out:
        if r["interference_flags"] == "mtt;ros":
            r["interference_flags"] = "ros;mtt"
    return out, None


def m_interference_dropped(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP04":
            r["interference_flags"] = "none"
    return out, None


def m_interference_overcalled(rows):
    out = [dict(r) for r in rows]
    for r in out:
        if r["compound_id"] == "PP02":
            r["interference_flags"] = "mtt"
    return out, None


CASES = [
    ("missing_compound", m_drop_compound, ["all_required_compounds_present",
                                           "row_count_is_8"], False),
    ("duplicate_compound", m_duplicate_compound, ["compound_ids_unique",
                                                  "row_count_is_8"], False),
    ("extra_unexpected_compound", m_extra_compound, ["no_unexpected_compounds",
                                                     "row_count_is_8"], False),
    ("reordered_header", m_reordered_header, ["header_matches_schema_exactly"], False),
    ("renamed_column", m_renamed_column, ["header_matches_schema_exactly"], False),
    ("empty_field_instead_of_NA", m_empty_field,
     ["fields_parse_as_declared_types"], False),
    ("exposure_within_relative_tolerance", m_exposure_wrong_basis, [], True),
    ("exposure_wrong_basis_40x", m_exposure_wrong_basis_large,
     ["numeric_results_within_tolerance"], False),
    ("protection_index_as_percentage", m_percentage_scale,
     ["units_and_ranges_plausible"], False),
    ("concentration_off_ladder", m_concentration_off_ladder,
     ["units_and_ranges_plausible"], False),
    ("confidence_bounds_swapped", m_swapped_ci,
     ["confidence_intervals_bracket_point_estimates"], False),
    ("evidence_identifiers_nonexistent", m_evidence_nonexistent,
     ["evidence_references_valid_and_relevant"], False),
    ("evidence_from_wrong_cell_model", m_evidence_wrong_cell_model,
     ["evidence_references_valid_and_relevant"], False),
    ("evidence_covers_too_few_experiments", m_evidence_too_few_experiments,
     ["evidence_references_valid_and_relevant"], False),
    ("numeric_shift_just_over_tolerance", m_altered_numeric_small,
     ["numeric_results_within_tolerance"], False),
    ("numeric_shift_within_tolerance", m_altered_numeric_within_tolerance, [], True),
    ("numeric_shift_large", m_altered_numeric_large,
     ["numeric_results_within_tolerance"], False),
    ("status_flipped_numbers_intact", m_status_flipped_numbers_intact,
     ["classifications_consistent_with_submitted_numbers",
      "classifications_match_expected"], False),
    ("status_value_not_allowed", m_status_not_allowed,
     ["status_and_flag_values_allowed"], False),
    ("NA_where_value_required", m_na_where_value_required,
     ["na_token_used_exactly_where_required"], False),
    ("claims_match_for_unmatchable_compound", m_missing_indeterminate_for_unmatchable,
     ["numeric_results_within_tolerance", "classifications_match_expected"], False),
    ("interference_flag_order_swapped", m_interference_order_swapped, [], True),
    ("interference_missed", m_interference_dropped,
     ["classifications_match_expected"], False),
    ("interference_overcalled", m_interference_overcalled,
     ["classifications_match_expected"], False),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args(argv)
    wd = pathlib.Path(args.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    rows = load()

    results, harness_ok = [], True

    # non-UTF8 case handled separately (needs raw bytes)
    bad = wd / "case_non_utf8.csv"
    bad.write_bytes(REF.read_bytes().replace(b"PP01", b"PP\xff1", 1))
    rc, rep = run(bad, wd / "rep_non_utf8.json")
    caught = failed_checks(rep)
    ok = rc != 0
    results.append({"case": "non_utf8_bytes", "expected_pass": False,
                    "verifier_exit": rc, "checks_failed": caught,
                    "behaved_as_expected": ok})
    harness_ok &= ok

    for name, fn, expect_checks, expect_pass in CASES:
        out, hdr = fn(rows)
        p = wd / f"case_{name}.csv"
        write(out, p, hdr)
        rc, rep = run(p, wd / f"rep_{name}.json")
        caught = failed_checks(rep)
        if expect_pass:
            ok = rc == 0
        else:
            ok = rc != 0 and any(c in caught for c in expect_checks)
        results.append({"case": name, "expected_pass": expect_pass,
                        "expected_checks": expect_checks, "verifier_exit": rc,
                        "checks_failed": caught, "behaved_as_expected": ok})
        harness_ok &= ok

    report = {"all_cases_behaved_as_expected": harness_ok, "cases": results}
    out = ROOT / "validation" / "negative_tests_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"{'case':46s} {'exit':>5s} {'as expected':>12s}  checks that fired")
    for r in results:
        print(f"  {r['case']:44s} {r['verifier_exit']:>5d} "
              f"{str(r['behaved_as_expected']):>12s}  "
              f"{', '.join(r['checks_failed']) or '-'}")
    print(f"\nall cases behaved as expected: {harness_ok}")
    print(f"wrote {out}")
    return 0 if harness_ok else 1


def run(results_path: pathlib.Path, json_path: pathlib.Path):
    r = subprocess.run([sys.executable, str(VERIFIER), "--results", str(results_path),
                        "--data", str(DATA), "--expected", str(EXPECTED),
                        "--json", str(json_path), "--quiet"],
                       capture_output=True, text=True)
    rep = json.loads(json_path.read_text()) if json_path.exists() else {}
    return r.returncode, rep


def failed_checks(rep) -> list[str]:
    return [c["check"] for c in rep.get("checks", []) if c["status"] == "FAIL"]


if __name__ == "__main__":
    sys.exit(main())
