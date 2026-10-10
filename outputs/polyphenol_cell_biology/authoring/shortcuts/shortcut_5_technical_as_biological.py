#!/usr/bin/env python3
"""
SHORTCUT 5 -- technical_as_biological
=====================================

Deliberately LIMITED analysis of the polyphenol_cell_biology benchmark.

The single deviation from study_specification.json:

    Every point estimate and every interval is computed as if each technical
    replicate WELL were an independent biological experiment.  Technical
    replicates are NOT averaged within a biological experiment, and
    biological_experiment_id is NOT used as the unit of inference.

Concretely:
  * one protection index per individual treated WELL, using that well's own
    biological experiment's vehicle means as the two denominators terms
    (the vehicle terms are still per-experiment means -- otherwise the
    index would not be defined at all);
  * all such well-level values are pooled across the seven biological
    experiments into a single sample of size n (n = 28 for the viability
    panel: 7 experiments x 4 replicate wells);
  * the published Student-t interval is applied with that inflated n;
  * the NRF2-dependence contrast is paired well-to-well by
    (biological_experiment_id, technical_replicate) instead of by
    biological experiment, again giving n = 28;
  * the interference indices are formed per individual control well
    (n = 21 for the cell-free MTT and the fluorescein-quench controls,
    n = 7 for the dye-free autofluorescence wells, because the design
    supplies only one dye-free well per experiment -- that index is
    therefore numerically unchanged by this shortcut).

The published t-quantile table only runs to df = 9.  The inflated samples
need df = 27 and df = 20, which the table does not contain, so this
implementation clamps to the largest tabulated entry
(df = 9, t = 2.262157163).  That is the most favourable value the table can
supply; it makes the intervals even narrower than a true t(27) would, and it
is recorded here because it is part of the flaw, not an accident.

EVERYTHING ELSE follows the specification exactly: the primary endpoint
(live_cell_density_1e3_per_well), the protection-index algebra, the
concentration-selection rule (ratio of means, tox_ratio >= 0.85, highest
tolerated rung), the exposure-matching rule (per-experiment means, >= 4
measured experiments for a candidate, window 0.70-1.428571428571, minimise
|ln ratio|), the classification thresholds (0.15, 0.15, 0.10) and the rule
order.
"""

import argparse
import json
import math
import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- constants

COMPOUNDS = ["PP01", "PP02", "PP03", "PP04", "PP05", "PP06", "PP07", "PP08"]
LADDER = [1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0]
BIOS = ["BIO01", "BIO02", "BIO03", "BIO04", "BIO05", "BIO06", "BIO07"]

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
MAX_DF = max(T_TABLE)

THETA_P = 0.15
THETA_D = 0.15
THETA_I = 0.10
TOL_RATIO = 0.85
EXP_WINDOW_LO = 0.70
EXP_WINDOW_HI = 1.428571428571
NA = "NA"

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


def t_quantile(n):
    """Published two-sided 95% t quantile for sample size n.

    SHORTCUT NOTE: the inflated well-level samples need df values the
    published table does not carry (27, 20, ...).  We clamp to the largest
    tabulated df.  This is part of the deviation under test.
    """
    df = int(n) - 1
    if df < 1:
        return float("nan")
    return T_TABLE[min(df, MAX_DF)]


def ci(values):
    """Mean and two-sided 95% Student-t interval over `values`.

    Under this shortcut `values` are WELL-level, not experiment-level.
    """
    v = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    n = v.size
    if n == 0:
        return float("nan"), float("nan"), float("nan"), 0
    mean = float(v.mean())
    if n == 1:
        return mean, float("nan"), float("nan"), 1
    sd = float(v.std(ddof=1))
    half = t_quantile(n) * sd / math.sqrt(n)
    return mean, mean - half, mean + half, n


def fmt(x, nd=6):
    if x is None:
        return NA
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return NA
    if not np.isfinite(xf):
        return NA
    return f"{xf:.{nd}f}"


