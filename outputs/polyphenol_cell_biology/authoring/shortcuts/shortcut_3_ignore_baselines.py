#!/usr/bin/env python3
"""
SHORTCUT IMPLEMENTATION -- 'ignore_baselines'
=============================================

DELIBERATELY FLAWED analysis of the polyphenol_cell_biology benchmark.
This script is NOT an attempt at the correct answer. It implements exactly one
named methodological deviation so that the benchmark verifier can be tested on
whether it detects that deviation.

THE DEVIATION (and nothing else):
  1. ARM.   Every genotype/compound effect is computed in the COMMON-oxidant-dose
            arm (challenge_id='CHAL_COMMON', panel_id='D_COMMON_DOSE', 300 uM tBHP
            for every cell model) instead of the specified primary condition
            (challenge_id='CHAL_ISO', panel_id='B_DOSE_RESPONSE', cell-model-specific
            isoeffective dose).  The cell models differ ~1.7-fold in baseline
            susceptibility, so in this arm they sit at different points of their own
            injury curves.
  2. SCALE. The effect is a RAW DIFFERENCE expressed as a fraction of the
            unchallenged control, not the deficit-normalised protection index:

              effect(g,c,d,b) =
                 ( Lbar(g, c,   d, b, CHAL_COMMON, D_COMMON_DOSE)
                 - Lbar(g, VEH, 0, b, CHAL_COMMON, D_COMMON_DOSE) )
                 / Lbar(g, VEH, 0, b, CHAL_NONE,   B_DOSE_RESPONSE)

            i.e. the denominator is the matched vehicle UNCHALLENGED density rather
            than that genotype's own challenge-induced injury deficit.  The genotype's
            own baseline susceptibility is therefore NOT divided out.
  3. CONC.  The D_COMMON_DOSE arm only carries 10/30/100 uM.  Where the
            concentration-selection rule picks a concentration outside that set, the
            closest available one on a log scale is used and REPORTED in
            primary_concentration_um.

EVERYTHING ELSE IS AS SPECIFIED: concentration-selection rule (tox_ratio >= 0.85,
highest tolerated, ratio-of-means, B_DOSE_RESPONSE/CHAL_NONE/CM_WT), exposure-matching
rule, Student-t interval convention with the published t-table, thresholds
(theta_P = theta_D = 0.15, interference 0.10), rule evaluation order, lineage
corroboration, rescue criterion, interference indices, NA token, evidence-sample rules.

Usage:
  python3 shortcut_3_ignore_baselines.py --data <data dir> --out <results csv>
"""

import argparse
import math
import os

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- constants
NA = "NA"
LADDER = [1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0]
BIOS = ["BIO01", "BIO02", "BIO03", "BIO04", "BIO05", "BIO06", "BIO07"]
COMPOUNDS = ["PP01", "PP02", "PP03", "PP04", "PP05", "PP06", "PP07", "PP08"]

# published two-sided 95% Student-t quantiles, indexed by degrees of freedom (n-1)
T_TABLE = {
    1: 12.706204736, 2: 4.30265273, 3: 3.182446305, 4: 2.776445105,
    5: 2.570581836, 6: 2.446911851, 7: 2.364624252, 8: 2.306004135,
    9: 2.262157163,
}

TOX_RATIO_MIN = 0.85
THETA_P = 0.15
THETA_D = 0.15
THETA_INTERFERENCE = 0.10
EXP_WIN_LO = 0.70
EXP_WIN_HI = 1.428571428571
EXP_MIN_MEASURED_BIOS = 4

# the DEVIATION: the common-dose arm only carries these administered concentrations
COMMON_ARM_CONCS = [10.0, 30.0, 100.0]

HEADER = [
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


# ----------------------------------------------------------------------------- helpers
def t_interval(values):
    """Student-t 95% interval on per-biological-experiment values."""
    v = [x for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n < 2:
        return (float("nan"), float("nan"), float("nan"))
    arr = np.asarray(v, dtype=float)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1))
    tq = T_TABLE[n - 1]
    half = tq * sd / math.sqrt(n)
    return (mean, mean - half, mean + half)


