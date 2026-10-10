"""
simcore.py -- PRIVATE simulation core for the `polyphenol_cell_biology` benchmark.

This module holds the *latent* (never disclosed) parameters and the deterministic
mean model that links:

    administered concentration -> intracellular exposure -> NRF2 activation
        -> target-gene induction -> antioxidant capacity -> effective oxidative
        insult -> cell injury -> observable readouts (counts / LDH / MTT / probe)

and, on a path that bypasses cell injury entirely:

    compound chemistry -> assay interference -> MTT and probe readouts

NOTHING in this file is read by the reference analysis or by the verifier.
It is consumed only by `generate_dataset.py` and by `calibrate.py`.

All numeric values here are invented free parameters chosen to produce specific,
distinguishable patterns. They are not derived from any publication and make no
claim about any real compound. See
`design/design_and_causal_assumptions.md` section 3 for the separation between
literature-supported *principles* (used as structure) and these *invented*
quantitative parameters.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Global latent constants
# ---------------------------------------------------------------------------

E_REF = 1000.0          # pmol/1e6 cells -- normalising constant for "exposure units" u
I50 = 200.0             # effective-insult units giving 50% survival
HILL = 2.2              # steepness of the injury response
AD_K = 0.55             # antioxidant-capacity gain per log2 fold-change of GCLC
KA_ACT = 0.25           # half-saturation (in u units) of NRF2 activation
L0 = 42.0               # 1e3 live cells/well, unchallenged vehicle, reference cell model
DEAD_COUNTABLE = 0.55   # fraction of killed cells still countable (rest detach/lyse)
MET_LOSS = 0.15         # fractional drop in per-cell MTT turnover at maximal injury

# qPCR anchors (Ct of the vehicle condition in the reference cell model)
CT0 = {
    "NQO1": 24.60,
    "HMOX1": 26.10,
    "GCLC": 25.30,
    "TXNRD1": 25.80,
    "NFE2L2": 24.90,
    "ACTB": 17.40,
    "RPLP0": 18.90,
}
TARGET_GENES = ["NQO1", "HMOX1", "GCLC", "TXNRD1"]
REFERENCE_GENES = ["ACTB", "RPLP0"]
GENOTYPE_GENE = "NFE2L2"
ALL_GENES = TARGET_GENES + [GENOTYPE_GENE] + REFERENCE_GENES

# Transcript kinetics: fraction of the 18 h log2FC already present at 6 h.
KINETIC_6H = {"NQO1": 0.58, "HMOX1": 0.72, "GCLC": 0.34, "TXNRD1": 0.50}

# Assay calibration constants (latent)
MTT_BLANK = 0.082           # cell-free vehicle A570 - A630 baseline
MTT_AMP = 0.0183            # (A570-A630) per 1e3 live cells/well
MTT_REF_WAVELENGTH = 0.045  # A630 plate/scatter offset
LDH_BLANK = 320.0           # AU, medium-only background
LDH_SLOPE = 61.0            # AU per 1e3 lysed cells/well
PROBE_BG = 850.0            # AU, dye-loaded but unstressed background
PROBE_AMP = 2900.0          # AU per (relative cell density) per (I/I50)^1.2
PROBE_NODYE_BG = 190.0      # AU, dye-free well background
PROBE_ROS_EXP = 1.2
QUENCH_STD_F = 42000.0      # AU of the fixed fluorescein standard
FOX_BLANK = 0.031           # cell-free peroxide-assay background absorbance
FOX_SLOPE = 0.00214         # absorbance per uM residual tert-butyl hydroperoxide


# ---------------------------------------------------------------------------
# Cell models (latent properties)
# ---------------------------------------------------------------------------
# nrf2_func : functional NRF2 activity relative to the parental line
# suscept   : baseline susceptibility multiplier on the oxidative insult
# growth    : unchallenged live-density multiplier relative to the parental line
# iso_tbhp  : the genotype-specific isoeffective challenge dose actually used (uM)
# nfe2l2_ct_shift : shift of the NFE2L2 amplicon Ct relative to the parental line

CELL_MODELS = {
    "CM_WT": dict(
        nrf2_func=1.00, suscept=1.00, growth=1.000, iso_tbhp=200.0,
        lineage="parental", transgene="none", nfe2l2_ct_shift=0.00,
        doubling_h=21.5, passage=14, nfe2l2_protein="detected",
        edit="none (parental)", guide="none", selection="none",
    ),
    "CM_WT_VEC": dict(
        nrf2_func=1.00, suscept=1.03, growth=0.984, iso_tbhp=194.0,
        lineage="parental", transgene="empty_vector", nfe2l2_ct_shift=0.05,
        doubling_h=22.0, passage=14, nfe2l2_protein="detected",
        edit="none (parental)", guide="none", selection="puromycin",
    ),
    "CM_KO_A": dict(
        nrf2_func=0.00, suscept=1.70, growth=0.952, iso_tbhp=118.0,
        lineage="clone_A", transgene="none", nfe2l2_ct_shift=2.70,
        doubling_h=23.8, passage=15, nfe2l2_protein="not_detected",
        edit="NFE2L2 exon 2, biallelic 11 bp deletion (frameshift)", guide="sgNFE2L2-1",
        selection="none",
    ),
    "CM_KO_A_VEC": dict(
        nrf2_func=0.00, suscept=1.74, growth=0.938, iso_tbhp=115.0,
        lineage="clone_A", transgene="empty_vector", nfe2l2_ct_shift=2.74,
        doubling_h=24.2, passage=15, nfe2l2_protein="not_detected",
        edit="NFE2L2 exon 2, biallelic 11 bp deletion (frameshift)", guide="sgNFE2L2-1",
        selection="puromycin",
    ),
    "CM_KO_A_RES": dict(
        nrf2_func=0.85, suscept=1.12, growth=0.961, iso_tbhp=179.0,
        lineage="clone_A", transgene="NFE2L2_CDS", nfe2l2_ct_shift=-2.95,
        doubling_h=22.4, passage=15, nfe2l2_protein="detected",
        edit="NFE2L2 exon 2, biallelic 11 bp deletion (frameshift)", guide="sgNFE2L2-1",
        selection="puromycin",
    ),
    "CM_KO_B": dict(
        nrf2_func=0.00, suscept=1.62, growth=0.967, iso_tbhp=123.0,
        lineage="clone_B", transgene="none", nfe2l2_ct_shift=2.42,
        doubling_h=23.1, passage=13, nfe2l2_protein="not_detected",
        edit="NFE2L2 exon 2, biallelic 4 bp insertion (frameshift)", guide="sgNFE2L2-4",
        selection="none",
    ),
    "CM_KO_B_RES": dict(
        nrf2_func=0.90, suscept=1.08, growth=0.974, iso_tbhp=185.0,
        lineage="clone_B", transgene="NFE2L2_CDS", nfe2l2_ct_shift=-3.10,
        doubling_h=22.1, passage=13, nfe2l2_protein="detected",
        edit="NFE2L2 exon 2, biallelic 4 bp insertion (frameshift)", guide="sgNFE2L2-4",
        selection="puromycin",
    ),
}

CELL_MODEL_ORDER = list(CELL_MODELS)

CHALLENGE_COMMON_UM = 300.0
CHALLENGE_AGENT = "tert-butyl_hydroperoxide"


# ---------------------------------------------------------------------------
# Compounds: latent archetypes and parameters
# ---------------------------------------------------------------------------
# The archetype -> identifier assignment is deliberately shuffled so the
# identifier ordering carries no pattern.
#
# uptake model:
#   E(cell_model, conc) = p_max * C/(kp + C)  +  t_max * nrf2_func * C/(kt + C)
#   (pmol per 1e6 cells, end of pretreatment)
#
# mechanism:
#   "adaptive" -> protection is produced by GCLC-dependent antioxidant capacity,
#                 requires NRF2; coup_GCLC is back-solved from `pi_target`.
#   "direct"   -> protection is produced by direct scavenging proportional to the
#                 exposure present *during* the challenge; d_max is back-solved.

COMPOUNDS = {
    # ------------------------------------------------------------------ PP01
    # archetype: pathway-response gene induction WITHOUT improved survival.
    # Strong NQO1/HMOX1/TXNRD1 induction, GCLC arm essentially not engaged.
    "PP01": dict(
        archetype="pathway_induction_without_protection",
        p_max=2800.0, kp=900.0, t_max=0.0, kt=900.0,
        primary_conc=100.0, next_conc=200.0,
        tox_ratio_primary=0.95, tox_ratio_next=0.74,
        mechanism="adaptive", pi_target=0.01,
        pot=1.00, coup={"NQO1": 5.00, "HMOX1": 3.80, "TXNRD1": 2.80},
        indep_hmox1=0.35,
        ks=0.30, retention=0.46, neut_k=0.0,
        mtt_cf=0.0000, mtt_ic=0.004, probe_auto=0.012, probe_quench=0.00008,
    ),
    # ------------------------------------------------------------------ PP02
    # archetype: canonical NRF2-dependent protection, no interference.
    "PP02": dict(
        archetype="nrf2_dependent_clean",
        p_max=2600.0, kp=900.0, t_max=0.0, kt=900.0,
        primary_conc=50.0, next_conc=100.0,
        tox_ratio_primary=0.96, tox_ratio_next=0.73,
        mechanism="adaptive", pi_target=0.60,
        pot=1.00, coup={"NQO1": 6.50, "HMOX1": 4.50, "TXNRD1": 3.20},
        indep_hmox1=0.28,
        ks=0.30, retention=0.52, neut_k=0.0,
        mtt_cf=0.0000, mtt_ic=0.003, probe_auto=0.008, probe_quench=0.00005,
    ),
    # ------------------------------------------------------------------ PP03
    # archetype: apparent genotype difference fully explained by exposure.
    # Direct (NRF2-independent) scavenger whose uptake uses an NRF2-regulated
    # transporter; the residual passive route is NOT saturating, so the knockout
    # can be dosed up to matched exposure -> protection is restored.
    "PP03": dict(
        archetype="exposure_explained_not_nrf2_dependent",
        p_max=620.0, kp=900.0, t_max=2350.0, kt=900.0,
        primary_conc=10.0, next_conc=30.0,
        tox_ratio_primary=0.94, tox_ratio_next=0.74,
        mechanism="direct", pi_target=0.52,
        pot=0.05, coup={"NQO1": 2.00, "HMOX1": 1.50, "TXNRD1": 1.20, "GCLC": 1.60},
        indep_hmox1=0.45,
        ks=0.050, retention=0.25, neut_k=0.0005,
        mtt_cf=0.0000, mtt_ic=0.005, probe_auto=0.030, probe_quench=0.00020,
    ),
    # ------------------------------------------------------------------ PP04
    # archetype: apparent benefit caused almost entirely by assay interference.
    # Reduces the tetrazolium directly in cell-free wells, is autofluorescent in
    # the probe channel AND quenches probe emission. No real protection.
    "PP04": dict(
        archetype="assay_interference_without_protection",
        p_max=2200.0, kp=1200.0, t_max=0.0, kt=1200.0,
        primary_conc=300.0, next_conc=600.0,
        tox_ratio_primary=0.95, tox_ratio_next=0.76,
        mechanism="direct", pi_target=0.00,
        pot=0.03, coup={"NQO1": 2.00, "HMOX1": 1.50, "TXNRD1": 1.20, "GCLC": 1.60},
        indep_hmox1=1.60,
        ks=0.60, retention=0.38, neut_k=0.00004,
        mtt_cf=0.001280, mtt_ic=0.060, probe_auto=4.00, probe_quench=0.00180,
    ),
    # ------------------------------------------------------------------ PP05
    # archetype: protection that persists without NRF2 (direct chemistry).
    # Washout-sensitive, strong cell-free oxidant neutralisation.
    "PP05": dict(
        archetype="direct_scavenger_not_nrf2_dependent",
        p_max=3200.0, kp=1000.0, t_max=0.0, kt=1000.0,
        primary_conc=100.0, next_conc=200.0,
        tox_ratio_primary=0.95, tox_ratio_next=0.75,
        mechanism="direct", pi_target=0.55,
        pot=0.08, coup={"NQO1": 2.00, "HMOX1": 1.50, "TXNRD1": 1.20, "GCLC": 1.60},
        indep_hmox1=0.40,
        ks=0.400, retention=0.12, neut_k=0.0015,
        mtt_cf=0.0000, mtt_ic=0.012, probe_auto=0.045, probe_quench=0.00030,
    ),
    # ------------------------------------------------------------------ PP06
    # archetype: genuine NRF2-dependent protection PLUS probe interference.
    # The direct cell count and LDH both confirm real protection; the probe
    # readout is independently corrupted by quenching.
    "PP06": dict(
        archetype="nrf2_dependent_plus_probe_interference",
        p_max=2400.0, kp=950.0, t_max=0.0, kt=950.0,
        primary_conc=100.0, next_conc=200.0,
        tox_ratio_primary=0.96, tox_ratio_next=0.74,
        mechanism="adaptive", pi_target=0.58,
        pot=1.00, coup={"NQO1": 5.50, "HMOX1": 4.00, "TXNRD1": 3.00},
        indep_hmox1=0.30,
        ks=0.30, retention=0.50, neut_k=0.0,
        mtt_cf=0.0000, mtt_ic=0.006, probe_auto=0.090, probe_quench=0.00520,
    ),
    # ------------------------------------------------------------------ PP07
    # archetype: dose-dependent toxicity, no supported protection.
    "PP07": dict(
        archetype="dose_limiting_toxicity_no_protection",
        p_max=2500.0, kp=900.0, t_max=0.0, kt=900.0,
        primary_conc=10.0, next_conc=30.0,
        tox_ratio_primary=0.94, tox_ratio_next=0.55,
        mechanism="direct", pi_target=0.00,
        pot=0.15, coup={"NQO1": 2.00, "HMOX1": 1.50, "TXNRD1": 1.20, "GCLC": 1.60},
        indep_hmox1=1.20,
        ks=0.20, retention=0.30, neut_k=0.00008,
        mtt_cf=0.0000, mtt_ic=0.004, probe_auto=0.020, probe_quench=0.00012,
    ),
    # ------------------------------------------------------------------ PP08
    # archetype: NRF2-dependent protection whose uptake is ALSO NRF2-dependent,
    # with the residual passive route saturating well below the wild-type working
    # exposure. No exposure-matched knockout stratum exists anywhere on the
    # ladder, so pathway dependence cannot be separated from delivery dependence
    # -> the disclosed contract returns `indeterminate`.
    "PP08": dict(
        archetype="nrf2_dependent_exposure_not_matchable",
        p_max=120.0, kp=60.0, t_max=6262.0, kt=900.0,
        primary_conc=50.0, next_conc=100.0,
        tox_ratio_primary=0.95, tox_ratio_next=0.72,
        mechanism="adaptive", pi_target=0.56,
        pot=1.00, coup={"NQO1": 5.80, "HMOX1": 4.20, "TXNRD1": 2.90},
        indep_hmox1=0.30,
        ks=0.30, retention=0.55, neut_k=0.0,
        mtt_cf=0.0000, mtt_ic=0.004, probe_auto=0.015, probe_quench=0.00009,
    ),
}

COMPOUND_ORDER = list(COMPOUNDS)

# Physicochemical descriptors (invented). Deliberately assigned WITHOUT
# correlation to archetype so they cannot be used to shortcut the answer.
PHYSCHEM = {
    "PP01": dict(mw=302.24, logp=1.48, solubility_mm=12.0, purity=99.1,
                 mrm="301.0 > 151.0", lloq_pmol=2.0, lloq_medium_um=0.050),
    "PP02": dict(mw=446.37, logp=0.52, solubility_mm=8.5, purity=98.4,
                 mrm="445.1 > 283.0", lloq_pmol=2.0, lloq_medium_um=0.050),
    "PP03": dict(mw=228.24, logp=3.12, solubility_mm=4.2, purity=99.6,
                 mrm="227.1 > 143.1", lloq_pmol=1.5, lloq_medium_um=0.040),
    "PP04": dict(mw=610.52, logp=0.31, solubility_mm=20.0, purity=97.8,
                 mrm="609.1 > 300.0", lloq_pmol=2.5, lloq_medium_um=0.060),
    "PP05": dict(mw=290.27, logp=2.04, solubility_mm=15.0, purity=99.3,
                 mrm="289.1 > 109.0", lloq_pmol=2.0, lloq_medium_um=0.050),
    "PP06": dict(mw=354.31, logp=1.76, solubility_mm=6.8, purity=98.9,
                 mrm="353.1 > 191.0", lloq_pmol=1.8, lloq_medium_um=0.045),
    "PP07": dict(mw=180.16, logp=1.21, solubility_mm=30.0, purity=99.8,
                 mrm="179.0 > 135.0", lloq_pmol=1.2, lloq_medium_um=0.035),
    "PP08": dict(mw=472.44, logp=3.81, solubility_mm=3.0, purity=98.1,
                 mrm="471.2 > 271.1", lloq_pmol=2.2, lloq_medium_um=0.055),
}

# Administered-concentration ladder, identical for every compound and cell model.
CONC_LADDER = [1.0, 3.0, 10.0, 30.0, 50.0, 100.0, 200.0, 300.0, 600.0]
CONC_CORE = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0]
CONC_EXTENSION = [50.0, 200.0, 600.0]
CONC_COMMON_ARM = [10.0, 30.0, 100.0]
CONC_QPCR = [10.0, 50.0, 100.0, 300.0]
TITRATION_DOSES = [50.0, 75.0, 150.0, 250.0, 400.0, 700.0]

VEHICLE_ID = "VEH"
VEHICLE_PCT = 0.20  # % v/v DMSO, constant across all wells including vehicle


# ---------------------------------------------------------------------------
# Mean model
# ---------------------------------------------------------------------------

def exposure_pre(cm_id: str, cmp_id: str, conc_um: float) -> float:
    """Mean intracellular exposure (pmol/1e6 cells) at the end of pretreatment."""
    if cmp_id == VEHICLE_ID or conc_um <= 0:
        return 0.0
    p = COMPOUNDS[cmp_id]
    f = CELL_MODELS[cm_id]["nrf2_func"]
    passive = p["p_max"] * conc_um / (p["kp"] + conc_um)
    carrier = p["t_max"] * f * conc_um / (p["kt"] + conc_um)
    return passive + carrier


def toxicity_params(cmp_id: str) -> tuple[float, float]:
    """Back-solve (k50, hill) of the toxicity curve from the two disclosed-free
    ratio targets at the primary and next-higher concentration in the parental line."""
    p = COMPOUNDS[cmp_id]
    u1 = exposure_pre("CM_WT", cmp_id, p["primary_conc"]) / E_REF
    u2 = exposure_pre("CM_WT", cmp_id, p["next_conc"]) / E_REF
    r1, r2 = p["tox_ratio_primary"], p["tox_ratio_next"]
    hill = math.log((r1 * (1.0 - r2)) / (r2 * (1.0 - r1))) / math.log(u2 / u1)
    k50 = u1 * (r1 / (1.0 - r1)) ** (1.0 / hill)
    return k50, hill


def toxicity(cmp_id: str, u_tox: float) -> float:
    """Fractional loss of viable cells caused by the compound itself (0..1)."""
    if cmp_id == VEHICLE_ID or u_tox <= 0:
        return 0.0
    k50, hill = _TOX_CACHE[cmp_id]
    return (u_tox ** hill) / (k50 ** hill + u_tox ** hill)


def nrf2_activation(cm_id: str, cmp_id: str, u_pre: float) -> float:
    if cmp_id == VEHICLE_ID or u_pre <= 0:
        return 0.0
    p = COMPOUNDS[cmp_id]
    f = CELL_MODELS[cm_id]["nrf2_func"]
    return f * p["pot"] * u_pre / (KA_ACT + u_pre)


def gene_log2fc(cm_id: str, cmp_id: str, u_pre: float, pretreat_h: float) -> dict:
    cmpd_key = cmp_id
    """log2 fold-change of each target gene vs the matched vehicle, same cell model."""
    out = {g: 0.0 for g in TARGET_GENES}
    if cmp_id == VEHICLE_ID or u_pre <= 0:
        return out
    p = COMPOUNDS[cmp_id]
    a = nrf2_activation(cm_id, cmp_id, u_pre)
    coup = dict(p["coup"])
    coup["GCLC"] = _GCLC_COUP[cmp_id]
    for g in TARGET_GENES:
        val = coup.get(g, 0.0) * a
        if g == "HMOX1":
            # NRF2-independent stress component: present even in the knockout.
            ku = _INDEP_KU[cmpd_key]
            val += p["indep_hmox1"] * u_pre / (ku + u_pre)
        if pretreat_h < 12.0:
            val *= KINETIC_6H[g]
        out[g] = val
    return out


def capacity(cm_id: str, cmp_id: str, u_pre: float, u_chal: float) -> tuple[float, float]:
    """(adaptive, direct) additive contributions to antioxidant capacity."""
    if cmp_id == VEHICLE_ID:
        return 0.0, 0.0
    p = COMPOUNDS[cmp_id]
    lfc = gene_log2fc(cm_id, cmp_id, u_pre, 18.0)
    adaptive = AD_K * lfc["GCLC"]
    d_max = _DMAX[cmp_id]
    direct = 0.0
    if d_max > 0.0 and u_chal > 0.0:
        direct = d_max * u_chal / (p["ks"] + u_chal)
    return adaptive, direct


def neutralised_fraction(cmp_id: str, conc_um: float, present_in_medium: bool) -> float:
    """Fraction of the oxidant consumed extracellularly by the compound."""
    if cmp_id == VEHICLE_ID or not present_in_medium or conc_um <= 0:
        return 0.0
    k = COMPOUNDS[cmp_id]["neut_k"]
    if k <= 0:
        return 0.0
    x = k * conc_um
    return x / (1.0 + x)


def mean_state(cm_id: str, cmp_id: str, conc_um: float, challenge_um: float,
               washout: bool, injury_factor: float = 1.0) -> dict:
    """Noise-free biological state of a well.

    Returns relative densities (fractions of the vehicle unchallenged density for
    the same cell model), plus the quantities the readout models need.
    """
    e_pre = exposure_pre(cm_id, cmp_id, conc_um)
    u_pre = e_pre / E_REF
    retention = COMPOUNDS[cmp_id]["retention"] if cmp_id != VEHICLE_ID else 0.0
    e_chal = e_pre * retention if washout else e_pre
    u_chal = e_chal / E_REF

    present_in_medium = (not washout) and cmp_id != VEHICLE_ID and conc_um > 0
    conc_in_medium = conc_um if present_in_medium else 0.0

    adaptive, direct = capacity(cm_id, cmp_id, u_pre, u_chal)
    cap = 1.0 + adaptive + direct

    d_eff = challenge_um * (1.0 - neutralised_fraction(cmp_id, conc_um, present_in_medium))
    insult = d_eff * CELL_MODELS[cm_id]["suscept"] * injury_factor / cap
    ros_index = insult / I50
    s_inj = 1.0 / (1.0 + ros_index ** HILL) if insult > 0 else 1.0

    u_tox = 0.6 * u_pre + 0.4 * u_chal
    s_tox = 1.0 - toxicity(cmp_id, u_tox)

    return dict(
        e_pre=e_pre, e_chal=e_chal, u_pre=u_pre, u_chal=u_chal,
        conc_in_medium=conc_in_medium, adaptive=adaptive, direct=direct, cap=cap,
        insult=insult, ros_index=ros_index, s_inj=s_inj, s_tox=s_tox,
        live_rel=s_tox * s_inj, killed_rel=1.0 - s_tox * s_inj,
        live_rel_prechallenge=s_tox,
    )


# ---------------------------------------------------------------------------
# Back-solving: mechanism strength from the per-compound protection target
# ---------------------------------------------------------------------------

def _solve_mechanism() -> tuple[dict, dict]:
    """Derive, for every compound, either the GCLC coupling coefficient
    (`adaptive` mechanism) or the maximal direct-scavenging term (`direct`
    mechanism), so that the noise-free protection index in the parental line at
    the compound's primary concentration equals its `pi_target` exactly."""
    gclc, dmax = {}, {}
    wt = CELL_MODELS["CM_WT"]
    d_iso = wt["iso_tbhp"]
    s_veh = 1.0 / (1.0 + (d_iso * wt["suscept"] / I50) ** HILL)

    for cid, p in COMPOUNDS.items():
        conc = p["primary_conc"]
        e_pre = exposure_pre("CM_WT", cid, conc)
        u_pre = e_pre / E_REF
        s_tox = 1.0 - _tox_from_targets(cid, 0.6 * u_pre + 0.4 * u_pre)
        s_inj = (s_veh + p["pi_target"] * (1.0 - s_veh)) / s_tox
        s_inj = min(max(s_inj, 1e-6), 1.0 - 1e-9)
        insult = I50 * ((1.0 / s_inj) - 1.0) ** (1.0 / HILL)
        d_eff = d_iso * (1.0 - neutralised_fraction(cid, conc, True))
        cap = d_eff * wt["suscept"] / insult
        gain = cap - 1.0

        a = wt["nrf2_func"] * p["pot"] * u_pre / (KA_ACT + u_pre)
        if p["mechanism"] == "adaptive":
            gclc[cid] = gain / (AD_K * a)
            dmax[cid] = 0.0
        else:
            gclc[cid] = p["coup"].get("GCLC", 0.0)
            adaptive_base = AD_K * gclc[cid] * a
            dmax[cid] = (gain - adaptive_base) * (p["ks"] + u_pre) / u_pre
    return gclc, dmax


