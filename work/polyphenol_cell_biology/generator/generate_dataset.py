"""
generate_dataset.py -- builds every solver-visible file for the
`polyphenol_cell_biology` benchmark from a single integer seed.

Usage:
    python3 generate_dataset.py --seed 20261010 --out ../data

All randomness comes from one numpy Generator consumed in a fixed order, so the
same seed reproduces the same bytes. Latent biology lives in `simcore.py`; this
module adds the hierarchical noise structure and the assay observation models.

Design principle enforced here: measurements from the same biological experiment
share latent factors (culture vigour, realised injury severity, instrument gain)
rather than being resampled independently per table.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd

import simcore as S

# ---------------------------------------------------------------------------
# Replication and noise structure (latent)
# ---------------------------------------------------------------------------

N_BIO = 7                      # independent biological experiments = units of inference
N_TECH_VIABILITY = 4           # technical replicate wells on the primary endpoint
N_TECH_PROBE = 3               # technical replicate wells, probe-loaded
N_TECH_CONTROL = 3             # technical replicate wells, cell-free controls
N_TECH_NODYE = 1               # dye-free control wells per condition
N_TECH_QPCR_REACTION = 3       # qPCR reaction replicates per RNA sample
N_INJECTIONS = 2               # LC-MS injection replicates per lysate
# Culture format per assay panel, with the matching well grid and plate capacity, so
# that a declared format can never disagree with the well positions it carries.
PANEL_FORMAT = {"VIABILITY": "96_well", "OXIDATIVE_STRESS": "96_well",
                "QPCR": "24_well", "EXPOSURE": "12_well"}
PANEL_SEEDING = {"VIABILITY": 12.0, "OXIDATIVE_STRESS": 12.0,
                 "QPCR": 60.0, "EXPOSURE": 300.0}
FORMAT_GRID = {"96_well": (8, 12), "24_well": (4, 6), "12_well": (3, 4)}
PLATE_PREFIX = {"VIABILITY": "VP", "OXIDATIVE_STRESS": "RP",
                "QPCR": "QP", "EXPOSURE": "XP"}

SD_VIGOUR = 0.070              # per biological experiment, log scale
SD_CM_VIGOUR = 0.035           # per experiment x cell model
SD_INJURY = 0.045              # per biological experiment, realised insult severity
SD_PLATE = 0.010               # per plate
SD_WELL = 0.024                # per well, biological
SD_MTT_GAIN = 0.030
SD_MTT_WELL = 0.0090           # absorbance units, additive
SD_LDH_GAIN = 0.050
SD_LDH_WELL = 0.050
SD_PROBE_GAIN = 0.060
SD_PROBE_WELL = 0.050
SD_CT_BATCH = 0.250
SD_CT_INPUT = 0.350            # RNA input variation, shared across genes in a sample
SD_CT_REACTION = 0.110
SD_LCMS_BIO = 0.080
SD_LCMS_INJECTION = 0.050
SD_FOX_WELL = 0.0040

IMAGED_AREA_FRACTION = 0.1000  # fraction of the well imaged for the direct count
QPCR_EFFICIENCY = 1.96         # amplification efficiency reported with each plate
# basal Ct increase in NFE2L2-null cells for constitutively NRF2-dependent genes
BASAL_CT_SHIFT = {"NQO1": 1.05, "GCLC": 0.62, "TXNRD1": 0.48, "HMOX1": 0.20}

WELL_ROWS = "ABCDEFGH"

PRETREAT_H = 18.0
PRETREAT_INTERIM_H = 6.0
CHALLENGE_DURATION_H = 1.5
READOUT_H = 24.0
PROBE_READOUT_H = 1.0


def _wellpos(i: int, fmt: str) -> str:
    """Well label for index i within a plate of the given format. Never produces a
    position outside that format's grid."""
    rows, cols = FORMAT_GRID[fmt]
    i %= rows * cols
    return f"{WELL_ROWS[i // cols]}{(i % cols) + 1}"


# ---------------------------------------------------------------------------
# Manifest construction
# ---------------------------------------------------------------------------

