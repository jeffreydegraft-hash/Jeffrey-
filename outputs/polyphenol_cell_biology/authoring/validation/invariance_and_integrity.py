#!/usr/bin/env python3
"""Invariance, join-integrity and leakage checks (PRIVATE authoring tool).

1. ROW-ORDER INVARIANCE  - shuffle every input table's rows; the reference analysis
   must produce byte-identical results.
2. COMPOUND-ID PERMUTATION INVARIANCE - relabel PP01..PP08 by a permutation
   throughout every file; the scientific results must follow the relabelling
   exactly, with no change to any number or status.
3. JOIN INTEGRITY - every declared key resolves, every declared uniqueness holds,
   no orphan rows.
4. UNIT AND RANGE COHERENCE - physical plausibility of every numeric column, and
   agreement between the manifest and cell_models on the challenge doses.
5. BATCH BALANCE - no cell model nested inside a batch or a plate.
6. MISSINGNESS - censoring confined to what the specification declares.
7. LEAKAGE - no mechanism or verdict vocabulary anywhere in the solver-visible
   files; identifiers and row positions uncorrelated with the outcome.

    python3 invariance_and_integrity.py --workdir /tmp/inv
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REF = ROOT / "reference" / "reference_analysis.py"

TABLES = ["compounds.csv", "cell_models.csv", "sample_manifest.csv",
          "viability_readouts.csv", "oxidative_stress_readouts.csv",
          "qpcr_ct_values.csv", "exposure_measurements.csv", "assay_controls.csv"]
STATIC = ["study_specification.json", "output_schema.json", "data_dictionary.csv"]

# Vocabulary that would betray a mechanism or a verdict if it appeared in a
# solver-visible data file.
LEAK_WORDS = [
    "archetype", "mechanism", "ground_truth", "groundtruth", "answer", "label",
    "protective", "protects", "scavenger", "scavenging", "interferer",
    "interfering", "hit", "true_", "expected_", "latent", "nrf2_dependent",
    "not_nrf2", "toxic_", "no_protection", "pathway_induction", "decoy",
    "positive_control", "negative_control", "class_", "activator", "inducer",
    "efficacy", "potency", "protection_index", "is_active", "active",
]
# Words whose presence is legitimate and expected in the contract documents.
ALLOWED_IN_SPEC_FILES = True

RESULT_COLS_NUMERIC = ["protection_index_wt", "protection_index_wt_ci_low",
                       "protection_index_wt_ci_high",
                       "protection_index_ko_primary_conc",
                       "protection_index_ko_exposure_matched",
                       "protection_index_rescue", "nrf2_dependence_contrast",
                       "nrf2_dependence_contrast_ci_low",
                       "nrf2_dependence_contrast_ci_high",
                       "primary_concentration_um",
                       "exposure_matched_ko_concentration_um",
                       "wt_primary_exposure_pmol_per_1e6_cells"]


def run_ref(data: pathlib.Path, out: pathlib.Path) -> pd.DataFrame:
    subprocess.run([sys.executable, str(REF), "--data", str(data), "--out", str(out)],
                   check=True, capture_output=True)
    return pd.read_csv(out, dtype=str)


def add(rep, name, ok, detail=""):
    rep["checks"].append({"check": name, "status": "pass" if ok else "FAIL",
                          "detail": detail})
    if not ok:
        rep["failed"] = True
    return ok


# --------------------------------------------------------------------- 1 & 2

def check_row_order_invariance(rep, wd):
    d = wd / "shuffled"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in STATIC:
        shutil.copy(DATA / f, d / f)
    for i, f in enumerate(TABLES):
        df = pd.read_csv(DATA / f, dtype=str, keep_default_na=False)
        df = df.sample(frac=1.0, random_state=1000 + i).reset_index(drop=True)
        df.to_csv(d / f, index=False, lineterminator="\n")
    base = run_ref(DATA, wd / "r_base.csv")
    shuf = run_ref(d, wd / "r_shuf.csv")
    same = (wd / "r_base.csv").read_bytes() == (wd / "r_shuf.csv").read_bytes()
    detail = ""
    if not same:
        diffs = []
        for c in base.columns:
            if not base[c].equals(shuf[c]):
                diffs.append(c)
        detail = f"columns that changed: {diffs}"
    add(rep, "row_order_invariance", same, detail)
    shutil.rmtree(d)


def check_id_permutation_invariance(rep, wd):
    """PP01->PP03->PP06->PP01 etc. Results must be the same rows under relabelling."""
    perm = {"PP01": "PP05", "PP02": "PP07", "PP03": "PP01", "PP04": "PP08",
            "PP05": "PP02", "PP06": "PP04", "PP07": "PP03", "PP08": "PP06"}
    d = wd / "permuted"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in STATIC:
        shutil.copy(DATA / f, d / f)
    for f in TABLES:
        df = pd.read_csv(DATA / f, dtype=str, keep_default_na=False)
        for col in df.columns:
            if df[col].isin(list(perm) + ["VEH", "NONE", ""]).all() and \
                    df[col].isin(list(perm)).any():
                df[col] = df[col].map(lambda v: perm.get(v, v))
        # MRM transitions etc. are compound-specific; permute whole compound rows
        if f == "compounds.csv":
            df = df.sort_values("compound_id", kind="mergesort").reset_index(drop=True)
        df.to_csv(d / f, index=False, lineterminator="\n")
    base = run_ref(DATA, wd / "r_base2.csv").set_index("compound_id")
    permd = run_ref(d, wd / "r_perm.csv").set_index("compound_id")

    bad = []
    for old, new in perm.items():
        if new not in permd.index or old not in base.index:
            bad.append(f"{old}->{new} missing")
            continue
        a, b = base.loc[old], permd.loc[new]
        for c in RESULT_COLS_NUMERIC:
            x, y = a[c], b[c]
            if x == "NA" or y == "NA":
                if x != y:
                    bad.append(f"{old}->{new}.{c}: {x} vs {y}")
                continue
            if abs(float(x) - float(y)) > 1e-9:
                bad.append(f"{old}->{new}.{c}: {x} vs {y}")
        for c in ("protection_status", "nrf2_dependence_status", "interference_flags"):
            if a[c] != b[c]:
                bad.append(f"{old}->{new}.{c}: {a[c]} vs {b[c]}")
    add(rep, "compound_id_permutation_invariance", not bad, "; ".join(bad[:15]))
    shutil.rmtree(d)


# ----------------------------------------------------------------------- 3

def check_joins(rep):
    man = pd.read_csv(DATA / "sample_manifest.csv", dtype=str, keep_default_na=False)
    add(rep, "sample_id_unique", man["sample_id"].is_unique,
        f"{len(man)} rows, {man['sample_id'].nunique()} unique")
    ids = set(man["sample_id"])
    panel = dict(zip(man["sample_id"], man["assay_panel"]))

    specs = [("viability_readouts.csv", "VIABILITY", ["sample_id"]),
             ("oxidative_stress_readouts.csv", "OXIDATIVE_STRESS", ["sample_id"]),
             ("qpcr_ct_values.csv", "QPCR",
              ["sample_id", "target_gene", "reaction_replicate"]),
             ("exposure_measurements.csv", "EXPOSURE",
              ["sample_id", "matrix", "injection_replicate"])]
    for f, pan, keys in specs:
        df = pd.read_csv(DATA / f, dtype=str, keep_default_na=False)
        orphans = sorted(set(df["sample_id"]) - ids)
        add(rep, f"{f}:all_sample_ids_resolve", not orphans,
            f"{len(orphans)} orphans e.g. {orphans[:3]}")
        wrong = sorted({s for s in set(df["sample_id"]) if panel.get(s) != pan})
        add(rep, f"{f}:sample_ids_belong_to_its_panel", not wrong,
            f"{len(wrong)} mismatched e.g. {wrong[:3]}")
        dup = df.duplicated(subset=keys).sum()
        add(rep, f"{f}:declared_key_unique", dup == 0,
            f"{dup} duplicate rows on {keys}")
        expected = {s for s, p in panel.items() if p == pan}
        unmeasured = sorted(expected - set(df["sample_id"]))
        add(rep, f"{f}:every_manifest_sample_measured", not unmeasured,
            f"{len(unmeasured)} manifest samples with no row e.g. {unmeasured[:3]}")

    ctl = pd.read_csv(DATA / "assay_controls.csv", dtype=str, keep_default_na=False)
    add(rep, "control_id_unique", ctl["control_id"].is_unique, "")
    add(rep, "controls_do_not_collide_with_sample_ids",
        not (set(ctl["control_id"]) & ids), "")

    cm = pd.read_csv(DATA / "cell_models.csv", dtype=str, keep_default_na=False)
    add(rep, "manifest_cell_models_all_declared",
        set(man["cell_model_id"]) <= set(cm["cell_model_id"]),
        f"{sorted(set(man['cell_model_id']) - set(cm['cell_model_id']))}")
    cpd = pd.read_csv(DATA / "compounds.csv", dtype=str, keep_default_na=False)
    add(rep, "manifest_compounds_all_declared",
        set(man["compound_id"]) <= set(cpd["compound_id"]),
        f"{sorted(set(man['compound_id']) - set(cpd['compound_id']))}")


# ----------------------------------------------------------------------- 4

def check_units_ranges(rep):
    man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False)
    cm = pd.read_csv(DATA / "cell_models.csv")
    ladder = {0.0, 1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0}
    concs = set(man["administered_conc_um"].astype(float))
    add(rep, "administered_concentrations_on_ladder", concs <= ladder,
        f"off-ladder: {sorted(concs - ladder)}")

    iso = dict(zip(cm["cell_model_id"], cm["isoeffective_challenge_tbhp_um"]))
    sub = man[man["challenge_id"] == "CHAL_ISO"]
    mism = sub[sub.apply(lambda r: float(r["challenge_conc_um"]) !=
                         float(iso[r["cell_model_id"]]), axis=1)]
    add(rep, "iso_challenge_dose_matches_cell_models", len(mism) == 0,
        f"{len(mism)} mismatched rows")
    sub = man[man["challenge_id"] == "CHAL_COMMON"]
    add(rep, "common_challenge_dose_identical_across_cell_models",
        set(sub["challenge_conc_um"].astype(float)) == {300.0},
        f"{sorted(set(sub['challenge_conc_um'].astype(float)))}")
    add(rep, "unchallenged_rows_have_zero_oxidant",
        (man[man["challenge_id"] == "CHAL_NONE"]["challenge_conc_um"]
         .astype(float) == 0).all(), "")

    via = pd.read_csv(DATA / "viability_readouts.csv")
    add(rep, "nuclei_counts_nonnegative_integers",
        bool((via["live_nuclei_count"] >= 0).all() and (via["dead_nuclei_count"] >= 0).all()
             and via["live_nuclei_count"].dtype.kind in "iu"), "")
    add(rep, "ldh_activity_positive", bool((via["ldh_activity_mu_per_l"] > 0).all()), "")
    add(rep, "mtt_absorbances_in_plausible_window",
        bool((via["mtt_absorbance_570nm"].between(0.0, 4.0)).all()
             and (via["mtt_absorbance_630nm"].between(0.0, 1.0)).all()),
        f"570nm range {via['mtt_absorbance_570nm'].min():.3f}-"
        f"{via['mtt_absorbance_570nm'].max():.3f}")
    add(rep, "mtt_570_exceeds_630_reference",
        bool((via["mtt_absorbance_570nm"] > via["mtt_absorbance_630nm"]).all()), "")

    ros = pd.read_csv(DATA / "oxidative_stress_readouts.csv")
    add(rep, "probe_fluorescence_positive", bool((ros["fluorescence_au"] > 0).all()), "")

    q = pd.read_csv(DATA / "qpcr_ct_values.csv")
    add(rep, "ct_values_in_plausible_window",
        bool(q["ct_value"].between(8.0, 40.0).all()),
        f"range {q['ct_value'].min():.2f}-{q['ct_value'].max():.2f}")

    # reference genes must be stable across treatments within a cell model
    man_i = man.set_index("sample_id")
    qm = q.merge(man[["sample_id", "cell_model_id", "compound_id",
                      "administered_conc_um"]], on="sample_id")
    worst = 0.0
    for g in ("ACTB", "RPLP0"):
        sub = qm[qm["target_gene"] == g]
        per = sub.groupby(["cell_model_id", "compound_id",
                           "administered_conc_um"])["ct_value"].mean()
        for cmid, grp in per.groupby(level=0):
            worst = max(worst, float(grp.max() - grp.min()))
    add(rep, "reference_genes_stable_across_treatments", worst < 1.0,
        f"largest within-cell-model spread of a reference gene mean Ct = {worst:.3f}")

    e = pd.read_csv(DATA / "exposure_measurements.csv", keep_default_na=False)
    meas = e[e["qualifier"] == "measured"]
    lys = meas[meas["matrix"] == "cell_lysate"]
    vals = lys["measured_value"].astype(float) / lys["cell_equivalents_1e6"].astype(float)
    add(rep, "derived_exposures_positive_and_plausible",
        bool((vals > 0).all() and vals.max() < 2e4),
        f"range {vals.min():.3f}-{vals.max():.1f} pmol per 1e6 cells")
    add(rep, "medium_rows_have_no_cell_equivalents",
        bool((e[e["matrix"] == "medium"]["cell_equivalents_1e6"] == "").all()), "")
    add(rep, "censored_rows_have_empty_value",
        bool((e[e["qualifier"] == "below_lloq"]["measured_value"] == "").all()), "")


# ----------------------------------------------------------------------- 5

def check_batch_balance(rep):
    man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False)
    bios = sorted(man["biological_experiment_id"].unique())
    add(rep, "seven_biological_experiments", len(bios) == 7, f"{bios}")

    via = man[man["assay_panel"] == "VIABILITY"]
    per = via.groupby("biological_experiment_id")["cell_model_id"].nunique()
    add(rep, "every_experiment_contains_every_cell_model",
        bool((per == man["cell_model_id"].nunique()).all() or
             (per == via["cell_model_id"].nunique()).all()),
        f"{per.to_dict()}")
    trt = via.groupby("biological_experiment_id").apply(
        lambda d: d.groupby(["compound_id", "administered_conc_um"]).ngroups,
        include_groups=False)
    add(rep, "every_experiment_contains_every_treatment_level",
        bool(trt.nunique() == 1), f"{trt.to_dict()}")

    pure = via.groupby("plate_id")["cell_model_id"].nunique()
    add(rep, "no_plate_contains_only_one_cell_model", bool((pure > 1).all()),
        f"{int((pure <= 1).sum())} single-cell-model plates of {len(pure)}")
    pure_t = via.groupby("plate_id")["compound_id"].nunique()
    add(rep, "no_plate_contains_only_one_compound", bool((pure_t > 1).all()),
        f"{int((pure_t <= 1).sum())} single-compound plates")

    bat = via.groupby("reagent_batch_id")["cell_model_id"].nunique()
    add(rep, "cell_model_not_nested_in_reagent_batch",
        bool((bat == via["cell_model_id"].nunique()).all()), f"{bat.to_dict()}")

    tech = via.groupby(["biological_experiment_id", "cell_model_id", "compound_id",
                        "administered_conc_um", "schedule_id",
                        "challenge_id"]).size()
    add(rep, "viability_technical_replication_is_four",
        set(tech.unique()) == {4}, f"observed replicate counts {sorted(set(tech.unique()))}")


# ----------------------------------------------------------------------- 6

def check_missingness(rep):
    e = pd.read_csv(DATA / "exposure_measurements.csv", keep_default_na=False)
    man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False,
                      low_memory=False)
    e = e.merge(man[["sample_id", "administered_conc_um"]], on="sample_id")
    cens = e[e["qualifier"] == "below_lloq"]

    # The documented rule: cell lysate is censored only at 1, 3 or 10 uM; medium is
    # censored only in the two post-washout conditions.
    lys = cens[cens["matrix"] == "cell_lysate"]
    bad = lys[lys["administered_conc_um"].astype(float) > 10.0]
    add(rep, "lysate_censoring_only_at_the_lowest_three_concentrations", len(bad) == 0,
        f"{len(bad)} censored lysate rows above 10 uM; highest censored concentration "
        f"is {lys['administered_conc_um'].astype(float).max()} uM")
    med = cens[cens["matrix"] == "medium"]
    bad = med[~med["sampling_condition"].isin(["POST_WASH_0P5H",
                                               "POST_CHALLENGE_24H_WASH"])]
    add(rep, "medium_censoring_only_in_the_post_washout_conditions", len(bad) == 0,
        f"{len(bad)} censored medium rows outside the washout conditions")
    mismatch = int((((e["qualifier"] == "below_lloq")
                     != (e["measured_value"].astype(str) == "")).sum()))
    add(rep, "censoring_flag_matches_empty_value_one_to_one", mismatch == 0,
        f"{mismatch} rows where the flag and the empty value disagree")

    # assay_controls: only 'undetermined' rows may have an empty value
    ctl = pd.read_csv(DATA / "assay_controls.csv", keep_default_na=False)
    empty = ctl[ctl["value"].astype(str) == ""]
    add(rep, "only_undetermined_controls_have_an_empty_value",
        set(empty["qualifier"]) <= {"undetermined"},
        f"qualifiers on empty-value control rows: {sorted(set(empty['qualifier']))}")
    sub = ctl[ctl["qualifier"] == "below_lloq"]
    add(rep, "sub_lloq_calibration_standards_still_carry_their_response",
        len(sub) > 0 and (sub["value"].astype(str) != "").all(),
        f"{len(sub)} sub-LLOQ standard rows, "
        f"{(sub['value'].astype(str) != '').sum()} with a recorded value")


def check_format_coherence(rep):
    """A declared culture format must never disagree with the well positions or the
    number of wells a plate carries."""
    man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False,
                      low_memory=False)
    grid = {"96_well": (8, 12), "24_well": (4, 6), "12_well": (3, 4)}
    problems = []
    for fmt, g in man.groupby("culture_format"):
        if fmt not in grid:
            problems.append(f"undeclared format {fmt}")
            continue
        rows, cols = grid[fmt]
        bad_rows = sorted(set(g["well_position"].str[0]) - set("ABCDEFGH"[:rows]))
        max_col = int(g["well_position"].str[1:].astype(int).max())
        cap = int(g.groupby("plate_id").size().max())
        if bad_rows:
            problems.append(f"{fmt}: rows outside the grid {bad_rows}")
        if max_col > cols:
            problems.append(f"{fmt}: column {max_col} exceeds {cols}")
        if cap > rows * cols:
            problems.append(f"{fmt}: a plate carries {cap} wells, capacity {rows * cols}")
    add(rep, "culture_format_agrees_with_well_grid_and_plate_capacity", not problems,
        "; ".join(problems))

    # a condition's technical replicates must sit together on one plate
    grp = man[man["assay_panel"] == "VIABILITY"].groupby(
        ["biological_experiment_id", "cell_model_id", "compound_id",
         "administered_conc_um", "schedule_id", "challenge_id"])["plate_id"].nunique()
    add(rep, "technical_replicates_of_a_condition_share_one_plate",
        bool((grp == 1).all()), f"{int((grp > 1).sum())} conditions split across plates")

    # the reagent lot is nested inside the experiment; record it explicitly so the
    # documentation and the evidence agree
    nest = man.groupby("reagent_batch_id")["biological_experiment_id"].unique()
    overlap = set(nest.iloc[0]) & set(nest.iloc[1]) if len(nest) == 2 else set()
    add(rep, "reagent_lot_nesting_is_as_documented", not overlap,
        "reagent lot is nested within the biological experiment, as the dictionary now "
        f"states: {{{', '.join(f'{k}: {sorted(v)}' for k, v in nest.items())}}}")
    cross = man.groupby("reagent_batch_id")["cell_model_id"].nunique()
    add(rep, "cell_model_crossed_with_reagent_lot",
        bool((cross == man["cell_model_id"].nunique()).all()), f"{cross.to_dict()}")

    for f in TABLES:
        df = pd.read_csv(DATA / f, keep_default_na=False, dtype=str)
        n_empty = int((df == "").sum().sum())
        cols = [c for c in df.columns if (df[c] == "").any()]
        allowed = {"sample_manifest.csv": {"sampling_condition",
                                           "sampling_time_h_from_pretreatment_start",
                                           "probe_loaded",
                                           "readout_time_h_post_challenge"},
                   "exposure_measurements.csv": {"measured_value",
                                                 "cell_equivalents_1e6"},
                   "assay_controls.csv": {"value", "notes"},
                   "compounds.csv": {"molecular_weight_g_per_mol", "logp_calculated",
                                     "max_dmso_solubility_mm", "dmso_stock_mm",
                                     "purity_pct", "lcms_mrm_transition_m_z",
                                     "lloq_intracellular_pmol", "lloq_medium_um",
                                     "internal_standard"}}.get(f, set())
        add(rep, f"{f}:empty_fields_only_in_declared_columns",
            set(cols) <= allowed, f"unexpected empty columns: {sorted(set(cols)-allowed)} "
                                  f"(total empty cells {n_empty})")


# ----------------------------------------------------------------------- 7

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def check_leakage(rep, results_path):
    # (a) Data files: scan column names and every distinct STRING VALUE as whole
    #     tokens. Substring matching produced false positives ("du-ratio-n"), so
    #     tokens are matched exactly.
    verdict_tokens = {
        "archetype", "mechanism", "groundtruth", "answer", "protective", "protects",
        "protection", "scavenger", "scavenging", "interferer", "interfering",
        "interference", "hit", "latent", "decoy", "activator", "inducer", "efficacy",
        "potency", "active", "inactive", "toxic", "nontoxic", "truth", "expected",
        "verdict", "score", "dependent", "independent", "positive", "negative",
    }
    hits = []
    for f in TABLES:
        df = pd.read_csv(DATA / f, dtype=str, keep_default_na=False)
        bad_cols = sorted(_tokens(" ".join(df.columns)) & verdict_tokens)
        if bad_cols:
            hits.append(f"{f}: column-name tokens {bad_cols}")
        for c in df.columns:
            vals = df[c].astype(str)
            if vals.nunique() > 400:          # free-numeric column, nothing to read
                continue
            bad = sorted(_tokens(" ".join(sorted(vals.unique()))) & verdict_tokens)
            if bad:
                hits.append(f"{f}:{c}: value tokens {bad}")
    add(rep, "no_verdict_vocabulary_in_data_file_names_or_values", not hits,
        " | ".join(hits[:8]))

    # (b) Data dictionary: prose legitimately discusses the design, so the check is
    #     that no description ties a SPECIFIC compound identifier to a conclusion.
    dd = pd.read_csv(DATA / "data_dictionary.csv", dtype=str, keep_default_na=False)
    dd_hits = []
    for _, row in dd.iterrows():
        blob = f"{row['column']} {row['allowed_values_or_range']} {row['description']}"
        named = re.findall(r"PP0[1-8]\b", blob)
        specific = [n for n in named if blob.count(n) and not
                    re.search(r"PP01-PP08|PP01\.\.PP08", blob)]
        if specific and (_tokens(blob) & verdict_tokens):
            dd_hits.append(f"{row['file']}:{row['column']} mentions {sorted(set(specific))} "
                           f"alongside {sorted(_tokens(blob) & verdict_tokens)}")
    add(rep, "data_dictionary_never_ties_a_named_compound_to_a_conclusion",
        not dd_hits, " | ".join(dd_hits[:6]))

    # (c) No per-compound rows anywhere outside compounds.csv carrying extra attributes
    cpd_cols = set(pd.read_csv(DATA / "compounds.csv", nrows=1).columns)
    add(rep, "compounds_table_carries_only_physicochemical_descriptors",
        not (_tokens(" ".join(cpd_cols)) & verdict_tokens),
        f"{sorted(_tokens(' '.join(cpd_cols)) & verdict_tokens)}")

    res = pd.read_csv(results_path, dtype=str)
    res["prot"] = res["protection_status"]
    order = list(res.sort_values("compound_id")["prot"])
    # Does identifier order group the outcomes? (runs test: fewer runs = grouped)
    runs = 1 + sum(1 for a, b in zip(order, order[1:]) if a != b)
    add(rep, "compound_id_order_does_not_group_outcomes", runs >= 4,
        f"protection_status in id order = {order} ({runs} runs; a grouped layout "
        f"would give 2)")

    # Row position vs outcome: is any table sorted so that a compound's rows cluster?
    clustered = []
    for f in ["sample_manifest.csv", "viability_readouts.csv"]:
        df = pd.read_csv(DATA / f, keep_default_na=False, dtype=str)
        if "compound_id" not in df.columns:
            man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False,
                              dtype=str)[["sample_id", "compound_id"]]
            df = df.merge(man, on="sample_id")
        for cid, sub in df.groupby("compound_id"):
            if cid == "VEH":
                continue
            pos = sub.index.to_numpy()
            # expected mean position for a uniformly scattered compound
            frac = pos.mean() / len(df)
            if not (0.40 <= frac <= 0.60):
                clustered.append(f"{f}:{cid} mean row position fraction {frac:.3f}")
    add(rep, "row_positions_uncorrelated_with_compound", not clustered,
        "; ".join(clustered[:8]))

    # Identifier numbering vs outcome
    man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False, dtype=str)
    man["n"] = man["sample_id"].str.extract(r"(\d+)").astype(int)
    g = man[man["compound_id"] != "VEH"].groupby("compound_id")["n"].mean()
    spread = (g.max() - g.min()) / len(man)
    add(rep, "sample_id_numbering_uncorrelated_with_compound", spread < 0.05,
        f"spread of mean identifier number across compounds = {spread:.4f} of the "
        f"identifier range")

    # Does a single physicochemical descriptor rank the compounds correctly?
    cpd = pd.read_csv(DATA / "compounds.csv")
    cpd = cpd[cpd["compound_id"] != "VEH"]
    res2 = res.set_index("compound_id")
    protected = {c for c in res2.index if res2.loc[c, "protection_status"] == "protected"}
    trivial = []
    for col in ("molecular_weight_g_per_mol", "logp_calculated",
                "max_dmso_solubility_mm", "purity_pct", "lloq_intracellular_pmol"):
        s = cpd.set_index("compound_id")[col].astype(float).sort_values()
        ranked = list(s.index)
        top = set(ranked[-len(protected):])
        bot = set(ranked[:len(protected)])
        if top == protected or bot == protected:
            trivial.append(f"{col} perfectly separates the protected compounds")
    add(rep, "no_physicochemical_descriptor_separates_the_outcome", not trivial,
        "; ".join(trivial))

    # No precomputed score columns. Tokens are matched whole; `ct_flag` and
    # `qualifier` are documented measurement-status fields that carry no conclusion,
    # and are the only status-like columns allowed.
    derived_tokens = {"score", "index", "fold", "ratio", "verdict", "result",
                      "classification", "call", "conclusion"}
    allowed_status_columns = {"ct_flag", "qualifier", "medium_qualifier",
                              "intracellular_qualifier"}
    suspicious = []
    for f in TABLES:
        for c in pd.read_csv(DATA / f, nrows=1).columns:
            toks = _tokens(c)
            if (toks & derived_tokens) and c not in allowed_status_columns:
                suspicious.append(f"{f}:{c}")
            if ("flag" in toks or "status" in toks) and c not in allowed_status_columns:
                suspicious.append(f"{f}:{c}")
    add(rep, "no_precomputed_score_or_verdict_columns", not suspicious,
        f"{suspicious}")


def check_shared_variation_across_assays(rep):
    """Measurements from the same biological experiment must share latent biological
    variation rather than being resampled independently per table. Test it: summarise
    each table per experiment and check the summaries are correlated. Independent
    generation would give correlations scattered around zero."""
    man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False,
                      low_memory=False)
    via = pd.read_csv(DATA / "viability_readouts.csv").merge(man, on="sample_id")
    exp = pd.read_csv(DATA / "exposure_measurements.csv", keep_default_na=False)
    exp = exp[exp["matrix"] == "cell_lysate"].merge(
        man[["sample_id", "biological_experiment_id"]], on="sample_id")
    ctl = pd.read_csv(DATA / "assay_controls.csv", keep_default_na=False)
    ros = pd.read_csv(DATA / "oxidative_stress_readouts.csv").merge(man, on="sample_id")

    # culture vigour, read independently from three different tables
    unchal = via[(via.compound_id == "VEH") & (via.challenge_id == "CHAL_NONE")
                 & (via.schedule_id == "PRE_NOWASH")
                 & (via.panel_id == "B_DOSE_RESPONSE")]
    a = unchal.groupby("biological_experiment_id")["live_nuclei_count"].mean()
    exp["cell_equivalents_1e6"] = pd.to_numeric(exp["cell_equivalents_1e6"],
                                                errors="coerce")
    b = exp.groupby("biological_experiment_id")["cell_equivalents_1e6"].mean()
    mx = ctl[ctl.control_type == "ldh_maximum_lysis"].copy()
    mx["value"] = pd.to_numeric(mx["value"], errors="coerce")
    c = mx.groupby("biological_experiment_id")["value"].mean()
    idx = sorted(set(a.index) & set(b.index) & set(c.index))
    r_ab = float(np.corrcoef(a[idx], b[idx])[0, 1])
    r_ac = float(np.corrcoef(a[idx], c[idx])[0, 1])
    add(rep, "culture_vigour_shared_between_viability_and_exposure_tables",
        r_ab > 0.5, f"Pearson r = {r_ab:.3f} across {len(idx)} biological experiments "
                    f"(independent generation would give r near 0)")
    add(rep, "culture_vigour_shared_between_viability_and_control_tables",
        r_ac > 0.5, f"Pearson r = {r_ac:.3f} across {len(idx)} biological experiments")

    # realised injury severity, shared between the count endpoint and the probe
    vc = via[(via.compound_id == "VEH") & (via.challenge_id == "CHAL_ISO")
             & (via.schedule_id == "PRE_NOWASH") & (via.panel_id == "B_DOSE_RESPONSE")]
    surv = (vc.groupby("biological_experiment_id")["live_nuclei_count"].mean()
            / a)                      # survival fraction per experiment
    # The raw probe signal also carries a per-experiment instrument gain, which is an
    # independent factor, so normalise it out with the challenged/unchallenged ratio
    # inside each experiment. Pool ALL probe-loaded wells rather than vehicle wells
    # only: every experiment contains the identical treatment set, so compound effects
    # contribute a constant factor and add no between-experiment variance, while
    # averaging over ~200 wells per side makes well-level noise negligible. Restricting
    # to the 3+3 vehicle wells leaves well noise comparable to the signal and the
    # correlation estimate is then too noisy to be a stable criterion.
    pr = ros[ros.probe_loaded_x == "yes"]
    num = pr[pr.challenge_id == "CHAL_ISO"].groupby(
        "biological_experiment_id")["fluorescence_au"].mean()
    den = pr[pr.challenge_id == "CHAL_NONE"].groupby(
        "biological_experiment_id")["fluorescence_au"].mean()
    ratio = num / den
    # matching survival summary, pooled over the same treatment set
    allv = via[(via.panel_id == "B_DOSE_RESPONSE") & (via.schedule_id == "PRE_NOWASH")]
    sn = allv[allv.challenge_id == "CHAL_ISO"].groupby(
        "biological_experiment_id")["live_nuclei_count"].mean()
    sd_ = allv[allv.challenge_id == "CHAL_NONE"].groupby(
        "biological_experiment_id")["live_nuclei_count"].mean()
    surv_all = sn / sd_
    j = sorted(set(surv_all.index) & set(ratio.index))
    n_probe = int(len(pr[pr.challenge_id == "CHAL_ISO"]) / max(len(j), 1))
    r_inj = float(np.corrcoef(surv_all[j], ratio[j])[0, 1])
    add(rep, "injury_severity_shared_between_count_and_probe_endpoints",
        r_inj < -0.8,
        f"Pearson r = {r_inj:.3f} across {len(j)} biological experiments between the "
        f"pooled survival fraction (viability table) and the pooled gain-normalised "
        f"probe response (probe table), each averaging about {n_probe} wells per "
        f"experiment per side: experiments that sustained more injury show both less "
        f"survival and more oxidant signal, which only a shared realised-injury factor "
        f"produces (independent per-table generation would give r near 0). The probe "
        f"ratio is self-normalising for cell number, because the dye-loaded signal and "
        f"its background both scale with it, so the only remaining shared driver is the "
        f"realised injury severity.")


def check_reference_isolation(rep):
    """The reference analysis must not be able to consult generator truth. Two checks:
    a static scan of its source, and the fact (proved by the clean-room test) that it
    runs correctly with only the 11 solver-visible files present."""
    # Scan EXECUTABLE CODE only. Comments and docstrings legitimately discuss what the
    # solver does not do, so a raw substring scan gives false positives.
    forbidden = ["simcore", "simulation_parameters", "latent", "archetype",
                 "generate_dataset", "_generator_seed"]

    def code_only(path: pathlib.Path) -> str:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)) and ast.get_docstring(node):
                node.body = node.body[1:]
        return ast.unparse(tree)

    ref_code = code_only(ROOT / "reference" / "reference_analysis.py")
    hits = [w for w in forbidden + ["expected_results"] if w in ref_code]
    add(rep, "reference_analysis_never_references_generator_truth", not hits,
        f"found in executable code: {hits}")

    # The only file names it may mention are the solver-visible inputs plus its own
    # output path.
    opened = re.findall(r"""['"]([A-Za-z0-9_./-]+\.(?:csv|json))['"]""", ref_code)
    allowed = set(TABLES) | set(STATIC) | {"results.csv"}
    outside = sorted({o for o in opened if pathlib.Path(o).name not in allowed})
    add(rep, "reference_analysis_only_names_solver_visible_files", not outside,
        f"names files outside the solver-visible set plus its own output: {outside}")

    ver_code = code_only(ROOT / "verifier" / "verify_results.py")
    vhits = [w for w in forbidden if w in ver_code]
    add(rep, "verifier_never_references_generator_truth", not vhits,
        f"found in executable code: {vhits}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args(argv)
    wd = pathlib.Path(args.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    rep = {"checks": [], "failed": False}

    check_row_order_invariance(rep, wd)
    check_id_permutation_invariance(rep, wd)
    check_joins(rep)
    check_units_ranges(rep)
    check_batch_balance(rep)
    check_missingness(rep)
    check_format_coherence(rep)
    check_leakage(rep, ROOT / "validation" / "results_reference.csv")
    check_shared_variation_across_assays(rep)
    check_reference_isolation(rep)

    out = ROOT / "validation" / "invariance_and_integrity_report.json"
    n_fail = sum(1 for c in rep["checks"] if c["status"] == "FAIL")
    rep["summary"] = {"checks_run": len(rep["checks"]), "checks_failed": n_fail,
                      "overall": "FAIL" if rep["failed"] else "PASS"}
    out.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")

    for c in rep["checks"]:
        line = f"  [{c['status']:4s}] {c['check']}"
        if c["detail"] and (c["status"] == "FAIL" or len(c["detail"]) < 160):
            line += f"\n         {c['detail'][:1200]}"
        print(line)
    print(f"\n  {rep['summary']['overall']}  ({n_fail} of {len(rep['checks'])} failed)")
    print(f"  wrote {out}")
    return 1 if rep["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
