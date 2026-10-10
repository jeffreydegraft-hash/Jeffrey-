# Adversarial audit of the solver-visible dataset
**Study:** `polyphenol_cell_biology` (synthetic)
**Scope audited:** `/home/user/Jeffrey-/work/polyphenol_cell_biology/data/` only. The generator, reference,
design, verifier and validation source directories were not read, listed or imported.
**Date:** 2026-10-10

---

## 0. Headline verdict

| Area | Verdict |
|---|---|
| Answer leakage | **No leak found.** No column, string, note, identifier, row order or physicochemical descriptor lets any graded field be read off without the intended analysis. |
| Join integrity | **Clean.** All four measurement tables resolve 1:1 / 1:N into the manifest with zero orphans in either direction; all declared uniqueness constraints hold. |
| Units / ranges | **Coherent and plausible**, with two documentation mismatches and one cosmetic physical implausibility (below). |
| Replication | **As the specification states** (7 biological experiments; 4 viability wells, 3 probe wells + 1 dye-free, 3 qPCR reactions, 2 LC-MS injections). The *task brief* I was given said "6 biological experiments, 3 technical replicates" — that is wrong; the spec and the data agree with each other on 7 and 4/3. |
| Batch balance | **One real failure:** `reagent_batch_id` is perfectly nested inside `biological_experiment_id`, contradicting the data dictionary. Cell model and treatment are fully crossed with batch and plate, as claimed. |
| Missingness | **Confined to censoring and the no-amplification controls**, but the specification's description of *where* censoring occurs is narrower than the data. |
| Identifiability | **All six spot-check contrasts are available and informative**, and all four `nrf2_dependence_status` branches are exercised by at least one compound. |

---

## PART 1 — LEAKAGE

### 1.1 Vocabulary scan
Every `.csv` and `.json` in the data directory was lower-cased and scanned for
`protect`, `interfer`, `scaveng`, `hit`, `positive control`, `true`, `label`, `class`,
`archetype`, `mechanis`, `dependent`, `inducer`, `quench`, `autofluor`, `toxic`, `active`,
`inactive`, `decoy`, `answer`, `key`, `expected`, `ground`, `gold`, `rank`, `score`,
`index`, `flag`, `verdict`, `status`, `effect`.

Result: **the five measurement/manifest tables are completely clean.**

* `sample_manifest.csv`, `viability_readouts.csv`, `oxidative_stress_readouts.csv`,
  `exposure_measurements.csv` — **zero** hits for any term.
* `qpcr_ct_values.csv` — one hit, the column name `ct_flag` (single value `ok`, 58,212/58,212 rows).
* `assay_controls.csv` — one hit, `quench` ×1533, from `control_type='fluorescein_standard_quench'`.
  That is the *name of a control assay applied identically to all eight compounds* (189 rows each),
  not a statement about any compound.
* `compounds.csv` — one hit, the column `test_article_class`, whose value is
  `"synthetic polyphenol-like test article"` for **all eight** compounds (`VEH` = `"vehicle control"`).
  No archetype, no class distinction.
* `cell_models.csv` — one hit, `isoeffective_...`, a design parameter.
* Hits in `study_specification.json`, `output_schema.json` and `data_dictionary.csv` are all
  *definitional* (they define `protection_index`, `nrf2_dependence_status`, the interference flags
  and their thresholds). None is attached to a compound identifier.

### 1.2 Free-text fields
`assay_controls.notes` is the only free-text field in any data table. It has **21 distinct values**
and is populated on 4,018 of 16,282 rows. Every value is a preparation description:
`"compound + oxidant co-incubated 1.5 h, no cells"`, `"calibration standard 200 uM tert-butyl hydroperoxide"`,
`"blank lysate spiked at 100 pmol"`, `"1 uM fluorescein standard, cell free"`,
`"no amplification within 40 cycles"`, `"vehicle, unchallenged, fully lysed with 1% Triton X-100"`, etc.
**No note mentions any `PP` identifier** (checked: 0 of 21 contain the substring `PP`), so no note can be
tied to a compound. `compounds.internal_standard` is the same string for all eight.

### 1.3 Identifiers and row order
* `sample_id` is `SMP000001`–`SMP076160`: an **exact permutation of 1..76,160** (verified), i.e. a dense
  random relabelling. Variance of the numeric part explained by design factors:
  η²(`sample_id` ~ `compound_id`) = **4.1e-05**; η²(~ `cell_model_id`) = **9.9e-05**.
  Mean `sample_id` number by compound spans only **447** around a grand mean of 38,080 (0.6% of range).
* Row order carries nothing: Spearman(row index, id number) = **+0.004** (manifest), **+0.005** (viability),
  **+0.007** (probe), **−0.003** (qPCR), **−0.011** (exposure), **−0.003** (controls).
  No table is sorted by its key. η²(row order ~ `compound_id`) = **6.6e-05**;
  η²(row order ~ `challenge_id`) = **5.8e-05**.
* `control_id` likewise: η²(~ `compound_id`) = **0.0075**, η²(~ `control_type`) = **0.0117** — negligible.
* **The protected set is not adjacent in ID order.** Protected under the disclosed rule:
  `PP02, PP03, PP05, PP06, PP08`; not protected: `PP01, PP04, PP07`. The two interfering compounds are
  `PP04` and `PP06`. No contiguous block, no parity pattern, no low/high split.

### 1.4 Design symmetry across compounds (an asymmetry would itself be a hint)
Rows per compound per panel are **byte-identical across all eight compounds**:

| panel | rows per compound |
|---|---|
| `B_DOSE_RESPONSE` | 5,544 |
| `D_COMMON_DOSE` | 588 |
| `Q_TRANSCRIPT` | 336 |
| `R_PROBE` | 1,512 |
| `X_EXPOSURE` | 1,260 |