def _tox_from_targets(cmp_id: str, u_tox: float) -> float:
    k50, hill = _TOX_CACHE[cmp_id]
    if u_tox <= 0:
        return 0.0
    return (u_tox ** hill) / (k50 ** hill + u_tox ** hill)


_TOX_CACHE = {cid: toxicity_params(cid) for cid in COMPOUNDS}
_INDEP_KU = {cid: exposure_pre("CM_WT", cid, COMPOUNDS[cid]["primary_conc"]) / E_REF / 3.0
             for cid in COMPOUNDS}
_GCLC_COUP, _DMAX = _solve_mechanism()


def latent_parameter_dump() -> dict:
    """Everything latent, for the private authoring record."""
    return {
        "global_constants": dict(
            E_REF=E_REF, I50=I50, HILL=HILL, AD_K=AD_K, KA_ACT=KA_ACT, L0=L0,
            DEAD_COUNTABLE=DEAD_COUNTABLE, MET_LOSS=MET_LOSS,
            CHALLENGE_COMMON_UM=CHALLENGE_COMMON_UM,
        ),
        "assay_calibration": dict(
            MTT_BLANK=MTT_BLANK, MTT_AMP=MTT_AMP, MTT_REF_WAVELENGTH=MTT_REF_WAVELENGTH,
            LDH_BLANK=LDH_BLANK, LDH_SLOPE=LDH_SLOPE, PROBE_BG=PROBE_BG,
            PROBE_AMP=PROBE_AMP, PROBE_NODYE_BG=PROBE_NODYE_BG,
            PROBE_ROS_EXP=PROBE_ROS_EXP, QUENCH_STD_F=QUENCH_STD_F,
            FOX_BLANK=FOX_BLANK, FOX_SLOPE=FOX_SLOPE,
        ),
        "ct_anchors": CT0,
        "transcript_kinetics_fraction_at_6h": KINETIC_6H,
        "cell_models": CELL_MODELS,
        "compounds": COMPOUNDS,
        "physicochemical_descriptors": PHYSCHEM,
        "derived_toxicity_k50_hill": {k: list(v) for k, v in _TOX_CACHE.items()},
        "derived_hmox1_independent_saturation_u": _INDEP_KU,
        "derived_gclc_coupling": _GCLC_COUP,
        "derived_direct_scavenging_dmax": _DMAX,
        "concentration_ladder": CONC_LADDER,
    }
