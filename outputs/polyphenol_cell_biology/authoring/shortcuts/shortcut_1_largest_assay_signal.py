#!/usr/bin/env python3
"""
SHORTCUT IMPLEMENTATION -- largest_assay_signal
===============================================

This script DELIBERATELY implements a flawed analysis of the
polyphenol_cell_biology benchmark, so that the benchmark's verifier can be
tested against a plausible reasoning shortcut.

THE DEVIATION (and nothing else):
  * The specified primary endpoint is live_cell_density_1e3_per_well, derived
    from the direct live-nuclei count (a NON-redox measurement).
  * This script instead uses the REDOX-DEPENDENT MTT signal
    (mtt_absorbance_570nm - mtt_absorbance_630nm) as if it measured survival,
    plugged into exactly the same algebraic forms the specification gives for
    live-cell density: the concentration-selection tox_ratio and the
    protection index PI.
  * A large reduction of the oxidative-stress probe fluorescence_au is
    additionally treated as corroborating protection (computed and reported in
    the run log; there is no output column for it).
  * assay_controls.csv is NEVER consulted -- no cell-free MTT control, no
    cell-free probe control, no fluorescein quench standard -- and
    interference_flags is reported as 'none' for every compound.

EVERYTHING ELSE follows study_specification.json exactly: the exposure-matching
rule, the paired Student-t interval convention with the published t table, the
classification thresholds and the rule evaluation order, the NA token, and the
evidence_sample_ids requirements.

Usage:
  python3 shortcut_1_largest_assay_signal.py --data <data dir> --out <results.csv>
"""

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

NA = "NA"
LADDER = [1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0]
COMPOUNDS = ["PP01", "PP02", "PP03", "PP04", "PP05", "PP06", "PP07", "PP08"]
BIOS = ["BIO01", "BIO02", "BIO03", "BIO04", "BIO05", "BIO06", "BIO07"]

T_TABLE = {
    1: 12.706204736, 2: 4.30265273, 3: 3.182446305, 4: 2.776445105,
    5: 2.570581836, 6: 2.446911851, 7: 2.364624252, 8: 2.306004135,
    9: 2.262157163,
}

THETA_P = 0.15
THETA_D = 0.15

