#!/usr/bin/env python3
"""
SHORTCUT 4 -- "ignore_exposure"

DELIBERATELY LIMITED analysis of the polyphenol_cell_biology benchmark.

Everything follows study_specification.json EXCEPT the exposure handling:

  * exposure_measurements.csv is NEVER read.
  * The analysis assumes that the same ADMINISTERED concentration implies the
    same intracellular EXPOSURE in every cell model.  The NRF2-dependence
    contrast is therefore computed as
        Delta = PI(CM_WT, primary conc) - PI(CM_KO_A, SAME primary conc)
    paired by biological experiment.
  * exposure_matched_ko_concentration_um is reported as the primary
    concentration for every compound (never NA).
  * protection_index_ko_exposure_matched is reported as the knockout
    protection index at that same administered concentration.
  * wt_primary_exposure_pmol_per_1e6_cells is NA for every compound, because
    no exposure data is used at all (the quantity is genuinely undefined under
    this method).
  * Consequently the 'indeterminate -- no exposure overlap' branch of
    classification.nrf2_dependence_status can never be taken.

No other deviation from the specification is intended.
"""

import argparse
import math
import os

import numpy as np
import pandas as pd

LADDER = [1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0]
BIOS = ["BIO01", "BIO02", "BIO03", "BIO04", "BIO05", "BIO06", "BIO07"]
COMPOUNDS = ["PP01", "PP02", "PP03", "PP04", "PP05", "PP06", "PP07", "PP08"]

T_QUANTILES = {
    1: 12.706204736, 2: 4.30265273, 3: 3.182446305, 4: 2.776445105,
    5: 2.570581836, 6: 2.446911851, 7: 2.364624252, 8: 2.306004135,
    9: 2.262157163,
}

THETA_P = 0.15
THETA_D = 0.15
THETA_I = 0.10
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


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def t_interval(values):
    """Student-t 95% interval on per-biological-experiment values."""
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    n = len(v)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    mean = float(v.mean())
    if n == 1:
        return (mean, float("nan"), float("nan"))
    sd = float(v.std(ddof=1))
    tq = T_QUANTILES[n - 1]
    half = tq * sd / math.sqrt(n)
    return (mean, mean - half, mean + half)


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


def fmt_conc(x):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return NA
    return f"{float(x):.1f}"


# --------------------------------------------------------------------------
# load
# --------------------------------------------------------------------------

def load(data_dir):
    sm = pd.read_csv(os.path.join(data_dir, "sample_manifest.csv"), low_memory=False)
    vr = pd.read_csv(os.path.join(data_dir, "viability_readouts.csv"), low_memory=False)
    osr = pd.read_csv(os.path.join(data_dir, "oxidative_stress_readouts.csv"), low_memory=False)
    ac = pd.read_csv(os.path.join(data_dir, "assay_controls.csv"), low_memory=False)
    # NOTE: exposure_measurements.csv is deliberately NOT read (shortcut mandate).
    return sm, vr, osr, ac


# --------------------------------------------------------------------------
# viability / protection index machinery
# --------------------------------------------------------------------------

def build_viability(sm, vr):
    """One table of B_DOSE_RESPONSE viability wells with the primary endpoint."""
    cols = [
        "sample_id", "biological_experiment_id", "panel_id", "assay_panel",
        "cell_model_id", "compound_id", "administered_conc_um", "schedule_id",
        "challenge_id", "readout_time_h_post_challenge",
    ]
    m = sm.loc[
        (sm.assay_panel == "VIABILITY") & (sm.panel_id == "B_DOSE_RESPONSE"), cols
    ]
    v = vr[["sample_id", "live_nuclei_count", "imaged_area_fraction"]]
    d = m.merge(v, on="sample_id", how="inner")
    d = d[d.readout_time_h_post_challenge == 24.0].copy()
    # primary endpoint
    d["live_density"] = d.live_nuclei_count / d.imaged_area_fraction / 1000.0
    return d