Stronger test: the **full design fingerprint** — the set of
(`panel_id`, `cell_model_id`, `administered_conc_um`, `schedule_id`, `challenge_id`,
`pretreatment_duration_h`, `sampling_condition`, `probe_loaded`, `readout_time_h_post_challenge`,
`biological_experiment_id`, `technical_replicate`) tuples — is **identical for all eight compounds**,
**9,240 design cells each**. Same for controls: `cell_free_mtt` 756, `cell_free_probe` 756,
`cell_free_oxidant_neutralisation` 189, `fluorescein_standard_quench` 189,
`lcms_calibration_standard` 49, `lcms_spike_recovery` 21 — identical per compound, with identical
concentration sets. **No compound has a panel, concentration, control or replicate the others lack.**

### 1.5 Physicochemical descriptors as a shortcut
Target variables derived under the disclosed rules (the correlation target only):

| compound | primary conc (µM) | PI_WT | 95% CI | protection_status | MTT idx | autofluor idx | quench idx | flags |
|---|---|---|---|---|---|---|---|---|
| PP01 | 100 | 0.0112 | [−0.022, 0.044] | not_protected | −0.0017 | −0.0012 | 0.0031 | none |
| PP02 | 50 | 0.5908 | [0.562, 0.620] | protected | 0.0001 | 0.0000 | −0.0076 | none |
| PP03 | 10 | 0.5103 | [0.485, 0.536] | protected | 0.0009 | −0.0011 | 0.0029 | none |
| PP04 | 300 | −0.0015 | [−0.032, 0.029] | not_protected | 0.4896 | 0.2053 | 0.3365 | mtt;ros |
| PP05 | 100 | 0.5411 | [0.518, 0.564] | protected | 0.0024 | 0.0003 | 0.0305 | none |
| PP06 | 100 | 0.5792 | [0.557, 0.602] | protected | 0.0037 | −0.0164 | 0.3391 | ros |
| PP07 | 10 | −0.0042 | [−0.036, 0.028] | not_protected | −0.0045 | −0.0018 | 0.0068 | none |
| PP08 | 50 | 0.5555 | [0.520, 0.591] | protected | −0.0002 | −0.0009 | 0.0065 | none |

**No descriptor separates protected from not-protected.** Exact (n=8, 56 combinations)
two-sided rank-sum p-values against the protected/not split:

| descriptor | p | ρ vs PI | ρ vs primary conc | perm p (primary conc) | best single-threshold accuracy |
|---|---|---|---|---|---|
| `molecular_weight_g_per_mol` | 1.000 | +0.357 | +0.593 | 0.129 | ≤0.750 |
| `logp_calculated` | 0.143 | +0.286 | −0.346 | 0.400 | ≤0.750 |
| `max_dmso_solubility_mm` | **0.071** | −0.667 | +0.259 | 0.536 | ≤0.750 |
| `purity_pct` | 1.000 | −0.357 | −0.593 | 0.129 | ≤0.750 |
| `lloq_intracellular_pmol` | 1.000 | +0.146 | **+0.671** | 0.079 | ≤0.750 |
| `lloq_medium_um` | 1.000 | +0.146 | +0.671 | 0.079 | ≤0.750 |

Ranges overlap in every case, e.g. `max_dmso_solubility_mm`: protected [3.0, 15.0] vs
not-protected [12.0, 30.0]; `logp_calculated`: protected [0.52, 3.81] vs not [0.31, 1.48].
Chance accuracy for a 5/3 split is 0.625, so **no descriptor beats 0.750** (i.e. still 2 of 8 wrong).
See §4 for the two marginal associations I regard as coincidence rather than leakage.

### 1.6 Precomputed quantities
Column inventory of every table was reviewed. There is **no** score, index, ratio, fold-change,
ΔΔCt, normalised value, protection index, exposure-per-cell, release index or flag anywhere.
Everything that the graded outputs need must be derived:
* viability gives raw `live_nuclei_count` / `dead_nuclei_count` plus the constant
  `imaged_area_fraction=0.1` and `fields_imaged=18` — no density;
* MTT is given as the two raw channels (`570nm`, `630nm`), never as a difference;
* qPCR gives raw `ct_value` only (`amplification_efficiency` constant 1.96) — no ΔCt, no ΔΔCt;
* exposure gives `measured_value` (pmol **on column**) and `cell_equivalents_1e6` separately,
  never the per-cell quotient;
* LDH is raw `ldh_activity_mu_per_l`; the blank and max-lysis bounds sit in a separate table.
The only pre-supplied design numbers (`isoeffective_challenge_tbhp_um`,
`common_arm_challenge_tbhp_um`) are *inputs*, not outcomes.

### 1.7 One hygiene issue (not a leak)
`data/_generator_seed.json` contains `{"seed": 20261010}` and is **not declared** in
`study_specification.json.input_files`. It discloses no result on its own — but it is an
undeclared generator artefact sitting in the solver-visible mount, and with access to the
(correctly quarantined) generator it would reproduce the dataset exactly. **Recommend removing it
from the mount.**

---

## PART 2 — COHERENCE AND JOIN INTEGRITY

