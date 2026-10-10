#!/usr/bin/env python3
"""Builds the delivered package under outputs/polyphenol_cell_biology/.

  * solver_inputs.zip : ONLY the data files, the data dictionary, the study
                        specification and the output schema. Nothing else.
  * authoring/        : generation code, private simulation parameters, design
                        assumptions, reference and independent analyses, the
                        verifier, the shortcut analyses, expected results,
                        dependency versions and all validation evidence.
  * README.md, validation_report.md, SHA256SUMS.txt are written separately.

Then verifies the archive, extracts it into a clean directory, and re-runs the
reference analysis and the verifier against the extracted copy alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

WORK = pathlib.Path(__file__).resolve().parent
REPO = WORK.parents[1]
OUT = REPO / "outputs" / "polyphenol_cell_biology"

SOLVER_INPUTS = [
    "compounds.csv", "cell_models.csv", "sample_manifest.csv",
    "viability_readouts.csv", "oxidative_stress_readouts.csv",
    "qpcr_ct_values.csv", "exposure_measurements.csv", "assay_controls.csv",
    "data_dictionary.csv", "study_specification.json", "output_schema.json",
]

# Anything matching these must NEVER appear inside solver_inputs.zip.
FORBIDDEN_IN_ZIP = ["simulation_parameters", "simcore", "expected", "reference_analysis",
                    "verify_results", "calibrate", "generate_dataset", "shortcut",
                    "NOTES", "PROVENANCE", "design_and_causal", "report", "seed_sweep",
                    "_generator_seed"]


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_zip() -> pathlib.Path:
    z = OUT / "solver_inputs.zip"
    if z.exists():
        z.unlink()
    with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as zf:
        for name in SOLVER_INPUTS:
            src = WORK / "data" / name
            if not src.is_file():
                raise SystemExit(f"missing solver input: {src}")
            # fixed timestamp so the archive is byte-reproducible
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, src.read_bytes())
    return z


def check_zip_contents(z: pathlib.Path) -> list[str]:
    problems = []
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
        bad = zf.testzip()
        if bad is not None:
            problems.append(f"corrupt member: {bad}")
        if sorted(names) != sorted(SOLVER_INPUTS):
            problems.append(f"unexpected member list: {sorted(names)}")
        for n in names:
            low = n.lower()
            for f in FORBIDDEN_IN_ZIP:
                if f.lower() in low:
                    problems.append(f"forbidden file in archive: {n}")
    return problems


def copy_authoring() -> None:
    a = OUT / "authoring"
    if a.exists():
        shutil.rmtree(a)
    layout = {
        "design": [("design/design_and_causal_assumptions.md", None),
                   ("design/PROVENANCE.md", None)],
        "generator": [("generator/simcore.py", None),
                      ("generator/generate_dataset.py", None),
                      ("generator/make_data_dictionary.py", None),
                      ("generator/calibrate.py", None)],
        "reference": [("reference/reference_analysis.py", None)],
        "independent": [("independent/independent_analysis.py", None),
                        ("independent/NOTES.md", None)],
        "verifier": [("verifier/verify_results.py", None)],
        ".": [("package.py", None)],
        "validation": [("validation/seed_sweep.py", None),
                       ("validation/negative_tests.py", None),
                       ("validation/invariance_and_integrity.py", None),
                       ("validation/shortcut_runner.py", None),
                       ("validation/clean_room_test.py", None),
                       ("validation/identifiability.py", None)],
    }
    for sub, items in layout.items():
        (a / sub).mkdir(parents=True, exist_ok=True)
        for rel, _ in items:
            src = WORK / rel
            if src.is_file():
                shutil.copy(src, a / sub / src.name)
            else:
                print(f"  note: optional authoring file absent: {rel}")

    # private simulation parameters
    sys.path.insert(0, str(WORK / "generator"))
    import simcore  # noqa: E402
    (a / "generator" / "simulation_parameters.json").write_text(
        json.dumps(simcore.latent_parameter_dump(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    # shortcut analyses
    (a / "shortcuts").mkdir(parents=True, exist_ok=True)
    for p in sorted((WORK / "shortcuts").glob("shortcut_*.py")):
        shutil.copy(p, a / "shortcuts" / p.name)

    # validation evidence and every produced results table
    ev = a / "validation"
    for p in sorted((WORK / "validation").glob("*.json")):
        shutil.copy(p, ev / p.name)
    for p in sorted((WORK / "validation").glob("results_*.csv")):
        shutil.copy(p, ev / p.name)
    for p in sorted((WORK / "validation").glob("*.md")):
        shutil.copy(p, ev / p.name)

    # expected results at the top of authoring/, where a reviewer will look first
    shutil.copy(WORK / "validation" / "expected_results.csv",
                a / "expected_results.csv")

    # dependency versions
    import numpy
    import pandas
    (a / "DEPENDENCIES.txt").write_text(
        "Runtime environment used to build and validate this package\n"
        "==========================================================\n\n"
        f"python                {sys.version.split()[0]}  ({sys.implementation.name})\n"
        f"numpy                 {numpy.__version__}        (BSD-3-Clause)\n"
        f"pandas                {pandas.__version__}        (BSD-3-Clause)\n"
        "scipy                 NOT INSTALLED - deliberately not required\n\n"
        "Dependency policy\n"
        "-----------------\n"
        "The GRADED PATH has no third-party dependency at all:\n"
        "  authoring/reference/reference_analysis.py  - Python standard library only\n"
        "  authoring/verifier/verify_results.py       - Python standard library only\n"
        "Both therefore run in a clean interpreter with nothing installed. The Student-t\n"
        "quantiles they need are published in study_specification.json precisely so that\n"
        "no statistics library is required and no two implementations can disagree on\n"
        "them.\n\n"
        "numpy and pandas are used only by the generator, the independent cross-check and\n"
        "the validation suite. They are used, not redistributed.\n",
        encoding="utf-8")


def clean_room(z: pathlib.Path, workdir: pathlib.Path) -> dict:
    """Extract the archive into an empty directory and run the reference analysis and
    the verifier against the extracted copy alone."""
    d = workdir / "clean_room"
    if d.exists():
        shutil.rmtree(d)
    (d / "data").mkdir(parents=True)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(d / "data")
    extracted = sorted(p.name for p in (d / "data").iterdir())
    res = d / "results.csv"
    ref = OUT / "authoring" / "reference" / "reference_analysis.py"
    ver = OUT / "authoring" / "verifier" / "verify_results.py"
    exp = OUT / "authoring" / "expected_results.csv"

    r1 = subprocess.run([sys.executable, str(ref), "--data", str(d / "data"),
                         "--out", str(res)], capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, str(ver), "--results", str(res),
                         "--data", str(d / "data"), "--expected", str(exp),
                         "--json", str(d / "verify.json"), "--quiet"],
                        capture_output=True, text=True)
    identical = (res.read_bytes() == (WORK / "validation" / "results_reference.csv"
                                      ).read_bytes()) if res.exists() else False
    return {
        "extracted_files": extracted,
        "extracted_file_count": len(extracted),
        "reference_analysis_exit": r1.returncode,
        "reference_analysis_stderr": r1.stderr[-2000:],
        "verifier_exit": r2.returncode,
        "results_byte_identical_to_working_copy": identical,
        "clean_room_dir": str(d),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args(argv)
    wd = pathlib.Path(args.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    print("building solver_inputs.zip ...")
    z = build_zip()
    problems = check_zip_contents(z)
    print(f"  {z.relative_to(REPO)}  {z.stat().st_size:,} bytes")
    inner = sum((WORK / 'data' / n).stat().st_size for n in SOLVER_INPUTS)
    print(f"  uncompressed input total: {inner:,} bytes "
          f"({inner / 1024 / 1024:.2f} MiB)")
    largest = max(SOLVER_INPUTS, key=lambda n: (WORK / 'data' / n).stat().st_size)
    print(f"  largest single input: {largest} "
          f"{(WORK / 'data' / largest).stat().st_size:,} bytes")
    if problems:
        print("  ARCHIVE PROBLEMS:")
        for p in problems:
            print(f"    - {p}")
        return 1
    print("  archive integrity: OK, contents exactly the 11 solver-visible files")

    print("copying authoring materials ...")
    copy_authoring()

    print("clean-room extraction test ...")
    cr = clean_room(z, wd)
    for k, v in cr.items():
        if k != "extracted_files":
            print(f"  {k}: {v}")
    ok = (cr["reference_analysis_exit"] == 0 and cr["verifier_exit"] == 0
          and cr["results_byte_identical_to_working_copy"]
          and cr["extracted_file_count"] == len(SOLVER_INPUTS))
    (OUT / "authoring" / "validation" / "clean_room_report.json").write_text(
        json.dumps({"ok": ok, **cr}, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("  CLEAN-ROOM TEST FAILED")
        return 1
    print("  clean-room test: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
