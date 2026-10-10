"""Noise-free calibration report for the simulation core (PRIVATE authoring tool).

Prints, for every compound:
  * the toxicity ratio curve across the whole administered-concentration ladder
    (which fixes the primary concentration under the disclosed selection rule),
  * the noise-free protection index in every cell model at the primary
    concentration, with and without washout,
  * the measured-exposure ratio of the knockout to the wild type across the
    ladder, and which concentration (if any) qualifies as exposure-matched,
  * the resulting noise-free classifications under the disclosed rules,
  * target-gene induction and the three interference indices.

This is a design-verification tool. It reads latent parameters, so it is never
part of the reference analysis.
"""

from __future__ import annotations

import math
import sys

import simcore as S

MATCH_LO, MATCH_HI = 0.70, 1.0 / 0.70   # disclosed exposure-overlap window
THETA_P = 0.15
THETA_D = 0.15
TOL_TOX = 0.85


def veh_challenged_survival(cm_id: str) -> float:
    cm = S.CELL_MODELS[cm_id]
    return 1.0 / (1.0 + (cm["iso_tbhp"] * cm["suscept"] / S.I50) ** S.HILL)


def pi_noisefree(cm_id: str, cmp_id: str, conc: float, washout: bool = False,
                 challenge: str = "ISO") -> float:
    cm = S.CELL_MODELS[cm_id]
    d = cm["iso_tbhp"] if challenge == "ISO" else S.CHALLENGE_COMMON_UM
    veh_chal = S.mean_state(cm_id, S.VEHICLE_ID, 0.0, d, washout)["live_rel"]
    veh_none = S.mean_state(cm_id, S.VEHICLE_ID, 0.0, 0.0, washout)["live_rel"]
    trt = S.mean_state(cm_id, cmp_id, conc, d, washout)["live_rel"]
    return (trt - veh_chal) / (veh_none - veh_chal)


def tox_ratio(cm_id: str, cmp_id: str, conc: float) -> float:
    trt = S.mean_state(cm_id, cmp_id, conc, 0.0, False)["live_rel"]
    veh = S.mean_state(cm_id, S.VEHICLE_ID, 0.0, 0.0, False)["live_rel"]
    return trt / veh


def primary_concentration(cmp_id: str) -> float | None:
    best = None
    for c in S.CONC_LADDER:
        if tox_ratio("CM_WT", cmp_id, c) >= TOL_TOX:
            best = c
    return best


def matched_ko_conc(cmp_id: str, primary: float) -> tuple[float | None, float]:
    e_wt = S.exposure_pre("CM_WT", cmp_id, primary)
    best, best_key, best_ratio = None, None, float("nan")
    for c in S.CONC_LADDER:
        e_ko = S.exposure_pre("CM_KO_A", cmp_id, c)
        if e_ko <= 0:
            continue
        r = e_ko / e_wt
        if MATCH_LO <= r <= MATCH_HI:
            key = abs(math.log(r))
            if best_key is None or key < best_key - 1e-12 or (
                    abs(key - best_key) <= 1e-12 and c < best):
                best, best_key, best_ratio = c, key, r
    return best, best_ratio


def interference_indices(cmp_id: str, primary: float) -> dict:
    p = S.COMPOUNDS[cmp_id]
    # cell-free MTT increment vs cellular vehicle signal
    cf = p["mtt_cf"] * primary
    cell_sig = S.MTT_AMP * S.L0
    mtt_idx = cf / cell_sig
    # probe autofluorescence vs the cellular probe signal in challenged vehicle
    veh = S.mean_state("CM_WT", S.VEHICLE_ID, 0.0, S.CELL_MODELS["CM_WT"]["iso_tbhp"], False)
    cell_probe = S.PROBE_AMP * veh["live_rel_prechallenge"] * veh["ros_index"] ** S.PROBE_ROS_EXP
    auto_idx = (p["probe_auto"] * primary) / cell_probe
    q = p["probe_quench"] * primary
    quench_idx = q / (1.0 + q)
    return dict(mtt=mtt_idx, probe_auto=auto_idx, probe_quench=quench_idx)