### 2.1 Foreign keys and uniqueness — all pass
| check | result |
|---|---|
| `sample_manifest.sample_id` unique | **yes**, 76,160/76,160 |
| `assay_controls.control_id` unique | **yes**, 16,282/16,282 |
| orphan `sample_id` in viability / probe / qPCR / exposure | **0 / 0 / 0 / 0** |
| manifest `VIABILITY` rows with a viability readout | 51,044 / 51,044 (0 missing, 0 extra) |
| manifest `OXIDATIVE_STRESS` rows with a probe readout | 12,264 / 12,264 |
| manifest `QPCR` rows with qPCR rows | 2,772 / 2,772 |
| manifest `EXPOSURE` rows with exposure rows | 10,080 / 10,080 |
| `viability_readouts.sample_id` duplicated | 0 (one row per sample) |
| `oxidative_stress_readouts.sample_id` duplicated | 0 (one row per sample) |
| (`sample_id`,`target_gene`,`reaction_replicate`) duplicated | 0 (58,212 rows = 2,772 × 7 × 3) |
| (`sample_id`,`matrix`,`injection_replicate`) duplicated | 0 (30,240 rows = 10,080 × (2 lysate + 1 medium)) |
| (`plate_id`,`well_position`) duplicated | 0 |
| `exposure_measurements.compound_id` == manifest `compound_id` | **100%** |
| controls deliberately do not join to the manifest | confirmed (`cell_model_id='CELL_FREE'` except the 147 cell-model-specific `ldh_maximum_lysis` rows) |

### 2.2 Units and ranges — coherent and plausible
* **Ct values:** global range **15.617 – 29.015**, no NAs, `ct_flag='ok'` on all 58,212 rows.
  Per gene: ACTB 15.62–18.93 (mean 17.45), RPLP0 17.14–20.37 (18.95), NQO1 19.16–27.12,
  HMOX1 21.62–27.56, GCLC 20.43–27.52, TXNRD1 22.48–27.88, NFE2L2 20.50–29.02. Sane 40-cycle window.
* **Reference-gene stability (checked, not assumed):** within each cell model, the mean
  treated-minus-vehicle Ct shift is **−0.18 to +0.13 cycles** for ACTB and **−0.18 to +0.13** for RPLP0.
  Per compound the mean shift of the two-gene average is **−0.09 to +0.005** cycles
  (PP01 −0.029, PP02 −0.023, PP03 −0.051, PP04 +0.005, PP05 −0.092, PP06 −0.057, PP07 −0.005, PP08 −0.040),
  and by concentration −0.053 to −0.021. The *per-sample* spread is larger (SD ≈ 0.43, |max| ≈ 1.9 cycles)
  but it is a **shared RNA-input shift**: the ACTB−RPLP0 difference is tight
  (**mean −1.501, SD 0.091, range −1.816 to −1.202**) and the non-induced NFE2L2 amplicon moves with it.
  That is exactly what the dictionary claims, and it is what the two reference genes correct.
* **Model verification via the NFE2L2 amplicon** (ΔCt vs the two-gene reference):
  CM_WT **6.74**, CM_KO_A **9.45**, CM_KO_A_VEC **9.49**, CM_KO_B **9.18** (≈2.4–2.7 cycles higher,
  i.e. transcript down ~5–6-fold, consistent with frameshift-triggered decay),
  CM_KO_A_RES **3.79**, CM_KO_B_RES **3.65** (re-expression). SDs ≤0.082. Consistent with
  `nfe2l2_protein_by_immunoblot`.
* **Absorbances positive:** `mtt_absorbance_570nm` 0.1013–1.6755; `mtt_absorbance_630nm` 0.0323–0.0589;
  **minimum MTT signal (570−630) = +0.0568** — never negative.
* **Fluorescence positive:** 50.4 – 4563.3 AU; `probe='DCFH-DA'`, ex 488, em 525, gain 80 constant.
* **Counts:** `live_nuclei_count` 1–5,462, `dead_nuclei_count` 0–2,832, **all integers, all ≥0**.
* **LDH:** 251.1 – 4,236.0 mU/L; blank mean 317.3; max-lysis 2,764–2,968 by cell model.
* **Concentrations:** `administered_conc_um` takes **only** {0, 1, 3, 10, 30, 50, 100, 200, 300, 600} —
  the published ladder plus 0 for vehicle. Nothing off-ladder.
* **Challenge doses match `cell_models.csv` exactly.** `CHAL_ISO` per model:
  CM_WT 200, CM_WT_VEC 194, CM_KO_A 118, CM_KO_A_VEC 115, CM_KO_A_RES 179, CM_KO_B 123, CM_KO_B_RES 185 —
  identical to `isoeffective_challenge_tbhp_um`, one value per model. `CHAL_COMMON` = 300 for all seven.
  `CHAL_T050/075/150/250/400/700` = 50/75/150/250/400/700. `CHAL_NONE` = 0 on every row.
* **LLOQ values match `compounds.csv`** per compound, in both matrices
  (lysate 1.2–2.5 pmol; medium 0.035–0.060 µM), `measured_unit` never mixed across matrices
  (`cell_lysate`→`pmol_on_column`, `medium`→`umol_per_litre`). `cell_equivalents_1e6` 0.79–1.31,
  empty on every medium row and present on every lysate row.
* **Medium concentrations recover the administered dose** (CM_WT, END_PRETREAT_NOWASH):
  0.93–0.99 µM at 1 µM, 9.0–9.5 at 10, 46.4–47.5 at 50, 92.3–96.8 at 100, 552–571 at 600,
  monotone for all eight compounds.
* **Control assays behave:** peroxide calibration is linear in every experiment (**R² 0.99967–0.99993**);
  LC-MS spike recovery **87.3–103.5%**; all 98 qPCR NTC/NRT rows are `undetermined`.

### 2.3 Replication — matches the specification
* **7 biological experiments** BIO01–BIO07 (spec: `n_biological_experiments: 7`,
  `t_quantile_for_graded_quantities: 2.446911851` = t(0.975, 6) ✓).
* **Viability: exactly 4 wells** per (experiment × cell model × compound × concentration × schedule ×
  challenge × panel × readout) — `{4: 12761}` design cells, **no cell with any other count**.