def build_manifest() -> pd.DataFrame:
    """Union of the purpose-built panels. Construction order is deterministic."""
    rows = []

    def add(panel, assay_panel, cm, cmp_id, conc, schedule, challenge_id,
            challenge_um, readout_h, n_tech, extra=None):
        for bio in range(1, N_BIO + 1):
            for tech in range(1, n_tech + 1):
                r = dict(
                    panel_id=panel,
                    assay_panel=assay_panel,
                    biological_experiment_id=f"BIO{bio:02d}",
                    reagent_batch_id="RB1" if bio <= 3 else "RB2",
                    cell_model_id=cm,
                    compound_id=cmp_id,
                    administered_conc_um=float(conc),
                    schedule_id=schedule,
                    challenge_id=challenge_id,
                    challenge_conc_um=float(challenge_um),
                    readout_time_h_post_challenge=readout_h,
                    technical_replicate=tech,
                )
                if extra:
                    r.update(extra)
                rows.append(r)

    cms = S.CELL_MODEL_ORDER
    wash_cms = ["CM_WT", "CM_KO_A", "CM_KO_A_VEC", "CM_KO_A_RES"]
    ros_cms = ["CM_WT", "CM_KO_A", "CM_KO_A_RES"]
    qpcr_cms = ["CM_WT", "CM_KO_A", "CM_KO_A_VEC", "CM_KO_A_RES", "CM_KO_B", "CM_KO_B_RES"]
    exposure_cms = ["CM_WT", "CM_KO_A", "CM_KO_A_VEC", "CM_KO_A_RES", "CM_KO_B"]

    # --- Panel A: vehicle-only oxidant titration (baseline susceptibility) ----
    for cm in cms:
        for dose in S.TITRATION_DOSES:
            add("A_TITRATION", "VIABILITY", cm, S.VEHICLE_ID, 0.0, "PRE_NOWASH",
                f"CHAL_T{int(dose):03d}", dose, READOUT_H, N_TECH_VIABILITY)

    # --- Panel B: core dose-response, both schedules -------------------------
    treatments = [(S.VEHICLE_ID, 0.0)] + [(c, d) for c in S.COMPOUND_ORDER
                                          for d in S.CONC_LADDER]
    for cm in cms:
        for cmp_id, conc in treatments:
            for chal_id, chal_um in (("CHAL_NONE", 0.0),
                                     ("CHAL_ISO", S.CELL_MODELS[cm]["iso_tbhp"])):
                add("B_DOSE_RESPONSE", "VIABILITY", cm, cmp_id, conc, "PRE_NOWASH",
                    chal_id, chal_um, READOUT_H, N_TECH_VIABILITY)
    for cm in wash_cms:
        for cmp_id, conc in treatments:
            for chal_id, chal_um in (("CHAL_NONE", 0.0),
                                     ("CHAL_ISO", S.CELL_MODELS[cm]["iso_tbhp"])):
                add("B_DOSE_RESPONSE", "VIABILITY", cm, cmp_id, conc, "PRE_WASH",
                    chal_id, chal_um, READOUT_H, N_TECH_VIABILITY)

    # --- Panel D: single common oxidant dose for every cell model ------------
    common_treatments = [(S.VEHICLE_ID, 0.0)] + [(c, d) for c in S.COMPOUND_ORDER
                                                 for d in S.CONC_COMMON_ARM]
    for cm in cms:
        for cmp_id, conc in common_treatments:
            add("D_COMMON_DOSE", "VIABILITY", cm, cmp_id, conc, "PRE_NOWASH",
                "CHAL_COMMON", S.CHALLENGE_COMMON_UM, READOUT_H, N_TECH_VIABILITY)

    # --- Panel R: oxidative-stress probe, with matched dye-free wells --------
    for cm in ros_cms:
        for cmp_id, conc in treatments:
            for chal_id, chal_um in (("CHAL_NONE", 0.0),
                                     ("CHAL_ISO", S.CELL_MODELS[cm]["iso_tbhp"])):
                add("R_PROBE", "OXIDATIVE_STRESS", cm, cmp_id, conc, "PRE_NOWASH",
                    chal_id, chal_um, PROBE_READOUT_H, N_TECH_PROBE,
                    extra=dict(probe_loaded=True))
                add("R_PROBE", "OXIDATIVE_STRESS", cm, cmp_id, conc, "PRE_NOWASH",
                    chal_id, chal_um, PROBE_READOUT_H, N_TECH_NODYE,
                    extra=dict(probe_loaded=False))

    # --- Panel Q: transcript samples, harvested during pretreatment ----------
    qpcr_treatments = [(S.VEHICLE_ID, 0.0)] + [(c, d) for c in S.COMPOUND_ORDER
                                               for d in S.CONC_QPCR]
    for cm in qpcr_cms:
        for cmp_id, conc in qpcr_treatments:
            for t in (PRETREAT_INTERIM_H, PRETREAT_H):
                add("Q_TRANSCRIPT", "QPCR", cm, cmp_id, conc, "PRE_NOWASH",
                    "CHAL_NONE", 0.0, float("nan"), 1,
                    extra=dict(harvest_time_h_from_pretreatment_start=t))

    # --- Panel X: compound exposure -----------------------------------------
    sampling = [
        ("END_PRETREAT_NOWASH", "PRE_NOWASH", "CHAL_NONE", 0.0, 18.0),
        ("POST_WASH_0P5H", "PRE_WASH", "CHAL_NONE", 0.0, 18.5),
        ("POST_CHALLENGE_24H_NOWASH", "PRE_NOWASH", "CHAL_ISO", None, 43.5),
        ("POST_CHALLENGE_24H_WASH", "PRE_WASH", "CHAL_ISO", None, 43.5),
    ]
    for cm in exposure_cms:
        for cmp_id in S.COMPOUND_ORDER:
            for conc in S.CONC_LADDER:
                for label, sched, chal_id, chal_um, t in sampling:
                    um = S.CELL_MODELS[cm]["iso_tbhp"] if chal_um is None else chal_um
                    add("X_EXPOSURE", "EXPOSURE", cm, cmp_id, conc, sched,
                        chal_id, um, float("nan"), 1,
                        extra=dict(sampling_condition=label,
                                   sampling_time_h_from_pretreatment_start=t))

    df = pd.DataFrame(rows)
    df["probe_loaded"] = df.get("probe_loaded", pd.Series([pd.NA] * len(df)))
    df["pretreatment_duration_h"] = np.where(
        df["panel_id"] == "Q_TRANSCRIPT",
        df.get("harvest_time_h_from_pretreatment_start", PRETREAT_H), PRETREAT_H)
    df["culture_format"] = df["assay_panel"].map(PANEL_FORMAT)
    df["seeding_density_1e3_per_well"] = df["assay_panel"].map(PANEL_SEEDING)
    return df