def fmt_sig(x, sig=6):
    if x is None:
        return NA
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return NA
    if not np.isfinite(xf):
        return NA
    if xf == 0:
        return "0.000000"
    return f"{xf:.{sig}g}"


def fmt_conc(x):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return NA
    return f"{float(x):g}"


# ---------------------------------------------------------------- load

def load(data_dir):
    man = pd.read_csv(os.path.join(data_dir, "sample_manifest.csv"))
    via = pd.read_csv(os.path.join(data_dir, "viability_readouts.csv"))
    ox = pd.read_csv(os.path.join(data_dir, "oxidative_stress_readouts.csv"))
    exp = pd.read_csv(os.path.join(data_dir, "exposure_measurements.csv"))
    ctl = pd.read_csv(os.path.join(data_dir, "assay_controls.csv"))

    # Primary endpoint. imaged_area_fraction is constant but we apply it as
    # specified in derived_quantities.
    via = via.copy()
    via["live_density"] = (
        via["live_nuclei_count"] / via["imaged_area_fraction"] / 1000.0
    )
    via["mtt_signal"] = (
        via["mtt_absorbance_570nm"] - via["mtt_absorbance_630nm"]
    )

    vcols = [
        "sample_id",
        "biological_experiment_id",
        "panel_id",
        "assay_panel",
        "cell_model_id",
        "compound_id",
        "administered_conc_um",
        "schedule_id",
        "challenge_id",
        "technical_replicate",
        "probe_loaded",
        "sampling_condition",
        "readout_time_h_post_challenge",
    ]
    V = man[man.assay_panel == "VIABILITY"][vcols].merge(
        via[["sample_id", "live_density", "mtt_signal"]], on="sample_id"
    )
    O = man[man.assay_panel == "OXIDATIVE_STRESS"][vcols].merge(
        ox[["sample_id", "fluorescence_au"]], on="sample_id"
    )
    X = man[man.assay_panel == "EXPOSURE"][
        [
            "sample_id",
            "biological_experiment_id",
            "cell_model_id",
            "administered_conc_um",
        ]
    ].merge(exp, on="sample_id")
    X["exposure"] = X["measured_value"] / X["cell_equivalents_1e6"]
    return V, O, X, ctl


# ------------------------------------------------- viability helper tables

def veh_terms(V, cell_model):
    """Per-experiment vehicle means, exactly as the specification defines
    them: Lbar over the technical replicate wells of the condition inside one
    biological experiment.

    These two denominators stay at experiment level under this shortcut --
    a well-level protection index still needs a matched vehicle reference,
    and the mandate concerns the UNIT OF INFERENCE for the treated values.
    """
    base = V[
        (V.cell_model_id == cell_model)
        & (V.panel_id == "B_DOSE_RESPONSE")
        & (V.compound_id == "VEH")
        & (V.administered_conc_um == 0.0)
        & (V.schedule_id == "PRE_NOWASH")
        & (V.readout_time_h_post_challenge == 24.0)
    ]
    iso = (
        base[base.challenge_id == "CHAL_ISO"]
        .groupby("biological_experiment_id")["live_density"]
        .mean()
    )
    none = (
        base[base.challenge_id == "CHAL_NONE"]
        .groupby("biological_experiment_id")["live_density"]
        .mean()
    )
    return iso, none