def lbar_table(viab):
    """Lbar: mean live_cell_density over technical replicates of a condition."""
    g = viab.groupby(
        ["cell_model_id", "compound_id", "administered_conc_um", "schedule_id",
         "challenge_id", "biological_experiment_id"],
        dropna=False,
    )["live_density"].mean()
    return g.to_dict()


def pi_per_bio(lb, cell_model, compound, conc, schedule="PRE_NOWASH"):
    """Per-biological-experiment protection index, CHAL_ISO primary condition."""
    out = {}
    for b in BIOS:
        num_t = lb.get((cell_model, compound, conc, schedule, "CHAL_ISO", b))
        veh_iso = lb.get((cell_model, "VEH", 0.0, schedule, "CHAL_ISO", b))
        veh_none = lb.get((cell_model, "VEH", 0.0, schedule, "CHAL_NONE", b))
        if num_t is None or veh_iso is None or veh_none is None:
            continue
        denom = veh_none - veh_iso
        if denom == 0:
            continue
        out[b] = (num_t - veh_iso) / denom
    return out


def select_primary_concentration(viab, compound):
    """
    concentration_selection_rule: RATIO OF MEANS.
    tox_ratio(d) = mean_b Lbar(CM_WT, c, d, b, CHAL_NONE, PRE_NOWASH)
                 / mean_b Lbar(CM_WT, VEH, 0, b, CHAL_NONE, PRE_NOWASH)
    Highest tolerated (>= 0.85) concentration on the ladder.
    """
    wt = viab[
        (viab.cell_model_id == "CM_WT")
        & (viab.schedule_id == "PRE_NOWASH")
        & (viab.challenge_id == "CHAL_NONE")
    ]
    veh = wt[(wt.compound_id == "VEH") & (wt.administered_conc_um == 0.0)]
    veh_per_bio = veh.groupby("biological_experiment_id")["live_density"].mean()
    veh_mean = float(veh_per_bio.mean())

    chosen = None
    for d in LADDER:
        sub = wt[(wt.compound_id == compound) & (wt.administered_conc_um == d)]
        if sub.empty:
            continue
        per_bio = sub.groupby("biological_experiment_id")["live_density"].mean()
        ratio = float(per_bio.mean()) / veh_mean
        if ratio >= 0.85:
            chosen = d
    return chosen


# --------------------------------------------------------------------------
# interference
# --------------------------------------------------------------------------

def mtt_index(ac, viab, compound, primary_conc):
    cf = ac[(ac.control_type == "cell_free_mtt") & (ac.challenge_id == "CHAL_NONE")]
    key = ["compound_id", "administered_conc_um", "biological_experiment_id",
           "plate_id", "technical_replicate"]
    piv = cf.pivot_table(index=key, columns="measured_quantity", values="value",
                         aggfunc="mean").reset_index()
    piv["mtt_signal"] = piv["mtt_absorbance_570nm"] - piv["mtt_absorbance_630nm"]

    cmp_rows = piv[(piv.compound_id == compound) & (piv.administered_conc_um == primary_conc)]
    veh_rows = piv[(piv.compound_id == "VEH") & (piv.administered_conc_um == 0.0)]
    cmp_b = cmp_rows.groupby("biological_experiment_id")["mtt_signal"].mean()
    veh_b = veh_rows.groupby("biological_experiment_id")["mtt_signal"].mean()

    cellveh = viab[
        (viab.cell_model_id == "CM_WT") & (viab.compound_id == "VEH")
        & (viab.administered_conc_um == 0.0) & (viab.challenge_id == "CHAL_NONE")
        & (viab.schedule_id == "PRE_NOWASH")
    ]
    cell_b = cellveh.groupby("biological_experiment_id")["mtt_signal_cells"].mean()

    vals = []
    for b in BIOS:
        if b in cmp_b.index and b in veh_b.index and b in cell_b.index:
            denom = cell_b[b] - veh_b[b]
            if denom != 0:
                vals.append((cmp_b[b] - veh_b[b]) / denom)
    return t_interval(vals)