def assign_plates_and_ids(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Assign plate identifiers so that every plate carries several cell models and
    several treatments (genotype is never inseparable from plate), keeping technical
    replicates of one condition together on one plate as in real practice.
    Then assign neutral sample identifiers by a random permutation."""
    group_cols = ["biological_experiment_id", "assay_panel", "panel_id",
                  "cell_model_id", "compound_id", "administered_conc_um",
                  "schedule_id", "challenge_id", "probe_loaded",
                  "sampling_condition", "pretreatment_duration_h"]
    group_cols = [c for c in group_cols if c in df.columns]
    df = df.copy()
    df["_grp"] = df.groupby(group_cols, dropna=False).ngroup()

    plate_of_group: dict[tuple, str] = {}
    sizes = df.groupby(["biological_experiment_id", "assay_panel", "_grp"]).size()
    for (bio, fam), sub in df.groupby(["biological_experiment_id", "assay_panel"],
                                      sort=True):
        groups = np.array(sorted(sub["_grp"].unique()))
        order = rng.permutation(len(groups))
        prefix = PLATE_PREFIX[fam]
        rows, cols = FORMAT_GRID[PANEL_FORMAT[fam]]
        capacity = rows * cols
        plate_idx, used = 0, 0
        for gi in order:
            g = groups[gi]
            n = int(sizes.loc[(bio, fam, g)])
            if used + n > capacity:          # never split a group across plates
                plate_idx += 1
                used = 0
            plate_of_group[(bio, fam, g)] = (
                f"{prefix}_{bio.replace('BIO', '')}_{plate_idx + 1:03d}")
            used += n

    df["plate_id"] = [plate_of_group[(b, f, g)] for b, f, g in
                      zip(df["biological_experiment_id"], df["assay_panel"], df["_grp"])]

    # well positions: fill each plate in order of (group, technical replicate), using
    # that plate's own format grid
    df = df.sort_values(["plate_id", "_grp", "technical_replicate"],
                        kind="mergesort").reset_index(drop=True)
    df["well_position"] = [
        _wellpos(i, PANEL_FORMAT[fam])
        for i, fam in zip(df.groupby("plate_id").cumcount(), df["assay_panel"])]

    perm = rng.permutation(len(df))
    ids = np.empty(len(df), dtype=object)
    for rank, idx in enumerate(perm):
        ids[idx] = f"SMP{rank + 1:06d}"
    df["sample_id"] = ids
    return df.drop(columns=["_grp"])


# ---------------------------------------------------------------------------
# Latent random effects, shared across assays from the same experiment
# ---------------------------------------------------------------------------

class Latents:
    def __init__(self, df: pd.DataFrame, rng: np.random.Generator):
        bios = sorted(df["biological_experiment_id"].unique())
        cms = S.CELL_MODEL_ORDER
        self.vigour = {b: float(np.exp(rng.normal(0, SD_VIGOUR))) for b in bios}
        self.injury = {b: float(np.exp(rng.normal(0, SD_INJURY))) for b in bios}
        self.cm_vig = {(b, c): float(np.exp(rng.normal(0, SD_CM_VIGOUR)))
                       for b in bios for c in cms}
        self.mtt_gain = {b: float(np.exp(rng.normal(0, SD_MTT_GAIN))) for b in bios}
        self.ldh_gain = {b: float(np.exp(rng.normal(0, SD_LDH_GAIN))) for b in bios}
        self.probe_gain = {b: float(np.exp(rng.normal(0, SD_PROBE_GAIN))) for b in bios}
        self.lcms_gain = {b: float(np.exp(rng.normal(0, SD_LCMS_BIO / 2))) for b in bios}
        self.ct_batch = {b: float(rng.normal(0, SD_CT_BATCH)) for b in bios}
        plates = sorted(df["plate_id"].unique())
        self.plate = {p: float(np.exp(rng.normal(0, SD_PLATE))) for p in plates}


# ---------------------------------------------------------------------------
# Readout generation
# ---------------------------------------------------------------------------

def generate_viability(df: pd.DataFrame, lat: Latents,
                       rng: np.random.Generator) -> pd.DataFrame:
    sub = df[df["assay_panel"] == "VIABILITY"].reset_index(drop=True)
    n = len(sub)
    well_noise = np.exp(rng.normal(0, SD_WELL, n))
    mtt_noise = rng.normal(0, SD_MTT_WELL, n)
    ldh_noise = np.exp(rng.normal(0, SD_LDH_WELL, n))

    live_n, dead_n, ldh, a570, a630 = [], [], [], [], []
    for i, r in enumerate(sub.itertuples(index=False)):
        cm = r.cell_model_id
        bio = r.biological_experiment_id
        st = S.mean_state(cm, r.compound_id, r.administered_conc_um,
                          r.challenge_conc_um, r.schedule_id == "PRE_WASH",
                          injury_factor=lat.injury[bio])
        scale = (S.L0 * S.CELL_MODELS[cm]["growth"] * lat.vigour[bio]
                 * lat.cm_vig[(bio, cm)] * lat.plate[r.plate_id] * well_noise[i])
        live_density = scale * st["live_rel"]
        killed_density = scale * st["killed_rel"]

        lam_live = max(live_density * 1000.0 * IMAGED_AREA_FRACTION, 0.0)
        lam_dead = max(killed_density * S.DEAD_COUNTABLE * 1000.0 * IMAGED_AREA_FRACTION, 0.0)
        live_n.append(int(rng.poisson(lam_live)))
        dead_n.append(int(rng.poisson(lam_dead)))

        ldh.append((S.LDH_BLANK + S.LDH_SLOPE * killed_density)
                   * lat.ldh_gain[bio] * ldh_noise[i])

        met = 1.0 - S.MET_LOSS * (1.0 - st["s_inj"])
        od = S.MTT_AMP * live_density * met * lat.mtt_gain[bio]
        if r.compound_id != S.VEHICLE_ID:
            p = S.COMPOUNDS[r.compound_id]
            od += p["mtt_cf"] * st["conc_in_medium"] * lat.mtt_gain[bio]
            od += p["mtt_ic"] * st["u_chal"] * (live_density / S.L0) * lat.mtt_gain[bio]
        a630_i = S.MTT_REF_WAVELENGTH + rng.normal(0, SD_MTT_WELL / 3)
        a570.append(S.MTT_BLANK + od + a630_i + mtt_noise[i])
        a630.append(a630_i)

    out = pd.DataFrame(dict(
        sample_id=sub["sample_id"],
        fields_imaged=18,
        imaged_area_fraction=IMAGED_AREA_FRACTION,
        live_nuclei_count=live_n,
        dead_nuclei_count=dead_n,
        ldh_activity_mu_per_l=np.round(ldh, 1),
        mtt_absorbance_570nm=np.round(a570, 4),
        mtt_absorbance_630nm=np.round(a630, 4),
        readout_time_h_post_challenge=sub["readout_time_h_post_challenge"],
    ))
    return out


def generate_oxidative_stress(df: pd.DataFrame, lat: Latents,
                              rng: np.random.Generator) -> pd.DataFrame:
    sub = df[df["assay_panel"] == "OXIDATIVE_STRESS"].reset_index(drop=True)
    n = len(sub)
    well_noise = np.exp(rng.normal(0, SD_WELL, n))
    probe_noise = np.exp(rng.normal(0, SD_PROBE_WELL, n))

    fl = []
    for i, r in enumerate(sub.itertuples(index=False)):
        cm, bio = r.cell_model_id, r.biological_experiment_id
        st = S.mean_state(cm, r.compound_id, r.administered_conc_um,
                          r.challenge_conc_um, r.schedule_id == "PRE_WASH",
                          injury_factor=lat.injury[bio])
        rel = (S.CELL_MODELS[cm]["growth"] * lat.vigour[bio] * lat.cm_vig[(bio, cm)]
               * lat.plate[r.plate_id] * well_noise[i] * st["live_rel_prechallenge"])
        loaded = bool(r.probe_loaded)
        base = S.PROBE_NODYE_BG
        if loaded:
            base = rel * (S.PROBE_BG
                          + S.PROBE_AMP * (st["ros_index"] ** S.PROBE_ROS_EXP))
        signal = base
        if r.compound_id != S.VEHICLE_ID:
            p = S.COMPOUNDS[r.compound_id]
            signal += p["probe_auto"] * st["conc_in_medium"]
            q = p["probe_quench"] * st["conc_in_medium"]
            signal *= 1.0 / (1.0 + q)
        fl.append(signal * lat.probe_gain[bio] * probe_noise[i])

    return pd.DataFrame(dict(
        sample_id=sub["sample_id"],
        probe="DCFH-DA",
        probe_loaded=np.where(sub["probe_loaded"].astype(bool), "yes", "no"),
        excitation_nm=488,
        emission_nm=525,
        gain_setting=80,
        fluorescence_au=np.round(fl, 1),
        readout_time_h_post_challenge=sub["readout_time_h_post_challenge"],
    ))


def generate_qpcr(df: pd.DataFrame, lat: Latents,
                  rng: np.random.Generator) -> pd.DataFrame:
    sub = df[df["assay_panel"] == "QPCR"].reset_index(drop=True)
    rows = []
    for r in sub.itertuples(index=False):
        cm, bio = r.cell_model_id, r.biological_experiment_id
        u = S.exposure_pre(cm, r.compound_id, r.administered_conc_um) / S.E_REF
        lfc = S.gene_log2fc(cm, r.compound_id, u, r.pretreatment_duration_h)
        input_shift = float(rng.normal(0, SD_CT_INPUT))
        for gene in S.ALL_GENES:
            base = S.CT0[gene] + lat.ct_batch[bio] + input_shift
            if gene in S.TARGET_GENES:
                base -= lfc[gene]
                # constitutively NRF2-dependent genes sit at a lower basal level in
                # the knockout; this cancels in a within-cell-model ddCt, and is
                # included only so the raw Ct values are internally coherent.
                base += BASAL_CT_SHIFT.get(gene, 0.0) * (
                    1.0 - S.CELL_MODELS[cm]["nrf2_func"])
            elif gene == S.GENOTYPE_GENE:
                base += S.CELL_MODELS[cm]["nfe2l2_ct_shift"]
            for rep in range(1, N_TECH_QPCR_REACTION + 1):
                ct = base + float(rng.normal(0, SD_CT_REACTION))
                rows.append((r.sample_id, gene, rep, round(ct, 3), "ok"))
    out = pd.DataFrame(rows, columns=["sample_id", "target_gene", "reaction_replicate",
                                      "ct_value", "ct_flag"])
    out["amplification_efficiency"] = QPCR_EFFICIENCY
    return out


def generate_exposure(df: pd.DataFrame, lat: Latents,
                      rng: np.random.Generator) -> pd.DataFrame:
    """LC-MS/MS exposure. `cell_lysate` rows carry the raw amount on column in pmol
    together with the cell equivalents analysed, so the exposure on the disclosed
    basis (pmol per 1e6 cells) has to be derived rather than read off."""
    sub = df[df["assay_panel"] == "EXPOSURE"].reset_index(drop=True)
    rows = []
    for r in sub.itertuples(index=False):
        cm, bio = r.cell_model_id, r.biological_experiment_id
        p = S.COMPOUNDS[r.compound_id]
        phys = S.PHYSCHEM[r.compound_id]
        e_pre = S.exposure_pre(cm, r.compound_id, r.administered_conc_um)
        cond = r.sampling_condition
        if cond == "END_PRETREAT_NOWASH":
            e, medium = e_pre, r.administered_conc_um * 0.94
        elif cond == "POST_WASH_0P5H":
            e, medium = e_pre * p["retention"], r.administered_conc_um * 0.0012
        elif cond == "POST_CHALLENGE_24H_NOWASH":
            e, medium = e_pre * 0.88, r.administered_conc_um * 0.86
        else:
            e, medium = e_pre * p["retention"] * 0.42, r.administered_conc_um * 0.0005

        bio_noise = float(np.exp(rng.normal(0, SD_LCMS_BIO)))
        fmt_scale = 300.0 / 12.0      # 12-well format vs the 96-well reference
        cells_1e3 = (S.L0 * fmt_scale * S.CELL_MODELS[cm]["growth"] * lat.vigour[bio]
                     * lat.cm_vig[(bio, cm)]
                     * float(np.exp(rng.normal(0, SD_WELL))))
        cell_equiv = cells_1e3 * 1e3 / 1e6          # 1e3 cells/well -> units of 1e6 cells

        for inj in range(1, N_INJECTIONS + 1):
            inj_noise = float(np.exp(rng.normal(0, SD_LCMS_INJECTION)))
            amount = e * bio_noise * inj_noise * lat.lcms_gain[bio] * cell_equiv
            below = amount < phys["lloq_pmol"]
            rows.append(dict(
                sample_id=r.sample_id, compound_id=r.compound_id,
                matrix="cell_lysate", sampling_condition=cond,
                sampling_time_h_from_pretreatment_start=r.sampling_time_h_from_pretreatment_start,
                injection_replicate=inj,
                measured_value=("" if below else round(amount, 3)),
                measured_unit="pmol_on_column",
                qualifier=("below_lloq" if below else "measured"),
                cell_equivalents_1e6=round(cell_equiv, 4),
                lloq_value=phys["lloq_pmol"], lloq_unit="pmol_on_column"))

        med = medium * float(np.exp(rng.normal(0, SD_LCMS_INJECTION)))
        below = med < phys["lloq_medium_um"]
        rows.append(dict(
            sample_id=r.sample_id, compound_id=r.compound_id,
            matrix="medium", sampling_condition=cond,
            sampling_time_h_from_pretreatment_start=r.sampling_time_h_from_pretreatment_start,
            injection_replicate=1,
            measured_value=("" if below else round(med, 4)),
            measured_unit="umol_per_litre",
            qualifier=("below_lloq" if below else "measured"),
            cell_equivalents_1e6="",
            lloq_value=phys["lloq_medium_um"], lloq_unit="umol_per_litre"))

    return pd.DataFrame(rows, columns=[
        "sample_id", "compound_id", "matrix", "sampling_condition",
        "sampling_time_h_from_pretreatment_start", "injection_replicate",
        "measured_value", "measured_unit", "qualifier",
        "cell_equivalents_1e6", "lloq_value", "lloq_unit"])


def generate_controls(lat: Latents, rng: np.random.Generator) -> pd.DataFrame:
    """Cell-free and instrument controls. `control_id` namespace is separate from
    `sample_id` because these wells contain no cells (or no template)."""
    rows = []
    k = [0]

    def add(ctype, assay, cmp_id, conc, cm, chal_id, chal_um, bio, plate, tech,
            quantity, value, unit, qualifier="measured", notes=""):
        k[0] += 1
        rows.append(dict(
            control_id=f"CTL{k[0]:06d}", control_type=ctype, assay=assay,
            compound_id=cmp_id, administered_conc_um=conc, cell_model_id=cm,
            challenge_id=chal_id, challenge_conc_um=chal_um,
            biological_experiment_id=bio, plate_id=plate, technical_replicate=tech,
            measured_quantity=quantity,
            value=("" if value is None else round(float(value), 5)),
            unit=unit, qualifier=qualifier, notes=notes))

    bios = [f"BIO{b:02d}" for b in range(1, N_BIO + 1)]
    iso_wt = S.CELL_MODELS["CM_WT"]["iso_tbhp"]

    for bio in bios:
        plate = f"CP_{bio.replace('BIO', '')}_01"
        for cmp_id in [S.VEHICLE_ID] + S.COMPOUND_ORDER:
            concs = [0.0] if cmp_id == S.VEHICLE_ID else S.CONC_LADDER
            for conc in concs:
                for chal_id, chal_um in (("CHAL_NONE", 0.0), ("CHAL_ISO", iso_wt)):
                    for tech in range(1, N_TECH_CONTROL + 1):
                        # cell-free MTT: detects direct tetrazolium reduction
                        cf = 0.0 if cmp_id == S.VEHICLE_ID else S.COMPOUNDS[cmp_id]["mtt_cf"] * conc
                        a630 = S.MTT_REF_WAVELENGTH + rng.normal(0, SD_MTT_WELL / 3)
                        a570 = (S.MTT_BLANK + cf * lat.mtt_gain[bio] + a630
                                + rng.normal(0, SD_MTT_WELL))
                        add("cell_free_mtt", "MTT", cmp_id, conc, "CELL_FREE",
                            chal_id, chal_um, bio, plate, tech,
                            "mtt_absorbance_570nm", a570, "absorbance_units")
                        add("cell_free_mtt", "MTT", cmp_id, conc, "CELL_FREE",
                            chal_id, chal_um, bio, plate, tech,
                            "mtt_absorbance_630nm", a630, "absorbance_units")
                        # cell-free probe, dye present and dye absent
                        for loaded in (True, False):
                            base = S.PROBE_BG * 0.42 if loaded else S.PROBE_NODYE_BG
                            sig = base
                            if cmp_id != S.VEHICLE_ID:
                                p = S.COMPOUNDS[cmp_id]
                                sig += p["probe_auto"] * conc
                                q = p["probe_quench"] * conc
                                sig *= 1.0 / (1.0 + q)
                            sig *= lat.probe_gain[bio] * float(np.exp(rng.normal(0, SD_PROBE_WELL)))
                            add("cell_free_probe", "OXIDATIVE_STRESS", cmp_id, conc,
                                "CELL_FREE", chal_id, chal_um, bio, plate, tech,
                                "fluorescence_au_probe_loaded" if loaded
                                else "fluorescence_au_probe_absent",
                                sig, "arbitrary_units")

        # fixed fluorescein standard + compound: isolates emission quenching
        for cmp_id in [S.VEHICLE_ID] + S.COMPOUND_ORDER:
            concs = [0.0] if cmp_id == S.VEHICLE_ID else S.CONC_LADDER
            for conc in concs:
                for tech in range(1, N_TECH_CONTROL + 1):
                    q = 0.0 if cmp_id == S.VEHICLE_ID else S.COMPOUNDS[cmp_id]["probe_quench"] * conc
                    auto = 0.0 if cmp_id == S.VEHICLE_ID else S.COMPOUNDS[cmp_id]["probe_auto"] * conc
                    val = ((S.QUENCH_STD_F + auto) / (1.0 + q)) * lat.probe_gain[bio] \
                        * float(np.exp(rng.normal(0, SD_PROBE_WELL / 2)))
                    add("fluorescein_standard_quench", "OXIDATIVE_STRESS", cmp_id,
                        conc, "CELL_FREE", "CHAL_NONE", 0.0, bio, plate, tech,
                        "fluorescein_standard_fluorescence_au", val, "arbitrary_units",
                        notes="1 uM fluorescein standard, cell free")

        # cell-free oxidant neutralisation (residual peroxide after co-incubation)
        for cmp_id in [S.VEHICLE_ID] + S.COMPOUND_ORDER:
            concs = [0.0] if cmp_id == S.VEHICLE_ID else S.CONC_LADDER
            for conc in concs:
                for tech in range(1, N_TECH_CONTROL + 1):
                    frac = S.neutralised_fraction(cmp_id, conc, True)
                    residual = iso_wt * (1.0 - frac)
                    val = (S.FOX_BLANK + S.FOX_SLOPE * residual
                           + rng.normal(0, SD_FOX_WELL))
                    add("cell_free_oxidant_neutralisation", "PEROXIDE_FOX", cmp_id,
                        conc, "CELL_FREE", "CHAL_ISO", iso_wt, bio, plate, tech,
                        "peroxide_assay_absorbance_560nm", val, "absorbance_units",
                        notes="compound + oxidant co-incubated 1.5 h, no cells")
        # peroxide assay calibration curve
        for level in (0.0, 25.0, 50.0, 100.0, 200.0, 400.0):
            for tech in range(1, N_TECH_CONTROL + 1):
                val = S.FOX_BLANK + S.FOX_SLOPE * level + rng.normal(0, SD_FOX_WELL)
                add("peroxide_calibration_standard", "PEROXIDE_FOX", "NONE", 0.0,
                    "CELL_FREE", "CHAL_NONE", level, bio, plate, tech,
                    "peroxide_assay_absorbance_560nm", val, "absorbance_units",
                    notes=f"calibration standard {level:.0f} uM tert-butyl hydroperoxide")

        # LDH blanks and maximum-lysis standards
        for tech in range(1, N_TECH_CONTROL + 1):
            add("ldh_medium_blank", "LDH", S.VEHICLE_ID, 0.0, "CELL_FREE",
                "CHAL_NONE", 0.0, bio, plate, tech, "ldh_activity_mu_per_l",
                S.LDH_BLANK * lat.ldh_gain[bio] * float(np.exp(rng.normal(0, SD_LDH_WELL))),
                "milliunits_per_litre", notes="culture medium only")
        for cm in S.CELL_MODEL_ORDER:
            for tech in range(1, N_TECH_CONTROL + 1):
                total = (S.L0 * S.CELL_MODELS[cm]["growth"] * lat.vigour[bio]
                         * lat.cm_vig[(bio, cm)])
                val = ((S.LDH_BLANK + S.LDH_SLOPE * total) * lat.ldh_gain[bio]
                       * float(np.exp(rng.normal(0, SD_LDH_WELL))))
                add("ldh_maximum_lysis", "LDH", S.VEHICLE_ID, 0.0, cm,
                    "CHAL_NONE", 0.0, bio, plate, tech, "ldh_activity_mu_per_l",
                    val, "milliunits_per_litre",
                    notes="vehicle, unchallenged, fully lysed with 1% Triton X-100")

        # qPCR no-template and no-reverse-transcriptase controls
        for gene in S.ALL_GENES:
            for ctype in ("qpcr_no_template", "qpcr_no_reverse_transcriptase"):
                add(ctype, "QPCR", "NONE", 0.0, "CELL_FREE", "CHAL_NONE", 0.0,
                    bio, f"QP_{bio.replace('BIO', '')}_CTL", 1, "ct_value",
                    None, "cycles", "undetermined",
                    notes="no amplification within 40 cycles")

        # LC-MS calibration standards and spike recovery
        for cmp_id in S.COMPOUND_ORDER:
            phys = S.PHYSCHEM[cmp_id]
            for level in (0.0, 2.0, 10.0, 50.0, 250.0, 1000.0, 4000.0):
                val = (level * 0.00242 * lat.lcms_gain[bio]
                       * float(np.exp(rng.normal(0, SD_LCMS_INJECTION))))
                add("lcms_calibration_standard", "LCMS", cmp_id, 0.0, "CELL_FREE",
                    "CHAL_NONE", 0.0, bio, f"XP_{bio.replace('BIO', '')}_CTL", 1,
                    "lcms_peak_area_ratio", val, "ratio_to_internal_standard",
                    "measured" if level >= phys["lloq_pmol"] else "below_lloq",
                    notes=f"standard {level:.1f} pmol on column")
            for level in (5.0, 100.0, 1000.0):
                rec = 100.0 * (0.92 + 0.05 * float(rng.random())) \
                    * float(np.exp(rng.normal(0, 0.03)))
                add("lcms_spike_recovery", "LCMS", cmp_id, 0.0, "CELL_FREE",
                    "CHAL_NONE", 0.0, bio, f"XP_{bio.replace('BIO', '')}_CTL", 1,
                    "recovery_pct", rec, "percent",
                    notes=f"blank lysate spiked at {level:.0f} pmol")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Static reference tables
# ---------------------------------------------------------------------------

def compounds_table() -> pd.DataFrame:
    rows = []
    for cid in S.COMPOUND_ORDER:
        p = S.PHYSCHEM[cid]
        rows.append(dict(
            compound_id=cid,
            test_article_class="synthetic polyphenol-like test article",
            molecular_weight_g_per_mol=p["mw"],
            logp_calculated=p["logp"],
            max_dmso_solubility_mm=p["solubility_mm"],
            dmso_stock_mm=50.0,
            purity_pct=p["purity"],
            vehicle="DMSO",
            final_vehicle_pct_v_v=S.VEHICLE_PCT,
            lcms_mrm_transition_m_z=p["mrm"],
            lloq_intracellular_pmol=p["lloq_pmol"],
            lloq_medium_um=p["lloq_medium_um"],
            internal_standard="IS-D4 (stable-isotope analogue)",
        ))
    rows.append(dict(
        compound_id=S.VEHICLE_ID,
        test_article_class="vehicle control",
        molecular_weight_g_per_mol="", logp_calculated="",
        max_dmso_solubility_mm="", dmso_stock_mm="", purity_pct="",
        vehicle="DMSO", final_vehicle_pct_v_v=S.VEHICLE_PCT,
        lcms_mrm_transition_m_z="", lloq_intracellular_pmol="",
        lloq_medium_um="", internal_standard=""))
    return pd.DataFrame(rows)


def cell_models_table() -> pd.DataFrame:
    rows = []
    for cid in S.CELL_MODEL_ORDER:
        cm = S.CELL_MODELS[cid]
        geno = "wild_type" if cm["nfe2l2_protein"] == "detected" and cm["lineage"] == "parental" \
            else ("NFE2L2_knockout" if cm["transgene"] != "NFE2L2_CDS"
                  else "NFE2L2_knockout_with_NFE2L2_re_expression")
        rows.append(dict(
            cell_model_id=cid,
            parental_line="IEC-SIM (simulated human intestinal epithelial line)",
            lineage=cm["lineage"],
            nfe2l2_genotype=geno,
            nfe2l2_edit_description=cm["edit"],
            guide_rna=cm["guide"],
            transgene=cm["transgene"],
            selection_marker=cm["selection"],
            nfe2l2_protein_by_immunoblot=cm["nfe2l2_protein"],
            passage_at_experiment=cm["passage"],
            population_doubling_time_h=cm["doubling_h"],
            seeding_density_1e3_per_well=12.0,
            challenge_agent=S.CHALLENGE_AGENT,
            challenge_duration_h=CHALLENGE_DURATION_H,
            isoeffective_challenge_tbhp_um=cm["iso_tbhp"],
            common_arm_challenge_tbhp_um=S.CHALLENGE_COMMON_UM,
        ))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

MANIFEST_COLS = [
    "sample_id", "biological_experiment_id", "reagent_batch_id", "plate_id",
    "well_position", "panel_id", "assay_panel", "cell_model_id", "compound_id",
    "administered_conc_um", "schedule_id", "pretreatment_duration_h",
    "challenge_id", "challenge_conc_um", "sampling_condition",
    "sampling_time_h_from_pretreatment_start", "probe_loaded",
    "readout_time_h_post_challenge", "technical_replicate", "culture_format",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    man = build_manifest()
    man = assign_plates_and_ids(man, rng)
    lat = Latents(man, rng)

    via = generate_viability(man, lat, rng)
    ros = generate_oxidative_stress(man, lat, rng)
    qpcr = generate_qpcr(man, lat, rng)
    expo = generate_exposure(man, lat, rng)
    ctrl = generate_controls(lat, rng)

    for c in ("sampling_condition", "sampling_time_h_from_pretreatment_start",
              "probe_loaded"):
        if c not in man.columns:
            man[c] = ""
    man["probe_loaded"] = man["probe_loaded"].map(
        lambda v: "" if v is pd.NA or (isinstance(v, float) and math.isnan(v))
        else ("yes" if bool(v) else "no"))
    man_out = man[MANIFEST_COLS].copy()
    man_out = man_out.fillna("")

    # Shuffle row order of every table so ordering carries no information.
    def shuffled(d):
        idx = rng.permutation(len(d))
        return d.iloc[idx].reset_index(drop=True)

    tables = {
        "compounds.csv": compounds_table(),
        "cell_models.csv": cell_models_table(),
        "sample_manifest.csv": shuffled(man_out),
        "viability_readouts.csv": shuffled(via),
        "oxidative_stress_readouts.csv": shuffled(ros),
        "qpcr_ct_values.csv": shuffled(qpcr),
        "exposure_measurements.csv": shuffled(expo),
        "assay_controls.csv": shuffled(ctrl),
    }
    for name, d in tables.items():
        d.to_csv(out / name, index=False, encoding="utf-8", lineterminator="\n")
        print(f"  wrote {name:34s} rows={len(d):7d} cols={len(d.columns):2d} "
              f"bytes={(out / name).stat().st_size:9d}")

    # The seed is deliberately NOT written into the data directory: it is a generator
    # artefact, it is not declared in study_specification.json input_files, and it has
    # no place in a solver-visible mount.
    print(f"  total bytes = {sum((out / n).stat().st_size for n in tables):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