def pi_wells(V, cell_model, compound, conc):
    """SHORTCUT CORE.

    Return a DataFrame with one protection index per individual treated
    WELL -- no averaging of technical replicates, no collapse to
    biological_experiment_id.

    Columns: biological_experiment_id, technical_replicate, pi, sample_id
    """
    if conc is None or not np.isfinite(conc):
        return pd.DataFrame(
            columns=[
                "biological_experiment_id",
                "technical_replicate",
                "pi",
                "sample_id",
            ]
        )
    iso, none = veh_terms(V, cell_model)
    treated = V[
        (V.cell_model_id == cell_model)
        & (V.panel_id == "B_DOSE_RESPONSE")
        & (V.compound_id == compound)
        & (V.administered_conc_um == conc)
        & (V.challenge_id == "CHAL_ISO")
        & (V.schedule_id == "PRE_NOWASH")
        & (V.readout_time_h_post_challenge == 24.0)
    ].copy()
    rows = []
    for _, r in treated.iterrows():
        b = r.biological_experiment_id
        if b not in iso.index or b not in none.index:
            continue
        denom = none[b] - iso[b]
        if denom == 0:
            continue
        rows.append(
            {
                "biological_experiment_id": b,
                "technical_replicate": int(r.technical_replicate),
                "pi": (r.live_density - iso[b]) / denom,
                "sample_id": r.sample_id,
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------- concentration selection

def select_primary_concentration(V, compound):
    """Specification concentration_selection_rule, unchanged.

    tox_ratio(d) = mean_b Lbar(CM_WT, c, d, b, CHAL_NONE) /
                   mean_b Lbar(CM_WT, VEH, 0, b, CHAL_NONE)
    A RATIO OF MEANS on the point estimate only; highest tolerated rung wins.
    """
    base = V[
        (V.cell_model_id == "CM_WT")
        & (V.panel_id == "B_DOSE_RESPONSE")
        & (V.challenge_id == "CHAL_NONE")
        & (V.schedule_id == "PRE_NOWASH")
        & (V.readout_time_h_post_challenge == 24.0)
    ]
    veh = base[(base.compound_id == "VEH") & (base.administered_conc_um == 0.0)]
    veh_mean = (
        veh.groupby("biological_experiment_id")["live_density"].mean().mean()
    )
    tolerated = []
    ratios = {}
    for d in LADDER:
        g = base[(base.compound_id == compound) & (base.administered_conc_um == d)]
        if g.empty:
            continue
        m = g.groupby("biological_experiment_id")["live_density"].mean().mean()
        ratios[d] = m / veh_mean
        if ratios[d] >= TOL_RATIO:
            tolerated.append(d)
    primary = max(tolerated) if tolerated else None
    return primary, ratios


# ------------------------------------------------- exposure matching

def exposure_mean(X, compound, cell_model, conc, min_measured=None):
    """Specification exposure aggregation, unchanged.

    Average only the 'measured' injection replicates within a sample, then
    average over the biological experiments that yielded a measured value.
    Returns (mean, n_experiments_with_measurement).
    """
    g = X[
        (X.compound_id == compound)
        & (X.cell_model_id == cell_model)
        & (X.administered_conc_um == conc)
        & (X.matrix == "cell_lysate")
        & (X.sampling_condition == "END_PRETREAT_NOWASH")
        & (X.qualifier == "measured")
    ]
    if g.empty:
        return None, 0
    per_exp = g.groupby("biological_experiment_id")["exposure"].mean()
    n = int(per_exp.size)
    if min_measured is not None and n < min_measured:
        return None, n
    return float(per_exp.mean()), n


def select_exposure_matched(X, compound, primary):
    """Specification exposure_matching_rule, unchanged."""
    if primary is None:
        return None, None
    e_wt, _ = exposure_mean(X, compound, "CM_WT", primary)
    if e_wt is None or e_wt <= 0:
        return None, None
    best, best_key = None, None
    for d in LADDER:
        e_ko, n = exposure_mean(X, compound, "CM_KO_A", d, min_measured=4)
        if e_ko is None or e_ko <= 0:
            continue
        ratio = e_ko / e_wt
        if not (EXP_WINDOW_LO <= ratio <= EXP_WINDOW_HI):
            continue
        key = abs(math.log(ratio))
        if best is None or key < best_key - 1e-15:
            best, best_key = d, key
    return e_wt, best


# ------------------------------------------------- interference indices

def mtt_interference_wells(V, ctl, compound, primary):
    """SHORTCUT: one index per individual cell-free MTT control WELL.

    Denominator reference (the cellular MTT signal and the vehicle cell-free
    signal) remains a per-experiment mean, as the specification defines it.
    n = 7 experiments x 3 control wells = 21.
    """
    if primary is None:
        return []
    cf = ctl[
        (ctl.control_type == "cell_free_mtt")
        & (ctl.challenge_id == "CHAL_NONE")
        & (ctl.qualifier == "measured")
    ]
    wide = cf.pivot_table(
        index=[
            "compound_id",
            "administered_conc_um",
            "biological_experiment_id",
            "technical_replicate",
        ],
        columns="measured_quantity",
        values="value",
        aggfunc="mean",
    ).reset_index()
    wide["mtt_signal"] = (
        wide["mtt_absorbance_570nm"] - wide["mtt_absorbance_630nm"]
    )

    veh = wide[(wide.compound_id == "VEH")]
    veh_exp = veh.groupby("biological_experiment_id")["mtt_signal"].mean()

    cells = V[
        (V.cell_model_id == "CM_WT")
        & (V.panel_id == "B_DOSE_RESPONSE")
        & (V.compound_id == "VEH")
        & (V.administered_conc_um == 0.0)
        & (V.challenge_id == "CHAL_NONE")
        & (V.schedule_id == "PRE_NOWASH")
        & (V.readout_time_h_post_challenge == 24.0)
    ]
    cells_exp = cells.groupby("biological_experiment_id")["mtt_signal"].mean()

    trt = wide[
        (wide.compound_id == compound) & (wide.administered_conc_um == primary)
    ]
    out = []
    for _, r in trt.iterrows():
        b = r.biological_experiment_id
        if b not in veh_exp.index or b not in cells_exp.index:
            continue
        denom = cells_exp[b] - veh_exp[b]
        if denom == 0:
            continue
        out.append((r.mtt_signal - veh_exp[b]) / denom)
    return out


def autofluorescence_wells(O, compound, primary):
    """SHORTCUT applied: one index per dye-free WELL.

    The design supplies exactly ONE dye-free well per biological experiment,
    so this index is numerically identical to the specification version and
    keeps n = 7.  Recorded explicitly so the shortcut's reach is honest.
    """
    if primary is None:
        return []
    base = O[
        (O.cell_model_id == "CM_WT")
        & (O.challenge_id == "CHAL_ISO")
        & (O.schedule_id == "PRE_NOWASH")
    ]
    veh = base[(base.compound_id == "VEH") & (base.administered_conc_um == 0.0)]
    veh_free = veh[veh.probe_loaded == "no"].groupby(
        "biological_experiment_id"
    )["fluorescence_au"].mean()
    veh_dye = veh[veh.probe_loaded == "yes"].groupby(
        "biological_experiment_id"
    )["fluorescence_au"].mean()

    trt = base[
        (base.compound_id == compound)
        & (base.administered_conc_um == primary)
        & (base.probe_loaded == "no")
    ]
    out = []
    for _, r in trt.iterrows():
        b = r.biological_experiment_id
        if b not in veh_free.index or b not in veh_dye.index:
            continue
        denom = veh_dye[b] - veh_free[b]
        if denom == 0:
            continue
        out.append((r.fluorescence_au - veh_free[b]) / denom)
    return out


def quench_wells(ctl, compound, primary):
    """SHORTCUT: one index per individual fluorescein-standard control WELL.
    n = 7 x 3 = 21.
    """
    if primary is None:
        return []
    q = ctl[
        (ctl.control_type == "fluorescein_standard_quench")
        & (ctl.measured_quantity == "fluorescein_standard_fluorescence_au")
        & (ctl.qualifier == "measured")
    ]
    veh_exp = (
        q[q.compound_id == "VEH"]
        .groupby("biological_experiment_id")["value"]
        .mean()
    )
    trt = q[(q.compound_id == compound) & (q.administered_conc_um == primary)]
    out = []
    for _, r in trt.iterrows():
        b = r.biological_experiment_id
        if b not in veh_exp.index or veh_exp[b] == 0:
            continue
        out.append((veh_exp[b] - r.value) / veh_exp[b])
    return out


# ------------------------------------------------- evidence ids

def evidence_ids(V, compound, primary):
    if primary is None:
        return NA
    g = V[
        (V.assay_panel == "VIABILITY")
        & (V.cell_model_id == "CM_WT")
        & (V.compound_id == compound)
        & (V.administered_conc_um == primary)
        & (V.challenge_id == "CHAL_ISO")
        & (V.schedule_id == "PRE_NOWASH")
        & (V.readout_time_h_post_challenge == 24.0)
    ]
    ids = []
    for b in BIOS:
        sub = g[g.biological_experiment_id == b].sort_values("sample_id")
        if sub.empty:
            continue
        ids.append(sub.iloc[0].sample_id)
    if not ids:
        return NA
    return ";".join(ids)


# ------------------------------------------------- per compound

def analyse(compound, V, O, X, ctl, diag):
    primary, _ = select_primary_concentration(V, compound)

    if primary is None:
        # specification concentration_selection_rule.if_none_qualifies
        return {
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
        }

    e_wt, matched = select_exposure_matched(X, compound, primary)

    # --- well-level protection indices (THE SHORTCUT) ---------------------
    wt = pi_wells(V, "CM_WT", compound, primary)
    ko_p = pi_wells(V, "CM_KO_A", compound, primary)
    ko_m = pi_wells(V, "CM_KO_A", compound, matched) if matched else pd.DataFrame()
    res = pi_wells(V, "CM_KO_A_RES", compound, primary)
    ko_b = pi_wells(V, "CM_KO_B", compound, primary)

    pi_wt, wt_lo, wt_hi, n_wt = ci(wt["pi"].tolist())
    pi_ko_p, _, _, _ = ci(ko_p["pi"].tolist())
    pi_res, res_lo, res_hi, _ = ci(res["pi"].tolist())
    pi_kob, kob_lo, kob_hi, _ = ci(ko_b["pi"].tolist())
    pi_koa_lo = ci(ko_p["pi"].tolist())[1]

    if matched is not None and not ko_m.empty:
        pi_ko_m, _, _, _ = ci(ko_m["pi"].tolist())
        # SHORTCUT: pair WELL to WELL by (experiment, technical_replicate)
        merged = wt.merge(
            ko_m,
            on=["biological_experiment_id", "technical_replicate"],
            suffixes=("_wt", "_ko"),
        )
        diffs = (merged["pi_wt"] - merged["pi_ko"]).tolist()
        delta, d_lo, d_hi, n_d = ci(diffs)
    else:
        pi_ko_m = float("nan")
        delta = d_lo = d_hi = float("nan")
        n_d = 0

    # --- protection_status ------------------------------------------------
    if np.isfinite(wt_lo) and wt_lo > THETA_P:
        prot = "protected"
    elif np.isfinite(wt_hi) and wt_hi < THETA_P:
        prot = "not_protected"
    else:
        prot = "indeterminate"

    # --- nrf2_dependence_status, rules in the published order -------------
    lineage_a = bool(np.isfinite(pi_koa_lo) and pi_koa_lo > THETA_P)
    lineage_b = bool(np.isfinite(kob_lo) and kob_lo > THETA_P)
    rescue_ok = bool(np.isfinite(res_lo) and res_lo > THETA_P)

    if prot != "protected":
        nrf2 = "not_assessable"
    elif matched is None or not np.isfinite(delta):
        nrf2 = "indeterminate"
    elif lineage_a != lineage_b:
        nrf2 = "indeterminate"
    elif np.isfinite(d_lo) and d_lo > THETA_D and rescue_ok:
        nrf2 = "nrf2_dependent"
    elif np.isfinite(d_hi) and d_hi < THETA_D:
        nrf2 = "not_nrf2_dependent"
    else:
        nrf2 = "indeterminate"

    # --- interference -----------------------------------------------------
    mtt_m, mtt_lo, mtt_hi, n_mtt = ci(mtt_interference_wells(V, ctl, compound, primary))
    af_m, af_lo, af_hi, n_af = ci(autofluorescence_wells(O, compound, primary))
    qz_m, qz_lo, qz_hi, n_qz = ci(quench_wells(ctl, compound, primary))

    flags = []
    if np.isfinite(mtt_lo) and mtt_lo > THETA_I:
        flags.append("mtt")
    if (np.isfinite(af_lo) and af_lo > THETA_I) or (
        np.isfinite(qz_lo) and qz_lo > THETA_I
    ):
        flags.append("ros")
    flag_str = ";".join(flags) if flags else "none"

    diag[compound] = {
        "primary_concentration_um": primary,
        "exposure_matched_ko_concentration_um": matched,
        "n_wt_wells": n_wt,
        "n_paired_well_diffs": n_d,
        "n_mtt_control_wells": n_mtt,
        "n_autofluor_wells": n_af,
        "n_quench_wells": n_qz,
        "t_used_wt": t_quantile(n_wt) if n_wt > 1 else None,
        "lineage_A_shows_protection": lineage_a,
        "lineage_B_shows_protection": lineage_b,
        "rescue_criterion_met": rescue_ok,
        "pi_ko_b": None if not np.isfinite(pi_kob) else round(pi_kob, 6),
        "mtt_index": None if not np.isfinite(mtt_m) else round(mtt_m, 6),
        "mtt_ci": [None if not np.isfinite(mtt_lo) else round(mtt_lo, 6),
                   None if not np.isfinite(mtt_hi) else round(mtt_hi, 6)],
        "autofluor_index": None if not np.isfinite(af_m) else round(af_m, 6),
        "autofluor_ci": [None if not np.isfinite(af_lo) else round(af_lo, 6),
                         None if not np.isfinite(af_hi) else round(af_hi, 6)],
        "quench_index": None if not np.isfinite(qz_m) else round(qz_m, 6),
        "quench_ci": [None if not np.isfinite(qz_lo) else round(qz_lo, 6),
                      None if not np.isfinite(qz_hi) else round(qz_hi, 6)],
    }

    return {
        "compound_id": compound,
        "primary_concentration_um": fmt_conc(primary),
        "wt_primary_exposure_pmol_per_1e6_cells": fmt_sig(e_wt),
        "exposure_matched_ko_concentration_um": fmt_conc(matched),
        "protection_index_wt": fmt(pi_wt),
        "protection_index_wt_ci_low": fmt(wt_lo),
        "protection_index_wt_ci_high": fmt(wt_hi),
        "protection_index_ko_primary_conc": fmt(pi_ko_p),
        "protection_index_ko_exposure_matched": fmt(pi_ko_m),
        "protection_index_rescue": fmt(pi_res),
        "nrf2_dependence_contrast": fmt(delta),
        "nrf2_dependence_contrast_ci_low": fmt(d_lo),
        "nrf2_dependence_contrast_ci_high": fmt(d_hi),
        "protection_status": prot,
        "nrf2_dependence_status": nrf2,
        "interference_flags": flag_str,
        "evidence_sample_ids": evidence_ids(V, compound, primary),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    V, O, X, ctl = load(args.data)
    diag = {}
    rows = [analyse(c, V, O, X, ctl, diag) for c in COMPOUNDS]

    out = pd.DataFrame(rows, columns=HEADER)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_csv(args.out, index=False)

    print("wrote", args.out)
    print("rows:", len(out), "columns:", len(out.columns))
    print("header ok:", list(out.columns) == HEADER)
    print(json.dumps(diag, indent=2, default=str))
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
