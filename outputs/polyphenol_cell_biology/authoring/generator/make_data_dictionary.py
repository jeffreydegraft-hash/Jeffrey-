"""Builds data_dictionary.csv from the generated CSVs plus curated descriptions.

Fails loudly if any emitted column lacks a description, so the dictionary can
never drift out of sync with the data.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import pandas as pd

# (unit, value_type, allowed_values_or_range, description)
D: dict[tuple[str, str], tuple[str, str, str, str]] = {}


def d(file: str, col: str, unit: str, vtype: str, allowed: str, desc: str) -> None:
    D[(file, col)] = (unit, vtype, allowed, desc)


# --------------------------------------------------------------- compounds.csv
F = "compounds.csv"
d(F, "compound_id", "", "string", "PP01-PP08, VEH",
  "Test-article identifier. Neutral label; PP01-PP08 are fictional synthetic test articles. VEH is the vehicle control and is not a compound.")
d(F, "test_article_class", "", "string", "free text",
  "Descriptive class. Identical for all eight compounds; carries no information about activity.")
d(F, "molecular_weight_g_per_mol", "g/mol", "number", "180-611",
  "Molecular weight, used for unit conversions between mass, molar and molar-amount bases. Empty for the vehicle.")
d(F, "logp_calculated", "", "number", "0.3-3.9",
  "Calculated octanol/water partition coefficient. A physicochemical descriptor only; it is not predictive of the study conclusions.")
d(F, "max_dmso_solubility_mm", "mmol/L", "number", "3-30",
  "Maximum solubility in dimethyl sulfoxide. Bounds the achievable stock concentration.")
d(F, "dmso_stock_mm", "mmol/L", "number", "50",
  "Nominal stock concentration used to prepare dosing solutions.")
d(F, "purity_pct", "percent", "number", "97.8-99.8",
  "Analytical purity of the test article as supplied.")
d(F, "vehicle", "", "string", "DMSO",
  "Solvent used for all treatments, including the vehicle control.")
d(F, "final_vehicle_pct_v_v", "percent v/v", "number", "0.2",
  "Final vehicle concentration in the culture medium. Constant across every well including vehicle wells, so vehicle exposure is matched.")
d(F, "lcms_mrm_transition_m_z", "m/z", "string", "free text",
  "Multiple-reaction-monitoring transition used for LC-MS/MS quantification.")
d(F, "lloq_intracellular_pmol", "pmol on column", "number", "1.2-2.5",
  "Lower limit of quantification for the cell-lysate assay, on the amount-on-column basis. Values below this are reported as censored.")
d(F, "lloq_medium_um", "umol/L", "number", "0.035-0.060",
  "Lower limit of quantification for the medium assay.")
d(F, "internal_standard", "", "string", "free text",
  "Stable-isotope internal standard used for LC-MS/MS quantification.")

# ------------------------------------------------------------- cell_models.csv
F = "cell_models.csv"
d(F, "cell_model_id", "", "string", "CM_WT, CM_WT_VEC, CM_KO_A, CM_KO_A_VEC, CM_KO_A_RES, CM_KO_B, CM_KO_B_RES",
  "Cell model identifier used throughout the manifest.")
d(F, "parental_line", "", "string", "free text",
  "Parental cell line. A simulated human intestinal epithelial line; not a real cell line.")
d(F, "lineage", "", "string", "parental, clone_A, clone_B",
  "Editing lineage. clone_A and clone_B are INDEPENDENTLY derived knockout clones made with different guide RNAs, supplied so clone-specific explanations can be addressed.")
d(F, "nfe2l2_genotype", "", "string", "wild_type, NFE2L2_knockout, NFE2L2_knockout_with_NFE2L2_re_expression",
  "Functional NFE2L2 genotype of the model.")
d(F, "nfe2l2_edit_description", "", "string", "free text",
  "Nature of the genome edit, where applicable.")
d(F, "guide_rna", "", "string", "none, sgNFE2L2-1, sgNFE2L2-4",
  "Guide RNA used to derive the clone. Different guides for clone_A and clone_B.")
d(F, "transgene", "", "string", "none, empty_vector, NFE2L2_CDS",
  "Stably introduced construct. empty_vector models are the vector controls; NFE2L2_CDS models are the functional rescues.")
d(F, "selection_marker", "", "string", "none, puromycin",
  "Selection used after transduction.")
d(F, "nfe2l2_protein_by_immunoblot", "", "string", "detected, not_detected",
  "Independent verification of the knockout at the protein level.")
d(F, "passage_at_experiment", "passages", "integer", "13-15",
  "Passage number at which the experiments were performed.")
d(F, "population_doubling_time_h", "hours", "number", "21.5-24.2",
  "Population doubling time. Models differ slightly, which is why unchallenged densities differ between models.")
d(F, "seeding_density_1e3_per_well", "1e3 cells/well", "number", "12",
  "Seeding density for the 96-well assay panels.")
d(F, "challenge_agent", "", "string", "tert-butyl_hydroperoxide",
  "Oxidant used for every challenge in the study. Constant, so it is recorded here rather than on every manifest row.")
d(F, "challenge_duration_h", "hours", "number", "1.5",
  "Duration of oxidant exposure before the medium was replaced for recovery. Constant for every challenged well; unchallenged wells have no challenge period.")
d(F, "isoeffective_challenge_tbhp_um", "umol/L", "number", "118-200",
  "The cell-model-specific tert-butyl hydroperoxide dose used in the CHAL_ISO arm, chosen from the vehicle-only titration so that the different models sustain approximately comparable injury. Doses were chosen from the titration curves so the realised insult is closely comparable across models; the underlying susceptibility difference itself is large and is plainly visible in the A_TITRATION panel and in the CHAL_COMMON arm.")
d(F, "common_arm_challenge_tbhp_um", "umol/L", "number", "300",
  "The single oxidant dose applied to every cell model in the CHAL_COMMON arm. Because the models differ in baseline susceptibility, they sit at different points on their own injury curves in this arm.")

# ---------------------------------------------------------- sample_manifest.csv
F = "sample_manifest.csv"
d(F, "sample_id", "", "string", "SMPnnnnnn",
  "Unique sample (well or culture) identifier. Primary key; referenced by every measurement table. Identifiers are assigned by a random permutation and carry no information.")
d(F, "biological_experiment_id", "", "string", "BIO01-BIO07",
  "Independent biological experiment. THIS IS THE UNIT OF INFERENCE. Technical replicates are nested inside it.")
d(F, "reagent_batch_id", "", "string", "RB1, RB2",
  "Medium and serum lot. Each biological experiment was run on a single lot, so the lot is NESTED within the experiment (RB1 = BIO01-BIO03, RB2 = BIO04-BIO07) and a lot effect cannot be separated from a between-experiment effect. Every lot does contain every cell model and every treatment level, so neither is confounded with the lot. No graded quantity is affected, because every protection index is formed within one experiment against that experiment's own matched vehicle controls.")
d(F, "plate_id", "", "string", "free text",
  "Physical plate. Each plate carries several cell models and several treatments, so cell model is not inseparable from plate. Prefix indicates the assay family.")
d(F, "well_position", "", "string", "A1-H12 for 96_well, A1-D6 for 24_well, A1-C4 for 12_well",
  "Well position on the plate, always inside the grid implied by culture_format.")
d(F, "panel_id", "", "string", "A_TITRATION, B_DOSE_RESPONSE, D_COMMON_DOSE, R_PROBE, Q_TRANSCRIPT, X_EXPOSURE",
  "Design panel. Panels are uniform across compounds: no compound receives a panel, concentration or control another does not.")
d(F, "assay_panel", "", "string", "VIABILITY, OXIDATIVE_STRESS, QPCR, EXPOSURE",
  "Which measurement table holds this sample's readouts.")
d(F, "cell_model_id", "", "string", "see cell_models.csv",
  "Cell model used for this sample.")
d(F, "compound_id", "", "string", "PP01-PP08, VEH",
  "Test article applied during pretreatment. VEH is the vehicle control.")
d(F, "administered_conc_um", "umol/L", "number", "0, 1, 3, 10, 30, 50, 100, 200, 300, 600",
  "Concentration administered IN THE MEDIUM during pretreatment. This is the administered basis, not an intracellular concentration; intracellular exposure is measured separately in exposure_measurements.csv.")
d(F, "schedule_id", "", "string", "PRE_NOWASH, PRE_WASH",
  "Treatment schedule. PRE_NOWASH retains the compound through the challenge; PRE_WASH removes it with two medium washes before the challenge.")
d(F, "pretreatment_duration_h", "hours", "number", "6, 18",
  "Duration of compound pretreatment before challenge or harvest. 6 h applies only to the interim transcript samples.")
d(F, "challenge_id", "", "string", "CHAL_NONE, CHAL_ISO, CHAL_COMMON, CHAL_T050, CHAL_T075, CHAL_T150, CHAL_T250, CHAL_T400, CHAL_T700",
  "Oxidative challenge condition. CHAL_ISO uses the cell-model-specific isoeffective dose; CHAL_COMMON uses 300 uM for every model; CHAL_Tnnn are vehicle-only titration levels.")
d(F, "challenge_conc_um", "umol/L", "number", "0-700",
  "Actual oxidant concentration applied to this well. For CHAL_ISO this varies by cell model.")
d(F, "sampling_condition", "", "string", "empty, END_PRETREAT_NOWASH, POST_WASH_0P5H, POST_CHALLENGE_24H_NOWASH, POST_CHALLENGE_24H_WASH",
  "For exposure samples only: when the sample was taken. END_PRETREAT_NOWASH is the reference exposure condition. POST_WASH_0P5H gives the residual exposure 0.5 h after washout. Empty for non-exposure samples.")
d(F, "sampling_time_h_from_pretreatment_start", "hours", "number", "empty, 18, 18.5, 43.5",
  "For exposure samples only: time of sampling measured from the start of pretreatment. Empty for non-exposure samples.")
d(F, "probe_loaded", "", "string", "empty, yes, no",
  "For oxidative-stress samples only: whether the fluorescent probe was loaded. 'no' wells are the matched dye-free background controls that reveal compound autofluorescence. Empty for other samples.")
d(F, "readout_time_h_post_challenge", "hours", "number", "empty, 1, 24",
  "Time of measurement after the challenge. 24 h for viability, 1 h for the oxidative-stress probe. Empty for transcript and exposure samples, which are taken before or independently of the challenge timeline.")
d(F, "technical_replicate", "", "integer", "1-4",
  "Technical replicate index WITHIN a biological experiment. Technical replicates are not independent experiments and must not be counted as such.")
d(F, "culture_format", "", "string", "96_well, 24_well, 12_well",
  "Culture vessel format. Transcript and exposure samples use larger formats because those assays need more material. The well_position values and the number of wells per plate_id always respect this format: 96_well is an 8x12 grid (A1-H12), 24_well a 4x6 grid (A1-D6), 12_well a 3x4 grid (A1-C4).")

# ------------------------------------------------------- viability_readouts.csv
F = "viability_readouts.csv"
d(F, "sample_id", "", "string", "SMPnnnnnn",
  "Foreign key to sample_manifest.sample_id. One row per sample.")
d(F, "fields_imaged", "fields", "integer", "18",
  "Number of microscope fields counted per well.")
d(F, "imaged_area_fraction", "fraction", "number", "0.1",
  "Fraction of the well area covered by the counted fields. Constant across all wells. Divide counts by this to obtain per-well densities.")
d(F, "live_nuclei_count", "nuclei", "integer", ">=0",
  "Live nuclei counted across the imaged fields: nuclei NOT stained by the membrane-impermeant dye. THE PRIMARY ENDPOINT is derived from this: live_cell_density_1e3_per_well = live_nuclei_count / imaged_area_fraction / 1000.")
d(F, "dead_nuclei_count", "nuclei", "integer", ">=0",
  "Dead nuclei counted across the imaged fields: nuclei stained by the membrane-impermeant dye. A membrane-integrity measure. Not all killed cells remain countable; some detach or lyse, which is why the supernatant LDH activity is also reported.")
d(F, "ldh_activity_mu_per_l", "milliunits/L", "number", ">0",
  "Lactate dehydrogenase activity in the culture supernatant: an independent, release-based measure of loss of membrane integrity. Convert to a release index using the matched ldh_medium_blank and the cell-model-matched ldh_maximum_lysis controls in assay_controls.csv.")
d(F, "mtt_absorbance_570nm", "absorbance units", "number", ">0",
  "MTT formazan absorbance at 570 nm, read in the conditioned medium without a medium exchange. This is a REDOX-DEPENDENT readout and is vulnerable to direct reduction of the tetrazolium by a reducing compound; the matched cell-free controls in assay_controls.csv quantify that interference.")
d(F, "mtt_absorbance_630nm", "absorbance units", "number", ">0",
  "Reference/scatter channel at 630 nm. The MTT signal is mtt_absorbance_570nm minus mtt_absorbance_630nm.")
d(F, "readout_time_h_post_challenge", "hours", "number", "24",
  "Time of measurement after the challenge.")

# ------------------------------------------------ oxidative_stress_readouts.csv
F = "oxidative_stress_readouts.csv"
d(F, "sample_id", "", "string", "SMPnnnnnn",
  "Foreign key to sample_manifest.sample_id. One row per sample.")
d(F, "probe", "", "string", "DCFH-DA",
  "Fluorescent probe used to report intracellular oxidant load.")
d(F, "probe_loaded", "", "string", "yes, no",
  "Whether the probe was loaded. 'no' rows are the matched dye-free background wells: their signal is the plate background plus any compound autofluorescence, which is how autofluorescence interference is detected.")
d(F, "excitation_nm", "nm", "integer", "488",
  "Excitation wavelength.")
d(F, "emission_nm", "nm", "integer", "525",
  "Emission wavelength.")
d(F, "gain_setting", "", "integer", "80",
  "Detector gain. Constant across all wells.")
d(F, "fluorescence_au", "arbitrary units", "number", ">0",
  "Measured fluorescence. Interpretation requires both the dye-free background wells and the cell-free controls, because a compound can add signal (autofluorescence) or remove it (quenching of emitted light).")
d(F, "readout_time_h_post_challenge", "hours", "number", "1",
  "Time of measurement after the challenge.")

# ---------------------------------------------------------- qpcr_ct_values.csv
F = "qpcr_ct_values.csv"
d(F, "sample_id", "", "string", "SMPnnnnnn",
  "Foreign key to sample_manifest.sample_id. Several rows per sample, one per gene per reaction replicate.")
d(F, "target_gene", "", "string", "NQO1, HMOX1, GCLC, TXNRD1, NFE2L2, ACTB, RPLP0",
  "Amplified gene. NQO1, HMOX1, GCLC and TXNRD1 are the pathway-response genes. NFE2L2 is the edited gene itself, included to verify the models. ACTB and RPLP0 are the reference genes; their stability across treatments can be checked from these raw values rather than assumed. Note that HMOX1 has a substantial inducible component that does NOT require NFE2L2.")
d(F, "reaction_replicate", "", "integer", "1-3",
  "qPCR reaction replicate from the same cDNA. This is a technical replicate nested inside the biological experiment.")
d(F, "ct_value", "cycles", "number", "roughly 14-32",
  "Raw threshold cycle. Lower means more abundant. No normalisation has been applied: a shared RNA-input shift affects all genes in a sample, which is what the reference genes are for.")
d(F, "ct_flag", "", "string", "ok",
  "Reaction status. All experimental reactions amplified normally; no-template and no-reverse-transcriptase controls are in assay_controls.csv.")
d(F, "amplification_efficiency", "", "number", "1.96",
  "Measured amplification efficiency of the assay (2.0 would be perfect doubling each cycle). Constant across plates.")

# ----------------------------------------------------- exposure_measurements.csv
F = "exposure_measurements.csv"
d(F, "sample_id", "", "string", "SMPnnnnnn",
  "Foreign key to sample_manifest.sample_id. Several rows per sample: cell-lysate injection replicates plus one medium measurement.")
d(F, "compound_id", "", "string", "PP01-PP08",
  "Compound quantified. Matches the compound administered to that sample.")
d(F, "matrix", "", "string", "cell_lysate, medium",
  "Analysed matrix. cell_lysate gives intracellular exposure; medium gives the extracellular concentration actually present.")
d(F, "sampling_condition", "", "string", "END_PRETREAT_NOWASH, POST_WASH_0P5H, POST_CHALLENGE_24H_NOWASH, POST_CHALLENGE_24H_WASH",
  "When the sample was taken. END_PRETREAT_NOWASH is the reference condition for exposure matching. POST_WASH_0P5H quantifies how much compound actually remains after washout, so washout-resistant protection need not be assumed.")
d(F, "sampling_time_h_from_pretreatment_start", "hours", "number", "18, 18.5, 43.5",
  "Sampling time measured from the start of pretreatment.")
d(F, "injection_replicate", "", "integer", "1-2",
  "LC-MS injection replicate of the same extract. A technical replicate nested inside the biological experiment.")
d(F, "measured_value", "see measured_unit", "number", "empty when censored",
  "Measured quantity. For cell_lysate rows this is the AMOUNT ON COLUMN in pmol, NOT a concentration: divide by cell_equivalents_1e6 to obtain exposure in pmol per 1e6 cells. For medium rows it is a concentration in umol/L. EMPTY when qualifier is 'below_lloq'.")
d(F, "measured_unit", "", "string", "pmol_on_column, umol_per_litre",
  "Unit and basis of measured_value. The two matrices use different bases; do not mix them.")
d(F, "qualifier", "", "string", "measured, below_lloq",
  "Measurement status. 'below_lloq' means the result was left-censored below lloq_value: the true value lies between zero and lloq_value. It must not be read as zero and must not be imputed. Censoring occurs where expected: in cell lysate at the lowest administered concentrations (1, 3 and 10 uM), most often after washout; and in medium at every concentration in the two post-washout conditions, where the compound was removed. Nothing above 10 uM is censored in cell lysate, and no medium sample is censored outside the washout conditions.")
d(F, "cell_equivalents_1e6", "1e6 cells", "number", "empty for medium rows",
  "Number of cell equivalents analysed, in units of 1e6 cells. The denominator for converting the amount on column into exposure per cell. Empty for medium rows.")
d(F, "lloq_value", "see lloq_unit", "number", ">0",
  "Lower limit of quantification applying to this row's matrix.")
d(F, "lloq_unit", "", "string", "pmol_on_column, umol_per_litre",
  "Unit of lloq_value.")

# ---------------------------------------------------------- assay_controls.csv
F = "assay_controls.csv"
d(F, "control_id", "", "string", "CTLnnnnnn",
  "Unique control identifier. A separate namespace from sample_id: these wells contain no cells, or no template, so they deliberately do NOT join to sample_manifest.csv.")
d(F, "control_type", "", "string", "cell_free_mtt, cell_free_probe, fluorescein_standard_quench, cell_free_oxidant_neutralisation, peroxide_calibration_standard, ldh_medium_blank, ldh_maximum_lysis, qpcr_no_template, qpcr_no_reverse_transcriptase, lcms_calibration_standard, lcms_spike_recovery",
  "Which control this is. cell_free_mtt detects direct reduction of the tetrazolium by the compound. cell_free_probe, run with and without dye, separates compound autofluorescence from probe signal. fluorescein_standard_quench isolates quenching of emitted light using a fixed fluorophore. cell_free_oxidant_neutralisation measures direct extracellular consumption of the oxidant by the compound, with peroxide_calibration_standard providing the calibration. ldh_medium_blank and ldh_maximum_lysis bound the LDH release scale per cell model. The qPCR and LC-MS controls document assay specificity and recovery.")
d(F, "assay", "", "string", "MTT, OXIDATIVE_STRESS, PEROXIDE_FOX, LDH, QPCR, LCMS",
  "Assay the control belongs to.")
d(F, "compound_id", "", "string", "PP01-PP08, VEH, NONE",
  "Compound present in the control well. VEH for vehicle-only controls; NONE where no test article applies.")
d(F, "administered_conc_um", "umol/L", "number", "0-600",
  "Compound concentration in the control well, on the same administered basis as the sample manifest.")
d(F, "cell_model_id", "", "string", "CELL_FREE, see cell_models.csv",
  "CELL_FREE for controls containing no cells. The LDH maximum-lysis controls are cell-model-specific, because the release scale depends on how many cells were present.")
d(F, "challenge_id", "", "string", "CHAL_NONE, CHAL_ISO",
  "Whether the oxidant was present in the control well.")
d(F, "challenge_conc_um", "umol/L", "number", "0-400",
  "Oxidant concentration in the control well. For peroxide_calibration_standard rows this is the known standard concentration.")
d(F, "biological_experiment_id", "", "string", "BIO01-BIO07",
  "Biological experiment in which the control was run. Controls are run in every experiment so they can be matched to the samples they are used with.")
d(F, "plate_id", "", "string", "free text",
  "Plate on which the control was run.")
d(F, "technical_replicate", "", "integer", "1-3",
  "Technical replicate index within the biological experiment.")
d(F, "measured_quantity", "", "string", "mtt_absorbance_570nm, mtt_absorbance_630nm, fluorescence_au_probe_loaded, fluorescence_au_probe_absent, fluorescein_standard_fluorescence_au, peroxide_assay_absorbance_560nm, ldh_activity_mu_per_l, ct_value, lcms_peak_area_ratio, recovery_pct",
  "Which quantity this row reports. The table is in long format because the controls are heterogeneous.")
d(F, "value", "see unit", "number", "empty when undetermined",
  "Measured value. Empty ONLY where qualifier is 'undetermined' (no amplification within 40 cycles, i.e. the no-template and no-reverse-transcriptase controls). Rows with qualifier='below_lloq' are LC-MS calibration standards prepared below the limit of quantification and DO carry a value: the standard's nominal amount is known by construction, so its measured response is recorded even though it is sub-quantifiable.")
d(F, "unit", "", "string", "absorbance_units, arbitrary_units, milliunits_per_litre, cycles, ratio_to_internal_standard, percent",
  "Unit of value.")
d(F, "qualifier", "", "string", "measured, below_lloq, undetermined",
  "Measurement status. 'undetermined' is the expected result for no-template and no-reverse-transcriptase controls, and is the only status with an empty value. 'below_lloq' marks a calibration standard prepared below the limit of quantification, which still carries its measured response.")
d(F, "notes", "", "string", "free text",
  "Human-readable note on how the control was prepared. Descriptive only.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    args = ap.parse_args(argv)
    data = pathlib.Path(args.data)

    files = ["compounds.csv", "cell_models.csv", "sample_manifest.csv",
             "viability_readouts.csv", "oxidative_stress_readouts.csv",
             "qpcr_ct_values.csv", "exposure_measurements.csv", "assay_controls.csv"]
    rows, missing, extra = [], [], []
    described = set(D)
    for f in files:
        cols = pd.read_csv(data / f, nrows=3, low_memory=False).columns.tolist()
        for c in cols:
            key = (f, c)
            if key not in D:
                missing.append(key)
                continue
            unit, vtype, allowed, desc = D[key]
            rows.append(dict(file=f, column=c, unit=unit, value_type=vtype,
                             allowed_values_or_range=allowed, description=desc))
            described.discard(key)
    extra = sorted(described)
    if missing:
        print("ERROR: columns without a dictionary entry:", missing, file=sys.stderr)
        return 1
    if extra:
        print("ERROR: dictionary entries with no matching column:", extra, file=sys.stderr)
        return 1

    out = pd.DataFrame(rows, columns=["file", "column", "unit", "value_type",
                                      "allowed_values_or_range", "description"])
    out.to_csv(data / "data_dictionary.csv", index=False, encoding="utf-8",
               lineterminator="\n")
    print(f"  wrote data_dictionary.csv rows={len(out)} "
          f"bytes={(data / 'data_dictionary.csv').stat().st_size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
