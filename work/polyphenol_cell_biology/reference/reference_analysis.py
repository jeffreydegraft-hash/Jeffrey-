#!/usr/bin/env python3
"""
Reference analysis for the `polyphenol_cell_biology` benchmark.

Reads ONLY the solver-visible inputs (the CSV files, study_specification.json and
output_schema.json) and writes /app/results.csv. It never reads the generator's
simulation parameters, any latent archetype assignment, or an answer key: every
number it produces is reconstructed from the observable records under the
disclosed evaluation contract.

Implementation uses the Python standard library only, so it runs in a clean
environment with no third-party packages installed.

    python3 reference_analysis.py --data /app/data --out /app/results.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys
from collections import defaultdict

# --------------------------------------------------------------------------- IO


def read_csv(path: pathlib.Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fnum(s):
    """Parse a numeric field; empty string -> None (documented 'not applicable')."""
    if s is None:
        return None
    s = s.strip()
    if s == "" or s == "NA":
        return None
    return float(s)


# ------------------------------------------------------------------ statistics


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def t_interval(xs: list[float], tq: dict[str, float]) -> tuple[float, float, float]:
    """Point estimate and two-sided 95% Student-t interval, per the disclosed
    uncertainty convention. The t quantile comes from the table published in
    study_specification.json, indexed by degrees of freedom."""
    n = len(xs)
    m = mean(xs)
    if n < 2:
        return m, float("nan"), float("nan")
    t = tq[str(n - 1)]
    half = t * sd(xs) / math.sqrt(n)
    return m, m - half, m + half


# ------------------------------------------------------------------- analysis


class Analysis:
    WT = "CM_WT"
    KO_A = "CM_KO_A"
    KO_B = "CM_KO_B"
    RESCUE = "CM_KO_A_RES"
    PRIMARY_PANEL = "B_DOSE_RESPONSE"
    PRIMARY_SCHEDULE = "PRE_NOWASH"
    VEHICLE = "VEH"
    EXPOSURE_REF_CONDITION = "END_PRETREAT_NOWASH"
    MIN_MEASURED_EXPERIMENTS_FOR_EXPOSURE = 4

    def __init__(self, data_dir: pathlib.Path):
        self.dir = data_dir
        self.spec = json.loads((data_dir / "study_specification.json").read_text(
            encoding="utf-8"))
        self.tq = self.spec["uncertainty_convention"]["t_quantiles_two_sided_95pct"]
        self.ladder = [float(x) for x in
                       self.spec["experimental_design"]["concentration_ladder_um"]]
        self.theta_p = float(self.spec["classification"]["protection_status"]
                             ["threshold_theta_P"])
        self.theta_d = float(self.spec["classification"]["nrf2_dependence_status"]
                             ["threshold_theta_D"])
        self.interf_threshold = float(self.spec["classification"]["interference_flags"]
                                      ["threshold"])
        self.tox_floor = 0.85
        self.match_lo, self.match_hi = 0.70, 1.0 / 0.70

        self.manifest = {r["sample_id"]: r for r in
                         read_csv(data_dir / "sample_manifest.csv")}
        self.compounds = [r["compound_id"] for r in
                          read_csv(data_dir / "compounds.csv")
                          if r["compound_id"] != self.VEHICLE]
        self.bios = sorted({r["biological_experiment_id"]
                            for r in self.manifest.values()})

        self._index_viability()
        self._index_exposure()
        self._index_probe()
        self._index_controls()

    # ---------------------------------------------------------------- indexing

    def _index_viability(self) -> None:
        """Technical-replicate mean live-cell density per
        (biological experiment, cell model, compound, concentration, schedule,
        challenge, panel). The biological experiment stays the unit of inference:
        technical replicates are averaged inside it, never pooled across it."""
        acc = defaultdict(list)
        self.sample_ids_by_cond = defaultdict(list)
        for row in read_csv(self.dir / "viability_readouts.csv"):
            m = self.manifest[row["sample_id"]]
            frac = fnum(row["imaged_area_fraction"])
            density = fnum(row["live_nuclei_count"]) / frac / 1000.0
            key = (m["biological_experiment_id"], m["cell_model_id"],
                   m["compound_id"], fnum(m["administered_conc_um"]),
                   m["schedule_id"], m["challenge_id"], m["panel_id"])
            acc[key].append(density)
            self.sample_ids_by_cond[key].append(row["sample_id"])
        self.live = {k: mean(v) for k, v in acc.items()}

    def _index_exposure(self) -> None:
        """Mean intracellular exposure in pmol per 1e6 cells, per
        (cell model, compound, concentration, sampling condition, experiment).
        Only injections flagged 'measured' contribute; censored samples drop out."""
        per_sample = defaultdict(list)
        for row in read_csv(self.dir / "exposure_measurements.csv"):
            if row["matrix"] != "cell_lysate" or row["qualifier"] != "measured":
                continue
            val = fnum(row["measured_value"])
            cells = fnum(row["cell_equivalents_1e6"])
            if val is None or not cells:
                continue
            m = self.manifest[row["sample_id"]]
            key = (m["cell_model_id"], row["compound_id"],
                   fnum(m["administered_conc_um"]), row["sampling_condition"],
                   m["biological_experiment_id"])
            per_sample[key].append(val / cells)
        self.exposure_by_bio = {k: mean(v) for k, v in per_sample.items()}

    def _index_probe(self) -> None:
        acc = defaultdict(list)
        for row in read_csv(self.dir / "oxidative_stress_readouts.csv"):
            m = self.manifest[row["sample_id"]]
            key = (m["biological_experiment_id"], m["cell_model_id"],
                   m["compound_id"], fnum(m["administered_conc_um"]),
                   m["schedule_id"], m["challenge_id"], row["probe_loaded"])
            acc[key].append(fnum(row["fluorescence_au"]))
        self.probe = {k: mean(v) for k, v in acc.items()}

    def _index_controls(self) -> None:
        """Cell-free MTT signal (570 minus 630 on matched replicate wells), the
        fixed-fluorophore quench standard, and the LDH scale controls."""
        mtt = defaultdict(dict)
        quench = defaultdict(list)
        for row in read_csv(self.dir / "assay_controls.csv"):
            val = fnum(row["value"])
            if val is None:
                continue
            bio = row["biological_experiment_id"]
            cid, conc = row["compound_id"], fnum(row["administered_conc_um"])
            if row["control_type"] == "cell_free_mtt" and row["challenge_id"] == "CHAL_NONE":
                k = (bio, cid, conc, row["technical_replicate"])
                mtt[k][row["measured_quantity"]] = val
            elif row["control_type"] == "fluorescein_standard_quench":
                quench[(bio, cid, conc)].append(val)

        acc = defaultdict(list)
        for (bio, cid, conc, _rep), q in mtt.items():
            if "mtt_absorbance_570nm" in q and "mtt_absorbance_630nm" in q:
                acc[(bio, cid, conc)].append(
                    q["mtt_absorbance_570nm"] - q["mtt_absorbance_630nm"])
        self.cf_mtt = {k: mean(v) for k, v in acc.items()}
        self.quench_std = {k: mean(v) for k, v in quench.items()}

        acc = defaultdict(list)
        for row in read_csv(self.dir / "viability_readouts.csv"):
            m = self.manifest[row["sample_id"]]
            key = (m["biological_experiment_id"], m["cell_model_id"],
                   m["compound_id"], fnum(m["administered_conc_um"]),
                   m["schedule_id"], m["challenge_id"], m["panel_id"])
            acc[key].append(fnum(row["mtt_absorbance_570nm"])
                            - fnum(row["mtt_absorbance_630nm"]))
        self.cell_mtt = {k: mean(v) for k, v in acc.items()}

    # ----------------------------------------------------------- core estimands

    def _L(self, bio, cm, cid, conc, challenge, schedule=None):
        return self.live.get((bio, cm, cid, conc, schedule or self.PRIMARY_SCHEDULE,
                              challenge, self.PRIMARY_PANEL))

    def protection_series(self, cm: str, cid: str, conc: float) -> list[float]:
        """Per-biological-experiment protection index, primary condition."""
        out = []
        for bio in self.bios:
            trt = self._L(bio, cm, cid, conc, "CHAL_ISO")
            vc = self._L(bio, cm, self.VEHICLE, 0.0, "CHAL_ISO")
            vn = self._L(bio, cm, self.VEHICLE, 0.0, "CHAL_NONE")
            if trt is None or vc is None or vn is None or vn == vc:
                continue
            out.append((trt - vc) / (vn - vc))
        return out

    def tox_ratio(self, cid: str, conc: float) -> float | None:
        """Wild-type unchallenged viability ratio to vehicle; point estimate only."""
        trt, veh = [], []
        for bio in self.bios:
            t = self._L(bio, self.WT, cid, conc, "CHAL_NONE")
            v = self._L(bio, self.WT, self.VEHICLE, 0.0, "CHAL_NONE")
            if t is not None and v is not None:
                trt.append(t)
                veh.append(v)
        if not trt:
            return None
        return mean(trt) / mean(veh)

    def primary_concentration(self, cid: str) -> float | None:
        best = None
        for conc in sorted(self.ladder):
            r = self.tox_ratio(cid, conc)
            if r is not None and r >= self.tox_floor:
                best = conc
        return best

    def exposure_mean(self, cm: str, cid: str, conc: float) -> tuple[float | None, int]:
        vals = [self.exposure_by_bio[(cm, cid, conc, self.EXPOSURE_REF_CONDITION, b)]
                for b in self.bios
                if (cm, cid, conc, self.EXPOSURE_REF_CONDITION, b) in self.exposure_by_bio]
        if not vals:
            return None, 0
        return mean(vals), len(vals)

    def matched_ko_concentration(self, cid: str, primary: float):
        e_wt, _ = self.exposure_mean(self.WT, cid, primary)
        if not e_wt:
            return None, None
        best, best_key = None, None
        for conc in sorted(self.ladder):
            e_ko, n = self.exposure_mean(self.KO_A, cid, conc)
            if e_ko is None or n < self.MIN_MEASURED_EXPERIMENTS_FOR_EXPOSURE:
                continue
            ratio = e_ko / e_wt
            if not (self.match_lo <= ratio <= self.match_hi):
                continue
            key = abs(math.log(ratio))
            if best_key is None or key < best_key - 1e-12:
                best, best_key = conc, key
        return best, e_wt

    def paired_contrast(self, cid: str, primary: float, matched: float) -> list[float]:
        """Per-experiment difference WT(primary) minus KO_A(exposure matched).
        Paired, because both cell models were measured in the same experiments."""
        out = []
        for bio in self.bios:
            a = self._single_pi(bio, self.WT, cid, primary)
            b = self._single_pi(bio, self.KO_A, cid, matched)
            if a is not None and b is not None:
                out.append(a - b)
        return out

    def _single_pi(self, bio, cm, cid, conc):
        trt = self._L(bio, cm, cid, conc, "CHAL_ISO")
        vc = self._L(bio, cm, self.VEHICLE, 0.0, "CHAL_ISO")
        vn = self._L(bio, cm, self.VEHICLE, 0.0, "CHAL_NONE")
        if trt is None or vc is None or vn is None or vn == vc:
            return None
        return (trt - vc) / (vn - vc)

    # ------------------------------------------------------------ interference

    def mtt_index_series(self, cid: str, primary: float) -> list[float]:
        out = []
        for bio in self.bios:
            cf_c = self.cf_mtt.get((bio, cid, primary))
            cf_v = self.cf_mtt.get((bio, self.VEHICLE, 0.0))
            cell_v = self.cell_mtt.get((bio, self.WT, self.VEHICLE, 0.0,
                                        self.PRIMARY_SCHEDULE, "CHAL_NONE",
                                        self.PRIMARY_PANEL))
            if None in (cf_c, cf_v, cell_v) or cell_v == cf_v:
                continue
            out.append((cf_c - cf_v) / (cell_v - cf_v))
        return out

    def probe_autofluor_series(self, cid: str, primary: float) -> list[float]:
        out = []
        for bio in self.bios:
            nd_c = self.probe.get((bio, self.WT, cid, primary,
                                   self.PRIMARY_SCHEDULE, "CHAL_ISO", "no"))
            nd_v = self.probe.get((bio, self.WT, self.VEHICLE, 0.0,
                                   self.PRIMARY_SCHEDULE, "CHAL_ISO", "no"))
            ld_v = self.probe.get((bio, self.WT, self.VEHICLE, 0.0,
                                   self.PRIMARY_SCHEDULE, "CHAL_ISO", "yes"))
            if None in (nd_c, nd_v, ld_v) or ld_v == nd_v:
                continue
            out.append((nd_c - nd_v) / (ld_v - nd_v))
        return out

    def probe_quench_series(self, cid: str, primary: float) -> list[float]:
        out = []
        for bio in self.bios:
            c = self.quench_std.get((bio, cid, primary))
            v = self.quench_std.get((bio, self.VEHICLE, 0.0))
            if c is None or not v:
                continue
            out.append((v - c) / v)
        return out

    # --------------------------------------------------------------- per compound

    def evaluate(self, cid: str) -> dict:
        res = {"compound_id": cid}
        primary = self.primary_concentration(cid)
        if primary is None:
            res.update({k: "NA" for k in (
                "primary_concentration_um", "wt_primary_exposure_pmol_per_1e6_cells",
                "exposure_matched_ko_concentration_um", "protection_index_wt",
                "protection_index_wt_ci_low", "protection_index_wt_ci_high",
                "protection_index_ko_primary_conc",
                "protection_index_ko_exposure_matched", "protection_index_rescue",
                "nrf2_dependence_contrast", "nrf2_dependence_contrast_ci_low",
                "nrf2_dependence_contrast_ci_high", "evidence_sample_ids")})
            res["protection_status"] = "not_evaluable"
            res["nrf2_dependence_status"] = "not_assessable"
            res["interference_flags"] = "none"
            return res

        res["primary_concentration_um"] = primary

        wt = self.protection_series(self.WT, cid, primary)
        pi_wt, lo, hi = t_interval(wt, self.tq)
        res["protection_index_wt"] = pi_wt
        res["protection_index_wt_ci_low"] = lo
        res["protection_index_wt_ci_high"] = hi

        res["protection_index_ko_primary_conc"] = mean(
            self.protection_series(self.KO_A, cid, primary))
        res["protection_index_rescue"] = mean(
            self.protection_series(self.RESCUE, cid, primary))

        matched, e_wt = self.matched_ko_concentration(cid, primary)
        res["wt_primary_exposure_pmol_per_1e6_cells"] = e_wt if e_wt else "NA"
        res["exposure_matched_ko_concentration_um"] = matched if matched else "NA"

        # protection status
        if lo > self.theta_p:
            prot = "protected"
        elif hi < self.theta_p:
            prot = "not_protected"
        else:
            prot = "indeterminate"
        res["protection_status"] = prot

        if matched is not None:
            res["protection_index_ko_exposure_matched"] = mean(
                self.protection_series(self.KO_A, cid, matched))
            diffs = self.paired_contrast(cid, primary, matched)
            d, dlo, dhi = t_interval(diffs, self.tq)
            res["nrf2_dependence_contrast"] = d
            res["nrf2_dependence_contrast_ci_low"] = dlo
            res["nrf2_dependence_contrast_ci_high"] = dhi
        else:
            res["protection_index_ko_exposure_matched"] = "NA"
            res["nrf2_dependence_contrast"] = "NA"
            res["nrf2_dependence_contrast_ci_low"] = "NA"
            res["nrf2_dependence_contrast_ci_high"] = "NA"
            d = dlo = dhi = None

        # NRF2 dependence status, rules applied in the disclosed order
        if prot != "protected":
            dep = "not_assessable"
        elif matched is None:
            dep = "indeterminate"
        else:
            _, rlo, _ = t_interval(self.protection_series(self.RESCUE, cid, primary),
                                   self.tq)
            rescue_ok = rlo > self.theta_p
            _, alo, _ = t_interval(self.protection_series(self.KO_A, cid, primary),
                                   self.tq)
            _, blo, _ = t_interval(self.protection_series(self.KO_B, cid, primary),
                                   self.tq)
            # a lineage "shows protection" iff its interval lower bound clears theta_P
            lineages_agree = ((alo > self.theta_p) == (blo > self.theta_p))
            if not lineages_agree:
                # clone-specific explanation cannot be excluded; this test is applied
                # before both Delta tests, per the disclosed evaluation order
                dep = "indeterminate"
            elif dlo > self.theta_d and rescue_ok:
                dep = "nrf2_dependent"
            elif dhi < self.theta_d:
                dep = "not_nrf2_dependent"
            else:
                dep = "indeterminate"
        res["nrf2_dependence_status"] = dep

        # interference, assessed independently of protection
        flags = []
        _, mlo, _ = t_interval(self.mtt_index_series(cid, primary), self.tq)
        if mlo > self.interf_threshold:
            flags.append("mtt")
        _, alo2, _ = t_interval(self.probe_autofluor_series(cid, primary), self.tq)
        _, qlo, _ = t_interval(self.probe_quench_series(cid, primary), self.tq)
        if alo2 > self.interf_threshold or qlo > self.interf_threshold:
            flags.append("ros")
        res["interference_flags"] = ";".join(flags) if flags else "none"

        # evidence: one wild-type primary-condition well per biological experiment
        ev = []
        for bio in self.bios:
            key = (bio, self.WT, cid, primary, self.PRIMARY_SCHEDULE,
                   "CHAL_ISO", self.PRIMARY_PANEL)
            ids = sorted(self.sample_ids_by_cond.get(key, []))
            if ids:
                ev.append(ids[0])
        res["evidence_sample_ids"] = ";".join(ev) if ev else "NA"
        return res


COLUMNS = ["compound_id", "primary_concentration_um",
           "wt_primary_exposure_pmol_per_1e6_cells",
           "exposure_matched_ko_concentration_um", "protection_index_wt",
           "protection_index_wt_ci_low", "protection_index_wt_ci_high",
           "protection_index_ko_primary_conc",
           "protection_index_ko_exposure_matched", "protection_index_rescue",
           "nrf2_dependence_contrast", "nrf2_dependence_contrast_ci_low",
           "nrf2_dependence_contrast_ci_high", "protection_status",
           "nrf2_dependence_status", "interference_flags", "evidence_sample_ids"]

ROUND = {"primary_concentration_um": 1, "wt_primary_exposure_pmol_per_1e6_cells": 2,
         "exposure_matched_ko_concentration_um": 1, "protection_index_wt": 4,
         "protection_index_wt_ci_low": 4, "protection_index_wt_ci_high": 4,
         "protection_index_ko_primary_conc": 4,
         "protection_index_ko_exposure_matched": 4, "protection_index_rescue": 4,
         "nrf2_dependence_contrast": 4, "nrf2_dependence_contrast_ci_low": 4,
         "nrf2_dependence_contrast_ci_high": 4}


def fmt(col, v):
    if isinstance(v, str):
        return v
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "NA"
    if col in ROUND:
        return f"{round(v, ROUND[col]):.{ROUND[col]}f}"
    return str(v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/app/data")
    ap.add_argument("--out", default="/app/results.csv")
    args = ap.parse_args(argv)

    an = Analysis(pathlib.Path(args.data))
    rows = [an.evaluate(c) for c in sorted(an.compounds)]

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([fmt(c, r.get(c, "NA")) for c in COLUMNS])

    for r in rows:
        print(f"  {r['compound_id']}  conc={fmt('primary_concentration_um', r['primary_concentration_um']):>5s} "
              f"E_wt={fmt('wt_primary_exposure_pmol_per_1e6_cells', r['wt_primary_exposure_pmol_per_1e6_cells']):>8s} "
              f"mKO={fmt('exposure_matched_ko_concentration_um', r['exposure_matched_ko_concentration_um']):>5s} "
              f"PI_wt={fmt('protection_index_wt', r['protection_index_wt']):>7s} "
              f"[{fmt('protection_index_wt_ci_low', r['protection_index_wt_ci_low']):>7s},"
              f"{fmt('protection_index_wt_ci_high', r['protection_index_wt_ci_high']):>7s}] "
              f"D={fmt('nrf2_dependence_contrast', r['nrf2_dependence_contrast']):>7s} "
              f"[{fmt('nrf2_dependence_contrast_ci_low', r['nrf2_dependence_contrast_ci_low']):>7s},"
              f"{fmt('nrf2_dependence_contrast_ci_high', r['nrf2_dependence_contrast_ci_high']):>7s}] "
              f"{r['protection_status']:14s} {r['nrf2_dependence_status']:19s} "
              f"{r['interference_flags']}")
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
