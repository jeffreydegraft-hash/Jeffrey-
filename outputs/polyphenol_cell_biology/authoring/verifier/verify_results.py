#!/usr/bin/env python3
"""
Deterministic verifier for the `polyphenol_cell_biology` benchmark.

Checks a submitted /app/results.csv against:
  * the published output schema (readability, header, coverage, types, value sets),
  * unit plausibility for every numeric field,
  * the expected numeric results, within the tolerances published in
    study_specification.json,
  * the disclosed classification rules applied to the submission's OWN numbers
    (so a submission whose arithmetic is right but whose reasoning is wrong is
    still caught, independently of the expected file),
  * the NA conventions,
  * validity and relevance of the supporting record references.

It inspects ONLY the submitted outputs and the solver-visible inputs. It does not
look at the solver's code, intermediate files, runtime or structure: any
implementation whose outputs satisfy these checks is accepted.

Exit status 0 = pass, 1 = fail.

    python3 verify_results.py --results /app/results.csv --data /app/data \
        --expected expected_results.csv [--json report.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys

COLUMNS = ["compound_id", "primary_concentration_um",
           "wt_primary_exposure_pmol_per_1e6_cells",
           "exposure_matched_ko_concentration_um", "protection_index_wt",
           "protection_index_wt_ci_low", "protection_index_wt_ci_high",
           "protection_index_ko_primary_conc",
           "protection_index_ko_exposure_matched", "protection_index_rescue",
           "nrf2_dependence_contrast", "nrf2_dependence_contrast_ci_low",
           "nrf2_dependence_contrast_ci_high", "protection_status",
           "nrf2_dependence_status", "interference_flags", "evidence_sample_ids"]

REQUIRED_COMPOUNDS = ["PP01", "PP02", "PP03", "PP04", "PP05", "PP06", "PP07", "PP08"]

NULLABLE = {"primary_concentration_um", "wt_primary_exposure_pmol_per_1e6_cells",
            "exposure_matched_ko_concentration_um",
            "protection_index_ko_exposure_matched", "nrf2_dependence_contrast",
            "nrf2_dependence_contrast_ci_low", "nrf2_dependence_contrast_ci_high",
            "evidence_sample_ids"}

NUMERIC = {"primary_concentration_um", "wt_primary_exposure_pmol_per_1e6_cells",
           "exposure_matched_ko_concentration_um", "protection_index_wt",
           "protection_index_wt_ci_low", "protection_index_wt_ci_high",
           "protection_index_ko_primary_conc",
           "protection_index_ko_exposure_matched", "protection_index_rescue",
           "nrf2_dependence_contrast", "nrf2_dependence_contrast_ci_low",
           "nrf2_dependence_contrast_ci_high"}

PROTECTION_INDEX_FIELDS = ["protection_index_wt", "protection_index_wt_ci_low",
                           "protection_index_wt_ci_high",
                           "protection_index_ko_primary_conc",
                           "protection_index_ko_exposure_matched",
                           "protection_index_rescue", "nrf2_dependence_contrast",
                           "nrf2_dependence_contrast_ci_low",
                           "nrf2_dependence_contrast_ci_high"]

PROTECTION_STATUSES = {"protected", "not_protected", "indeterminate", "not_evaluable"}
DEPENDENCE_STATUSES = {"nrf2_dependent", "not_nrf2_dependent", "indeterminate",
                       "not_assessable"}
INTERFERENCE_VALUES = {"none", "mtt", "ros", "mtt;ros"}

# Unit-plausibility envelopes. A submission outside these has almost certainly
# reported a quantity on the wrong basis (for example a raw LC-MS amount in pmol
# instead of pmol per 1e6 cells, or a percentage instead of a fraction).
PLAUSIBLE = {
    "wt_primary_exposure_pmol_per_1e6_cells": (0.1, 2.0e4),
    "protection_index": (-5.0, 5.0),
}

NA = "NA"


class Result:
    def __init__(self):
        self.checks: list[dict] = []
        self.failed = False

    def add(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append({"check": name, "status": "pass" if ok else "FAIL",
                            "detail": detail})
        if not ok:
            self.failed = True
        return ok

    def report(self) -> dict:
        n_fail = sum(1 for c in self.checks if c["status"] == "FAIL")
        return {"overall": "FAIL" if self.failed else "PASS",
                "checks_run": len(self.checks), "checks_failed": n_fail,
                "checks": self.checks}


def num(s):
    """Parse a numeric field. Returns None for the NA token, for an empty field and
    for anything unparseable: a malformed field is reported by the type check, and
    must never crash the verifier."""
    s = (s or "").strip()
    if s == NA or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="/app/results.csv")
    ap.add_argument("--data", default="/app/data")
    ap.add_argument("--expected", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    R = Result()
    try:
        return _run(R, args)
    except Exception as exc:          # noqa: BLE001 - deliberate catch-all
        R.add("verifier_completed_without_internal_error", False,
              f"{type(exc).__name__}: {exc}")
        return finish(R, args)


def _run(R: "Result", args) -> int:

    data = pathlib.Path(args.data)
    spec = json.loads((data / "study_specification.json").read_text(encoding="utf-8"))
    tol = spec["grading_tolerances"]
    TOL_PI = float(tol["protection_index_absolute"])
    TOL_D = float(tol["nrf2_dependence_contrast_absolute"])
    TOL_CI = float(tol["confidence_interval_bound_absolute"])
    TOL_EXP = float(tol["exposure_relative"])
    ladder = {float(x) for x in
              spec["experimental_design"]["concentration_ladder_um"]}
    theta_p = float(spec["classification"]["protection_status"]["threshold_theta_P"])
    theta_d = float(spec["classification"]["nrf2_dependence_status"]["threshold_theta_D"])
    bios = set(spec["experimental_design"]["replication"]["biological_experiments"])

    # ---------------------------------------------------------------- readability
    path = pathlib.Path(args.results)
    if not R.add("file_exists", path.is_file(), str(path)):
        return finish(R, args)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        R.add("file_is_utf8", False, str(e))
        return finish(R, args)
    R.add("file_is_utf8", True)
    try:
        rows = list(csv.DictReader(text.splitlines()))
        header = csv.reader(text.splitlines()).__next__()
    except Exception as e:
        R.add("file_parses_as_csv", False, repr(e))
        return finish(R, args)
    R.add("file_parses_as_csv", True)

    if not R.add("header_matches_schema_exactly", header == COLUMNS,
                 f"expected {COLUMNS} got {header}"):
        return finish(R, args)

    # ------------------------------------------------------------------ coverage
    ids = [r["compound_id"].strip() for r in rows]
    R.add("row_count_is_8", len(rows) == 8, f"got {len(rows)}")
    R.add("compound_ids_unique", len(set(ids)) == len(ids),
          f"duplicates: {sorted({i for i in ids if ids.count(i) > 1})}")
    missing = [c for c in REQUIRED_COMPOUNDS if c not in ids]
    R.add("all_required_compounds_present", not missing, f"missing: {missing}")
    extra = [i for i in ids if i not in REQUIRED_COMPOUNDS]
    R.add("no_unexpected_compounds", not extra, f"unexpected: {extra}")
    if R.failed:
        return finish(R, args)

    by_id = {r["compound_id"].strip(): r for r in rows}

    # ------------------------------------------------- types, value sets, units
    type_errors, enum_errors, unit_errors, bracket_errors = [], [], [], []
    for cid in REQUIRED_COMPOUNDS:
        r = by_id[cid]
        for col in COLUMNS:
            raw = (r[col] or "")
            if raw.strip() == "" :
                type_errors.append(f"{cid}.{col}: empty field (use the NA token)")
                continue
            if raw.strip() == NA and col not in NULLABLE:
                type_errors.append(f"{cid}.{col}: NA not allowed for this column")
        for col in NUMERIC:
            raw = (r[col] or "").strip()
            if raw == NA:
                continue
            try:
                v = float(raw)
            except ValueError:
                type_errors.append(f"{cid}.{col}: '{raw}' is not a number")
                continue
            if math.isnan(v) or math.isinf(v):
                type_errors.append(f"{cid}.{col}: non-finite value '{raw}'")
                continue
            if col in ("primary_concentration_um",
                       "exposure_matched_ko_concentration_um"):
                if v not in ladder:
                    unit_errors.append(
                        f"{cid}.{col}: {v} is not on the published concentration "
                        f"ladder {sorted(ladder)}")
            elif col == "wt_primary_exposure_pmol_per_1e6_cells":
                lo, hi = PLAUSIBLE[col]
                if not (lo <= v <= hi):
                    unit_errors.append(
                        f"{cid}.{col}: {v} outside the plausible range "
                        f"[{lo}, {hi}] pmol per 1e6 cells - wrong unit or basis?")
            elif col in PROTECTION_INDEX_FIELDS:
                lo, hi = PLAUSIBLE["protection_index"]
                if not (lo <= v <= hi):
                    unit_errors.append(
                        f"{cid}.{col}: {v} outside the plausible range [{lo}, {hi}] "
                        f"for a fraction-of-deficit-recovered scale - percentage "
                        f"instead of fraction?")
        if r["protection_status"].strip() not in PROTECTION_STATUSES:
            enum_errors.append(f"{cid}.protection_status: "
                               f"'{r['protection_status']}' not allowed")
        if r["nrf2_dependence_status"].strip() not in DEPENDENCE_STATUSES:
            enum_errors.append(f"{cid}.nrf2_dependence_status: "
                               f"'{r['nrf2_dependence_status']}' not allowed")
        flags_raw = r["interference_flags"].strip()
        flags_set = set(filter(None, flags_raw.split(";")))
        canonical = ("none" if flags_set in ({"none"}, set())
                     else ";".join(f for f in ("mtt", "ros") if f in flags_set))
        if flags_raw not in INTERFERENCE_VALUES and canonical not in INTERFERENCE_VALUES:
            enum_errors.append(f"{cid}.interference_flags: '{flags_raw}' not allowed; "
                               f"allowed values are {sorted(INTERFERENCE_VALUES)}")
        elif not flags_set <= {"none", "mtt", "ros"} or (
                "none" in flags_set and len(flags_set) > 1):
            enum_errors.append(f"{cid}.interference_flags: '{flags_raw}' mixes 'none' "
                               f"with a flag, or contains an unknown flag")
        # intervals must bracket their point estimate
        for pt, lo_c, hi_c in (("protection_index_wt", "protection_index_wt_ci_low",
                                "protection_index_wt_ci_high"),
                               ("nrf2_dependence_contrast",
                                "nrf2_dependence_contrast_ci_low",
                                "nrf2_dependence_contrast_ci_high")):
            p, lo, hi = num(r[pt]), num(r[lo_c]), num(r[hi_c])
            if None in (p, lo, hi):
                continue
            if not (lo <= p <= hi):
                bracket_errors.append(
                    f"{cid}: {lo_c}={lo} .. {hi_c}={hi} does not bracket {pt}={p}")
            if hi < lo:
                bracket_errors.append(f"{cid}: {hi_c} < {lo_c}")

    R.add("fields_parse_as_declared_types", not type_errors, "; ".join(type_errors))
    R.add("status_and_flag_values_allowed", not enum_errors, "; ".join(enum_errors))
    R.add("units_and_ranges_plausible", not unit_errors, "; ".join(unit_errors))
    R.add("confidence_intervals_bracket_point_estimates", not bracket_errors,
          "; ".join(bracket_errors))

    # ------------------------------------------------------- NA convention rules
    na_errors = []
    for cid in REQUIRED_COMPOUNDS:
        r = by_id[cid]
        matched_na = r["exposure_matched_ko_concentration_um"].strip() == NA
        group = ["protection_index_ko_exposure_matched", "nrf2_dependence_contrast",
                 "nrf2_dependence_contrast_ci_low",
                 "nrf2_dependence_contrast_ci_high"]
        if matched_na:
            for g in group:
                if r[g].strip() != NA:
                    na_errors.append(
                        f"{cid}: exposure_matched_ko_concentration_um is NA so {g} "
                        f"must be NA, got '{r[g]}'")
            if r["nrf2_dependence_status"].strip() != "indeterminate":
                na_errors.append(
                    f"{cid}: no exposure-matched stratum, so nrf2_dependence_status "
                    f"must be 'indeterminate', got '{r['nrf2_dependence_status']}'")
        else:
            for g in group:
                if r[g].strip() == NA:
                    na_errors.append(
                        f"{cid}: exposure_matched_ko_concentration_um is given so {g} "
                        f"must not be NA")
    R.add("na_token_used_exactly_where_required", not na_errors, "; ".join(na_errors))

    # ---------------- classification consistent with the submission's own numbers
    logic_errors = []
    for cid in REQUIRED_COMPOUNDS:
        r = by_id[cid]
        lo, hi = num(r["protection_index_wt_ci_low"]), num(r["protection_index_wt_ci_high"])
        ps = r["protection_status"].strip()
        if lo is not None and hi is not None and ps != "not_evaluable":
            if ps == "protected" and not lo > theta_p:
                logic_errors.append(
                    f"{cid}: protection_status='protected' but its own interval lower "
                    f"bound {lo} does not exceed {theta_p}")
            if ps == "not_protected" and not hi < theta_p:
                logic_errors.append(
                    f"{cid}: protection_status='not_protected' but its own interval "
                    f"upper bound {hi} is not below {theta_p}")
            if ps == "indeterminate" and not (lo <= theta_p <= hi):
                logic_errors.append(
                    f"{cid}: protection_status='indeterminate' but its own interval "
                    f"[{lo}, {hi}] does not contain {theta_p}")
        ds = r["nrf2_dependence_status"].strip()
        dlo, dhi = (num(r["nrf2_dependence_contrast_ci_low"]),
                    num(r["nrf2_dependence_contrast_ci_high"]))
        if ps != "protected" and ds != "not_assessable":
            logic_errors.append(
                f"{cid}: protection_status='{ps}' is not 'protected', so "
                f"nrf2_dependence_status must be 'not_assessable', got '{ds}'")
        if ds == "nrf2_dependent" and dlo is not None and not dlo > theta_d:
            logic_errors.append(
                f"{cid}: nrf2_dependence_status='nrf2_dependent' but its own contrast "
                f"interval lower bound {dlo} does not exceed {theta_d}")
        if ds == "not_nrf2_dependent" and dhi is not None and not dhi < theta_d:
            logic_errors.append(
                f"{cid}: nrf2_dependence_status='not_nrf2_dependent' but its own "
                f"contrast interval upper bound {dhi} is not below {theta_d}")
    R.add("classifications_consistent_with_submitted_numbers", not logic_errors,
          "; ".join(logic_errors))

    # --------------------------------------------- numeric agreement with expected
    exp_rows = {r["compound_id"]: r for r in
                csv.DictReader(pathlib.Path(args.expected).read_text(
                    encoding="utf-8").splitlines())}
    num_errors, status_errors = [], []
    for cid in REQUIRED_COMPOUNDS:
        got, want = by_id[cid], exp_rows[cid]
        for col in NUMERIC:
            g, w = num(got[col]), num(want[col])
            if w is None and g is None:
                continue
            if (w is None) != (g is None):
                num_errors.append(f"{cid}.{col}: expected "
                                  f"{'NA' if w is None else w}, got "
                                  f"{'NA' if g is None else g}")
                continue
            if col in ("primary_concentration_um",
                       "exposure_matched_ko_concentration_um"):
                if g != w:
                    num_errors.append(f"{cid}.{col}: expected {w}, got {g} "
                                      f"(exact match required)")
            elif col == "wt_primary_exposure_pmol_per_1e6_cells":
                if abs(g - w) > TOL_EXP * abs(w):
                    num_errors.append(
                        f"{cid}.{col}: expected {w:.4g}, got {g:.4g} "
                        f"(relative tolerance {TOL_EXP})")
            else:
                t = TOL_CI if col.endswith(("_ci_low", "_ci_high")) else (
                    TOL_D if col.startswith("nrf2_dependence_contrast") else TOL_PI)
                if abs(g - w) > t:
                    num_errors.append(f"{cid}.{col}: expected {w:.4f}, got {g:.4f} "
                                      f"(absolute tolerance {t})")
        for col in ("protection_status", "nrf2_dependence_status"):
            if got[col].strip() != want[col].strip():
                status_errors.append(f"{cid}.{col}: expected "
                                     f"'{want[col]}', got '{got[col]}'")
        gf = set(filter(None, got["interference_flags"].strip().split(";")))
        wf = set(filter(None, want["interference_flags"].strip().split(";")))
        if gf - {"none"} != wf - {"none"} or ("none" in gf) != ("none" in wf):
            status_errors.append(f"{cid}.interference_flags: expected "
                                 f"'{want['interference_flags']}', got "
                                 f"'{got['interference_flags']}'")
    R.add("numeric_results_within_tolerance", not num_errors, "; ".join(num_errors))
    R.add("classifications_match_expected", not status_errors,
          "; ".join(status_errors))

    # ---------------------------------------------- evidence reference validation
    manifest = {}
    with open(data / "sample_manifest.csv", newline="", encoding="utf-8") as fh:
        for m in csv.DictReader(fh):
            manifest[m["sample_id"]] = m
    ev_errors = []
    for cid in REQUIRED_COMPOUNDS:
        r = by_id[cid]
        raw = r["evidence_sample_ids"].strip()
        primary = num(r["primary_concentration_um"])
        if raw == NA:
            if primary is not None:
                ev_errors.append(f"{cid}: evidence_sample_ids is NA but a primary "
                                 f"concentration was reported")
            continue
        sids = [s for s in raw.split(";") if s]
        if not (7 <= len(sids) <= 30):
            ev_errors.append(f"{cid}: {len(sids)} evidence identifiers, "
                             f"required between 7 and 30")
        unknown = [s for s in sids if s not in manifest]
        if unknown:
            ev_errors.append(f"{cid}: evidence identifiers not in the manifest: "
                             f"{unknown[:5]}")
        seen_bios = set()
        for s in sids:
            m = manifest.get(s)
            if m is None:
                continue
            bad = []
            if m["assay_panel"] != "VIABILITY":
                bad.append(f"assay_panel={m['assay_panel']}")
            if m["cell_model_id"] != "CM_WT":
                bad.append(f"cell_model_id={m['cell_model_id']}")
            if m["compound_id"] != cid:
                bad.append(f"compound_id={m['compound_id']}")
            if primary is not None and float(m["administered_conc_um"]) != primary:
                bad.append(f"administered_conc_um={m['administered_conc_um']}")
            if m["challenge_id"] != "CHAL_ISO":
                bad.append(f"challenge_id={m['challenge_id']}")
            if m["schedule_id"] != "PRE_NOWASH":
                bad.append(f"schedule_id={m['schedule_id']}")
            if m["readout_time_h_post_challenge"] not in ("24.0", "24"):
                bad.append(f"readout={m['readout_time_h_post_challenge']}")
            if bad:
                ev_errors.append(f"{cid}: evidence {s} does not match the required "
                                 f"condition ({', '.join(bad)})")
            seen_bios.add(m["biological_experiment_id"])
        if sids and not unknown and seen_bios != bios:
            ev_errors.append(f"{cid}: evidence covers {sorted(seen_bios)}, "
                             f"must cover every biological experiment {sorted(bios)}")
    R.add("evidence_references_valid_and_relevant", not ev_errors,
          "; ".join(ev_errors[:20]))

    return finish(R, args)


def finish(R: Result, args) -> int:
    rep = R.report()
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rep, indent=2) + "\n",
                                           encoding="utf-8")
    if not args.quiet:
        for c in rep["checks"]:
            line = f"  [{c['status']:4s}] {c['check']}"
            if c["status"] == "FAIL" and c["detail"]:
                line += f"\n         {c['detail'][:4000]}"
            print(line)
        print(f"\n  {rep['overall']}  ({rep['checks_failed']} of "
              f"{rep['checks_run']} checks failed)")
    return 1 if R.failed else 0


if __name__ == "__main__":
    sys.exit(main())
