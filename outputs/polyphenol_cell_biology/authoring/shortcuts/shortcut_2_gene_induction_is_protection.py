#!/usr/bin/env python3
"""
SHORTCUT ANALYSIS 2 -- "gene_induction_is_protection"

DELIBERATELY FLAWED ANALYSIS. This script is NOT an attempt at the correct
answer. It implements one specific plausible reasoning shortcut so that a
benchmark verifier can be tested against it:

    Treat pathway-gene induction alone as proof of protection.

What it does wrong (the single mandated deviation):
  * The survival endpoints (live_cell_density_1e3_per_well, LDH) are IGNORED
    entirely. No protection index as defined in study_specification.json
    effect_scale is ever computed.
  * Instead, a "pathway response score" is computed from qPCR: the mean over
    the four pathway-response genes (NQO1, HMOX1, GCLC, TXNRD1) of the
    log2 fold change at 18 h of pretreatment, by the ddCt convention in
    study_specification.json derived_quantities.delta_delta_ct.
  * That score is substituted for the protection index everywhere a
    protection index is required (wild type, knockout at the primary
    administered concentration, knockout at the exposure-matched
    concentration, rescue), so the "NRF2 dependence contrast" becomes a
    paired difference of pathway scores.
  * A compound is called 'protected' when the 95% Student-t lower bound of
    the wild-type pathway score exceeds 1.0 (a two-fold mean induction).

What it keeps faithful to the specification:
  * the concentration-selection rule (highest tolerated concentration in
    wild-type cells, tox_ratio >= 0.85 on live nuclei counts),
  * E_WT and the exposure-matching rule for CM_KO_A,
  * the biological experiment as the unit of inference, n = 7,
  * the published Student-t quantile 2.446911851,
  * the interference indices and flag rules (computed correctly),
  * the evidence_sample_ids rules,
  * the output schema, column order, NA token and allowed status values.

One implementation note that is forced by the data rather than chosen:
the Q_TRANSCRIPT panel was only run at administered concentrations
10, 100 and 300 uM. The primary concentration (and the exposure-matched
knockout concentration) are not always one of those. Because
protection_index_wt is non-nullable in output_schema.json, this script does
what a shortcut-taker would do: it evaluates the pathway score at the
ladder concentration nearest the required one on a log scale among the
concentrations the transcript panel actually covers, and records the
substitution. This is an additional, unavoidable approximation of the
flawed method and is reported in the run log.
"""

from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np
import pandas as pd

LADDER = [1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0]
BIOS = ["BIO01", "BIO02", "BIO03", "BIO04", "BIO05", "BIO06", "BIO07"]
COMPOUNDS = ["PP01", "PP02", "PP03", "PP04", "PP05", "PP06", "PP07", "PP08"]
PATHWAY_GENES = ["NQO1", "HMOX1", "GCLC", "TXNRD1"]
REFERENCE_GENES = ["ACTB", "RPLP0"]
NA = "NA"

T_TABLE = {
    1: 12.706204736,
    2: 4.30265273,
    3: 3.182446305,
    4: 2.776445105,
    5: 2.570581836,
    6: 2.446911851,
    7: 2.364624252,
    8: 2.306004135,
    9: 2.262157163,
}

THETA_PROTECT_SCORE = 1.0   # the shortcut's protection threshold (2-fold induction)
THETA_D = 0.15              # dependence-contrast threshold, as specified
TOX_RATIO_MIN = 0.85
INTERFERENCE_THRESHOLD = 0.10
EXPOSURE_WINDOW_LO = 0.70
EXPOSURE_WINDOW_HI = 1.428571428571
MIN_MEASURED_EXPERIMENTS = 3

OUTPUT_COLUMNS = [
    "compound_id",
    "primary_concentration_um",
    "wt_primary_exposure_pmol_per_1e6_cells",
    "exposure_matched_ko_concentration_um",
    "protection_index_wt",
    "protection_index_wt_ci_low",
    "protection_index_wt_ci_high",
    "protection_index_ko_primary_conc",
    "protection_index_ko_exposure_matched",
    "protection_index_rescue",
    "nrf2_dependence_contrast",
    "nrf2_dependence_contrast_ci_low",
    "nrf2_dependence_contrast_ci_high",
    "protection_status",
    "nrf2_dependence_status",
    "interference_flags",
    "evidence_sample_ids",
]


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def t_interval(values):
    """Student-t 95% interval on a sequence of per-biological-experiment values."""
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    n = v.size
    if n == 0:
        return (float("nan"), float("nan"), float("nan"), 0)
    mean = float(v.mean())
    if n == 1:
        return (mean, float("nan"), float("nan"), 1)
    sd = float(v.std(ddof=1))
    t = T_TABLE[n - 1]
    half = t * sd / math.sqrt(n)
    return (mean, mean - half, mean + half, n)


