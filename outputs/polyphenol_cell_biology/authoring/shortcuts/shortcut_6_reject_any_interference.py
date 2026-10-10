#!/usr/bin/env python3
"""
Shortcut 6: reject_any_interference

Everything is computed exactly as study_specification.json requires -- the
protection indices, the exposure matching, the paired NRF2-dependence contrast
and the interference indices.  Then ONE deliberate deviation is applied:

    for any compound whose interference_flags != 'none',
        protection_status      := 'not_protected'
        nrf2_dependence_status := 'not_assessable'

on the (flawed) reasoning that an interfering compound's data cannot be
trusted.  The specification says the opposite: interference is a statement
about a MEASUREMENT, and the primary endpoint (direct live/dead nuclei count)
is deliberately immune to redox interference.  Numeric fields are left as
correctly computed, so the override leaves the numbers contradicting the
statuses.

Usage:
  python3 shortcut_6_reject_any_interference.py --data DATA_DIR --out OUT_CSV
"""

import argparse
import json
import os

import numpy as np
import pandas as pd

BIOS = ["BIO01", "BIO02", "BIO03", "BIO04", "BIO05", "BIO06", "BIO07"]
LADDER = [1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0]
COMPOUNDS = ["PP01", "PP02", "PP03", "PP04", "PP05", "PP06", "PP07", "PP08"]
T975 = 2.446911851          # t(0.975, 6)
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


# ----------------------------------------------------------------- utilities
def t_ci(vals):
    """Student-t 95% interval on per-biological-experiment values."""
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    n = len(v)
    if n == 0:
        return (np.nan, np.nan, np.nan)
    m = v.mean()
    if n < 2:
        return (m, np.nan, np.nan)
    sd = v.std(ddof=1)
    half = T975 * sd / np.sqrt(n)
    return (m, m - half, m + half)


def fmt_num(x, dec=6):
    if x is None or not np.isfinite(x):
        return NA
    return f"{x:.{dec}f}"


def fmt_sig(x, sig=6):
    if x is None or not np.isfinite(x):
        return NA
    return f"{x:.{sig}g}"


def fmt_conc(x):
    if x is None or not np.isfinite(x):
        return NA
    return f"{float(x):g}"


# ----------------------------------------------------------------- load data
def load(data_dir):
    d = {}
    d["man"] = pd.read_csv(os.path.join(data_dir, "sample_manifest.csv"))
    d["via"] = pd.read_csv(os.path.join(data_dir, "viability_readouts.csv"))
    d["oxs"] = pd.read_csv(os.path.join(data_dir, "oxidative_stress_readouts.csv"))
    d["exp"] = pd.read_csv(os.path.join(data_dir, "exposure_measurements.csv"))
    d["ctl"] = pd.read_csv(os.path.join(data_dir, "assay_controls.csv"))
    return d


def build_viability(d):
    """Per-well live cell density in the primary (B_DOSE_RESPONSE / 24 h) panel."""
    man = d["man"]
    via = d["via"].copy()
    via = via.rename(columns={"readout_time_h_post_challenge": "rt_readout"})
    m = man[man.assay_panel == "VIABILITY"]
    j = m.merge(via, on="sample_id", how="inner")
    j["live_density"] = j["live_nuclei_count"] / j["imaged_area_fraction"] / 1000.0
    return j


# --------------------------------------------------------- primary endpoint
def lbar_table(viab):
    """mean live_density per (cell_model, compound, conc, bio, challenge, schedule)."""
    sub = viab[(viab.panel_id == "B_DOSE_RESPONSE")
               & (viab.readout_time_h_post_challenge == 24.0)]
    g = sub.groupby(["cell_model_id", "compound_id", "administered_conc_um",
                     "biological_experiment_id", "challenge_id", "schedule_id"],
                    dropna=False)["live_density"].mean()
    return g.to_dict()


def pi_per_bio(lb, model, compound, conc, schedule="PRE_NOWASH"):
    """Per-biological-experiment protection index; dict bio -> PI."""
    out = {}
    for b in BIOS:
        try:
            treat = lb[(model, compound, float(conc), b, "CHAL_ISO", schedule)]
            veh_iso = lb[(model, "VEH", 0.0, b, "CHAL_ISO", schedule)]
            veh_none = lb[(model, "VEH", 0.0, b, "CHAL_NONE", schedule)]
        except KeyError:
            continue
        denom = veh_none - veh_iso
        if not np.isfinite(denom) or denom == 0:
            continue
        out[b] = (treat - veh_iso) / denom
    return out