COLUMNS = [
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


# --------------------------------------------------------------------------
# uncertainty convention (per specification: Student-t on per-experiment values)
# --------------------------------------------------------------------------
def t_interval(values):
    """Mean and two-sided 95% Student-t interval of per-experiment values."""
    v = [float(x) for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n == 0:
        return (None, None, None, 0)
    mean = float(np.mean(v))
    if n == 1:
        return (mean, None, None, 1)
    sd = float(np.std(v, ddof=1))
    tq = T_TABLE[n - 1]
    half = tq * sd / math.sqrt(n)
    return (mean, mean - half, mean + half, n)


def fmt(x, nd=6):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return NA
    return f"{float(x):.{nd}f}"


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def load(data_dir):
    man = pd.read_csv(os.path.join(data_dir, "sample_manifest.csv"))
    via = pd.read_csv(os.path.join(data_dir, "viability_readouts.csv"))
    oxs = pd.read_csv(os.path.join(data_dir, "oxidative_stress_readouts.csv"))
    exp = pd.read_csv(os.path.join(data_dir, "exposure_measurements.csv"))
    # NOTE: assay_controls.csv is deliberately NOT read by this shortcut.

    # === THE DEVIATION =====================================================
    # The redox-dependent MTT signal is used as the survival endpoint, in
    # place of the specified direct live-nuclei count.
    via = via.copy()
    via["mtt_signal"] = via["mtt_absorbance_570nm"] - via["mtt_absorbance_630nm"]
    via["endpoint"] = via["mtt_signal"]
    # (the specified endpoint would have been:
    #   via['live_nuclei_count'] / via['imaged_area_fraction'] / 1000.0 )
    # =======================================================================

    vdf = man.merge(via[["sample_id", "endpoint", "mtt_signal"]], on="sample_id", how="inner")
    vdf = vdf[vdf.assay_panel == "VIABILITY"]

    pdf = man.merge(oxs[["sample_id", "fluorescence_au", "probe_loaded"]].rename(
        columns={"probe_loaded": "pl"}), on="sample_id", how="inner")

    edf = man.merge(
        exp[["sample_id", "compound_id", "matrix", "sampling_condition",
             "injection_replicate", "measured_value", "qualifier",
             "cell_equivalents_1e6"]].rename(
            columns={"compound_id": "exp_compound_id",
                     "sampling_condition": "exp_sampling_condition"}),
        on="sample_id", how="inner")

    return man, vdf, pdf, edf


# --------------------------------------------------------------------------
# Lbar: per-experiment mean of the (MTT) endpoint over technical replicates
# --------------------------------------------------------------------------
def build_lbar(vdf):
    """dict[(cell_model, compound, conc, bio, challenge, schedule)] -> mean endpoint"""
    sub = vdf[(vdf.panel_id == "B_DOSE_RESPONSE") & (vdf.readout_time_h_post_challenge == 24.0)]
    g = sub.groupby(["cell_model_id", "compound_id", "administered_conc_um",
                     "biological_experiment_id", "challenge_id", "schedule_id"])["endpoint"].mean()
    return g.to_dict()


def pi_per_experiment(lbar, cell_model, compound, conc, schedule="PRE_NOWASH"):
    """Protection index per biological experiment, in the spec's algebraic form
    but computed on the MTT signal."""
    out = {}
    for b in BIOS:
        try:
            treated = lbar[(cell_model, compound, conc, b, "CHAL_ISO", schedule)]
            veh_iso = lbar[(cell_model, "VEH", 0.0, b, "CHAL_ISO", schedule)]
            veh_none = lbar[(cell_model, "VEH", 0.0, b, "CHAL_NONE", schedule)]
        except KeyError:
            continue
        denom = veh_none - veh_iso
        if denom == 0:
            continue
        out[b] = (treated - veh_iso) / denom
    return out


# --------------------------------------------------------------------------
# concentration selection -- spec rule, applied to the MTT signal
# --------------------------------------------------------------------------
def select_primary_concentration(lbar, compound):
    veh = [lbar[("CM_WT", "VEH", 0.0, b, "CHAL_NONE", "PRE_NOWASH")]
           for b in BIOS if ("CM_WT", "VEH", 0.0, b, "CHAL_NONE", "PRE_NOWASH") in lbar]
    veh_mean = float(np.mean(veh))
    ratios = {}
    for d in LADDER:
        vals = [lbar[("CM_WT", compound, d, b, "CHAL_NONE", "PRE_NOWASH")]
                for b in BIOS if ("CM_WT", compound, d, b, "CHAL_NONE", "PRE_NOWASH") in lbar]
        if not vals:
            continue
        ratios[d] = float(np.mean(vals)) / veh_mean
    tolerated = [d for d in LADDER if d in ratios and ratios[d] >= 0.85]
    primary = max(tolerated) if tolerated else None
    return primary, ratios


# --------------------------------------------------------------------------
# exposure -- unchanged from the specification
# --------------------------------------------------------------------------
def exposure_by_conc(edf, compound, cell_model):
    """-> dict[conc] = (mean over experiments with a measured value, n_measured)"""
    sub = edf[(edf.exp_compound_id == compound) &
              (edf.cell_model_id == cell_model) &
              (edf.matrix == "cell_lysate") &
              (edf.exp_sampling_condition == "END_PRETREAT_NOWASH")]
    res = {}
    for d, gd in sub.groupby("administered_conc_um"):
        per_bio = []
        for b, gb in gd.groupby("biological_experiment_id"):
            ok = gb[gb.qualifier == "measured"]
            if len(ok) == 0:
                continue  # censored sample: excluded, never imputed
            per_bio.append(float(np.mean(ok.measured_value / ok.cell_equivalents_1e6)))
        if per_bio:
            res[float(d)] = (float(np.mean(per_bio)), len(per_bio))
    return res


def match_exposure(e_wt, ko_exposures):
    if e_wt is None or e_wt <= 0:
        return None
    best, best_score = None, None
    for d in LADDER:
        if d not in ko_exposures:
            continue
        val, n = ko_exposures[d]
        if n < 3:          # censored concentration: cannot qualify
            continue
        ratio = val / e_wt
        if not (0.70 <= ratio <= 1.428571428571):
            continue
        score = abs(math.log(ratio))
        if best_score is None or score < best_score - 1e-12:
            best, best_score = d, score
    return best


# --------------------------------------------------------------------------
# probe "corroboration" (part of the shortcut; not an output column)
# --------------------------------------------------------------------------
def probe_reduction(pdf, compound, conc):
    """Fractional reduction of probe fluorescence vs vehicle, CM_WT, CHAL_ISO,
    probe-loaded wells. The shortcut treats a large reduction as corroborating
    protection. It consults NO cell-free control and NO dye-free well, so it
    cannot tell a real reduction from quenching of the emitted light."""
    sub = pdf[(pdf.cell_model_id == "CM_WT") & (pdf.challenge_id == "CHAL_ISO") &
              (pdf.schedule_id == "PRE_NOWASH") & (pdf.pl == "yes")]
    vals = []
    for b in BIOS:
        t = sub[(sub.compound_id == compound) & (sub.administered_conc_um == conc) &
                (sub.biological_experiment_id == b)].fluorescence_au
        v = sub[(sub.compound_id == "VEH") & (sub.administered_conc_um == 0.0) &
                (sub.biological_experiment_id == b)].fluorescence_au
        if len(t) == 0 or len(v) == 0:
            continue
        vals.append(1.0 - float(t.mean()) / float(v.mean()))
    return t_interval(vals)


# --------------------------------------------------------------------------
# evidence sample ids -- per the specification
# --------------------------------------------------------------------------
def evidence_ids(man, compound, conc):
    sub = man[(man.assay_panel == "VIABILITY") &
              (man.cell_model_id == "CM_WT") &
              (man.compound_id == compound) &
              (man.administered_conc_um == conc) &
              (man.challenge_id == "CHAL_ISO") &
              (man.schedule_id == "PRE_NOWASH") &
              (man.readout_time_h_post_challenge == 24.0)]
    ids = []
    for b in BIOS:
        s = sub[sub.biological_experiment_id == b].sort_values(
            ["technical_replicate", "sample_id"])
        if len(s):
            ids.append(str(s.sample_id.iloc[0]))
    return ";".join(ids) if ids else NA


# --------------------------------------------------------------------------
def analyse(data_dir, log):
    man, vdf, pdf, edf = load(data_dir)
    lbar = build_lbar(vdf)
    rows = []

    for c in COMPOUNDS:
        primary, ratios = select_primary_concentration(lbar, c)
        log.append(f"[{c}] MTT-based tox_ratio by concentration: " +
                   ", ".join(f"{d:g}:{ratios.get(d, float('nan')):.3f}" for d in LADDER))

        if primary is None:
            # spec: no tolerated concentration -> everything NA, not_evaluable
            rows.append({
                "compound_id": c, "primary_concentration_um": NA,
                "wt_primary_exposure_pmol_per_1e6_cells": NA,
                "exposure_matched_ko_concentration_um": NA,
                "protection_index_wt": NA, "protection_index_wt_ci_low": NA,
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
            log.append(f"[{c}] no tolerated concentration under the MTT tox_ratio")
            continue

        # ---- wild-type protection (MTT-based) ----
        pi_wt = pi_per_experiment(lbar, "CM_WT", c, primary)
        wt_mean, wt_lo, wt_hi, n_wt = t_interval(list(pi_wt.values()))

        if wt_lo is not None and wt_lo > THETA_P:
            prot = "protected"
        elif wt_hi is not None and wt_hi < THETA_P:
            prot = "not_protected"
        else:
            prot = "indeterminate"

        # ---- exposure (unchanged from the specification) ----
        wt_exp = exposure_by_conc(edf, c, "CM_WT")
        e_wt = wt_exp.get(primary, (None, 0))[0]
        ko_exp = exposure_by_conc(edf, c, "CM_KO_A")
        matched = match_exposure(e_wt, ko_exp)

        # ---- knockout, rescue, lineage B (MTT-based) ----
        pi_ko_prim = pi_per_experiment(lbar, "CM_KO_A", c, primary)
        ko_prim_mean, _, _, _ = t_interval(list(pi_ko_prim.values()))

        pi_res = pi_per_experiment(lbar, "CM_KO_A_RES", c, primary)
        res_mean, res_lo, res_hi, _ = t_interval(list(pi_res.values()))

        pi_kob = pi_per_experiment(lbar, "CM_KO_B", c, primary)
        kob_mean, kob_lo, kob_hi, _ = t_interval(list(pi_kob.values()))

        if matched is not None:
            pi_ko_match = pi_per_experiment(lbar, "CM_KO_A", c, matched)
            ko_match_mean, _, _, _ = t_interval(list(pi_ko_match.values()))
            # PAIRED by biological experiment, per the uncertainty convention
            diffs = [pi_wt[b] - pi_ko_match[b] for b in BIOS
                     if b in pi_wt and b in pi_ko_match]
            d_mean, d_lo, d_hi, _ = t_interval(diffs)
        else:
            ko_match_mean = d_mean = d_lo = d_hi = None

        # ---- NRF2-dependence status, rules in the specified order ----
        if prot != "protected":
            dep = "not_assessable"
        elif matched is None:
            dep = "indeterminate"
        else:
            rescue_ok = (res_lo is not None and res_lo > THETA_D)
            # lineage agreement: does CM_KO_B show protection by the same rule?
            if kob_lo is not None and kob_lo > THETA_P:
                kob_protected = True
            elif kob_hi is not None and kob_hi < THETA_P:
                kob_protected = False
            else:
                kob_protected = False
            koa_protected = False  # CM_KO_A at the primary administered concentration
            koa_lo = t_interval(list(pi_ko_prim.values()))[1]
            koa_hi = t_interval(list(pi_ko_prim.values()))[2]
            if koa_lo is not None and koa_lo > THETA_P:
                koa_protected = True
            lineages_agree = (koa_protected == kob_protected)

            if d_lo is not None and d_lo > THETA_D and rescue_ok and lineages_agree:
                dep = "nrf2_dependent"
            elif d_hi is not None and d_hi < THETA_D:
                dep = "not_nrf2_dependent"
            else:
                dep = "indeterminate"

        # ---- shortcut "corroboration" from the probe, logged only ----
        pr_mean, pr_lo, pr_hi, pr_n = probe_reduction(pdf, c, primary)
        if pr_mean is not None:
            log.append(f"[{c}] probe fluorescence reduction vs vehicle "
                       f"(treated as corroborating protection): {pr_mean:.3f} "
                       f"[{pr_lo:.3f},{pr_hi:.3f}] n={pr_n}")

        # ---- interference: cell-free controls NEVER consulted ----
        flags = "none"

        rows.append({
            "compound_id": c,
            "primary_concentration_um": fmt(primary, 1),
            "wt_primary_exposure_pmol_per_1e6_cells": fmt(e_wt, 6),
            "exposure_matched_ko_concentration_um": fmt(matched, 1) if matched is not None else NA,
            "protection_index_wt": fmt(wt_mean),
            "protection_index_wt_ci_low": fmt(wt_lo),
            "protection_index_wt_ci_high": fmt(wt_hi),
            "protection_index_ko_primary_conc": fmt(ko_prim_mean),
            "protection_index_ko_exposure_matched": fmt(ko_match_mean),
            "protection_index_rescue": fmt(res_mean),
            "nrf2_dependence_contrast": fmt(d_mean),
            "nrf2_dependence_contrast_ci_low": fmt(d_lo),
            "nrf2_dependence_contrast_ci_high": fmt(d_hi),
            "protection_status": prot,
            "nrf2_dependence_status": dep,
            "interference_flags": flags,
            "evidence_sample_ids": evidence_ids(man, c, primary),
        })
        log.append(f"[{c}] primary={primary:g} E_WT={e_wt} matched={matched} "
                   f"PI_wt={wt_mean:.3f}[{wt_lo:.3f},{wt_hi:.3f}] "
                   f"PI_ko_prim={ko_prim_mean:.3f} PI_ko_match="
                   f"{'NA' if ko_match_mean is None else f'{ko_match_mean:.3f}'} "
                   f"PI_res={res_mean:.3f} PI_koB={kob_mean:.3f} -> {prot}/{dep}")

    return pd.DataFrame(rows, columns=COLUMNS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    log = []
    df = analyse(args.data, log)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    df.to_csv(args.out, index=False, lineterminator="\n")

    for line in log:
        print(line, file=sys.stderr)
    print(f"wrote {len(df)} rows to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