def nearest_on_log_scale(target, available):
    """Closest available concentration to `target` on a log scale; ties -> lower."""
    best = None
    for d in sorted(available):
        dist = abs(math.log(d) - math.log(target))
        if best is None or dist < best[0] - 1e-12:
            best = (dist, d)
    return best[1]


def fmt(x, nd=6):
    if x is None:
        return NA
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return NA
    return f"{x:.{nd}f}"


def fmt_conc(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return NA
    return f"{float(x):.1f}"


def fmt_sig(x, sig=6):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return NA
    return f"{x:.{sig}g}"


# ----------------------------------------------------------------------------- loading
def load(data_dir):
    man = pd.read_csv(os.path.join(data_dir, "sample_manifest.csv"))
    via = pd.read_csv(os.path.join(data_dir, "viability_readouts.csv"))
    oxs = pd.read_csv(os.path.join(data_dir, "oxidative_stress_readouts.csv"))
    exp = pd.read_csv(os.path.join(data_dir, "exposure_measurements.csv"))
    ctl = pd.read_csv(os.path.join(data_dir, "assay_controls.csv"))

    via = via.drop(columns=["readout_time_h_post_challenge"])
    v = man.merge(via, on="sample_id", how="inner")
    v["live_cell_density"] = v["live_nuclei_count"] / v["imaged_area_fraction"] / 1000.0
    v["mtt_signal"] = v["mtt_absorbance_570nm"] - v["mtt_absorbance_630nm"]

    oxs = oxs.drop(columns=["readout_time_h_post_challenge", "probe_loaded"])
    o = man.merge(oxs, on="sample_id", how="inner")

    return man, v, o, exp, ctl


# ----------------------------------------------------------------------------- tables
def build_lbar_tables(v):
    """Per-condition, per-biological-experiment technical-replicate means of
    live_cell_density, for the two arms this analysis needs."""
    # DEVIATION arm: common administered oxidant dose
    d = v[(v.panel_id == "D_COMMON_DOSE")
          & (v.assay_panel == "VIABILITY")
          & (v.challenge_id == "CHAL_COMMON")
          & (v.schedule_id == "PRE_NOWASH")
          & (v.readout_time_h_post_challenge == 24.0)]
    common = (d.groupby(["cell_model_id", "compound_id", "administered_conc_um",
                         "biological_experiment_id"])["live_cell_density"]
              .mean())

    # unchallenged vehicle reference (denominator of the raw-difference scale)
    n = v[(v.panel_id == "B_DOSE_RESPONSE")
          & (v.assay_panel == "VIABILITY")
          & (v.challenge_id == "CHAL_NONE")
          & (v.schedule_id == "PRE_NOWASH")
          & (v.readout_time_h_post_challenge == 24.0)]
    unchal = (n.groupby(["cell_model_id", "compound_id", "administered_conc_um",
                         "biological_experiment_id"])["live_cell_density"]
              .mean())

    return common, unchal


def effect_per_bio(common, unchal, model, compound, conc):
    """The DEVIATED effect scale, per biological experiment.

    ( treated challenged  -  vehicle challenged ) / vehicle unchallenged,
    all in the common-oxidant-dose arm except the unchallenged denominator,
    which comes from CHAL_NONE in B_DOSE_RESPONSE.
    """
    out = {}
    for b in BIOS:
        try:
            treated = common.loc[(model, compound, float(conc), b)]
            veh_ch = common.loc[(model, "VEH", 0.0, b)]
            veh_un = unchal.loc[(model, "VEH", 0.0, b)]
        except KeyError:
            continue
        if not np.isfinite(veh_un) or veh_un == 0:
            continue
        out[b] = (treated - veh_ch) / veh_un
    return out


# ------------------------------------------------- concentration-selection rule (as spec)
def primary_concentration(v, compound):
    """Highest tolerated concentration in wild-type cells: tox_ratio >= 0.85,
    tox_ratio being a RATIO OF MEANS over biological experiments.
    Unchanged from the specification."""
    base = v[(v.panel_id == "B_DOSE_RESPONSE")
             & (v.assay_panel == "VIABILITY")
             & (v.cell_model_id == "CM_WT")
             & (v.challenge_id == "CHAL_NONE")
             & (v.schedule_id == "PRE_NOWASH")
             & (v.readout_time_h_post_challenge == 24.0)]
    per_bio = (base.groupby(["compound_id", "administered_conc_um",
                             "biological_experiment_id"])["live_cell_density"].mean())
    veh = per_bio.loc[("VEH", 0.0)].mean()
    tolerated = []
    for d in LADDER:
        key = (compound, float(d))
        if key not in per_bio.index.droplevel(2).unique():
            continue
        num = per_bio.loc[key].mean()
        if num / veh >= TOX_RATIO_MIN:
            tolerated.append(d)
    return max(tolerated) if tolerated else None


# ------------------------------------------------------- exposure matching rule (as spec)
def exposure_table(man, exp):
    """Per (cell model, compound, conc, bio) mean intracellular exposure over
    the 'measured' injection replicates at END_PRETREAT_NOWASH."""
    e = exp[(exp.matrix == "cell_lysate")
            & (exp.sampling_condition == "END_PRETREAT_NOWASH")].copy()
    e = e.merge(man[["sample_id", "cell_model_id", "administered_conc_um",
                     "biological_experiment_id", "panel_id"]], on="sample_id", how="left")
    e = e[e.panel_id == "X_EXPOSURE"]
    meas = e[e.qualifier == "measured"].copy()
    meas["exposure"] = meas["measured_value"] / meas["cell_equivalents_1e6"]
    # average only the measured injection replicates within a sample
    per_sample = (meas.groupby(["cell_model_id", "compound_id", "administered_conc_um",
                                "biological_experiment_id"])["exposure"].mean())
    return per_sample


def e_mean(per_sample, model, compound, conc):
    """Mean over the biological experiments that yielded a measured value, plus count."""
    try:
        s = per_sample.loc[(model, compound, float(conc))]
    except KeyError:
        return (float("nan"), 0)
    return (float(s.mean()), int(s.shape[0]))


def exposure_matched_conc(per_sample, compound, e_wt):
    """Unchanged from the specification."""
    if not np.isfinite(e_wt) or e_wt <= 0:
        return None
    best = None
    for d in LADDER:
        val, nb = e_mean(per_sample, "CM_KO_A", compound, d)
        if nb < EXP_MIN_MEASURED_BIOS or not np.isfinite(val) or val <= 0:
            continue  # censored candidate
        ratio = val / e_wt
        if not (EXP_WIN_LO <= ratio <= EXP_WIN_HI):
            continue
        score = abs(math.log(ratio))
        if best is None or score < best[0] - 1e-12:
            best = (score, d)
    return None if best is None else best[1]


# ------------------------------------------------------------- interference (as specified)
def interference(v, o, ctl, compound, conc):
    flags = []

    # ---- MTT interference index
    cf = ctl[(ctl.control_type == "cell_free_mtt") & (ctl.challenge_id == "CHAL_NONE")]
    cf570 = cf[cf.measured_quantity == "mtt_absorbance_570nm"]
    cf630 = cf[cf.measured_quantity == "mtt_absorbance_630nm"]
    key = ["compound_id", "administered_conc_um", "biological_experiment_id",
           "plate_id", "technical_replicate"]
    cfm = cf570.merge(cf630[key + ["value"]], on=key, suffixes=("_570", "_630"))
    cfm["mtt_signal"] = cfm["value_570"] - cfm["value_630"]
    cf_bio = cfm.groupby(["compound_id", "administered_conc_um",
                          "biological_experiment_id"])["mtt_signal"].mean()

    cellref = v[(v.panel_id == "B_DOSE_RESPONSE")
                & (v.assay_panel == "VIABILITY")
                & (v.cell_model_id == "CM_WT")
                & (v.compound_id == "VEH")
                & (v.challenge_id == "CHAL_NONE")
                & (v.schedule_id == "PRE_NOWASH")
                & (v.readout_time_h_post_challenge == 24.0)]
    cell_bio = cellref.groupby("biological_experiment_id")["mtt_signal"].mean()

    mtt_idx = []
    for b in BIOS:
        try:
            cpd = cf_bio.loc[(compound, float(conc), b)]
            veh = cf_bio.loc[("VEH", 0.0, b)]
            cells = cell_bio.loc[b]
        except KeyError:
            continue
        denom = cells - veh
        if denom == 0:
            continue
        mtt_idx.append((cpd - veh) / denom)
    m_mean, m_lo, m_hi = t_interval(mtt_idx)
    if np.isfinite(m_lo) and m_lo > THETA_INTERFERENCE:
        flags.append("mtt")

    ros = False

    # ---- probe autofluorescence index
    sub = o[(o.panel_id == "R_PROBE")
            & (o.cell_model_id == "CM_WT")
            & (o.challenge_id == "CHAL_ISO")
            & (o.schedule_id == "PRE_NOWASH")]
    g = sub.groupby(["compound_id", "administered_conc_um", "probe_loaded",
                     "biological_experiment_id"])["fluorescence_au"].mean()
    auto_idx = []
    for b in BIOS:
        try:
            cpd_free = g.loc[(compound, float(conc), "no", b)]
            veh_free = g.loc[("VEH", 0.0, "no", b)]
            veh_load = g.loc[("VEH", 0.0, "yes", b)]
        except KeyError:
            continue
        denom = veh_load - veh_free
        if denom == 0:
            continue
        auto_idx.append((cpd_free - veh_free) / denom)
    a_mean, a_lo, a_hi = t_interval(auto_idx)
    if np.isfinite(a_lo) and a_lo > THETA_INTERFERENCE:
        ros = True

    # ---- probe quench index
    q = ctl[ctl.control_type == "fluorescein_standard_quench"]
    qb = q.groupby(["compound_id", "administered_conc_um",
                    "biological_experiment_id"])["value"].mean()
    quench_idx = []
    for b in BIOS:
        try:
            cpd = qb.loc[(compound, float(conc), b)]
            veh = qb.loc[("VEH", 0.0, b)]
        except KeyError:
            continue
        if veh == 0:
            continue
        quench_idx.append((veh - cpd) / veh)
    q_mean, q_lo, q_hi = t_interval(quench_idx)
    if np.isfinite(q_lo) and q_lo > THETA_INTERFERENCE:
        ros = True

    if ros:
        flags.append("ros")

    order = {"mtt": 0, "ros": 1}
    flags = sorted(set(flags), key=lambda f: order[f])
    return ";".join(flags) if flags else "none"


# -------------------------------------------------------------- evidence sample ids
def evidence_ids(man, compound, conc):
    """Per the specification: VIABILITY wells in CM_WT with this compound at the
    primary concentration, CHAL_ISO, PRE_NOWASH, readout 24 h, covering BIO01..BIO07."""
    s = man[(man.assay_panel == "VIABILITY")
            & (man.cell_model_id == "CM_WT")
            & (man.compound_id == compound)
            & (man.administered_conc_um == float(conc))
            & (man.challenge_id == "CHAL_ISO")
            & (man.schedule_id == "PRE_NOWASH")
            & (man.readout_time_h_post_challenge == 24.0)]
    ids = []
    for b in BIOS:
        cand = sorted(s[s.biological_experiment_id == b]["sample_id"].tolist())
        if cand:
            ids.append(cand[0])
    return ";".join(ids) if len(ids) == len(BIOS) else NA


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    man, v, o, exp, ctl = load(args.data)
    common, unchal = build_lbar_tables(v)
    per_sample_exp = exposure_table(man, exp)

    rows = []
    notes = []

    for cpd in COMPOUNDS:
        spec_conc = primary_concentration(v, cpd)

        if spec_conc is None:
            rows.append([cpd] + [NA] * 12 + ["not_evaluable", "not_assessable", "none", NA])
            continue

        # DEVIATION 3: remap onto the concentrations the common-dose arm carries
        conc = nearest_on_log_scale(spec_conc, COMMON_ARM_CONCS)
        if conc != spec_conc:
            notes.append(f"{cpd}: selection rule chose {spec_conc} uM; "
                         f"common-dose arm carries only {COMMON_ARM_CONCS}; used {conc} uM")

        # exposure reference at the reported primary concentration (rule unchanged)
        e_wt, e_wt_n = e_mean(per_sample_exp, "CM_WT", cpd, conc)
        ko_conc = exposure_matched_conc(per_sample_exp, cpd, e_wt)

        # ---------------- the DEVIATED effect estimates
        eff_wt = effect_per_bio(common, unchal, "CM_WT", cpd, conc)
        pi_wt, pi_wt_lo, pi_wt_hi = t_interval([eff_wt[b] for b in BIOS if b in eff_wt])

        eff_ko_pri = effect_per_bio(common, unchal, "CM_KO_A", cpd, conc)
        pi_ko_pri, ko_pri_lo, _ = t_interval([eff_ko_pri[b] for b in BIOS if b in eff_ko_pri])

        eff_res = effect_per_bio(common, unchal, "CM_KO_A_RES", cpd, conc)
        pi_res, res_lo, _ = t_interval([eff_res[b] for b in BIOS if b in eff_res])

        eff_kob = effect_per_bio(common, unchal, "CM_KO_B", cpd, conc)
        _, kob_lo, _ = t_interval([eff_kob[b] for b in BIOS if b in eff_kob])

        # exposure-matched knockout stratum
        if ko_conc is None:
            pi_ko_match = None
            delta = delta_lo = delta_hi = None
            ko_match_used = None
        else:
            # the common-dose arm carries only 10/30/100 uM, so the exposure-matched
            # concentration is read at its closest available neighbour on a log scale.
            ko_match_used = nearest_on_log_scale(ko_conc, COMMON_ARM_CONCS)
            if ko_match_used != ko_conc:
                notes.append(f"{cpd}: exposure-matched KO concentration {ko_conc} uM "
                             f"not in the common-dose arm; read at {ko_match_used} uM")
            eff_ko_m = effect_per_bio(common, unchal, "CM_KO_A", cpd, ko_match_used)
            pi_ko_match, _, _ = t_interval([eff_ko_m[b] for b in BIOS if b in eff_ko_m])
            paired = [eff_wt[b] - eff_ko_m[b] for b in BIOS
                      if b in eff_wt and b in eff_ko_m]
            delta, delta_lo, delta_hi = t_interval(paired)

        # ---------------- classification (rules and order unchanged)
        if np.isfinite(pi_wt_lo) and pi_wt_lo > THETA_P:
            protection_status = "protected"
        elif np.isfinite(pi_wt_hi) and pi_wt_hi < THETA_P:
            protection_status = "not_protected"
        else:
            protection_status = "indeterminate"

        if protection_status != "protected":
            nrf2_status = "not_assessable"
        elif ko_conc is None:
            nrf2_status = "indeterminate"
        else:
            koa_protects = bool(np.isfinite(ko_pri_lo) and ko_pri_lo > THETA_P)
            kob_protects = bool(np.isfinite(kob_lo) and kob_lo > THETA_P)
            rescue_ok = bool(np.isfinite(res_lo) and res_lo > THETA_P)
            if koa_protects != kob_protects:
                nrf2_status = "indeterminate"
            elif np.isfinite(delta_lo) and delta_lo > THETA_D and rescue_ok:
                nrf2_status = "nrf2_dependent"
            elif np.isfinite(delta_hi) and delta_hi < THETA_D:
                nrf2_status = "not_nrf2_dependent"
            else:
                nrf2_status = "indeterminate"

        flags = interference(v, o, ctl, cpd, conc)
        ev = evidence_ids(man, cpd, conc)

        rows.append([
            cpd,
            fmt_conc(conc),
            fmt_sig(e_wt) if e_wt_n > 0 else NA,
            fmt_conc(ko_conc) if ko_conc is not None else NA,
            fmt(pi_wt), fmt(pi_wt_lo), fmt(pi_wt_hi),
            fmt(pi_ko_pri),
            fmt(pi_ko_match) if pi_ko_match is not None else NA,
            fmt(pi_res),
            fmt(delta) if delta is not None else NA,
            fmt(delta_lo) if delta_lo is not None else NA,
            fmt(delta_hi) if delta_hi is not None else NA,
            protection_status, nrf2_status, flags, ev,
        ])

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out = pd.DataFrame(rows, columns=HEADER)
    out.to_csv(args.out, index=False)

    print("wrote", args.out)
    print("rows:", len(out))
    for n in notes:
        print("NOTE", n)
    with pd.option_context("display.width", 250, "display.max_columns", 50):
        print(out.drop(columns=["evidence_sample_ids"]).to_string(index=False))


if __name__ == "__main__":
    main()
