#!/usr/bin/env python3
"""
Independent second implementation of the polyphenol_cell_biology evaluation contract.

Written from study_specification.json + output_schema.json + data_dictionary.csv only.
No generator, private parameter file or reference solver was consulted.

Design note: every quantity that the specification states as data (the concentration
ladder, the compound list, the Student-t table, the classification thresholds, the
primary condition, the NA token, the set of biological experiments) is READ FROM
study_specification.json / output_schema.json at run time rather than hard-coded, so
the implementation follows the contract rather than a snapshot of it. The handful of
numbers that the specification states only in prose (the 0.85 tolerance criterion, the
exposure window 0.70 .. 1.428571428571, the 3-experiment censoring threshold) are
named constants below, each quoting the sentence it comes from.

Usage:
    python3 independent_analysis.py --data <data_dir> --out <results.csv>
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants stated only in the specification's prose
# ---------------------------------------------------------------------------

# concentration_selection_rule.criterion:
#   "A concentration is tolerated if tox_ratio >= 0.85."
TOX_RATIO_MIN = 0.85

# exposure_matching_rule.qualifying_window:
#   "A concentration d qualifies if 0.70 <= E_KO(d) / E_WT <= 1.428571428571"
EXPO_WINDOW_LO = 0.70
EXPO_WINDOW_HI = 1.428571428571

# exposure_matching_rule.aggregation:
#   "A concentration is treated as CENSORED ... if fewer than 3 of the ...
#    biological experiments yield a measured value."
EXPO_MIN_MEASURED_BIOS = 3

PRIMARY_PANEL = "B_DOSE_RESPONSE"
WT = "CM_WT"
KO_A = "CM_KO_A"
KO_A_RES = "CM_KO_A_RES"
KO_B = "CM_KO_B"

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


class Contract:
    """The disclosed contract, read from the two JSON files."""

    def __init__(self, data_dir: str):
        with open(os.path.join(data_dir, "study_specification.json")) as fh:
            spec = json.load(fh)
        with open(os.path.join(data_dir, "output_schema.json")) as fh:
            schema = json.load(fh)
        self.spec = spec
        self.schema = schema

        ed = spec["experimental_design"]
        self.ladder = [float(x) for x in ed["concentration_ladder_um"]]
        self.bios = list(ed["replication"]["biological_experiments"])
        self.n_bio_expected = int(ed["replication"]["n_biological_experiments"])

        unc = spec["uncertainty_convention"]
        self.t_table = {int(k): float(v)
                        for k, v in unc["t_quantiles_two_sided_95pct"].items()}
        self.t_graded = float(unc["t_quantile_for_graded_quantities"])

        pc = spec["primary_condition"]
        self.primary_cell_model = pc["cell_model_id"]
        self.primary_challenge = pc["challenge_id"]
        self.primary_schedule = pc["schedule_id"]
        self.primary_readout_h = float(pc["readout_time_h_post_challenge"])
        self.primary_panel = pc.get("panel_id", PRIMARY_PANEL)

        cls = spec["classification"]
        self.theta_p = float(cls["protection_status"]["threshold_theta_P"])
        self.theta_d = float(cls["nrf2_dependence_status"]["threshold_theta_D"])
        self.theta_interference = float(cls["interference_flags"]["threshold"])

        self.na = spec["na_convention"]["token"]
        self.compounds = list(schema["format"]["required_compounds"])
        self.row_count = int(schema["format"]["row_count"])

        # self-consistency: the tabulated quantile for the graded quantities must be
        # the one at dof = n - 1 for the declared number of biological experiments.
        expect = self.t_table.get(self.n_bio_expected - 1)
        if expect is None or abs(expect - self.t_graded) > 1e-9:
            print(
                f"WARNING: spec t_quantile_for_graded_quantities={self.t_graded} "
                f"is not the table entry for dof={self.n_bio_expected - 1} "
                f"({expect}); using the table indexed by the number of "
                f"biological experiments actually contributing.",
                file=sys.stderr,
            )

    def t_quantile(self, n: int) -> float:
        dof = n - 1
        if dof not in self.t_table:
            raise ValueError(
                f"no tabulated two-sided 95% t quantile for dof={dof} "
                f"(table covers {sorted(self.t_table)})"
            )
        return self.t_table[dof]

    def t_summary(self, values) -> tuple[float, float, float, int]:
        """mean, ci_low, ci_high, n.

        uncertainty_convention.formula:
            CI = mean +/- t(0.975, n-1) * SD / sqrt(n)
        with SD the sample standard deviation (ddof = n-1) of the
        per-biological-experiment values and n the number of biological
        experiments contributing.
        """
        v = np.asarray(pd.Series(values, dtype="float64").dropna(), dtype=float)
        n = int(v.size)
        if n == 0:
            return float("nan"), float("nan"), float("nan"), 0
        mean = float(v.mean())
        if n == 1:
            return mean, float("nan"), float("nan"), 1
        half = self.t_quantile(n) * float(v.std(ddof=1)) / math.sqrt(n)
        return mean, mean - half, mean + half, n


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load(data_dir: str) -> dict[str, pd.DataFrame]:
    def rd(name):
        return pd.read_csv(os.path.join(data_dir, name))

    return {
        "manifest": rd("sample_manifest.csv"),
        "viability": rd("viability_readouts.csv"),
        "oxidative": rd("oxidative_stress_readouts.csv"),
        "exposure": rd("exposure_measurements.csv"),
        "controls": rd("assay_controls.csv"),
        "compounds": rd("compounds.csv"),
        "cell_models": rd("cell_models.csv"),
    }


# ---------------------------------------------------------------------------
# Primary endpoint: per-condition, per-biological-experiment Lbar
# ---------------------------------------------------------------------------

LBAR_GROUP = [
    "cell_model_id",
    "compound_id",
    "administered_conc_um",
    "challenge_id",
    "biological_experiment_id",
]


def build_lbar(ct: Contract, manifest: pd.DataFrame,
               viability: pd.DataFrame) -> pd.DataFrame:
    """Lbar: the arithmetic mean of live_cell_density_1e3_per_well over the
    technical replicate wells of a condition, within one biological experiment,
    restricted to the primary panel / schedule / readout time.

    The matched mean mtt_signal of the same wells is carried along; it supplies the
    cell-based denominator of the MTT interference index.
    """
    v = viability.copy()
    v["live_cell_density_1e3_per_well"] = (
        v["live_nuclei_count"] / v["imaged_area_fraction"] / 1000.0
    )
    v["mtt_signal"] = v["mtt_absorbance_570nm"] - v["mtt_absorbance_630nm"]

    df = manifest.merge(
        v[["sample_id", "live_cell_density_1e3_per_well", "mtt_signal"]],
        on="sample_id",
        how="inner",
        validate="one_to_one",
    )
    df = df[
        (df["panel_id"] == ct.primary_panel)
        & (df["schedule_id"] == ct.primary_schedule)
        & (df["readout_time_h_post_challenge"] == ct.primary_readout_h)
    ]
    return df.groupby(LBAR_GROUP, as_index=False).agg(
        Lbar=("live_cell_density_1e3_per_well", "mean"),
        mtt=("mtt_signal", "mean"),
        n_wells=("sample_id", "size"),
    )


def build_pi(ct: Contract, lbar: pd.DataFrame) -> pd.DataFrame:
    """Per-biological-experiment protection index, for every
    (cell model, compound, concentration) under the challenge condition:

        PI = (Lbar(g,c,d,b,ISO) - Lbar(g,VEH,0,b,ISO))
             / (Lbar(g,VEH,0,b,NONE) - Lbar(g,VEH,0,b,ISO))

    All three terms come from the same cell model, biological experiment, schedule
    and readout time (the schedule/readout restriction is already applied in
    build_lbar). Vehicle terms use compound_id 'VEH' and administered_conc_um 0.
    """
    key = ["cell_model_id", "biological_experiment_id"]
    is_veh = (lbar["compound_id"] == "VEH") & (lbar["administered_conc_um"] == 0.0)

    veh_iso = lbar[is_veh & (lbar["challenge_id"] == ct.primary_challenge)][
        key + ["Lbar"]
    ].rename(columns={"Lbar": "L_veh_iso"})
    veh_none = lbar[is_veh & (lbar["challenge_id"] == "CHAL_NONE")][
        key + ["Lbar"]
    ].rename(columns={"Lbar": "L_veh_none"})

    treated = lbar[
        (lbar["compound_id"] != "VEH")
        & (lbar["challenge_id"] == ct.primary_challenge)
    ].copy()
    treated = treated.merge(veh_iso, on=key, how="left", validate="many_to_one")
    treated = treated.merge(veh_none, on=key, how="left", validate="many_to_one")

    treated["pi"] = (treated["Lbar"] - treated["L_veh_iso"]) / (
        treated["L_veh_none"] - treated["L_veh_iso"]
    )
    return treated[
        [
            "cell_model_id",
            "compound_id",
            "administered_conc_um",
            "biological_experiment_id",
            "pi",
        ]
    ]


def pi_series(pi: pd.DataFrame, cell_model: str, compound: str, conc) -> pd.Series:
    """Per-biological-experiment PI values, indexed by biological_experiment_id."""
    if conc is None or not np.isfinite(float(conc)):
        return pd.Series(dtype="float64")
    sel = pi[
        (pi["cell_model_id"] == cell_model)
        & (pi["compound_id"] == compound)
        & (pi["administered_conc_um"] == float(conc))
    ]
    return sel.set_index("biological_experiment_id")["pi"].sort_index()


# ---------------------------------------------------------------------------
# concentration_selection_rule
# ---------------------------------------------------------------------------

def select_primary_concentration(ct: Contract, lbar: pd.DataFrame, compound: str):
    """Highest tolerated concentration in wild-type cells.

        tox_ratio(c,d) = mean_b Lbar(CM_WT,c,d,b,CHAL_NONE,PRE_NOWASH)
                         / mean_b Lbar(CM_WT,VEH,0,b,CHAL_NONE,PRE_NOWASH)

    tolerated iff tox_ratio >= 0.85. Point estimate only, no interval, so the rule
    is deterministic. The primary concentration is the highest tolerated rung.
    """
    wt_none = lbar[
        (lbar["cell_model_id"] == WT) & (lbar["challenge_id"] == "CHAL_NONE")
    ]
    veh = wt_none[
        (wt_none["compound_id"] == "VEH") & (wt_none["administered_conc_um"] == 0.0)
    ]["Lbar"]
    if veh.empty:
        return float("nan"), {}
    denom = float(veh.mean())

    per_conc = (
        wt_none[wt_none["compound_id"] == compound]
        .groupby("administered_conc_um")["Lbar"]
        .mean()
    )
    ratios = {float(d): float(per_conc[d] / denom) for d in per_conc.index}
    tolerated = [d for d in ct.ladder
                 if d in ratios and ratios[d] >= TOX_RATIO_MIN]
    return (max(tolerated) if tolerated else float("nan")), ratios


# ---------------------------------------------------------------------------
# exposure_matching_rule
# ---------------------------------------------------------------------------

def build_exposure(manifest: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    """Per-(cell model, compound, concentration, biological experiment) intracellular
    exposure at END_PRETREAT_NOWASH.

    Within one exposure sample only the injection replicates whose qualifier is
    'measured' are averaged. A sample with no measured injection is censored and
    simply absent from the result: it is never imputed and never read as zero.
    """
    e = exposure[
        (exposure["matrix"] == "cell_lysate")
        & (exposure["sampling_condition"] == "END_PRETREAT_NOWASH")
        & (exposure["qualifier"] == "measured")
    ].copy()
    e["exposure_pmol_per_1e6_cells"] = e["measured_value"] / e["cell_equivalents_1e6"]

    cols = [
        "sample_id",
        "cell_model_id",
        "compound_id",
        "administered_conc_um",
        "biological_experiment_id",
    ]
    e = e.merge(
        manifest[cols],
        on="sample_id",
        how="inner",
        validate="many_to_one",
        suffixes=("_lcms", ""),
    )
    assert (e["compound_id_lcms"] == e["compound_id"]).all(), (
        "exposure_measurements.compound_id disagrees with sample_manifest.compound_id"
    )

    return e.groupby(
        [
            "cell_model_id",
            "compound_id",
            "administered_conc_um",
            "biological_experiment_id",
        ],
        as_index=False,
    )["exposure_pmol_per_1e6_cells"].mean()


def exposure_point(per_sample: pd.DataFrame, cell_model: str, compound: str):
    """{concentration: (mean over the biological experiments that yielded a measured
    value, number of such experiments)}."""
    sel = per_sample[
        (per_sample["cell_model_id"] == cell_model)
        & (per_sample["compound_id"] == compound)
    ]
    g = sel.groupby("administered_conc_um")["exposure_pmol_per_1e6_cells"].agg(
        ["mean", "count"]
    )
    return {float(d): (float(r["mean"]), int(r["count"])) for d, r in g.iterrows()}


def select_exposure_matched_conc(ct: Contract, per_sample: pd.DataFrame,
                                 compound: str, e_wt: float):
    """The CM_KO_A concentration whose measured exposure best matches E_WT.

    Qualifies if 0.70 <= E_KO(d)/E_WT <= 1.428571428571; among qualifying rungs,
    minimise |ln(E_KO(d)/E_WT)|, ties broken toward the lower concentration.
    A concentration whose knockout exposure is censored cannot qualify.
    """
    if e_wt is None or not np.isfinite(e_wt) or e_wt == 0:
        return float("nan"), {}
    ko = exposure_point(per_sample, KO_A, compound)
    diagnostics: dict[float, tuple] = {}
    candidates: list[tuple[float, float]] = []
    for d in ct.ladder:
        if d not in ko:
            diagnostics[d] = ("censored:no_measured_sample", None, 0)
            continue
        val, n_bio = ko[d]
        if n_bio < EXPO_MIN_MEASURED_BIOS:
            diagnostics[d] = ("censored:too_few_measured_bios", val, n_bio)
            continue
        ratio = val / e_wt
        if EXPO_WINDOW_LO <= ratio <= EXPO_WINDOW_HI:
            diagnostics[d] = ("qualifies", ratio, n_bio)
            candidates.append((abs(math.log(ratio)), d))
        else:
            diagnostics[d] = ("outside_window", ratio, n_bio)
    if not candidates:
        return float("nan"), diagnostics
    candidates.sort(key=lambda t: (t[0], t[1]))   # tie -> lower concentration
    return candidates[0][1], diagnostics


# ---------------------------------------------------------------------------
# interference indices
# ---------------------------------------------------------------------------

def build_cell_free_mtt(controls: pd.DataFrame) -> pd.DataFrame:
    """Cell-free MTT signal per control well: 570 nm minus the 630 nm reference.
    Wells are control_type='cell_free_mtt' with challenge_id='CHAL_NONE'.
    """
    c = controls[
        (controls["control_type"] == "cell_free_mtt")
        & (controls["challenge_id"] == "CHAL_NONE")
    ]
    wide = c.pivot_table(
        index=[
            "compound_id",
            "administered_conc_um",
            "biological_experiment_id",
            "plate_id",
            "technical_replicate",
        ],
        columns="measured_quantity",
        values="value",
        aggfunc="mean",
    ).reset_index()
    wide["mtt_signal"] = wide["mtt_absorbance_570nm"] - wide["mtt_absorbance_630nm"]
    return wide


def mtt_interference_index(cf_mtt: pd.DataFrame, cell_mtt: pd.Series,
                           compound: str, conc: float) -> pd.Series:
    """Per biological experiment:
        (mean cell-free mtt_signal with the compound at the primary concentration
         - mean cell-free mtt_signal with vehicle)
        / (mean mtt_signal of vehicle-treated CM_WT cells at CHAL_NONE, PRE_NOWASH
           - mean cell-free mtt_signal with vehicle)
    """
    veh_b = (
        cf_mtt[cf_mtt["compound_id"] == "VEH"]
        .groupby("biological_experiment_id")["mtt_signal"].mean()
    )
    cmp_b = (
        cf_mtt[(cf_mtt["compound_id"] == compound)
               & (cf_mtt["administered_conc_um"] == conc)]
        .groupby("biological_experiment_id")["mtt_signal"].mean()
    )
    return ((cmp_b - veh_b) / (cell_mtt - veh_b)).dropna().sort_index()


def probe_autofluorescence_index(ox_wt: pd.DataFrame, compound: str,
                                 conc: float) -> pd.Series:
    """Per biological experiment, CM_WT / CHAL_ISO / PRE_NOWASH:
        (mean dye-free with the compound - mean dye-free with vehicle)
        / (mean dye-loaded vehicle - mean dye-free vehicle)
    """
    veh = ox_wt[ox_wt["compound_id"] == "VEH"]
    dfree_v = (
        veh[veh["probe_loaded"] == "no"]
        .groupby("biological_experiment_id")["fluorescence_au"].mean()
    )
    load_v = (
        veh[veh["probe_loaded"] == "yes"]
        .groupby("biological_experiment_id")["fluorescence_au"].mean()
    )
    dfree_c = (
        ox_wt[(ox_wt["compound_id"] == compound)
              & (ox_wt["administered_conc_um"] == conc)
              & (ox_wt["probe_loaded"] == "no")]
        .groupby("biological_experiment_id")["fluorescence_au"].mean()
    )
    return ((dfree_c - dfree_v) / (load_v - dfree_v)).dropna().sort_index()


def probe_quench_index(controls: pd.DataFrame, compound: str,
                       conc: float) -> pd.Series:
    """Per biological experiment, from control_type='fluorescein_standard_quench':
        (mean with vehicle - mean with the compound) / (mean with vehicle)
    """
    q = controls[controls["control_type"] == "fluorescein_standard_quench"]
    veh_b = (
        q[q["compound_id"] == "VEH"]
        .groupby("biological_experiment_id")["value"].mean()
    )
    cmp_b = (
        q[(q["compound_id"] == compound) & (q["administered_conc_um"] == conc)]
        .groupby("biological_experiment_id")["value"].mean()
    )
    return ((veh_b - cmp_b) / veh_b).dropna().sort_index()


# ---------------------------------------------------------------------------
# evidence_sample_ids
# ---------------------------------------------------------------------------

def evidence_ids(ct: Contract, manifest: pd.DataFrame, compound: str,
                 conc: float) -> str:
    sel = manifest[
        (manifest["assay_panel"] == "VIABILITY")
        & (manifest["cell_model_id"] == WT)
        & (manifest["compound_id"] == compound)
        & (manifest["administered_conc_um"] == conc)
        & (manifest["challenge_id"] == ct.primary_challenge)
        & (manifest["schedule_id"] == ct.primary_schedule)
        & (manifest["readout_time_h_post_challenge"] == ct.primary_readout_h)
    ]
    # one identifier per biological experiment, so every experiment is covered and
    # the list length equals the number of biological experiments
    picks = (
        sel.sort_values(["biological_experiment_id", "technical_replicate",
                         "sample_id"])
        .groupby("biological_experiment_id")["sample_id"]
        .first()
        .sort_index()
        .tolist()
    )
    return ";".join(picks)


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------

def fmt(ct: Contract, x, nd: int = 6) -> str:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return ct.na
    return f"{xf:.{nd}f}" if np.isfinite(xf) else ct.na


def fmt_conc(ct: Contract, x) -> str:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return ct.na
    return f"{xf:.1f}" if np.isfinite(xf) else ct.na


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------

def analyse(data_dir: str) -> tuple[pd.DataFrame, dict, Contract]:
    ct = Contract(data_dir)
    d = load(data_dir)
    manifest = d["manifest"]

    data_bios = sorted(manifest["biological_experiment_id"].unique())
    if data_bios != sorted(ct.bios):
        print(
            f"WARNING: biological experiments in the data {data_bios} differ from "
            f"the set declared in study_specification.json {sorted(ct.bios)}.",
            file=sys.stderr,
        )

    lbar = build_lbar(ct, manifest, d["viability"])
    pi = build_pi(ct, lbar)
    per_sample_exposure = build_exposure(manifest, d["exposure"])
    cf_mtt = build_cell_free_mtt(d["controls"])

    # cell-based MTT denominator: vehicle-treated CM_WT, CHAL_NONE, PRE_NOWASH
    cell_mtt = (
        lbar[
            (lbar["cell_model_id"] == WT)
            & (lbar["compound_id"] == "VEH")
            & (lbar["challenge_id"] == "CHAL_NONE")
        ]
        .set_index("biological_experiment_id")["mtt"]
        .sort_index()
    )

    ox = manifest.merge(
        d["oxidative"][["sample_id", "probe_loaded", "fluorescence_au"]],
        on="sample_id",
        how="inner",
        validate="one_to_one",
        suffixes=("_manifest", ""),
    )
    ox_wt = ox[
        (ox["cell_model_id"] == WT)
        & (ox["challenge_id"] == ct.primary_challenge)
        & (ox["schedule_id"] == ct.primary_schedule)
    ]

    rows = []
    diag: dict[str, dict] = {}

    for compound in ct.compounds:
        info: dict = {}
        primary, tox_ratios = select_primary_concentration(ct, lbar, compound)
        info["tox_ratios"] = tox_ratios
        info["primary_concentration_um"] = primary

        if not np.isfinite(primary):
            # concentration_selection_rule.if_none_qualifies
            row = {c: ct.na for c in OUTPUT_COLUMNS}
            row["compound_id"] = compound
            row["protection_status"] = "not_evaluable"
            # nrf2 rule order: protection_status is not 'protected' -> not_assessable
            row["nrf2_dependence_status"] = "not_assessable"
            rows.append(row)
            diag[compound] = info
            continue

        # ---- wild-type protection ------------------------------------------
        pi_wt = pi_series(pi, WT, compound, primary)
        wt_mean, wt_lo, wt_hi, n_wt = ct.t_summary(pi_wt)
        info["n_bio_wt"] = n_wt
        info["pi_wt_per_bio"] = {k: float(v) for k, v in pi_wt.items()}

        if wt_lo > ct.theta_p:
            protection_status = "protected"
        elif wt_hi < ct.theta_p:
            protection_status = "not_protected"
        else:
            protection_status = "indeterminate"
        info["protection_status"] = protection_status

        # ---- knockout clone A at the same administered concentration --------
        pi_ko_primary = pi_series(pi, KO_A, compound, primary)
        ko_pri_mean, ko_pri_lo, ko_pri_hi, _ = ct.t_summary(pi_ko_primary)

        # ---- rescue criterion ----------------------------------------------
        pi_res = pi_series(pi, KO_A_RES, compound, primary)
        res_mean, res_lo, _, _ = ct.t_summary(pi_res)
        rescue_ok = bool(np.isfinite(res_lo) and res_lo > ct.theta_d)
        info["rescue"] = {"mean": res_mean, "ci_low": res_lo, "holds": rescue_ok}

        # ---- independent lineage corroboration ------------------------------
        pi_kob = pi_series(pi, KO_B, compound, primary)
        kob_mean, kob_lo, kob_hi, _ = ct.t_summary(pi_kob)
        shows_a = bool(np.isfinite(ko_pri_lo) and ko_pri_lo > ct.theta_p)
        shows_b = bool(np.isfinite(kob_lo) and kob_lo > ct.theta_p)
        lineages_agree = shows_a == shows_b
        info["lineage"] = {
            "ko_a_mean": ko_pri_mean, "ko_a_ci_low": ko_pri_lo,
            "ko_a_shows_protection": shows_a,
            "ko_b_mean": kob_mean, "ko_b_ci_low": kob_lo,
            "ko_b_shows_protection": shows_b,
            "agree": lineages_agree,
        }

        # ---- exposure matching ----------------------------------------------
        wt_exp = exposure_point(per_sample_exposure, WT, compound)
        e_wt, e_wt_n = wt_exp.get(primary, (float("nan"), 0))
        info["e_wt"] = e_wt
        info["e_wt_n_bio"] = e_wt_n

        matched_conc, expo_diag = select_exposure_matched_conc(
            ct, per_sample_exposure, compound, e_wt
        )
        info["exposure_diagnostics"] = expo_diag
        info["exposure_matched_ko_concentration_um"] = matched_conc

        if np.isfinite(matched_conc):
            pi_ko_matched = pi_series(pi, KO_A, compound, matched_conc)
            ko_m_mean, _, _, _ = ct.t_summary(pi_ko_matched)
            paired = (pi_wt - pi_ko_matched).dropna()   # per-experiment difference
            delta, delta_lo, delta_hi, n_pair = ct.t_summary(paired)
            info["n_pairs"] = n_pair
        else:
            ko_m_mean = delta = delta_lo = delta_hi = float("nan")

        # ---- nrf2_dependence_status, first matching rule wins ---------------
        if protection_status != "protected":
            nrf2_status = "not_assessable"
        elif not np.isfinite(matched_conc):
            nrf2_status = "indeterminate"
        elif (np.isfinite(delta_lo) and delta_lo > ct.theta_d
              and rescue_ok and lineages_agree):
            nrf2_status = "nrf2_dependent"
        elif np.isfinite(delta_hi) and delta_hi < ct.theta_d:
            nrf2_status = "not_nrf2_dependent"
        else:
            nrf2_status = "indeterminate"

        # ---- interference ---------------------------------------------------
        mtt_m, mtt_lo, mtt_hi, _ = ct.t_summary(
            mtt_interference_index(cf_mtt, cell_mtt, compound, primary))
        auto_m, auto_lo, auto_hi, _ = ct.t_summary(
            probe_autofluorescence_index(ox_wt, compound, primary))
        q_m, q_lo, q_hi, _ = ct.t_summary(
            probe_quench_index(d["controls"], compound, primary))
        info["mtt_index"] = (mtt_m, mtt_lo, mtt_hi)
        info["autofluorescence_index"] = (auto_m, auto_lo, auto_hi)
        info["quench_index"] = (q_m, q_lo, q_hi)

        flags = []
        if np.isfinite(mtt_lo) and mtt_lo > ct.theta_interference:
            flags.append("mtt")
        if (np.isfinite(auto_lo) and auto_lo > ct.theta_interference) or (
            np.isfinite(q_lo) and q_lo > ct.theta_interference
        ):
            flags.append("ros")
        interference = ";".join(flags) if flags else "none"

        rows.append(
            {
                "compound_id": compound,
                "primary_concentration_um": fmt_conc(ct, primary),
                "wt_primary_exposure_pmol_per_1e6_cells": fmt(ct, e_wt),
                "exposure_matched_ko_concentration_um": fmt_conc(ct, matched_conc),
                "protection_index_wt": fmt(ct, wt_mean),
                "protection_index_wt_ci_low": fmt(ct, wt_lo),
                "protection_index_wt_ci_high": fmt(ct, wt_hi),
                "protection_index_ko_primary_conc": fmt(ct, ko_pri_mean),
                "protection_index_ko_exposure_matched": fmt(ct, ko_m_mean),
                "protection_index_rescue": fmt(ct, res_mean),
                "nrf2_dependence_contrast": fmt(ct, delta),
                "nrf2_dependence_contrast_ci_low": fmt(ct, delta_lo),
                "nrf2_dependence_contrast_ci_high": fmt(ct, delta_hi),
                "protection_status": protection_status,
                "nrf2_dependence_status": nrf2_status,
                "interference_flags": interference,
                "evidence_sample_ids": evidence_ids(ct, manifest, compound, primary),
            }
        )
        diag[compound] = info

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS), diag, ct


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, help="directory holding the input CSVs")
    ap.add_argument("--out", required=True, help="path of the results CSV to write")
    ap.add_argument("--diagnostics", help="optional path for a JSON diagnostics dump")
    args = ap.parse_args(argv)

    results, diag, ct = analyse(args.data)

    assert list(results.columns) == OUTPUT_COLUMNS, "output header mismatch"
    assert len(results) == ct.row_count, (
        f"expected {ct.row_count} rows, got {len(results)}")
    assert sorted(results["compound_id"]) == sorted(ct.compounds), (
        "compound set mismatch")
    assert not results.isna().any().any(), "no field may be empty; use the NA token"

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    results.to_csv(args.out, index=False)

    if args.diagnostics:
        with open(args.diagnostics, "w") as fh:
            json.dump(diag, fh, indent=2, default=str)

    print(results.to_string(index=False), file=sys.stderr)
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