* **Probe: exactly 3** dye-loaded wells and **exactly 1** dye-free well per condition
  (3,066 conditions each; 9,198 + 3,066 = 12,264 rows).
* **qPCR: 1 culture** per condition (2,772), **7 genes × 3 reaction replicates** for every one of them
  (`{7: 2772}` genes/sample, `{3: 19404}` replicates per sample-gene).
* **Exposure: 1 culture** per condition (10,080), **2 cell-lysate injections + 1 medium injection** for
  every one (`{('cell_lysate',2): 10080, ('medium',1): 10080}`).
* `technical_replicate` ranges: VIABILITY 1–4, OXIDATIVE_STRESS 1–3, QPCR 1, EXPOSURE 1 — consistent.
* Panels match the spec exactly: `A_TITRATION` = VEH only, 7 models, PRE_NOWASH, six titration levels;
  `B_DOSE_RESPONSE` = 9-point ladder + 0, CHAL_NONE/CHAL_ISO, PRE_WASH present in exactly
  **CM_WT, CM_KO_A, CM_KO_A_VEC, CM_KO_A_RES**; `D_COMMON_DOSE` = 10/30/100 µM, 7 models;
  `Q_TRANSCRIPT` = 10/50/100/300 µM, **6 models** (CM_WT_VEC excluded), 6 h and 18 h, CHAL_NONE only;
  `R_PROBE` = 3 models, full ladder; `X_EXPOSURE` = **5 models**, full ladder (no 0 µM), four sampling
  conditions with the washout conditions appearing **only** on PRE_WASH and the no-wash conditions
  **only** on PRE_NOWASH.

### 2.4 Batch balance — **one real failure**
* Every biological experiment contains **all 7 cell models**, **all 9 compound levels** (8 + VEH), and
  **exactly 4,097 distinct design cells** — identical for BIO01 … BIO07. Treatment and cell model are
  therefore never nested inside an experiment. ✓
* **No plate contains only one cell model: 0 of 1,064 plates.** Distribution of cell models per plate:
  7 models on 380 plates, 6 on 202, 5 on 221, 4 on 2, 3 on 257, 2 on 2. Compounds per plate: 8 on 631,
  9 on 302, 7 on 119, 6 on 10, 5 on 2. ✓
* Cell model is **not** nested inside reagent batch: all 7 models appear in both RB1 and RB2
  (e.g. CM_WT 6,690 / 8,920); every (batch × compound) cell has ≥960 rows. ✓
* **FAILURE — `reagent_batch_id` is perfectly nested inside `biological_experiment_id`:**
  `RB1` = BIO01, BIO02, BIO03 (10,880 rows each) and `RB2` = BIO04–BIO07 (10,880 each), with
  **zero overlap**. `data_dictionary.csv`, row `sample_manifest.csv,reagent_batch_id`, states
  *"Crosses the biological experiments; every batch contains every cell model and every treatment."*
  The second clause is true; **the first is false.** Consequence: a medium/serum-lot effect is
  perfectly collinear with a 3-vs-4 partition of the units of inference and cannot be estimated
  separately. Magnitude is modest and smaller than the between-experiment spread — vehicle unchallenged
  live density is 39.33 (RB1) vs 42.11 (RB2) ×10³/well, while individual experiments run
  34.83 (BIO03) to 46.68 (BIO06) — and because every protection index is formed *within* an experiment
  against that experiment's own matched vehicle controls, **no graded quantity is biased**. But the
  dictionary sentence should be corrected or the batch assignment re-randomised.
* Plates never span experiments (0 of 1,064), which is normal and not a confound given the above.
* Position effects were checked as well: vehicle unchallenged density is 40.83 on edge wells vs
  40.93 on inner wells, and compound shares differ by at most 0.035 between edge and inner.

### 2.5 Missingness — confined, with a documentation mismatch
Missing cells by table (all accounted for):
* `sample_manifest`: `sampling_condition` and `sampling_time_h_from_pretreatment_start` empty on
  **66,080** rows = every non-exposure sample (76,160 − 10,080 ✓); `probe_loaded` empty on **63,896**
  = every non-probe sample (76,160 − 12,264 ✓); `readout_time_h_post_challenge` empty on **12,852**
  = qPCR 2,772 + exposure 10,080 ✓. All are the declared "does not apply" case.
* `viability_readouts`, `oxidative_stress_readouts`, `qpcr_ct_values`: **zero missing values anywhere.**
* `exposure_measurements`: `measured_value` empty on **4,793** rows; `qualifier=='below_lloq'`
  **matches `measured_value.isna()` exactly, 1:1, on all 30,240 rows.** `cell_equivalents_1e6`
  empty on exactly the 10,080 medium rows.
* `assay_controls`: `value` empty on **98** rows, all of them `qpcr_no_template` (49) and
  `qpcr_no_reverse_transcriptase` (49) with `qualifier='undetermined'` — exactly the declared case.
  `notes` empty on 12,264 rows (an optional descriptive field).
* **No other missing value exists in any file.**

**Mismatch (minor, documentation):** `study_specification.json`
`missing_value_conventions.below_lloq` and the dictionary both say censoring occurs
*"at the lowest administered concentration, and after washout"*. The actual distribution of the
4,793 censored rows is:

| matrix | sampling condition | 1 µM | 3 µM | 10 µM | 30 µM | 50 µM | 100 µM |
|---|---|---|---|---|---|---|---|
| cell_lysate | END_PRETREAT_NOWASH | 141 | 0 | 0 | – | – | – |
| cell_lysate | POST_CHALLENGE_24H_NOWASH | 161 | 2 | 0 | – | – | – |
| cell_lysate | POST_CHALLENGE_24H_WASH | 551 | 461 | 120 | – | – | – |
| cell_lysate | POST_WASH_0P5H | 530 | 181 | 5 | – | – | – |
| medium | POST_CHALLENGE_24H_WASH | 280 | 280 | 280 | 280 | 280 | 128 |
| medium | POST_WASH_0P5H | 280 | 280 | 280 | 253 | 20 | 0 |