# ------------------------------------------------- concentration selection
def primary_concentration(lb, compound):
    """Highest tolerated concentration: ratio of means >= 0.85 in CM_WT, CHAL_NONE."""
    veh = [lb.get(("CM_WT", "VEH", 0.0, b, "CHAL_NONE", "PRE_NOWASH"))
           for b in BIOS]
    veh = [x for x in veh if x is not None and np.isfinite(x)]
    if not veh:
        return None
    veh_mean = float(np.mean(veh))
    best = None
    for dcon in LADDER:
        vals = [lb.get(("CM_WT", compound, dcon, b, "CHAL_NONE", "PRE_NOWASH"))
                for b in BIOS]
        vals = [x for x in vals if x is not None and np.isfinite(x)]
        if not vals:
            continue
        if float(np.mean(vals)) / veh_mean >= 0.85:
            best = dcon
    return best


# ------------------------------------------------------- exposure matching
def exposure_table(d):
    """
    (cell_model, compound, conc, bio) -> mean over 'measured' injection replicates
    of intracellular exposure (pmol / 1e6 cells), END_PRETREAT_NOWASH cell lysate.
    """
    man = d["man"]
    ex = d["exp"]
    ex = ex[(ex.matrix == "cell_lysate")
            & (ex.sampling_condition == "END_PRETREAT_NOWASH")]
    keep = man[["sample_id", "cell_model_id", "administered_conc_um",
                "biological_experiment_id"]]
    j = ex.merge(keep, on="sample_id", how="inner")
    j = j[j.qualifier == "measured"].copy()
    j["expo"] = j["measured_value"] / j["cell_equivalents_1e6"]
    # average injection replicates within a sample first, then within a bio exp
    per_sample = j.groupby(["cell_model_id", "compound_id", "administered_conc_um",
                            "biological_experiment_id", "sample_id"])["expo"].mean()
    per_bio = per_sample.groupby(level=[0, 1, 2, 3]).mean()
    return per_bio.to_dict()


def e_wt(expo, compound, conc):
    vals = [expo.get(("CM_WT", compound, float(conc), b)) for b in BIOS]
    vals = [v for v in vals if v is not None and np.isfinite(v)]
    if not vals:
        return None
    return float(np.mean(vals))


def matched_ko_conc(expo, compound, ewt):
    if ewt is None or not np.isfinite(ewt) or ewt == 0:
        return None
    cands = []
    for dcon in LADDER:
        vals = [expo.get(("CM_KO_A", compound, dcon, b)) for b in BIOS]
        vals = [v for v in vals if v is not None and np.isfinite(v)]
        if len(vals) < 4:          # censored candidate: cannot qualify
            continue
        eko = float(np.mean(vals))
        ratio = eko / ewt
        if 0.70 <= ratio <= 1.428571428571:
            cands.append((abs(np.log(ratio)), dcon))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[1]))
    return cands[0][1]


# ------------------------------------------------------------ interference
def mtt_index(d, lb_mtt_wt, compound, conc):
    """Per-bio cell-free MTT interference index."""
    ctl = d["ctl"]
    cf = ctl[(ctl.control_type == "cell_free_mtt") & (ctl.challenge_id == "CHAL_NONE")]

    def sig(sel):
        a = sel[sel.measured_quantity == "mtt_absorbance_570nm"]["value"].mean()
        b = sel[sel.measured_quantity == "mtt_absorbance_630nm"]["value"].mean()
        return a - b

    out = {}
    for b in BIOS:
        cb = cf[cf.biological_experiment_id == b]
        cmp_sel = cb[(cb.compound_id == compound)
                     & (cb.administered_conc_um == float(conc))]
        veh_sel = cb[cb.compound_id == "VEH"]
        if cmp_sel.empty or veh_sel.empty:
            continue
        s_cmp = sig(cmp_sel)
        s_veh = sig(veh_sel)
        cell_veh = lb_mtt_wt.get(b)
        if cell_veh is None or not np.isfinite(cell_veh):
            continue
        denom = cell_veh - s_veh
        if not np.isfinite(denom) or denom == 0:
            continue
        out[b] = (s_cmp - s_veh) / denom
    return out