def probe_autofluorescence_index(sm, osr, compound, primary_conc):
    cols = ["sample_id", "biological_experiment_id", "cell_model_id", "compound_id",
            "administered_conc_um", "schedule_id", "challenge_id", "probe_loaded",
            "panel_id", "assay_panel"]
    m = sm.loc[sm.assay_panel == "OXIDATIVE_STRESS", cols]
    d = m.merge(osr[["sample_id", "fluorescence_au"]], on="sample_id", how="inner")
    d = d[(d.cell_model_id == "CM_WT") & (d.challenge_id == "CHAL_ISO")
          & (d.schedule_id == "PRE_NOWASH")]

    cmp_free = d[(d.compound_id == compound) & (d.administered_conc_um == primary_conc)
                 & (d.probe_loaded == "no")].groupby("biological_experiment_id")["fluorescence_au"].mean()
    veh_free = d[(d.compound_id == "VEH") & (d.administered_conc_um == 0.0)
                 & (d.probe_loaded == "no")].groupby("biological_experiment_id")["fluorescence_au"].mean()
    veh_dye = d[(d.compound_id == "VEH") & (d.administered_conc_um == 0.0)
                & (d.probe_loaded == "yes")].groupby("biological_experiment_id")["fluorescence_au"].mean()

    vals = []
    for b in BIOS:
        if b in cmp_free.index and b in veh_free.index and b in veh_dye.index:
            denom = veh_dye[b] - veh_free[b]
            if denom != 0:
                vals.append((cmp_free[b] - veh_free[b]) / denom)
    return t_interval(vals)


def probe_quench_index(ac, compound, primary_conc):
    q = ac[ac.control_type == "fluorescein_standard_quench"]
    cmp_b = q[(q.compound_id == compound) & (q.administered_conc_um == primary_conc)
              ].groupby("biological_experiment_id")["value"].mean()
    veh_b = q[(q.compound_id == "VEH") & (q.administered_conc_um == 0.0)
              ].groupby("biological_experiment_id")["value"].mean()
    vals = []
    for b in BIOS:
        if b in cmp_b.index and b in veh_b.index and veh_b[b] != 0:
            vals.append((veh_b[b] - cmp_b[b]) / veh_b[b])
    return t_interval(vals)


# --------------------------------------------------------------------------
# evidence
# --------------------------------------------------------------------------