So censoring also reaches the **second and third** ladder points (3 and 10 µM), and 163 lysate rows are
censored at `POST_CHALLENGE_24H_NOWASH`, which is neither "the lowest concentration" (2 of them) nor
"after washout". Every instance is physically sensible — the 24 h post-challenge no-wash samples have
decayed, and the washout samples are depleted — but the sentence is narrower than the data.
**Crucially this does not affect the graded exposure quantity:** at the reference condition
`END_PRETREAT_NOWASH` censoring occurs **only at 1 µM** (CM_KO_A 37, CM_KO_A_VEC 40, CM_KO_B 37,
CM_KO_A_RES 14, CM_WT 13 injections), so every candidate concentration from 3 µM upward has measured
values in all 7 experiments except PP08 at 1 µM (4 of 7 — exactly at the rule's ≥4 minimum, and it
fails the window anyway). Censored fraction of lysate rows by concentration: 1 µM 61.7%, 3 µM 28.8%,
10 µM 5.6%, **0% at 30 µM and above**.

### 2.6 Cosmetic physical implausibility
`culture_format` disagrees with the well grid for the non-96-well panels. All `well_position` values
come from the 96-well nomenclature A1–H12 (96 distinct values, none outside the grid), and:
* the 210 `XP_*` exposure plates are labelled `culture_format='6_well'` but carry **48 distinct wells**
  each (rows A–D × columns 1–12);
* the 63 `QP_*` transcript plates are labelled `12_well` but carry **12 to 48** wells (up to A–D × 1–12).

**266 plate records exceed their declared format capacity.** A 6-well plate has no well `D11`.
Nothing in the graded analysis touches `plate_id`, `well_position` or `culture_format`, so this is
cosmetic — but it is an internal inconsistency a careful solver will notice. Either widen the format
label (e.g. one `plate_id` = a rack of plates) or renumber the wells.

### 2.7 One more documentation nit
`data_dictionary.csv` says `assay_controls.value` is *"Empty where qualifier is 'undetermined' ...
or 'below_lloq'"*. There are **70 rows with `qualifier='below_lloq'` that do carry a value**
(all `lcms_calibration_standard`, `lcms_peak_area_ratio` 0.0 – 0.00516 — the zero and 2 pmol standards).
Scientifically right (a sub-LLOQ standard still has a peak-area ratio) but contrary to the dictionary,
and these rows feed no graded quantity.

### 2.8 Plausibility note on the LDH release index
Using the disclosed recipe (`ldh_medium_blank` by experiment, `ldh_maximum_lysis` by cell model ×
experiment), the derived index spans **−0.027 to 1.228**, with **7.2%** of wells below 0 and **3.0%**
above 1. For a noisy ratio bounded by two small control sets this is expected, and the index is only the
*corroborating* endpoint, not graded — but an implementation that clips to [0,1] would silently diverge.

---

## PART 3 — IDENTIFIABILITY SPOT CHECK

Primary concentrations recovered from the disclosed selection rule (ratio of means, tolerated ≥0.85,
highest tolerated point) — `tox_ratio` in CM_WT, CHAL_NONE, PRE_NOWASH, panel B, 24 h:

| cmp | 1 | 3 | 10 | 30 | 50 | 100 | 200 | 300 | 600 | primary |
|---|---|---|---|---|---|---|---|---|---|---|
| PP01 | 0.986 | 1.000 | 0.992 | 0.996 | 0.977 | **0.935** | 0.738 | 0.505 | 0.188 | **100** |
| PP02 | 0.990 | 0.995 | 0.997 | 0.974 | **0.951** | 0.727 | 0.258 | 0.105 | 0.023 | **50** |
| PP03 | 0.997 | 0.975 | **0.929** | 0.737 | 0.559 | 0.316 | 0.154 | 0.098 | 0.050 | **10** |
| PP04 | 0.992 | 0.986 | 1.000 | 1.001 | 0.991 | 0.984 | 0.984 | **0.938** | 0.755 | **300** |
| PP05 | 1.003 | 0.991 | 0.991 | 0.979 | 0.978 | **0.942** | 0.747 | 0.525 | 0.201 | **100** |
| PP06 | 0.999 | 0.989 | 0.991 | 1.002 | 0.992 | **0.958** | 0.741 | 0.472 | 0.143 | **100** |
| PP07 | 0.997 | 0.985 | **0.926** | 0.547 | 0.273 | 0.076 | 0.019 | 0.009 | 0.003 | **10** |
| PP08 | 0.993 | 0.993 | 0.988 | 0.981 | **0.946** | 0.717 | 0.283 | 0.125 | 0.031 | **50** |

Every compound has a clearly tolerated concentration (nearest value to the 0.85 criterion is 0.926,
0.076 away), so the `not_evaluable` branch is never forced — consistent with the spec's own note.

### 3.1 Washout vs no washout, CM_WT, primary concentration — **AVAILABLE**
Paired per-experiment differences, n=7 each:

| cmp | conc | PI PRE_NOWASH (95% CI) | PI PRE_WASH (95% CI) | paired Δ (95% CI) |
|---|---|---|---|---|
| PP01 | 100 | 0.011 [−0.022, 0.044] | 0.047 [0.030, 0.064] | −0.036 [−0.078, 0.007] |
| PP02 | 50 | 0.591 [0.562, 0.620] | 0.649 [0.616, 0.682] | −0.058 [−0.102, −0.014] |
| **PP03** | 10 | 0.510 [0.485, 0.536] | **0.277** [0.253, 0.302] | **+0.233** [0.194, 0.272] |
| PP04 | 300 | −0.002 [−0.032, 0.029] | 0.012 [−0.007, 0.030] | −0.013 [−0.044, 0.017] |
| **PP05** | 100 | 0.541 [0.518, 0.564] | **0.165** [0.144, 0.186] | **+0.376** [0.341, 0.411] |
| PP06 | 100 | 0.579 [0.557, 0.602] | 0.604 [0.577, 0.631] | −0.025 [−0.060, 0.012] |
| PP07 | 10 | −0.004 [−0.036, 0.028] | −0.006 [−0.021, 0.009] | +0.002 [−0.041, 0.044] |
| PP08 | 50 | 0.556 [0.520, 0.591] | 0.595 [0.568, 0.621] | −0.039 [−0.092, 0.014] |

The contrast is informative and discriminating: PP02/PP06/PP08 keep their protection after washout
(Δ ≈ 0, even slightly negative), whereas **PP05 loses 69% of it and PP03 loses 46%** — the signature of
protection that needs the compound present during the challenge. The confidence intervals separate
these two groups unambiguously.

### 3.2 Residual intracellular exposure after washout — **AVAILABLE**, 7/7 experiments measured
CM_WT, primary concentration, pmol per 10⁶ cells; `POST_WASH_0P5H` ÷ `END_PRETREAT_NOWASH`:

| cmp | conc | E(END_PRETREAT_NOWASH) | E(POST_WASH_0P5H) | residual fraction | censored experiments |
|---|---|---|---|---|---|
| PP01 | 100 | 265.43 | 124.40 | **0.469** | 0 |
| PP02 | 50 | 133.28 | 73.51 | **0.552** | 0 |
| PP03 | 10 | 30.90 | 8.29 | **0.268** | 0 |
| PP04 | 300 | 445.54 | 170.41 | **0.383** | 0 |
| PP05 | 100 | 308.00 | 34.75 | **0.113** | 0 |
| PP06 | 100 | 226.66 | 115.52 | **0.510** | 0 |
| PP07 | 10 | 27.01 | 7.998 | **0.296** | 0 |
| PP08 | 50 | 378.83 | 217.67 | **0.575** | 0 |

Nothing is censored at either condition for any compound at its primary concentration, so
washout-resistant protection need not be *assumed* — it can be checked against how much compound
actually remains. Note PP05: only 11% residual yet PI falls from 0.541 to 0.165, consistent;
PP03: 27% residual with PI falling to 0.277.

### 3.3 Cell-free oxidant neutralisation vs vehicle — **AVAILABLE**
`cell_free_oxidant_neutralisation` at the primary concentration, calibrated against
`peroxide_calibration_standard` (0/25/50/100/200/400 µM; per-experiment linear fit, R² ≥ 0.99967),
challenge fixed at 200 µM tBHP:

| cmp | conc | residual peroxide (µM) | vehicle (µM) | ratio (95% CI) | % oxidant removed |
|---|---|---|---|---|---|
| PP01 | 100 | 200.39 | 199.90 | 1.002 [0.995, 1.009] | −0.2% |
| PP02 | 50 | 199.80 | 199.90 | 1.000 [0.990, 1.009] | 0.0% |
| PP03 | 10 | 199.26 | 199.90 | 0.997 [0.990, 1.003] | 0.3% |
| PP04 | 300 | 197.23 | 199.90 | 0.987 [0.981, 0.992] | 1.3% |
| **PP05** | 100 | **174.33** | 199.90 | **0.872 [0.865, 0.879]** | **12.8%** |
| PP06 | 100 | 199.91 | 199.90 | 1.000 [0.993, 1.007] | 0.0% |
| PP07 | 10 | 200.00 | 199.90 | 1.000 [0.995, 1.006] | 0.0% |
| PP08 | 50 | 200.07 | 199.90 | 1.001 [0.996, 1.006] | −0.1% |