def apparent_mtt_pi(cmp_id: str, conc: float) -> float:
    """Protection index computed (incorrectly) from the MTT signal in WT."""
    cm = "CM_WT"
    d = S.CELL_MODELS[cm]["iso_tbhp"]
    p = S.COMPOUNDS[cmp_id]

    def sig(cid, c, dose):
        st = S.mean_state(cm, cid, c, dose, False)
        met = 1.0 - S.MET_LOSS * (1.0 - st["s_inj"])
        od = S.MTT_AMP * S.L0 * S.CELL_MODELS[cm]["growth"] * st["live_rel"] * met
        if cid != S.VEHICLE_ID:
            od += S.COMPOUNDS[cid]["mtt_cf"] * st["conc_in_medium"]
            od += S.COMPOUNDS[cid]["mtt_ic"] * st["u_chal"] * st["live_rel"]
        return od

    return (sig(cmp_id, conc, d) - sig(S.VEHICLE_ID, 0, d)) / (
        sig(S.VEHICLE_ID, 0, 0) - sig(S.VEHICLE_ID, 0, d))


def classify(cmp_id: str) -> dict:
    primary = primary_concentration(cmp_id)
    if primary is None:
        return dict(compound=cmp_id, primary=None, status="no_tolerated_conc")
    pi_wt = pi_noisefree("CM_WT", cmp_id, primary)
    pi_ko_primary = pi_noisefree("CM_KO_A", cmp_id, primary)
    pi_kob_primary = pi_noisefree("CM_KO_B", cmp_id, primary)
    pi_res = pi_noisefree("CM_KO_A_RES", cmp_id, primary)
    pi_wash = pi_noisefree("CM_WT", cmp_id, primary, washout=True)
    mko, mratio = matched_ko_conc(cmp_id, primary)
    pi_ko_matched = pi_noisefree("CM_KO_A", cmp_id, mko) if mko else float("nan")
    contrast = (pi_wt - pi_ko_matched) if mko else float("nan")

    prot = "protected" if pi_wt > THETA_P else "not_protected"
    if prot != "protected":
        dep = "not_assessable"
    elif mko is None:
        dep = "indeterminate"
    elif contrast > THETA_D:
        dep = "nrf2_dependent" if pi_res > THETA_P else "indeterminate"
    else:
        dep = "not_nrf2_dependent"

    idx = interference_indices(cmp_id, primary)
    flags = []
    if idx["mtt"] > 0.10:
        flags.append("mtt")
    if idx["probe_auto"] > 0.10 or idx["probe_quench"] > 0.10:
        flags.append("ros")

    return dict(
        compound=cmp_id, archetype=S.COMPOUNDS[cmp_id]["archetype"], primary=primary,
        e_wt=S.exposure_pre("CM_WT", cmp_id, primary),
        pi_wt=pi_wt, pi_ko_primary=pi_ko_primary, pi_kob_primary=pi_kob_primary,
        pi_res=pi_res, pi_wash=pi_wash, matched_ko=mko, match_ratio=mratio,
        pi_ko_matched=pi_ko_matched, contrast=contrast,
        protection=prot, dependence=dep, interference=";".join(flags) or "none",
        mtt_idx=idx["mtt"], auto_idx=idx["probe_auto"], quench_idx=idx["probe_quench"],
        apparent_mtt_pi=apparent_mtt_pi(cmp_id, primary),
    )