def mtt_cell_vehicle(viab):
    """mean mtt_signal of vehicle CM_WT, CHAL_NONE, PRE_NOWASH, panel B, 24 h, per bio."""
    sub = viab[(viab.panel_id == "B_DOSE_RESPONSE")
               & (viab.readout_time_h_post_challenge == 24.0)
               & (viab.cell_model_id == "CM_WT")
               & (viab.compound_id == "VEH")
               & (viab.challenge_id == "CHAL_NONE")
               & (viab.schedule_id == "PRE_NOWASH")].copy()
    sub["mtt_signal"] = sub["mtt_absorbance_570nm"] - sub["mtt_absorbance_630nm"]
    return sub.groupby("biological_experiment_id")["mtt_signal"].mean().to_dict()


def autofluor_index(d, compound, conc):
    """Per-bio probe autofluorescence index from oxidative_stress_readouts."""
    man = d["man"]
    oxs = d["oxs"][["sample_id", "fluorescence_au"]]
    sel = man[(man.assay_panel == "OXIDATIVE_STRESS")
              & (man.cell_model_id == "CM_WT")
              & (man.challenge_id == "CHAL_ISO")
              & (man.schedule_id == "PRE_NOWASH")]
    j = sel.merge(oxs, on="sample_id", how="inner")
    out = {}
    for b in BIOS:
        jb = j[j.biological_experiment_id == b]
        cmp_free = jb[(jb.compound_id == compound)
                      & (jb.administered_conc_um == float(conc))
                      & (jb.probe_loaded == "no")]["fluorescence_au"]
        veh_free = jb[(jb.compound_id == "VEH") & (jb.probe_loaded == "no")]["fluorescence_au"]
        veh_load = jb[(jb.compound_id == "VEH") & (jb.probe_loaded == "yes")]["fluorescence_au"]
        if cmp_free.empty or veh_free.empty or veh_load.empty:
            continue
        denom = veh_load.mean() - veh_free.mean()
        if not np.isfinite(denom) or denom == 0:
            continue
        out[b] = (cmp_free.mean() - veh_free.mean()) / denom
    return out


def quench_index(d, compound, conc):
    ctl = d["ctl"]
    q = ctl[ctl.control_type == "fluorescein_standard_quench"]
    out = {}
    for b in BIOS:
        qb = q[q.biological_experiment_id == b]
        veh = qb[qb.compound_id == "VEH"]["value"]
        cmp_ = qb[(qb.compound_id == compound)
                  & (qb.administered_conc_um == float(conc))]["value"]
        if veh.empty or cmp_.empty:
            continue
        vm = veh.mean()
        if not np.isfinite(vm) or vm == 0:
            continue
        out[b] = (vm - cmp_.mean()) / vm
    return out