Only PP05 consumes oxidant extracellularly, with an interval that excludes 1.00 by a wide margin
while all seven others bracket it. Extracellular chemistry is cleanly separable from cellular
protection. (PP04's 1.3% is detectable but an order of magnitude smaller.)

### 3.4 CM_KO_A / CM_WT measured exposure across the ladder — **AVAILABLE**; one compound never overlaps
E_KO(d) / E_WT at `END_PRETREAT_NOWASH`, qualifying window 0.70 – 1.42857
(count of experiments yielding a measured value in brackets where it is not 7):

| cmp | E_WT | 1 | 3 | 10 | 30 | 50 | 100 | 200 | 300 | 600 | matched |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PP01 | 265.43 | 0.012 | 0.037 | 0.119 | 0.335 | 0.588 | **1.026** | 1.932 | 2.653 | 4.045 | **100** |
| PP02 | 133.28 | 0.020 | 0.062 | 0.210 | 0.633 | **1.094** | 1.979 | 3.621 | 4.958 | 7.710 | **50** |
| PP03 | 30.90 | censored(0) | 0.066 | 0.211 | 0.620 | **1.045** | 1.990 | 3.570 | 4.892 | 8.300 | **50** |
| PP04 | 445.54 | censored(0) | 0.012 | 0.043 | 0.116 | 0.190 | 0.371 | 0.694 | **1.015** | 1.618 | **300** |
| PP05 | 308.00 | 0.010 | 0.029 | 0.099 | 0.310 | 0.487 | **0.921** | 1.626 | 2.386 | 3.757 | **100** |
| PP06 | 226.66 | 0.011 | 0.033 | 0.107 | 0.303 | 0.521 | **0.989** | 1.902 | 2.504 | 4.226 | **100** |
| PP07 | 27.01 | 0.106 | 0.321 | **1.041** | 3.024 | 4.883 | 9.641 | 16.650 | 22.889 | 38.219 | **10** |
| **PP08** | 378.83 | 0.006 (4) | 0.015 | 0.046 | 0.110 | 0.153 | 0.193 | 0.226 | 0.261 | **0.296** | **none** |

**Yes — one compound's knockout exposure never reaches the wild-type working exposure.** For **PP08**
the ratio **saturates at 0.296 even at 600 µM**, the top of the ladder: 2.4-fold short of the 0.70
window floor and still rising only marginally (0.226 → 0.261 → 0.296 over a 3-fold dose increase).
No concentration qualifies, so the `exposure_matching_rule.if_none_qualifies` branch and the
`indeterminate` status it forces are genuinely exercised by the data, not just defined on paper.
For the other seven, exactly **one** concentration qualifies, so the selection is unambiguous.
**Near-boundary observation:** PP04 at 200 µM has a ratio of **0.69447**, only 0.0055 below the window
floor. Even if an implementation nudged it inside, selection would be unchanged
(|ln 0.694| = 0.365 vs |ln 1.015| = 0.015 at 300 µM), so the answer is robust — but it is the tightest
boundary in the dataset and worth knowing about.

### 3.5 HMOX1 induction in CM_KO_A — **YES, an NRF2-independent component is identifiable**
log2 fold change (= −ΔΔCt) at 18 h, treated vs matched vehicle, 95% CI over 7 experiments:

| cmp | conc | gene | CM_WT | CM_KO_A |
|---|---|---|---|---|
| **PP04** | 300 | **HMOX1** | **1.215 [1.160, 1.269]** | **1.099 [0.929, 1.270]** |
| PP04 | 300 | NQO1 | 0.022 [−0.060, 0.104] | −0.029 [−0.135, 0.077] |
| **PP07** | 10 | **HMOX1** | **0.899 [0.848, 0.950]** | **0.865 [0.724, 1.007]** |
| PP07 | 10 | NQO1 | −0.064 [−0.166, 0.037] | −0.007 [−0.103, 0.089] |
| PP05 | 100 | HMOX1 | 0.329 [0.259, 0.398] | 0.269 [0.165, 0.373] |
| PP03 | 10 | HMOX1 | 0.290 [0.176, 0.405] | 0.166 [0.041, 0.292] |
| PP01 | 100 | HMOX1 | 2.282 [2.184, 2.381] | 0.224 [0.026, 0.421] |
| PP02 | 50 | HMOX1 | 1.820 [1.725, 1.914] | 0.138 [0.016, 0.261] |
| PP06 | 100 | HMOX1 | 2.097 [2.053, 2.142] | 0.205 [0.110, 0.300] |
| PP08 | 50 | HMOX1 | 2.751 [2.677, 2.824] | −0.019 [−0.156, 0.118] |

**PP04 (+1.10) and PP07 (+0.87) induce HMOX1 in the NFE2L2-null background essentially as strongly as
in wild type**, with intervals far from zero, while their NQO1/GCLC/TXNRD1 responses are flat in both
genotypes. By contrast PP01/PP02/PP06/PP08 induce HMOX1 by 1.8–2.8 log2 in CM_WT and only 0–0.22 in
CM_KO_A. The NRF2-independent HMOX1 component the spec warns about is therefore directly measurable,
and the dissociation from survival is visible too: PP01 induces NQO1 +2.62 and HMOX1 +2.28 in CM_WT yet
has PI = 0.011 [−0.022, 0.044]. Pathway induction cannot be mistaken for protection on this data.
The NFE2L2 amplicon itself is flat under treatment in every model (|log2FC| ≤ 0.11), as it should be.

### 3.6 Baseline susceptibility: vehicle oxidant titration per cell model — **AVAILABLE**
Panel `A_TITRATION` (VEH only, PRE_NOWASH, 7 models × 6 doses × 7 experiments × 4 wells), live cell
density ×10³/well, and the same normalised to each model's own unchallenged vehicle from panel B:

| model | 50 | 75 | 150 | 250 | 400 | 700 | unchallenged | normalised 150 µM |
|---|---|---|---|---|---|---|---|---|
| CM_WT | 41.2 | 38.8 | 28.8 | 17.2 | 8.0 | 2.8 | 43.4 | **0.664** |
| CM_WT_VEC | 39.5 | 37.1 | 27.1 | 15.7 | 7.4 | 2.5 | 41.3 | 0.657 |
| CM_KO_A | 35.4 | 29.9 | 15.7 | 7.0 | 2.8 | 0.9 | 40.9 | **0.384** |
| CM_KO_A_VEC | 35.1 | 29.6 | 14.9 | 6.6 | 2.6 | 0.8 | 39.8 | 0.375 |
| CM_KO_B | 36.2 | 30.9 | 16.7 | 7.5 | 3.0 | 0.9 | 40.8 | **0.410** |
| CM_KO_A_RES | 37.6 | 34.9 | 24.1 | 13.4 | 6.2 | 2.0 | 39.6 | 0.610 |
| CM_KO_B_RES | 38.5 | 35.9 | 25.7 | 14.5 | 6.8 | 2.3 | 40.7 | 0.630 |

A full six-point monotone curve per model, with vector controls tracking their parents (0.657 vs 0.664;
0.375 vs 0.384) and both rescues sitting partway back toward wild type (0.610, 0.630) — exactly the
partial rescue the spec describes. Genotype-specific baseline susceptibility (Q3) is directly
estimable, and it justifies the 1.7-fold spread of isoeffective doses (200 vs 118 µM) independently of
`cell_models.csv`. The `CHAL_COMMON` arm confirms the warning: at a single 300 µM dose the vehicle
densities are CM_WT 13.0 vs CM_KO_A 4.98 (×10³/well), i.e. the models sit at very different points on
their own curves.

### 3.7 Supporting contrasts also confirmed present
Per-compound PI at the primary administered concentration across all seven models (n=7 each):

| cmp | PI_WT | PI_KO_A (CI low) | PI_KO_B (CI low) | lineage A>0.15 | lineage B>0.15 | PI_rescue (CI low) | rescue>0.15 | PI_WT_VEC | PI_KO_A_VEC | Δ paired (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|
| PP01 | 0.011 | −0.049 (−0.073) | −0.060 (−0.088) | no | no | −0.007 (−0.034) | no | 0.019 | −0.041 | 0.061 [0.018, 0.103] |
| PP02 | 0.591 | −0.034 (−0.053) | −0.054 (−0.093) | no | no | 0.526 (0.492) | **yes** | 0.611 | −0.047 | **0.624 [0.590, 0.658]** |
| PP03 | 0.510 | 0.282 (0.246) | 0.269 (0.242) | **yes** | **yes** | 0.516 (0.479) | yes | 0.529 | 0.293 | **−0.031 [−0.062, 0.001]** |
| PP04 | −0.002 | −0.010 (−0.023) | −0.034 (−0.060) | no | no | −0.009 (−0.032) | no | 0.010 | −0.008 | 0.009 [−0.024, 0.041] |
| PP05 | 0.541 | 0.530 (0.483) | 0.542 (0.502) | **yes** | **yes** | 0.553 (0.521) | yes | 0.557 | 0.543 | **0.011 [−0.048, 0.069]** |
| PP06 | 0.579 | −0.025 (−0.051) | −0.056 (−0.092) | no | no | 0.536 (0.514) | **yes** | 0.607 | −0.026 | **0.605 [0.572, 0.637]** |
| PP07 | −0.004 | −0.001 (−0.029) | −0.017 (−0.046) | no | no | 0.002 (−0.018) | no | 0.005 | −0.006 | −0.003 [−0.056, 0.050] |
| PP08 | 0.556 | 0.014 (−0.023) | −0.054 (−0.023) | no | no | 0.528 (0.506) | **yes** | 0.578 | 0.011 | NA (no matched stratum) |

* **The two knockout lineages never disagree** on the protection boolean (A and B match for all 8),
  so the lineage-disagreement route to `indeterminate` is not triggered here — but the booleans are
  computable, which is what the audit asked.
* **Empty-vector controls track their parents** closely everywhere (e.g. PP06: 0.579 WT vs 0.607 WT_VEC;
  −0.025 KO_A vs −0.026 KO_A_VEC), so transduction/selection is excluded as an explanation.
* The exposure-conditioning distinction is live and matters: for **PP03** the unconditioned genotype
  comparison (0.510 vs 0.282 at the same administered dose) *looks* NRF2-dependent, while at matched
  measured exposure (KO at 50 µM, PI 0.541) the paired contrast is **−0.031 [−0.062, 0.001]**. A solver
  that skipped the exposure matching would get the opposite classification. This is the causal-mediation
  trap the spec describes, and it is genuinely baited.
* **All four `nrf2_dependence_status` branches are reachable:** `nrf2_dependent` (PP02, PP06),
  `not_nrf2_dependent` (PP03, PP05), `indeterminate` via no matched stratum (PP08),
  `not_assessable` (PP01, PP04, PP07). `protection_status` exercises `protected` (5) and
  `not_protected` (3); `indeterminate` and `not_evaluable` are not exercised, which is consistent with
  the spec's stated margin design.

### 3.8 Classification margins
The nearest approach of any graded quantity to its decision boundary:

| boundary | closest compound | distance |
|---|---|---|
| protection θ_P = 0.15 (CI bound) | PP04 (hi 0.029) | **0.121** |
| Δ θ_D = 0.15 (CI bound) | PP05 (hi 0.069) | **0.081** |
| rescue θ_P = 0.15 (CI low) | PP01 (−0.034) | 0.184 |
| interference 0.10 (CI low) | PP05 quench (0.0101) | **0.090** |
| tolerance 0.85 (tox_ratio) | PP03/PP07 (0.926) | 0.076 |
| exposure window 0.70 | PP04 at 200 µM (0.6945) | **0.0055** (selection unaffected) |

Apart from the PP04 exposure-window case — which cannot change the selected concentration — every
margin is at least 0.076, i.e. **an order of magnitude above the published tolerances**
(0.005 on indices, 0.008 on bounds). The spec's claim that no within-tolerance disagreement can flip
a status field holds on this seed.

---

## Summary of actionable items
1. **Fix** `data_dictionary.csv`: `reagent_batch_id` does **not** cross the biological experiments
   (RB1 = BIO01–03, RB2 = BIO04–07, zero overlap). Either correct the sentence or re-randomise.
2. **Fix** the censoring description in `study_specification.json`
   (`missing_value_conventions.below_lloq`) and the dictionary: censoring also occurs at 3 and 10 µM,
   and at `POST_CHALLENGE_24H_NOWASH`.
3. **Fix** `culture_format` vs `well_position` for the 266 `XP_*`/`QP_*` plate records, or relabel
   `plate_id` as a rack.
4. **Fix** the dictionary line on `assay_controls.value` (70 `below_lloq` rows do carry a value).
5. **Remove** `data/_generator_seed.json` from the solver-visible mount — undeclared and unnecessary.
6. The task brief's "6 biological experiments, 3 technical replicates" contradicts both the spec and the
   data (7 experiments; 4 viability wells, 3 probe wells). The brief is the thing that is wrong.