def fmt(x, nd=6):
    if x is None:
        return NA
    try:
        if not np.isfinite(x):
            return NA
    except TypeError:
        return NA
    return f"{float(x):.{nd}f}"


def fmt_conc(x):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return NA
    return f"{float(x):.1f}"


def log_nearest(target, available):
    """Pick the available concentration nearest to target on a log scale."""
    if not available:
        return None
    if target in available:
        return target
    return min(sorted(available), key=lambda q: (abs(math.log(q) - math.log(target)), q))


# ----------------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------------

def load(data_dir):
    d = {}
    d["manifest"] = pd.read_csv(os.path.join(data_dir, "sample_manifest.csv"))
    d["viability"] = pd.read_csv(os.path.join(data_dir, "viability_readouts.csv"))
    d["probe"] = pd.read_csv(os.path.join(data_dir, "oxidative_stress_readouts.csv"))
    d["qpcr"] = pd.read_csv(os.path.join(data_dir, "qpcr_ct_values.csv"))
    d["exposure"] = pd.read_csv(os.path.join(data_dir, "exposure_measurements.csv"))
    d["controls"] = pd.read_csv(os.path.join(data_dir, "assay_controls.csv"))
    return d


# ----------------------------------------------------------------------------
# concentration selection (kept faithful to the specification)
# ----------------------------------------------------------------------------

def build_viability(d):
    man = d["manifest"]
    v = d["viability"].drop(columns=["readout_time_h_post_challenge"])
    j = man.merge(v, on="sample_id", how="inner")
    j["live_density"] = j["live_nuclei_count"] / j["imaged_area_fraction"] / 1000.0
    j["mtt_signal"] = j["mtt_absorbance_570nm"] - j["mtt_absorbance_630nm"]
    return j


def primary_concentration(via, compound):
    base = via[
        (via.panel_id == "B_DOSE_RESPONSE")
        & (via.readout_time_h_post_challenge == 24.0)
        & (via.cell_model_id == "CM_WT")
        & (via.challenge_id == "CHAL_NONE")
        & (via.schedule_id == "PRE_NOWASH")
    ]
    veh = base[(base.compound_id == "VEH") & (base.administered_conc_um == 0.0)]
    veh_mean = veh.groupby("biological_experiment_id").live_density.mean().mean()
    tolerated = []
    for conc in LADDER:
        s = base[(base.compound_id == compound) & (base.administered_conc_um == conc)]
        if s.empty:
            continue
        per_exp = s.groupby("biological_experiment_id").live_density.mean()
        if float(per_exp.mean()) / float(veh_mean) >= TOX_RATIO_MIN:
            tolerated.append(conc)
    return (max(tolerated) if tolerated else None)


# ----------------------------------------------------------------------------
# exposure (kept faithful to the specification)
# ----------------------------------------------------------------------------

def build_exposure(d):
    man = d["manifest"][
        ["sample_id", "biological_experiment_id", "cell_model_id", "compound_id",
         "administered_conc_um", "panel_id"]
    ]
    e = d["exposure"].drop(columns=["compound_id"])
    j = e.merge(man, on="sample_id", how="inner")
    j = j[(j.matrix == "cell_lysate") & (j.sampling_condition == "END_PRETREAT_NOWASH")]
    j = j.copy()
    j["exposure"] = j["measured_value"] / j["cell_equivalents_1e6"]
    return j


def exposure_per_experiment(exp, compound, cell_model, conc):
    """Per-experiment mean over 'measured' injection replicates. Censored samples dropped."""
    s = exp[
        (exp.compound_id == compound)
        & (exp.cell_model_id == cell_model)
        & (exp.administered_conc_um == conc)
        & (exp.qualifier == "measured")
    ]
    if s.empty:
        return {}
    per_sample = s.groupby(["biological_experiment_id", "sample_id"]).exposure.mean()
    return per_sample.groupby("biological_experiment_id").mean().to_dict()