def evidence_ids(sm, compound, primary_conc):
    sel = sm[
        (sm.assay_panel == "VIABILITY")
        & (sm.cell_model_id == "CM_WT")
        & (sm.compound_id == compound)
        & (sm.administered_conc_um == primary_conc)
        & (sm.challenge_id == "CHAL_ISO")
        & (sm.schedule_id == "PRE_NOWASH")
        & (sm.readout_time_h_post_challenge == 24.0)
    ]
    ids = []
    for b in BIOS:
        sub = sel[sel.biological_experiment_id == b].sort_values("sample_id")
        if not sub.empty:
            ids.append(str(sub.iloc[0]["sample_id"]))
    return ";".join(ids) if ids else NA


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sm, vr, osr, ac = load(args.data)

    viab = build_viability(sm, vr)
    # MTT signal on the cell-containing wells (needed for the MTT interference denominator)
    vr2 = vr.set_index("sample_id")
    viab["mtt_signal_cells"] = (
        viab.sample_id.map(vr2["mtt_absorbance_570nm"])
        - viab.sample_id.map(vr2["mtt_absorbance_630nm"])
    )
    lb = lbar_table(viab)

    rows = []
    for c in COMPOUNDS:
        primary = select_primary_concentration(viab, c)

        if primary is None:
            # if_none_qualifies branch (not taken by this dataset)
            rows.append({
                "compound_id": c,
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

        # ---- protection indices, per biological experiment ----
        pi_wt = pi_per_bio(lb, "CM_WT", c, primary)
        pi_koa = pi_per_bio(lb, "CM_KO_A", c, primary)
        pi_kob = pi_per_bio(lb, "CM_KO_B", c, primary)
        pi_res = pi_per_bio(lb, "CM_KO_A_RES", c, primary)

        wt_m, wt_lo, wt_hi = t_interval(list(pi_wt.values()))
        koa_m, _, _ = t_interval(list(pi_koa.values()))
        res_m, res_lo, res_hi = t_interval(list(pi_res.values()))
        kob_m, kob_lo, kob_hi = t_interval(list(pi_kob.values()))
        koa_m2, koa_lo, koa_hi = t_interval(list(pi_koa.values()))

        # ---- SHORTCUT: contrast at the SAME administered concentration ----
        shared = [b for b in BIOS if b in pi_wt and b in pi_koa]
        diffs = [pi_wt[b] - pi_koa[b] for b in shared]
        d_m, d_lo, d_hi = t_interval(diffs)

        # ---- protection_status ----
        if wt_lo > THETA_P:
            protection_status = "protected"
        elif wt_hi < THETA_P:
            protection_status = "not_protected"
        else:
            protection_status = "indeterminate"

        # ---- nrf2_dependence_status (spec order; the no-overlap branch
        #      can never fire under this shortcut) ----
        if protection_status != "protected":
            nrf2_status = "not_assessable"
        else:
            koa_shows = koa_lo > THETA_P
            kob_shows = kob_lo > THETA_P
            if koa_shows != kob_shows:
                nrf2_status = "indeterminate"
            elif d_lo > THETA_D and res_lo > THETA_P:
                nrf2_status = "nrf2_dependent"
            elif d_hi < THETA_D:
                nrf2_status = "not_nrf2_dependent"
            else:
                nrf2_status = "indeterminate"

        # ---- interference ----
        _, mtt_lo, _ = mtt_index(ac, viab, c, primary)
        _, auto_lo, _ = probe_autofluorescence_index(sm, osr, c, primary)
        _, quench_lo, _ = probe_quench_index(ac, c, primary)
        flags = []
        if np.isfinite(mtt_lo) and mtt_lo > THETA_I:
            flags.append("mtt")
        if (np.isfinite(auto_lo) and auto_lo > THETA_I) or \
           (np.isfinite(quench_lo) and quench_lo > THETA_I):
            flags.append("ros")
        interference = ";".join(flags) if flags else "none"

        rows.append({
            "compound_id": c,
            "primary_concentration_um": fmt_conc(primary),
            # SHORTCUT: exposure never read -> genuinely undefined here
            "wt_primary_exposure_pmol_per_1e6_cells": NA,
            # SHORTCUT: assumed matched at the same administered concentration
            "exposure_matched_ko_concentration_um": fmt_conc(primary),
            "protection_index_wt": fmt(wt_m),
            "protection_index_wt_ci_low": fmt(wt_lo),
            "protection_index_wt_ci_high": fmt(wt_hi),
            "protection_index_ko_primary_conc": fmt(koa_m),
            # SHORTCUT: identical to the unconditioned knockout value
            "protection_index_ko_exposure_matched": fmt(koa_m),
            "protection_index_rescue": fmt(res_m),
            "nrf2_dependence_contrast": fmt(d_m),
            "nrf2_dependence_contrast_ci_low": fmt(d_lo),
            "nrf2_dependence_contrast_ci_high": fmt(d_hi),
            "protection_status": protection_status,
            "nrf2_dependence_status": nrf2_status,
            "interference_flags": interference,
            "evidence_sample_ids": evidence_ids(sm, c, primary),
        })

    out = pd.DataFrame(rows, columns=HEADER)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_csv(args.out, index=False)
    print(out.to_string(index=False))
    print(f"\nwrote {len(out)} rows to {args.out}")


if __name__ == "__main__":
    main()
