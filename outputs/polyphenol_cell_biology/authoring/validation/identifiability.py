#!/usr/bin/env python3
"""Identifiability evidence: for each intended distinction, compute the contrast that
separates it, using SOLVER-VISIBLE DATA ONLY.

The point is not to re-derive the answers. It is to demonstrate that every competing
explanation the dataset is supposed to contain is actually separable from its
neighbours by a contrast a solver can compute — so the task is solvable on evidence
rather than guessable.

    python3 identifiability.py
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
T = {1: 12.706204736, 2: 4.302652730, 3: 3.182446305, 4: 2.776445105,
     5: 2.570581836, 6: 2.446911851, 7: 2.364624252}

man = pd.read_csv(DATA / "sample_manifest.csv", keep_default_na=False, low_memory=False)
via = pd.read_csv(DATA / "viability_readouts.csv")
ctl = pd.read_csv(DATA / "assay_controls.csv", keep_default_na=False)
exp = pd.read_csv(DATA / "exposure_measurements.csv", keep_default_na=False)
qpcr = pd.read_csv(DATA / "qpcr_ct_values.csv")
spec = json.loads((DATA / "study_specification.json").read_text())
LADDER = [float(x) for x in spec["experimental_design"]["concentration_ladder_um"]]
COMPOUNDS = [f"PP0{i}" for i in range(1, 9)]
BIOS = spec["experimental_design"]["replication"]["biological_experiments"]

V = via.merge(man, on="sample_id")
V["dens"] = V["live_nuclei_count"] / V["imaged_area_fraction"] / 1000.0
V["ldh"] = V["ldh_activity_mu_per_l"]
G = (V[V["panel_id"] == "B_DOSE_RESPONSE"]
     .groupby(["biological_experiment_id", "cell_model_id", "compound_id",
               "administered_conc_um", "schedule_id", "challenge_id"])
     [["dens", "ldh"]].mean())


def pi_series(cm, cid, conc, schedule="PRE_NOWASH", col="dens"):
    out = []
    for b in BIOS:
        try:
            t = G.loc[(b, cm, cid, conc, schedule, "CHAL_ISO"), col]
            vc = G.loc[(b, cm, "VEH", 0.0, schedule, "CHAL_ISO"), col]
            vn = G.loc[(b, cm, "VEH", 0.0, schedule, "CHAL_NONE"), col]
        except KeyError:
            continue
        out.append((t - vc) / (vn - vc))
    return np.array(out)


def ci(x):
    n = len(x)
    if n < 2:
        return float(np.mean(x)), float("nan"), float("nan")
    h = T[n - 1] * np.std(x, ddof=1) / np.sqrt(n)
    return float(np.mean(x)), float(np.mean(x) - h), float(np.mean(x) + h)


def tox_ratio(cid, conc, cm="CM_WT"):
    t = np.mean([G.loc[(b, cm, cid, conc, "PRE_NOWASH", "CHAL_NONE"), "dens"]
                 for b in BIOS])
    v = np.mean([G.loc[(b, cm, "VEH", 0.0, "PRE_NOWASH", "CHAL_NONE"), "dens"]
                 for b in BIOS])
    return t / v


def primary(cid):
    best = None
    for c in LADDER:
        if tox_ratio(cid, c) >= 0.85:
            best = c
    return best


# exposure
E = exp[(exp["matrix"] == "cell_lysate") & (exp["qualifier"] == "measured")].copy()
E["val"] = E["measured_value"].astype(float) / E["cell_equivalents_1e6"].astype(float)
E = E.merge(man[["sample_id", "cell_model_id", "administered_conc_um",
                 "biological_experiment_id"]], on="sample_id")
EP = (E.groupby(["sampling_condition", "cell_model_id", "compound_id",
                 "administered_conc_um"])["val"].mean())


def expo(cm, cid, conc, cond="END_PRETREAT_NOWASH"):
    try:
        return float(EP.loc[(cond, cm, cid, conc)])
    except KeyError:
        return float("nan")


# qPCR ddCt
Q = qpcr.merge(man[["sample_id", "cell_model_id", "compound_id",
                    "administered_conc_um", "biological_experiment_id",
                    "pretreatment_duration_h"]], on="sample_id")
QS = Q.groupby(["sample_id", "target_gene"])["ct_value"].mean().unstack()
QM = QS.join(man.set_index("sample_id")[["cell_model_id", "compound_id",
                                         "administered_conc_um",
                                         "biological_experiment_id",
                                         "pretreatment_duration_h"]])
QM["ref"] = QM[["ACTB", "RPLP0"]].mean(axis=1)


def lfc(gene, cm, cid, conc, t=18.0):
    sub = QM[(QM.cell_model_id == cm) & (QM.pretreatment_duration_h == t)]
    tr = sub[(sub.compound_id == cid) & (sub.administered_conc_um == conc)]
    ve = sub[(sub.compound_id == "VEH")]
    if tr.empty or ve.empty:
        return float("nan")
    return float(-((tr[gene] - tr["ref"]).mean() - (ve[gene] - ve["ref"]).mean()))


def main() -> int:
    rows = []
    print("=" * 112)
    print("A. PROTECTION BY TWO INDEPENDENT SURVIVAL ENDPOINTS vs THE REDOX READOUTS")
    print("   (interference shows up as a redox endpoint moving while the direct count does not)")
    print("=" * 112)
    print(f"  {'cmp':5s} {'prim':>5s} {'PI count':>20s} {'PI by LDH release':>18s} "
          f"{'PI by MTT signal':>17s}")
    V["mtt"] = V["mtt_absorbance_570nm"] - V["mtt_absorbance_630nm"]
    GM = (V[V["panel_id"] == "B_DOSE_RESPONSE"]
          .groupby(["biological_experiment_id", "cell_model_id", "compound_id",
                    "administered_conc_um", "schedule_id", "challenge_id"])
          [["mtt", "ldh"]].mean())
    for cid in COMPOUNDS:
        p = primary(cid)
        m, lo, hi = ci(pi_series("CM_WT", cid, p))
        # LDH: injury falls, so protection = fraction of the LDH excursion reversed
        ldhv = []
        for b in BIOS:
            t = G.loc[(b, "CM_WT", cid, p, "PRE_NOWASH", "CHAL_ISO"), "ldh"]
            vc = G.loc[(b, "CM_WT", "VEH", 0.0, "PRE_NOWASH", "CHAL_ISO"), "ldh"]
            vn = G.loc[(b, "CM_WT", "VEH", 0.0, "PRE_NOWASH", "CHAL_NONE"), "ldh"]
            ldhv.append((vc - t) / (vc - vn))
        mttv = []
        for b in BIOS:
            t = GM.loc[(b, "CM_WT", cid, p, "PRE_NOWASH", "CHAL_ISO"), "mtt"]
            vc = GM.loc[(b, "CM_WT", "VEH", 0.0, "PRE_NOWASH", "CHAL_ISO"), "mtt"]
            vn = GM.loc[(b, "CM_WT", "VEH", 0.0, "PRE_NOWASH", "CHAL_NONE"), "mtt"]
            mttv.append((t - vc) / (vn - vc))
        print(f"  {cid:5s} {p:>5.0f} {m:>8.3f} [{lo:>6.3f},{hi:>6.3f}] "
              f"{np.mean(ldhv):>18.3f} {np.mean(mttv):>17.3f}")
        rows.append(dict(compound=cid, primary=p, pi_count=m, pi_ldh=float(np.mean(ldhv)),
                         pi_mtt=float(np.mean(mttv))))

    print()
    print("=" * 112)
    print("B. WASHOUT CONTRAST AND MEASURED RESIDUAL EXPOSURE")
    print("   (persistent cellular protection survives washout; extracellular chemistry does not)")
    print("=" * 112)
    print(f"  {'cmp':5s} {'PI no-wash':>11s} {'PI washout':>11s} {'retained PI':>12s} "
          f"{'residual exposure':>18s} {'cell-free oxidant':>18s}")
    fox = ctl[ctl.control_type == "cell_free_oxidant_neutralisation"]
    foxv = fox[fox.compound_id == "VEH"]["value"].astype(float).mean()
    for cid in COMPOUNDS:
        p = primary(cid)
        a = ci(pi_series("CM_WT", cid, p))[0]
        b = ci(pi_series("CM_WT", cid, p, "PRE_WASH"))[0]
        e0 = expo("CM_WT", cid, p)
        e1 = expo("CM_WT", cid, p, "POST_WASH_0P5H")
        fc = fox[(fox.compound_id == cid) & (fox.administered_conc_um == p)]["value"].astype(float).mean()
        neut = 1.0 - (fc - 0.031) / (foxv - 0.031)
        print(f"  {cid:5s} {a:>11.3f} {b:>11.3f} {b / a if abs(a) > 0.05 else float('nan'):>12.2f} "
              f"{e1 / e0:>17.1%} {neut:>17.1%}")
        rows[COMPOUNDS.index(cid)].update(pi_washout=b, residual_fraction=e1 / e0,
                                          oxidant_neutralised=float(neut))

    print()
    print("=" * 112)
    print("C. KNOCKOUT / WILD-TYPE MEASURED EXPOSURE RATIO ACROSS THE LADDER")
    print("   (* marks a rung inside the disclosed 0.70-1.4286 matching window)")
    print("=" * 112)
    print("  cmp  " + "".join(f"{c:>9.0f}" for c in LADDER) + "   matched")
    for cid in COMPOUNDS:
        p = primary(cid)
        ew = expo("CM_WT", cid, p)
        line, best, bk = "", None, None
        for c in LADDER:
            ek = expo("CM_KO_A", cid, c)
            r = ek / ew
            ok = 0.70 <= r <= 1.0 / 0.70
            if ok and (bk is None or abs(np.log(r)) < bk):
                best, bk = c, abs(np.log(r))
            line += f"{r:>8.3f}{'*' if ok else ' '}"
        print(f"  {cid} {line}   {best}")
        # nan-safe: the lowest ladder rung is censored for some compounds
        ratios = [expo("CM_KO_A", cid, c) / ew for c in LADDER]
        ratios = [r for r in ratios if r == r]
        rows[COMPOUNDS.index(cid)].update(matched_ko_conc=best,
                                          ko_wt_exposure_ratio_max=max(ratios))

    print()
    print("=" * 112)
    print("D. GENOTYPE COMPARISON: SAME ADMINISTERED DOSE vs MATCHED MEASURED EXPOSURE")
    print("   (the pair of contrasts that separates a delivery effect from a pathway effect)")
    print("=" * 112)
    print(f"  {'cmp':5s} {'PI wt':>8s} {'PI ko same dose':>16s} {'PI ko matched':>14s} "
          f"{'PI rescue':>10s} {'PI ko_B':>9s}")
    for cid in COMPOUNDS:
        p = primary(cid)
        ew = expo("CM_WT", cid, p)
        best, bk = None, None
        for c in LADDER:
            r = expo("CM_KO_A", cid, c) / ew
            if 0.70 <= r <= 1.0 / 0.70 and (bk is None or abs(np.log(r)) < bk):
                best, bk = c, abs(np.log(r))
        a = ci(pi_series("CM_WT", cid, p))[0]
        bd = ci(pi_series("CM_KO_A", cid, p))[0]
        bm = ci(pi_series("CM_KO_A", cid, best))[0] if best else float("nan")
        rs = ci(pi_series("CM_KO_A_RES", cid, p))[0]
        kb = ci(pi_series("CM_KO_B", cid, p))[0]
        print(f"  {cid:5s} {a:>8.3f} {bd:>16.3f} {bm:>14.3f} {rs:>10.3f} {kb:>9.3f}")
        rows[COMPOUNDS.index(cid)].update(pi_ko_same_dose=bd, pi_ko_matched=bm,
                                          pi_rescue=rs, pi_ko_b=kb)

    print()
    print("=" * 112)
    print("E. PATHWAY RESPONSE (log2 fold change, 18 h) IN WILD TYPE AND IN THE KNOCKOUT")
    print("   (gene induction is NOT evidence of protection; HMOX1 has an NRF2-independent component)")
    print("=" * 112)
    print(f"  {'cmp':5s} " + "".join(f"{g + ' WT':>11s}" for g in
                                     ("NQO1", "GCLC", "HMOX1")) +
          "".join(f"{g + ' KO':>11s}" for g in ("NQO1", "GCLC", "HMOX1")))
    for cid in COMPOUNDS:
        p = primary(cid)
        pq = min([c for c in (10.0, 50.0, 100.0, 300.0)], key=lambda c: abs(np.log(c / p)))
        vals = [lfc(g, "CM_WT", cid, pq) for g in ("NQO1", "GCLC", "HMOX1")] + \
               [lfc(g, "CM_KO_A", cid, pq) for g in ("NQO1", "GCLC", "HMOX1")]
        print(f"  {cid:5s} " + "".join(f"{v:>11.3f}" for v in vals))
        rows[COMPOUNDS.index(cid)].update(
            lfc_nqo1_wt=vals[0], lfc_gclc_wt=vals[1], lfc_hmox1_wt=vals[2],
            lfc_nqo1_ko=vals[3], lfc_gclc_ko=vals[4], lfc_hmox1_ko=vals[5],
            qpcr_conc_used=pq)

    print()
    print("=" * 112)
    print("F. BASELINE SUSCEPTIBILITY FROM THE VEHICLE-ONLY OXIDANT TITRATION")
    print("   (survival fraction of the unchallenged vehicle control, per cell model)")
    print("=" * 112)
    TT = (V[V["panel_id"] == "A_TITRATION"]
          .groupby(["cell_model_id", "challenge_conc_um"])["dens"].mean())
    base = (V[(V["panel_id"] == "B_DOSE_RESPONSE") & (V["compound_id"] == "VEH")
              & (V["challenge_id"] == "CHAL_NONE") & (V["schedule_id"] == "PRE_NOWASH")]
            .groupby("cell_model_id")["dens"].mean())
    doses = sorted({d for (_c, d) in TT.index})
    print("  cell model      " + "".join(f"{d:>8.0f}" for d in doses) + "    iso dose  S(iso)")
    cmtab = pd.read_csv(DATA / "cell_models.csv").set_index("cell_model_id")
    tit = {}
    for cm in base.index:
        line = "".join(f"{TT.loc[(cm, d)] / base[cm]:>8.3f}" for d in doses)
        iso = float(cmtab.loc[cm, "isoeffective_challenge_tbhp_um"])
        siso = np.mean([G.loc[(b, cm, "VEH", 0.0, "PRE_NOWASH", "CHAL_ISO"), "dens"]
                        for b in BIOS]) / base[cm]
        print(f"  {cm:15s} {line}   {iso:>8.0f}  {siso:>6.3f}")
        tit[cm] = dict(iso=iso, s_iso=float(siso),
                       curve={str(d): float(TT.loc[(cm, d)] / base[cm]) for d in doses})

    print()
    print("=" * 112)
    print("G. COMMON-OXIDANT-DOSE ARM: the same arm on a raw scale gives a DIFFERENT answer")
    print("=" * 112)
    GC = (V[V["panel_id"] == "D_COMMON_DOSE"]
          .groupby(["biological_experiment_id", "cell_model_id", "compound_id",
                    "administered_conc_um"])["dens"].mean())
    print(f"  {'cmp':5s} {'conc':>5s} {'WT gain / unchal':>17s} {'KO gain / unchal':>17s} "
          f"{'naive contrast':>15s}   correct exposure-matched contrast")
    for cid in COMPOUNDS:
        p = primary(cid)
        cc = min([10.0, 30.0, 100.0], key=lambda c: abs(np.log(c / p)))
        out = {}
        for cm in ("CM_WT", "CM_KO_A"):
            g = []
            for b in BIOS:
                t = GC.loc[(b, cm, cid, cc)]
                vc = GC.loc[(b, cm, "VEH", 0.0)]
                un = G.loc[(b, cm, "VEH", 0.0, "PRE_NOWASH", "CHAL_NONE"), "dens"]
                g.append((t - vc) / un)
            out[cm] = float(np.mean(g))
        ew = expo("CM_WT", cid, p)
        best, bk = None, None
        for c in LADDER:
            r = expo("CM_KO_A", cid, c) / ew
            if 0.70 <= r <= 1.0 / 0.70 and (bk is None or abs(np.log(r)) < bk):
                best, bk = c, abs(np.log(r))
        corr = (ci(pi_series("CM_WT", cid, p))[0] - ci(pi_series("CM_KO_A", cid, best))[0]
                ) if best else float("nan")
        print(f"  {cid:5s} {cc:>5.0f} {out['CM_WT']:>17.3f} {out['CM_KO_A']:>17.3f} "
              f"{out['CM_WT'] - out['CM_KO_A']:>15.3f}   {corr:>10.3f}")
        rows[COMPOUNDS.index(cid)].update(naive_common_dose_contrast=
                                          out['CM_WT'] - out['CM_KO_A'],
                                          correct_contrast=corr)

    out = ROOT / "validation" / "identifiability_report.json"
    out.write_text(json.dumps({"per_compound": rows, "titration": tit}, indent=2,
                              default=float) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