def exposure_matched_concentration(exp, compound, e_wt):
    """exposure_matching_rule: window 0.70..1.4286 on E_KO/E_WT, minimise |ln ratio|."""
    if e_wt is None or not np.isfinite(e_wt) or e_wt == 0:
        return None, None, {}
    candidates = []
    detail = {}
    for conc in LADDER:
        per_exp = exposure_per_experiment(exp, compound, "CM_KO_A", conc)
        n_meas = len(per_exp)
        if n_meas < MIN_MEASURED_EXPERIMENTS:
            detail[conc] = ("censored", n_meas, None, None)
            continue
        e_ko = float(np.mean(list(per_exp.values())))
        ratio = e_ko / e_wt
        qualifies = EXPOSURE_WINDOW_LO <= ratio <= EXPOSURE_WINDOW_HI
        detail[conc] = ("measured", n_meas, e_ko, ratio)
        if qualifies:
            candidates.append((abs(math.log(ratio)), conc, e_ko))
    if not candidates:
        return None, None, detail
    candidates.sort(key=lambda r: (r[0], r[1]))
    return candidates[0][1], candidates[0][2], detail


# ----------------------------------------------------------------------------
# THE SHORTCUT: pathway response score from qPCR, used in place of PI
# ----------------------------------------------------------------------------

def build_pathway_scores(d):
    """
    Per (cell_model_id, compound_id, administered_conc_um, biological_experiment_id)
    at 18 h of pretreatment: the mean over NQO1, HMOX1, GCLC and TXNRD1 of
    log2_fold_change = -ddCt, with ddCt taken against the matched vehicle
    (same cell model, same biological experiment, same harvest time).
    """
    man = d["manifest"]
    q = man[(man.panel_id == "Q_TRANSCRIPT") & (man.pretreatment_duration_h == 18.0)]
    q = q[["sample_id", "biological_experiment_id", "cell_model_id", "compound_id",
           "administered_conc_um", "pretreatment_duration_h"]]
    ct = d["qpcr"].merge(q, on="sample_id", how="inner")

    # mean over reaction replicates
    per_gene = (
        ct.groupby(["sample_id", "biological_experiment_id", "cell_model_id",
                    "compound_id", "administered_conc_um", "target_gene"])
          .ct_value.mean()
          .reset_index()
    )
    wide = per_gene.pivot_table(
        index=["sample_id", "biological_experiment_id", "cell_model_id",
               "compound_id", "administered_conc_um"],
        columns="target_gene",
        values="ct_value",
    ).reset_index()

    wide["ct_ref"] = wide[REFERENCE_GENES].mean(axis=1)
    for g in PATHWAY_GENES:
        wide[f"dct_{g}"] = wide[g] - wide["ct_ref"]

    # vehicle dCt per (cell model, biological experiment)
    veh = wide[(wide.compound_id == "VEH") & (wide.administered_conc_um == 0.0)]
    veh_idx = veh.set_index(["cell_model_id", "biological_experiment_id"])

    rows = []
    treated = wide[wide.compound_id != "VEH"]
    for _, r in treated.iterrows():
        key = (r.cell_model_id, r.biological_experiment_id)
        if key not in veh_idx.index:
            continue
        vr = veh_idx.loc[key]
        if isinstance(vr, pd.DataFrame):
            vr = vr.iloc[0]
        l2fcs = []
        for g in PATHWAY_GENES:
            ddct = r[f"dct_{g}"] - vr[f"dct_{g}"]
            l2fcs.append(-ddct)
        rows.append({
            "cell_model_id": r.cell_model_id,
            "compound_id": r.compound_id,
            "administered_conc_um": float(r.administered_conc_um),
            "biological_experiment_id": r.biological_experiment_id,
            "pathway_score": float(np.mean(l2fcs)),
        })
    scores = pd.DataFrame(rows)
    return scores


def score_per_experiment(scores, compound, cell_model, conc_requested, log):
    """
    Return (dict bio_exp -> score, concentration actually used).
    The transcript panel does not cover every ladder concentration; the
    shortcut falls back to the log-nearest covered concentration.
    """
    if conc_requested is None:
        return {}, None
    s = scores[(scores.compound_id == compound) & (scores.cell_model_id == cell_model)]
    if s.empty:
        return {}, None
    available = sorted(float(x) for x in s.administered_conc_um.unique())
    used = log_nearest(float(conc_requested), available)
    if used is None:
        return {}, None
    if used != float(conc_requested):
        log.append(
            f"  {compound} {cell_model}: transcript panel has no "
            f"{conc_requested} uM arm; pathway score read at {used} uM "
            f"(log-nearest of {available})"
        )
    sel = s[s.administered_conc_um == used]
    return sel.set_index("biological_experiment_id").pathway_score.to_dict(), used