def main() -> int:
    print("=" * 110)
    print("VEHICLE-CHALLENGED SURVIVAL FRACTION PER CELL MODEL (isoeffective dose)")
    print("=" * 110)
    for cm in S.CELL_MODEL_ORDER:
        print(f"  {cm:14s} iso_tbhp={S.CELL_MODELS[cm]['iso_tbhp']:6.1f} uM   "
              f"S_veh(ISO)={veh_challenged_survival(cm):.4f}   "
              f"S_veh(COMMON 300)={1.0/(1.0+(S.CHALLENGE_COMMON_UM*S.CELL_MODELS[cm]['suscept']/S.I50)**S.HILL):.4f}")

    print()
    print("=" * 110)
    print("TOXICITY RATIO IN CM_WT ACROSS THE LADDER (selection rule: highest conc with ratio >= 0.85)")
    print("=" * 110)
    hdr = "  cmpd  " + "".join(f"{c:>9.0f}" for c in S.CONC_LADDER) + "   primary"
    print(hdr)
    for cid in S.COMPOUND_ORDER:
        row = "".join(f"{tox_ratio('CM_WT', cid, c):>9.3f}" for c in S.CONC_LADDER)
        print(f"  {cid}  {row}   {primary_concentration(cid)}")

    print()
    print("=" * 110)
    print("KO_A / WT MEASURED-EXPOSURE RATIO AT THE PRIMARY CONCENTRATION (window 0.700 - 1.4286)")
    print("=" * 110)
    print("  cmpd  " + "".join(f"{c:>9.0f}" for c in S.CONC_LADDER) + "   matched")
    for cid in S.COMPOUND_ORDER:
        primary = primary_concentration(cid)
        e_wt = S.exposure_pre("CM_WT", cid, primary)
        row = ""
        for c in S.CONC_LADDER:
            r = S.exposure_pre("CM_KO_A", cid, c) / e_wt
            mark = "*" if MATCH_LO <= r <= MATCH_HI else " "
            row += f"{r:>8.3f}{mark}"
        mko, mr = matched_ko_conc(cid, primary)
        print(f"  {cid}  {row}   {mko}")

    print()
    print("=" * 110)
    print("NOISE-FREE PROTECTION INDICES AND CLASSIFICATIONS")
    print("=" * 110)
    rows = [classify(cid) for cid in S.COMPOUND_ORDER]
    print(f"  {'cmpd':5s} {'prim':>5s} {'E_WT':>7s} {'PI_WT':>7s} {'PI_KOA':>7s} {'PI_KOB':>7s} "
          f"{'PI_RES':>7s} {'PI_wash':>8s} {'mKO':>5s} {'PI_mKO':>7s} {'contr':>7s}")
    for r in rows:
        print(f"  {r['compound']:5s} {r['primary']:>5.0f} {r['e_wt']:>7.1f} {r['pi_wt']:>7.3f} "
              f"{r['pi_ko_primary']:>7.3f} {r['pi_kob_primary']:>7.3f} {r['pi_res']:>7.3f} "
              f"{r['pi_wash']:>8.3f} {str(r['matched_ko']):>5s} {r['pi_ko_matched']:>7.3f} "
              f"{r['contrast']:>7.3f}")
    print()
    print(f"  {'cmpd':5s} {'protection':14s} {'nrf2_dependence':20s} {'interference':12s} "
          f"{'mtt_i':>7s} {'auto_i':>7s} {'quench_i':>8s} {'MTT-PI':>7s}")
    for r in rows:
        print(f"  {r['compound']:5s} {r['protection']:14s} {r['dependence']:20s} "
              f"{r['interference']:12s} {r['mtt_idx']:>7.3f} {r['auto_idx']:>7.3f} "
              f"{r['quench_idx']:>8.3f} {r['apparent_mtt_pi']:>7.3f}")

    print()
    print("=" * 110)
    print("TARGET-GENE log2FC AT THE PRIMARY CONCENTRATION, 18 h PRETREATMENT")
    print("=" * 110)
    print(f"  {'cmpd':5s} {'cell_model':13s} " + "".join(f"{g:>9s}" for g in S.TARGET_GENES))
    for cid in S.COMPOUND_ORDER:
        primary = primary_concentration(cid)
        for cm in ["CM_WT", "CM_KO_A", "CM_KO_A_RES"]:
            u = S.exposure_pre(cm, cid, primary) / S.E_REF
            lfc = S.gene_log2fc(cm, cid, u, 18.0)
            print(f"  {cid:5s} {cm:13s} " + "".join(f"{lfc[g]:>9.3f}" for g in S.TARGET_GENES))

    print()
    print("=" * 110)
    print("BASELINE-SUSCEPTIBILITY TRAP: naive contrast computed in the COMMON-DOSE arm")
    print("=" * 110)
    print(f"  {'cmpd':5s} {'PI_WT(common)':>14s} {'PI_KOA(common)':>15s} {'naive contrast':>15s} "
          f"{'correct contrast':>17s}")
    for cid in S.COMPOUND_ORDER:
        primary = primary_concentration(cid)
        if primary not in S.CONC_COMMON_ARM:
            cc = min(S.CONC_COMMON_ARM, key=lambda c: abs(math.log(c / primary)))
        else:
            cc = primary
        a = pi_noisefree("CM_WT", cid, cc, challenge="COMMON")
        b = pi_noisefree("CM_KO_A", cid, cc, challenge="COMMON")
        r = classify(cid)
        print(f"  {cid:5s} {a:>14.3f} {b:>15.3f} {a - b:>15.3f} {r['contrast']:>17.3f}"
              f"   (common arm conc {cc:.0f} uM)")

    print()
    print("=" * 110)
    print("DERIVED LATENT MECHANISM STRENGTHS")
    print("=" * 110)
    for cid in S.COMPOUND_ORDER:
        k50, h = S._TOX_CACHE[cid]
        print(f"  {cid}: mechanism={S.COMPOUNDS[cid]['mechanism']:9s} "
              f"gclc_coup={S._GCLC_COUP[cid]:7.3f} d_max={S._DMAX[cid]:7.3f} "
              f"tox_k50={k50:.5f} tox_hill={h:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