# -------------------------------------------------------------- evidence ids
def evidence_ids(d, compound, conc):
    man = d["man"]
    sel = man[(man.assay_panel == "VIABILITY")
              & (man.cell_model_id == "CM_WT")
              & (man.compound_id == compound)
              & (man.administered_conc_um == float(conc))
              & (man.challenge_id == "CHAL_ISO")
              & (man.schedule_id == "PRE_NOWASH")
              & (man.readout_time_h_post_challenge == 24.0)]
    ids = []
    for b in BIOS:
        sb = sel[sel.biological_experiment_id == b].sort_values("sample_id")
        if len(sb):
            ids.append(sb.iloc[0]["sample_id"])
    return ";".join(ids) if len(ids) == len(BIOS) else NA


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    d = load(args.data)
    viab = build_viability(d)
    lb = lbar_table(viab)
    expo = exposure_table(d)
    mtt_cell_veh = mtt_cell_vehicle(viab)

    rows = []
    notes = []

    for c in COMPOUNDS:
        conc = primary_concentration(lb, c)

        if conc is None:
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

        # ---- protection indices (correct)
        pi_wt = pi_per_bio(lb, "CM_WT", c, conc)
        pi_ko_prim = pi_per_bio(lb, "CM_KO_A", c, conc)
        pi_kob_prim = pi_per_bio(lb, "CM_KO_B", c, conc)
        pi_res = pi_per_bio(lb, "CM_KO_A_RES", c, conc)

        wt_m, wt_lo, wt_hi = t_ci(list(pi_wt.values()))
        ko_m, ko_lo, _ = t_ci(list(pi_ko_prim.values()))
        res_m, res_lo, _ = t_ci(list(pi_res.values()))
        kob_m, kob_lo, _ = t_ci(list(pi_kob_prim.values()))

        # ---- exposure matching (correct)
        ewt = e_wt(expo, c, conc)
        ko_conc = matched_ko_conc(expo, c, ewt)

        if ko_conc is None:
            pi_ko_em = {}
            em_m = np.nan
            delta_m = delta_lo = delta_hi = np.nan
        else:
            pi_ko_em = pi_per_bio(lb, "CM_KO_A", c, ko_conc)
            em_m, _, _ = t_ci(list(pi_ko_em.values()))
            paired = [pi_wt[b] - pi_ko_em[b] for b in BIOS
                      if b in pi_wt and b in pi_ko_em]
            delta_m, delta_lo, delta_hi = t_ci(paired)

        # ---- protection_status (correct)
        if wt_lo > THETA_P:
            prot = "protected"
        elif wt_hi < THETA_P:
            prot = "not_protected"
        else:
            prot = "indeterminate"

        # ---- nrf2_dependence_status (correct, spec order)
        if prot != "protected":
            nrf2 = "not_assessable"
        elif ko_conc is None:
            nrf2 = "indeterminate"
        elif (bool(np.isfinite(ko_lo) and ko_lo > THETA_P)
              != bool(np.isfinite(kob_lo) and kob_lo > THETA_P)):
            # independent-lineage disagreement on the single boolean
            nrf2 = "indeterminate"
        elif delta_lo > THETA_D and res_lo > THETA_P:
            nrf2 = "nrf2_dependent"
        elif np.isfinite(delta_hi) and delta_hi < THETA_D:
            nrf2 = "not_nrf2_dependent"
        else:
            nrf2 = "indeterminate"

        # ---- interference flags (correct)
        mi = mtt_index(d, mtt_cell_veh, c, conc)
        af = autofluor_index(d, c, conc)
        qi = quench_index(d, c, conc)
        _, mi_lo, _ = t_ci(list(mi.values()))
        _, af_lo, _ = t_ci(list(af.values()))
        _, qi_lo, _ = t_ci(list(qi.values()))
        flags = []
        if np.isfinite(mi_lo) and mi_lo > THETA_I:
            flags.append("mtt")
        if (np.isfinite(af_lo) and af_lo > THETA_I) or (np.isfinite(qi_lo) and qi_lo > THETA_I):
            flags.append("ros")
        iflags = ";".join(flags) if flags else "none"

        # =============== THE DELIBERATE SHORTCUT ===============
        # Reject every compound that shows any assay interference.
        if iflags != "none":
            prot = "not_protected"
            nrf2 = "not_assessable"
            notes.append(f"{c}: overridden by shortcut (flags={iflags})")
        # =======================================================

        rows.append({
            "compound_id": c,
            "primary_concentration_um": fmt_conc(conc),
            "wt_primary_exposure_pmol_per_1e6_cells": fmt_sig(ewt),
            "exposure_matched_ko_concentration_um": fmt_conc(ko_conc),
            "protection_index_wt": fmt_num(wt_m),
            "protection_index_wt_ci_low": fmt_num(wt_lo),
            "protection_index_wt_ci_high": fmt_num(wt_hi),
            "protection_index_ko_primary_conc": fmt_num(ko_m),
            "protection_index_ko_exposure_matched": fmt_num(em_m),
            "protection_index_rescue": fmt_num(res_m),
            "nrf2_dependence_contrast": fmt_num(delta_m),
            "nrf2_dependence_contrast_ci_low": fmt_num(delta_lo),
            "nrf2_dependence_contrast_ci_high": fmt_num(delta_hi),
            "protection_status": prot,
            "nrf2_dependence_status": nrf2,
            "interference_flags": iflags,
            "evidence_sample_ids": evidence_ids(d, c, conc),
        })

    out = pd.DataFrame(rows, columns=HEADER)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_csv(args.out, index=False)

    print(json.dumps({"rows": len(out), "header_ok": list(out.columns) == HEADER,
                      "overrides": notes}, indent=2))
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