# ----------------------------------------------------------------------------
# interference (computed correctly, per the specification)
# ----------------------------------------------------------------------------

def cell_free_mtt_signal(controls):
    cf = controls[(controls.control_type == "cell_free_mtt")
                  & (controls.challenge_id == "CHAL_NONE")]
    keys = ["compound_id", "administered_conc_um", "biological_experiment_id",
            "plate_id", "technical_replicate"]
    w = cf.pivot_table(index=keys, columns="measured_quantity", values="value").reset_index()
    w["mtt_signal"] = w["mtt_absorbance_570nm"] - w["mtt_absorbance_630nm"]
    return w


def mtt_interference(cf_mtt, via, compound, conc):
    wt_veh = via[
        (via.panel_id == "B_DOSE_RESPONSE")
        & (via.readout_time_h_post_challenge == 24.0)
        & (via.cell_model_id == "CM_WT")
        & (via.compound_id == "VEH")
        & (via.administered_conc_um == 0.0)
        & (via.challenge_id == "CHAL_NONE")
        & (via.schedule_id == "PRE_NOWASH")
    ].groupby("biological_experiment_id").mtt_signal.mean()

    veh_cf = cf_mtt[(cf_mtt.compound_id == "VEH")].groupby(
        "biological_experiment_id").mtt_signal.mean()
    cmp_cf = cf_mtt[(cf_mtt.compound_id == compound)
                    & (cf_mtt.administered_conc_um == conc)].groupby(
        "biological_experiment_id").mtt_signal.mean()

    out = {}
    for b in BIOS:
        if b in veh_cf.index and b in cmp_cf.index and b in wt_veh.index:
            den = wt_veh[b] - veh_cf[b]
            if den != 0:
                out[b] = float((cmp_cf[b] - veh_cf[b]) / den)
    return out


def probe_autofluorescence(d, compound, conc):
    man = d["manifest"]
    p = d["probe"].drop(columns=["probe_loaded", "readout_time_h_post_challenge"])
    j = man.merge(p, on="sample_id", how="inner")
    j = j[(j.cell_model_id == "CM_WT") & (j.challenge_id == "CHAL_ISO")
          & (j.schedule_id == "PRE_NOWASH")]
    dyefree_cmp = j[(j.compound_id == compound) & (j.administered_conc_um == conc)
                    & (j.probe_loaded == "no")].groupby(
        "biological_experiment_id").fluorescence_au.mean()
    dyefree_veh = j[(j.compound_id == "VEH") & (j.administered_conc_um == 0.0)
                    & (j.probe_loaded == "no")].groupby(
        "biological_experiment_id").fluorescence_au.mean()
    loaded_veh = j[(j.compound_id == "VEH") & (j.administered_conc_um == 0.0)
                   & (j.probe_loaded == "yes")].groupby(
        "biological_experiment_id").fluorescence_au.mean()
    out = {}
    for b in BIOS:
        if b in dyefree_cmp.index and b in dyefree_veh.index and b in loaded_veh.index:
            den = loaded_veh[b] - dyefree_veh[b]
            if den != 0:
                out[b] = float((dyefree_cmp[b] - dyefree_veh[b]) / den)
    return out


def probe_quench(controls, compound, conc):
    q = controls[controls.control_type == "fluorescein_standard_quench"]
    veh = q[q.compound_id == "VEH"].groupby("biological_experiment_id").value.mean()
    cmp_ = q[(q.compound_id == compound) & (q.administered_conc_um == conc)].groupby(
        "biological_experiment_id").value.mean()
    out = {}
    for b in BIOS:
        if b in veh.index and b in cmp_.index and veh[b] != 0:
            out[b] = float((veh[b] - cmp_[b]) / veh[b])
    return out


# ----------------------------------------------------------------------------
# evidence sample ids (per specification)
# ----------------------------------------------------------------------------

def evidence_ids(man, compound, conc):
    s = man[
        (man.assay_panel == "VIABILITY")
        & (man.cell_model_id == "CM_WT")
        & (man.compound_id == compound)
        & (man.administered_conc_um == conc)
        & (man.challenge_id == "CHAL_ISO")
        & (man.schedule_id == "PRE_NOWASH")
        & (man.readout_time_h_post_challenge == 24.0)
    ]
    ids = []
    for b in BIOS:
        sub = s[s.biological_experiment_id == b].sort_values("sample_id")
        if len(sub):
            ids.append(sub.iloc[0].sample_id)
    return ids


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    d = load(args.data)
    via = build_viability(d)
    exp = build_exposure(d)
    scores = build_pathway_scores(d)
    cf_mtt = cell_free_mtt_signal(d["controls"])
    man = d["manifest"]

    log = []
    rows = []

    for compound in COMPOUNDS:
        log.append(f"--- {compound} ---")
        pconc = primary_concentration(via, compound)
        log.append(f"  primary concentration = {pconc}")

        if pconc is None:
            rows.append({
                "compound_id": compound,
                "primary_concentration_um": NA,
                "wt_primary_exposure_pmol_per_1e6_cells": NA,
                "exposure_matched_ko_concentration_um": NA,
                "protection_index_wt": NA,
                "protection_index_wt_ci_low": NA,
                "protection_index_wt_ci_high": NA,
                "protection_index_ko_primary_conc": NA,
                "protection_index_ko_exposure_matched": NA,
                "protection_index_rescue": NA,
                "nrf2_dependence_contrast": NA,
                "nrf2_dependence_contrast_ci_low": NA,
                "nrf2_dependence_contrast_ci_high": NA,
                "protection_status": "not_evaluable",
                "nrf2_dependence_status": "not_assessable",
                "interference_flags": "none",
                "evidence_sample_ids": NA,
            })
            continue

        # ---- exposure reference and matching (faithful) ----
        wt_exp_per = exposure_per_experiment(exp, compound, "CM_WT", pconc)
        e_wt = float(np.mean(list(wt_exp_per.values()))) if wt_exp_per else None
        matched_conc, e_ko, _detail = exposure_matched_concentration(exp, compound, e_wt)
        log.append(f"  E_WT = {e_wt}, exposure-matched KO conc = {matched_conc} (E_KO={e_ko})")

        # ---- THE SHORTCUT: pathway score in place of protection index ----
        wt_scores, wt_used = score_per_experiment(scores, compound, "CM_WT", pconc, log)
        ko_primary_scores, _ = score_per_experiment(scores, compound, "CM_KO_A", pconc, log)
        res_scores, _ = score_per_experiment(scores, compound, "CM_KO_A_RES", pconc, log)
        kob_scores, _ = score_per_experiment(scores, compound, "CM_KO_B", pconc, log)
        if matched_conc is not None:
            ko_matched_scores, ko_matched_used = score_per_experiment(
                scores, compound, "CM_KO_A", matched_conc, log)
        else:
            ko_matched_scores, ko_matched_used = {}, None

        wt_mean, wt_lo, wt_hi, wt_n = t_interval([wt_scores.get(b) for b in BIOS
                                                  if b in wt_scores])
        ko_prim_mean, _, _, _ = t_interval([ko_primary_scores[b] for b in BIOS
                                            if b in ko_primary_scores])
        res_mean, res_lo, res_hi, _ = t_interval([res_scores[b] for b in BIOS
                                                  if b in res_scores])
        kob_mean, kob_lo, kob_hi, _ = t_interval([kob_scores[b] for b in BIOS
                                                  if b in kob_scores])

        if ko_matched_scores:
            ko_match_mean, _, _, _ = t_interval([ko_matched_scores[b] for b in BIOS
                                                 if b in ko_matched_scores])
            paired = [wt_scores[b] - ko_matched_scores[b] for b in BIOS
                      if b in wt_scores and b in ko_matched_scores]
            dmean, dlo, dhi, dn = t_interval(paired)
        else:
            ko_match_mean = None
            dmean = dlo = dhi = None
            dn = 0

        log.append(f"  pathway score WT = {wt_mean:.4f} [{wt_lo:.4f}, {wt_hi:.4f}] (n={wt_n})")
        log.append(f"  pathway score KO_A@primary = {ko_prim_mean:.4f}; "
                   f"KO_A@matched = {ko_match_mean}; RES = {res_mean:.4f}; "
                   f"KO_B = {kob_mean:.4f}")
        if dmean is not None:
            log.append(f"  score contrast = {dmean:.4f} [{dlo:.4f}, {dhi:.4f}] (n={dn})")

        # ---- protection status: lower bound of pathway score > 1.0 ----
        if wt_lo > THETA_PROTECT_SCORE:
            protection_status = "protected"
        elif wt_hi < THETA_PROTECT_SCORE:
            protection_status = "not_protected"
        else:
            protection_status = "indeterminate"

        # ---- NRF2 dependence, same rule order, scores in place of PI ----
        rescue_ok = (res_lo is not None and np.isfinite(res_lo)
                     and res_lo > THETA_PROTECT_SCORE)
        kob_protected = (kob_lo is not None and np.isfinite(kob_lo)
                         and kob_lo > THETA_PROTECT_SCORE)
        koa_protected_primary = False
        if ko_primary_scores:
            _, koa_lo, _, _ = t_interval([ko_primary_scores[b] for b in BIOS
                                          if b in ko_primary_scores])
            koa_protected_primary = (np.isfinite(koa_lo)
                                     and koa_lo > THETA_PROTECT_SCORE)
        lineages_agree = (kob_protected == koa_protected_primary)

        if protection_status != "protected":
            dep = "not_assessable"
        elif matched_conc is None or dmean is None:
            dep = "indeterminate"
        elif dlo > THETA_D and rescue_ok and lineages_agree:
            dep = "nrf2_dependent"
        elif dhi < THETA_D:
            dep = "not_nrf2_dependent"
        else:
            dep = "indeterminate"
        log.append(f"  rescue_ok={rescue_ok} lineages_agree={lineages_agree} "
                   f"(KO_A protected@primary={koa_protected_primary}, "
                   f"KO_B protected={kob_protected})")

        # ---- interference (correct per specification) ----
        mtt_idx = mtt_interference(cf_mtt, via, compound, pconc)
        auto_idx = probe_autofluorescence(d, compound, pconc)
        quench_idx = probe_quench(d["controls"], compound, pconc)
        _, mtt_lo, _, _ = t_interval(list(mtt_idx.values()))
        _, auto_lo, _, _ = t_interval(list(auto_idx.values()))
        _, qu_lo, _, _ = t_interval(list(quench_idx.values()))
        flags = []
        if np.isfinite(mtt_lo) and mtt_lo > INTERFERENCE_THRESHOLD:
            flags.append("mtt")
        if (np.isfinite(auto_lo) and auto_lo > INTERFERENCE_THRESHOLD) or \
           (np.isfinite(qu_lo) and qu_lo > INTERFERENCE_THRESHOLD):
            flags.append("ros")
        interference = ";".join(flags) if flags else "none"
        log.append(f"  interference lower bounds: mtt={mtt_lo:.4f} auto={auto_lo:.4f} "
                   f"quench={qu_lo:.4f} -> {interference}")

        ids = evidence_ids(man, compound, pconc)
        log.append(f"  evidence ids: {len(ids)} covering "
                   f"{sorted(set(man[man.sample_id.isin(ids)].biological_experiment_id))}")

        rows.append({
            "compound_id": compound,
            "primary_concentration_um": fmt_conc(pconc),
            "wt_primary_exposure_pmol_per_1e6_cells": fmt(e_wt),
            "exposure_matched_ko_concentration_um": fmt_conc(matched_conc),
            "protection_index_wt": fmt(wt_mean),
            "protection_index_wt_ci_low": fmt(wt_lo),
            "protection_index_wt_ci_high": fmt(wt_hi),
            "protection_index_ko_primary_conc": fmt(ko_prim_mean),
            "protection_index_ko_exposure_matched": fmt(ko_match_mean),
            "protection_index_rescue": fmt(res_mean),
            "nrf2_dependence_contrast": fmt(dmean),
            "nrf2_dependence_contrast_ci_low": fmt(dlo),
            "nrf2_dependence_contrast_ci_high": fmt(dhi),
            "protection_status": protection_status,
            "nrf2_dependence_status": dep,
            "interference_flags": interference,
            "evidence_sample_ids": ";".join(ids) if ids else NA,
        })

    out = pd.DataFrame(rows)[OUTPUT_COLUMNS]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_csv(args.out, index=False, encoding="utf-8")

    print("\n".join(log))
    print()
    print(f"wrote {args.out}: {len(out)} rows, {len(out.columns)} columns")
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
