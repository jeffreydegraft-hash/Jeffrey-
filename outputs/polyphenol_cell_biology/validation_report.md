# Validation report — `polyphenol_cell_biology`

**Dataset version** `v1.0.0` · generator seed `20261010` · validated 2026-10-10
**Verdict:** every check listed below was executed and passed, with one honestly-reported
limitation (§5) and seven open issues (§7). **Frontier difficulty is UNMEASURED** (§6).

This report separates three questions that are easy to conflate:

1. **Is the dataset scientifically coherent?** → §2, §3. Yes, with evidence.
2. **Are its intended answers reproducibly recoverable?** → §1, §4. Yes, with evidence.
3. **Do strong agents actually struggle to solve it?** → §6. **Not established.** Passing
   (1) and (2) says nothing about (3), and no agent trial was run.

---

## 0. The expected answer

| cmp | primary conc (µM) | E_WT (pmol/10⁶ cells) | matched KO conc | PI wild type [95% CI] | PI KO same dose | PI KO matched | PI rescue | NRF2 contrast [95% CI] | protection | NRF2 dependence | interference |
|---|---:|---:|---:|---|---:|---:|---:|---|---|---|---|
| PP01 | 100 | 280.06 | 100 | −0.005 [−0.039, 0.029] | −0.052 | −0.052 | −0.010 | 0.047 [0.007, 0.086] | `not_protected` | `not_assessable` | `none` |
| PP02 | 50 | 137.99 | 50 | 0.601 [0.566, 0.635] | −0.034 | −0.034 | 0.581 | 0.635 [0.580, 0.690] | `protected` | `nrf2_dependent` | `none` |
| PP03 | 10 | 33.42 | **50** | 0.522 [0.502, 0.542] | **0.273** | **0.538** | 0.530 | −0.017 [−0.062, 0.028] | `protected` | `not_nrf2_dependent` | `none` |
| PP04 | 300 | 437.43 | 300 | −0.008 [−0.047, 0.031] | −0.012 | −0.012 | 0.015 | 0.004 [−0.044, 0.051] | `not_protected` | `not_assessable` | **`mtt;ros`** |
| PP05 | 100 | 308.85 | 100 | 0.553 [0.532, 0.575] | 0.541 | 0.541 | 0.588 | 0.013 [−0.021, 0.047] | `protected` | `not_nrf2_dependent` | `none` |
| PP06 | 100 | 227.25 | 100 | 0.582 [0.541, 0.623] | −0.032 | −0.032 | 0.547 | 0.614 [0.560, 0.667] | `protected` | `nrf2_dependent` | **`ros`** |
| PP07 | 10 | 27.76 | 10 | −0.014 [−0.039, 0.011] | 0.003 | 0.003 | 0.009 | −0.017 [−0.062, 0.028] | `not_protected` | `not_assessable` | `none` |
| PP08 | 50 | 389.92 | **NA** | 0.558 [0.533, 0.583] | 0.018 | **NA** | 0.531 | **NA** | `protected` | **`indeterminate`** | `none` |

The distribution is deliberately non-trivial: 5 protected / 3 not; 2 NRF2-dependent, 2 not
NRF2-dependent, 1 `indeterminate`, 3 `not_assessable`; one compound with two interference
flags, one with one, six with none. **PP06 is simultaneously `protected`, `nrf2_dependent` and
an assay interferer** — the mixed finding a collapsed hit/no-hit verdict would destroy.

---

## 1. Reproducibility

| check | how | result |
|---|---|---|
| Same seed reproduces the data byte-for-byte | regenerate with seed `20261010`, SHA-256 all 8 CSVs | **PASS** — all 8 hashes identical |
| All files parse | `csv` and `pandas` readers over all 11 inputs | **PASS** |
| Reference analysis deterministic | two consecutive runs | **PASS** — byte-identical |
| Independent analysis deterministic | two consecutive runs | **PASS** — byte-identical |
| Clean-room reconstruction | extract `solver_inputs.zip` into an **empty** directory; run the reference analysis and verifier against the extracted copy **only** | **PASS** — 11 files extracted, both exit 0, output byte-identical to the working copy |
| Archive integrity | `ZipFile.testzip()` plus member-list assertion | **PASS** — no corrupt member; contents exactly the 11 solver-visible files |
| No authoring material in the archive | explicit deny-list scan of archive members | **PASS** |

Evidence: `authoring/validation/seed_sweep_report.json`,
`authoring/validation/clean_room_report.json`.

## 2. Scientific coherence, join integrity and leakage — 75 checks, all passing

`authoring/validation/invariance_and_integrity.py` → `invariance_and_integrity_report.json`.

Four of these checks were themselves wrong on first run and were **fixed rather than
loosened**: a substring scan flagged the harmless word "label" in a prose description and
matched "ratio" inside "du**ratio**n"; the reference-isolation scan flagged words that appear
only in the docstring stating the solver does *not* read generator truth; and the
shared-variation test was underpowered. In the first three the checker was the problem, not the
data. The fourth exposed a real modelling error (see below).

**Joins and keys.** `sample_id` unique across 76,160 manifest rows. For each of the four
measurement tables: every `sample_id` resolves to the manifest, every referenced sample belongs
to that table's panel, the declared composite key is unique, and **every** manifest sample of
that panel has a measurement row — no orphans in either direction. `control_id` unique and
disjoint from `sample_id`; the cell-free controls deliberately do not join to the manifest, and
that is documented.

**Units and ranges.** Administered concentrations lie only on the published 9-point ladder. The
`CHAL_ISO` dose matches `cell_models.csv` on every row; `CHAL_COMMON` is 300 µM for every cell
model; unchallenged rows carry exactly 0 oxidant. Nuclei counts are non-negative integers; LDH
activity positive; MTT absorbance within 0.1–1.7 with 570 nm above the 630 nm reference in every
well; probe fluorescence positive; Ct within 15–29; derived exposures 1.2–2800 pmol/10⁶ cells.

**Culture format is physically coherent.** Every declared `culture_format` agrees with the well
positions it carries and with the number of wells per plate: `96_well` is an 8×12 grid (A1–H12,
≤96 wells/plate), `24_well` a 4×6 grid (A1–D6, ≤24), `12_well` a 3×4 grid (A1–C4, ≤12). A
condition's technical replicates always sit together on one plate. *This was broken in an
earlier build* — exposure samples labelled `6_well` carried 96-well positions up to `D11`,
which is physically impossible. The independent blind audit (§8) caught it; the generator now
derives the grid and the plate capacity from the format.

**Reference genes are stable, not assumed stable.** Largest within-cell-model spread of a mean
reference-gene Ct across all treatment levels: **0.49 cycles** for `ACTB`/`RPLP0`, against ~1.8
(`NQO1`) and ~1.6 (`HMOX1`) for the inducible genes. The normaliser is justified from the raw
data rather than assumed.

**Batch balance.** 7 biological experiments, each containing all 7 cell models and all 73
treatment levels. **Zero** of 1,064 plates carry only one cell model; zero carry only one
compound. Both reagent lots contain all 7 cell models. Viability technical replication is
exactly 4 wells per condition per experiment, everywhere. The reagent lot is **nested** inside
the biological experiment (RB1 = BIO01–03, RB2 = BIO04–07) — the data dictionary originally
claimed it *crossed* experiments, which was false. The dictionary now states the nesting and why
it biases no graded quantity (every protection index is formed within one experiment against
that experiment's own matched controls), and a check records the structure so documentation and
evidence cannot drift apart again.

**Missingness.** Empty fields occur only in the columns documented as conditional. The censoring
flag matches an empty value one-to-one on all 30,240 exposure rows. Cell-lysate censoring occurs
only at 1, 3 and 10 µM — nothing above 10 µM is censored; medium censoring occurs only in the
two post-washout conditions. In `assay_controls`, only `undetermined` rows have an empty value;
the 70 sub-LLOQ LC-MS calibration standards correctly **do** carry their measured response,
since a standard's nominal amount is known by construction. All three of these descriptions were
wrong or incomplete in an earlier draft of the contract and were corrected after the audit
measured the actual distribution. **No missingness was added to create difficulty.**

**Leakage.** No verdict or mechanism token appears in any data file's column names or string
values — `nrf2_dependent`, `not_nrf2_dependent`, `not_assessable`, `not_protected`, `protected`
and `mtt;ros` occur **zero** times across the eight CSVs, and appear in the two JSON files only
as enumerated allowed values, never on a line that also names a compound. No CSV contains a
compound identifier together with its verdict. The data dictionary never ties a named compound to
a conclusion. `compounds.csv` carries physicochemical descriptors only. No precomputed score,
index, fold-change or flag column exists (`ct_flag` and `qualifier` are documented
measurement-status fields). Compound-identifier order does not group the outcomes; mean row
position is within 0.40–0.60 of every table for every compound; the spread of mean `sample_id`
number across compounds is under 0.01 of the identifier range; and **no** physicochemical
descriptor (MW, logP, solubility, purity, LLOQ) separates protected from unprotected compounds.
An undeclared `_generator_seed.json` sat in the data directory in an earlier build and has been
removed; it was never inside the archive.

**Shared biological variation across assays — measured, not asserted.** The requirement is that
tables from the same biological experiment share latent variation rather than being resampled
independently per table:

| shared factor | tables compared | Pearson *r* over 7 experiments |
|---|---|---:|
| culture vigour | mean unchallenged nuclei count (`viability_readouts`) vs mean cell equivalents analysed (`exposure_measurements`) | **+0.994** |
| culture vigour | mean unchallenged nuclei count vs mean LDH maximum-lysis control (`assay_controls`) | **+0.882** |
| realised injury severity | pooled survival fraction (`viability_readouts`) vs pooled gain-normalised probe response (`oxidative_stress_readouts`) | **−0.972** |

Independent per-table generation would put all three near zero. **Getting the third right
required fixing a real modelling error.** The first attempt gave *r* = −0.25, and the tempting
move was to loosen the threshold. Diagnosis instead found two problems: the per-experiment probe
summary rested on only 3+3 vehicle wells, and — more importantly — the dye-loaded background did
**not** scale with cell number, so an unchallenged dye-loaded well read the same regardless of
how many cells were in it. That is physically wrong, and it left the probe ratio carrying a
culture-vigour term that survival does not. The generator now scales the dye-loaded signal and
its background with cell number, while dye-*free* wells keep a constant instrument background
since no probe is present to report anything. That fixes the physics and makes the ratio
self-normalising for cell number; the correlation is now −0.972.

**The reference analysis cannot consult generator truth.** Three executed checks back this: its
executable code — comments and docstrings stripped via AST, so prose about what it does *not* do
cannot create a false pass — contains no reference to the simulation core, the private
parameters, any latent or archetype name, or any expected-result file; the only file names it
mentions are the eleven solver-visible inputs plus its own output path; and the same holds for
the verifier. The clean-room test (§1) is the conclusive demonstration.

**Invariance.**
- **Row order:** shuffling every input table's rows leaves the reference output
  **byte-identical**.
- **Compound-identifier permutation:** relabelling `PP01..PP08` by the permutation
  `PP01→PP05, PP02→PP07, PP03→PP01, PP04→PP08, PP05→PP02, PP06→PP04, PP07→PP03, PP08→PP06`
  throughout every file reproduces every number to within 1×10⁻⁹ and every status exactly, under
  the relabelling. The identifiers carry no information.

## 3. Scientific identifiability — is each intended distinction actually recoverable?

`authoring/validation/identifiability.py` → `identifiability_report.json`. Every number below
comes from **solver-visible data only**.

| # | explanation the dataset must contain | separating contrast, measured | verdict |
|---|---|---|---|
| 1 | NRF2-dependent protective contribution | **PP02, PP06**: PI 0.601 / 0.582 in wild type; −0.034 / −0.032 in KO-A; −0.042 / −0.041 in the **independently derived** KO-B lineage; restored to 0.581 / 0.547 by functional `NFE2L2` re-expression but not by empty vector. `NQO1` +2.6 log₂ and `GCLC` +1.8 log₂ in wild type, ≈0 in KO. Protection survives washout (PI 0.635 / 0.630) with ~50 % residual exposure; cell-free oxidant neutralisation ≈0 % | **identifiable** |
| 2 | protection that persists without NRF2 | **PP05**: PI 0.553 wild type vs 0.541 in KO at matched exposure; `NQO1` +0.03 log₂, i.e. no pathway response; washout cuts protection to 0.164 with only 11.5 % residual exposure; cell-free oxidant neutralisation **13.6 %** — direct extracellular chemistry | **identifiable** |
| 3 | apparent benefit caused primarily by assay interference | **PP04**: protection index by direct count **−0.008** and by LDH release **+0.016**, but by the MTT signal **+0.981**. Cell-free MTT reproduces the whole effect without cells (index ≈0.50); dye-free wells show autofluorescence and the fixed-fluorophore standard shows ~33 % quenching | **identifiable** |
| 4 | genuine protection accompanied by assay interference | **PP06**: direct count **and** LDH both give PI ≈0.58, so protection is real and NRF2-dependent by row 1 — while the fixed-fluorophore quench standard independently shows the probe readout is corrupted (`ros` flagged). Its MTT index is ≈0, so the interference is probe-specific | **identifiable** |
| 5 | pathway-response gene induction without improved survival | **PP01**: `NQO1` +2.6 log₂ and `HMOX1` +2.2 in wild type, both abolished in KO — yet `GCLC` only +0.1, and PI by count −0.005 [−0.039, 0.029] and by LDH +0.008. Strong, genuinely NRF2-dependent transcription, no survival benefit | **identifiable** |
| 6 | dose-dependent toxicity / absence of supported protection | **PP07**: wild-type unchallenged viability ratio falls ≈1.00 → 0.94 → 0.55 → 0.28 → 0.08 across 3/10/30/50/100 µM, so the selection rule forces evaluation at 10 µM, where PI is −0.014 [−0.039, 0.011] | **identifiable** |
| 7 | apparent genotype difference that changes interpretation once exposure is considered | **PP03**: at the **same administered dose** PI is 0.522 (wild type) vs 0.273 (KO) — on its own that reads as NRF2 dependence. Measured KO exposure at that dose is ~0.23× wild type. At the exposure-matched rung (50 µM) KO protection is **0.538**, fully restored. The genotype effect is **delivery, not pathway** | **identifiable** |
| 8 | a genotype difference that **cannot** be resolved → `indeterminate` | **PP08**: PI 0.558 wild type, 0.018 KO, rescue 0.531 — the same qualitative pattern as row 1. But measured KO exposure **peaks at 0.271× wild type across the whole ladder, including 600 µM**, where it is not toxic, so no rung can enter the 0.70–1.43 matching window. Pathway dependence cannot be separated from delivery dependence, and the contract requires `indeterminate` | **correctly indeterminate** |

**Rows 7 and 8 are the decisive pair:** identical qualitative patterns at a fixed administered
concentration, opposite correct conclusions, separated **only** by whether the measured exposure
ranges overlap.

**Genotype-specific baseline susceptibility is real and visible.** The vehicle-only oxidant
titration gives, at 150 µM, survival fractions of 0.667 (wild type) vs 0.389 (KO-A) — a large
intrinsic difference, with the two rescue lines intermediate at 0.61–0.62 and the vector
controls tracking their parents. The isoeffective doses (200 µM wild type, 118 µM KO-A, 179 µM
rescue, …, all published in `cell_models.csv`) bring every cell model to a vehicle-challenged
survival of **0.511–0.522**, which is why the deficit-normalised scale is comparable across
genotypes at the primary condition. The **common-oxidant-dose arm** preserves the error for
anyone who uses it.

**One intended branch is never exercised.** The independent-knockout-lineage corroboration rule
is specified and implemented, but KO-A and KO-B agree for all eight compounds, so its
disagreement branch is never taken. Reported as a limitation, not a pass (§7).

## 4. Two independent implementations, and the tolerances

The reference analysis (pure Python standard library) and a **separately written** second
implementation (numpy/pandas) were produced from the published contract. The second did not
import, read or inspect the reference solver, the generator, the private simulation parameters,
or any expected-result file; the independence constraint and its own 13 internal cross-checks
are recorded in `authoring/independent/NOTES.md`.

**Measured agreement:** maximum absolute disagreement across all protection indices, contrasts
and interval bounds for all eight compounds = **4.9×10⁻⁵**; maximum relative disagreement on the
exposure quantity = **1.2×10⁻⁴**. Every categorical status, every `NA` placement, every selected
concentration: **identical**. The residual is output rounding, not method.

**Tolerances were set from that measurement**, not chosen to accommodate a disagreement:
protection indices and contrasts ±0.005, interval bounds ±0.008, exposure ±1 % relative,
concentrations and statuses exact. These are ~100× the measured implementation disagreement — so
an implementation writing two-decimal results is still accepted — and ~6× smaller than the
closest approach of any graded value to any classification boundary across ten seeds (0.0507,
§4.2), so **a disagreement within tolerance cannot change any status field**.

The independent implementation found **six genuine defects in the contract**, all fixed before
delivery: three stale "5 biological experiments" figures left from an earlier parameterisation;
an unnamed panel in the MTT-interference denominator; an ordering ambiguity that let the
lineage-corroboration rule contradict the stated rule order (the rule is now its own ordered
step, placed before both threshold tests); and an incompletely specified `not_evaluable` branch.
It also flagged that the concentration-selection rule is a ratio of means while the protection
index is a mean of ratios — a real inconsistency of style, now documented as deliberate with the
reason given. Finding and fixing these is the main value the second implementation delivered.

### 4.1 Verifier behaviour — 25 adversarial submissions, all handled as intended

`authoring/validation/negative_tests.py` → `negative_tests_report.json`.

| defect injected | detected by |
|---|---|
| non-UTF-8 bytes | `file_is_utf8` |
| missing · duplicated · extra compound | `row_count_is_8` plus `all_required_compounds_present` / `compound_ids_unique` / `no_unexpected_compounds` |
| reordered header · renamed column | `header_matches_schema_exactly` |
| empty field instead of the `NA` token | `fields_parse_as_declared_types` |
| exposure on the wrong basis (×40, raw pmol not per 10⁶ cells) | `numeric_results_within_tolerance` |
| protection index as a percentage | `units_and_ranges_plausible` |
| concentration not on the published ladder | `units_and_ranges_plausible` |
| confidence bounds swapped | `confidence_intervals_bracket_point_estimates` |
| evidence identifiers that do not exist | `evidence_references_valid_and_relevant` |
| evidence citing **knockout** wells for the wild-type estimate | `evidence_references_valid_and_relevant` |
| evidence covering only 3 of 7 biological experiments | `evidence_references_valid_and_relevant` |
| numeric shift just over tolerance · large shift | `numeric_results_within_tolerance` |
| status flipped while the numbers stay correct | `classifications_consistent_with_submitted_numbers` **and** `classifications_match_expected` |
| status value outside the allowed set | `status_and_flag_values_allowed` |
| `NA` where a value is required · a matched stratum claimed for the unmatchable compound | `na_token_used_exactly_where_required`, `classifications_match_expected` |
| interference flag missed · over-called | `classifications_match_expected` |
| **deliberately accepted:** shift within tolerance; exposure within relative tolerance; `ros;mtt` instead of `mtt;ros` | accepted — equivalent-correct submissions |

The verifier was **hardened during this testing**: a malformed field originally raised a
traceback instead of a reported failure. It now catches every exception and records it as a
failed check, so a crash can never be mistaken for a pass. The verifier inspects only the
submitted outputs and the solver-visible inputs — never the solver's code, structure or runtime.

### 4.2 Multi-seed stability — 10 seeds

Seeds `20261010, 7, 101, 20240229, 31337, 555, 20260601, 1, 999983, 42`. For each, the whole
dataset was regenerated and the reference analysis re-run.

- **All 8 × 10 = 80 protection statuses, 80 NRF2-dependence statuses and 80 interference flag
  sets: identical to the intended answer in every case.**
- Every primary concentration and every exposure-matched concentration identical in every case,
  including PP08's `NA`.
- Worst-case distance from a decision boundary over all compounds and all seeds: **+0.0507**
  (PP05's NRF2-dependence call). Next tightest: PP03 dependence +0.0799, PP01 protection
  +0.1035, PP07 +0.1098, PP04 +0.1127. All others exceed +0.32.

**PP05's "not NRF2-dependent" call is the least-margined conclusion in the package** and the one
to re-check if the design is re-seeded or re-parameterised. It is correct on all ten seeds, by a
margin at least 6× the grading tolerance.

## 5. Shortcut analyses — what the verifier catches, and what it cannot

Six deliberately limited analyses were implemented from the published contract by agents that
never saw the reference solver or any expected result, each faithfully executing one specific
flawed method (confirmed by reading their source). `authoring/validation/shortcut_runner.py` →
`shortcut_report.json`.

| shortcut | wrong scientific conclusions | rejected? | which checks fired |
|---|---:|---|---|
| **1. Rank by the largest apparent antioxidant / viability-assay signal** — uses MTT and probe fluorescence as if they measured survival; never consults the cell-free controls | **4** | **yes** | `numeric_results_within_tolerance`, `classifications_match_expected` |
| **2. Treat pathway-gene induction alone as proof of protection** | **6** | **yes** | `classifications_consistent_with_submitted_numbers`, `numeric_results_within_tolerance`, `classifications_match_expected` |
| **3. Compare genotypes without accounting for their different baselines** — uses the common-oxidant-dose arm on a raw scale | **1** | **yes** | `numeric_results_within_tolerance`, `classifications_match_expected` |
| **4. Ignore measured exposure and residual compound after washout** | **2** | **yes** | `numeric_results_within_tolerance`, `classifications_match_expected` |
| **5. Count technical replicates as independent biological experiments** | **0** | **yes** | `numeric_results_within_tolerance` (22 interval bounds wrong) |
| **6. Reject every compound that shows assay interference** | **2** | **yes** | `classifications_consistent_with_submitted_numbers`, `classifications_match_expected` |

**The specific errors:**

- **Shortcut 1** calls **PP04 `protected`** — its MTT-based protection index is 0.981 against a
  direct-count index of −0.008 — and reports `none` for every interference flag, missing both
  PP04's `mtt;ros` and PP06's `ros`. It mistakes the interference for the biology.
- **Shortcut 2** calls **PP01 `protected` and `nrf2_dependent`** on a 6-fold, genuinely
  NRF2-dependent `NQO1` induction that produces no survival benefit, and calls **PP03 and PP05
  `not_protected`** because they protect by direct chemistry without inducing the pathway.
  Transcription is neither necessary nor sufficient for protection here, and the shortcut errs
  in both directions.
- **Shortcut 3** computes PP03's dependence contrast as 0.134 [0.113, 0.154] — an interval
  straddling the 0.15 threshold — and returns `indeterminate` where the correct answer is
  `not_nrf2_dependent` (correct contrast −0.017). Worth reporting honestly: on a previously
  generated seed this same shortcut landed on the correct label by **0.002**. Its method is
  wrong either way; whether its *label* comes out right is close to a coin flip, which is
  exactly why the numeric results are graded and not only the categories.
- **Shortcut 4** calls **PP03 `nrf2_dependent`** (its KO cells merely receive ~0.23× the
  exposure) and **PP08 `nrf2_dependent`** (where the honest answer is `indeterminate`, because
  exposure can never be matched). Both intended traps fire.
- **Shortcut 6** calls **PP06 `not_protected` / `not_assessable`**, discarding a compound whose
  direct cell count and LDH release both show genuine, NRF2-dependent protection, purely because
  its probe readout is corrupted. This is why protection and interference are separate findings.

### The honest limitation

**Shortcut 5 (technical replicates as biological) reaches the correct categorical conclusions.**
Pooling individual wells inflates *n* from 7 to ~28 and narrows every interval, but because
every effect sits far from its threshold, no classification changes. It is detected **only**
because the interval bounds are themselves graded outputs. The detection margin is the narrowest
in the package and is worth stating exactly:

| compound | largest interval-bound deviation from correct | detected at tolerance 0.008? |
|---|---:|---|
| PP01 | 0.0160 | yes |
| PP02 | 0.0254 | yes |
| PP03 | 0.0141 | yes |
| PP04 | 0.0191 | yes |
| PP05 | 0.0012 | **no** |
| PP06 | 0.0202 | yes |
| PP07 | 0.0216 | yes |
| PP08 | 0.0047 | **no** |

Pseudoreplication of this balanced design is caught on **6 of 8 rows** at the published
tolerance, and its largest effect on any bound is **0.0254**. Consequences, stated plainly: if
the interval-bound tolerance were loosened past ~0.026 this shortcut would pass entirely; if the
interval bounds were dropped from the output schema, or the numeric check applied as a
pass-if-most-rows rule, it would pass with every scientific verdict intact. **Had the task
graded only point estimates and statuses, this shortcut would have passed undetected.** This is
the strongest argument for grading the uncertainty bounds, for grading them per row, and for
keeping the tolerance tight.

**No formatting failure was manufactured to make a shortcut fail**, and **no shortcut produced
wrong science that the verifier accepted.**

## 6. Difficulty-testing status

**Frontier difficulty is UNMEASURED.**

- **No agent trial was run.** No model, agent or human was given the task and scored.
- **No material was uploaded anywhere** and **no external model trial was initiated**, as
  instructed. The entire build and validation ran locally.
- **No failure rate is claimed.** The task is **not** described as frontier-stumping, and
  nothing here should be read as evidence about how hard strong agents find it.

What *has* been established is narrower: the dataset is scientifically coherent (§2, §3), its
intended answers are reproducibly recoverable from the solver-visible files alone by two
independent implementations (§4), and six plausible reasoning shortcuts are rejected (§5) — five
of them for genuinely wrong science. **Shortcut rejection is evidence that specific reasoning
errors are penalised. It is not evidence that a strong agent will commit them.**

**If authorised trials are run later, record for each:** the exact dataset version and generator
seed (`v1.0.0` / `20261010`); the verbatim solver prompt; the model identifier and version; the
agent configuration (tools, turn and token limits, retries, whether the specification was given
in context or had to be read from disk); the number of attempts; the full `results.csv` submitted
and the verifier's JSON report for each; and the cause of each failure — **distinguishing
scientific-reasoning failures** (wrong endpoint, wrong comparison, exposure ignored, technical
replicates miscounted, interference conflated with biology, refusal to return `indeterminate`)
**from environment, file-access, parsing, formatting or time-limit failures.** Those are
different findings and must not be pooled.

## 7. Unresolved issues

1. **Benchmark-platform eligibility is unresolved.** TerminalBench guidelines were not present in
   the build environment, so the package was built against the requester's requirements rather
   than a platform rule set. `authoring/design/PROVENANCE.md` §5 lists the five specific open
   questions a reviewer must check — in particular whether **fully synthetic inputs** are
   eligible, whether **AI-assisted authoring** is permitted and how it must be declared, and
   whether a task whose correct answer includes an **`indeterminate`** verdict is acceptable.
   **No claim of eligibility or approval is made.**
2. **The lineage-corroboration branch is untested by this dataset** (§3). The rule is specified
   and implemented, but KO-A and KO-B agree for all eight compounds, so a solver that omitted the
   lineage check entirely would score identically. Exercising it would require a compound whose
   lineages disagree, at the cost of a deliberately seed-fragile effect.
3. **The `not_evaluable` branch is never taken.** Every compound has a tolerated concentration.
   The branch is now fully specified so the contract is complete, but it is unexercised.
4. **One stated convention is not load-bearing.** The contract insists the protection index is a
   mean of ratios, not a ratio of means. The independent implementation measured the difference
   on this dataset at **≤9.5×10⁻⁴** — inside tolerance. The convention is stated for good reason
   (the estimators genuinely differ in general) but here it would not discriminate a solver that
   chose the other.
5. **PP05's NRF2-dependence margin is the tightest conclusion** (§4.2): +0.0507 in the worst of
   ten seeds. Correct everywhere tested, but most sensitive to re-parameterisation.
6. **Washout-resistant protection carries substantial residual exposure.** For PP02, PP06 and
   PP08, 50–52 % of intracellular compound remains 0.5 h after washout. The washout arm is
   therefore weaker evidence for "persistent cellular adaptation" than it first appears. This is
   deliberate and measurable — the residual exposure is supplied precisely so a solver can check
   rather than assume — and no graded answer depends on the washout arm. But a careful solver
   should notice the limitation, and a reviewer should not read the washout contrast as clean.
7. **The reagent lot cannot be estimated separately from the experiment** (§2). Each experiment
   used one lot, so a lot effect is collinear with a 3-vs-4 partition of the units of inference.
   The measured magnitude is modest — vehicle unchallenged density ~39.3 vs ~42.1 ×10³/well,
   against a between-experiment range of ~34.8–46.7 — and no graded quantity is affected, since
   every protection index is formed within one experiment. Re-randomising the lot across
   experiments would remove the collinearity if a future version wants it.

**The solver-facing submission prompt is deliberately unwritten**, as requested. The package is
not runnable as a task until someone writes it.

## 8. An independent blind audit was also run

A separate agent, given **only** the eleven solver-visible files and explicitly denied access to
the generator, the private parameters and the reference solver, audited the dataset for leakage,
coherence and identifiability. Its full report is `authoring/validation/audit_report.md`.
Headline findings:

- **Leakage: none found.** No column, string, note, identifier, row order or physicochemical
  descriptor lets any graded field be read off without the intended analysis.
- **Join integrity, units, ranges, replication and identifiability: all pass**, independently
  confirming §2 and §3 — including that PP08's knockout exposure never overlaps the wild-type
  working exposure, that an NRF2-independent `HMOX1` component is directly measurable in KO-A,
  and that the baseline-susceptibility and washout contrasts are available.
- **Six real defects, since fixed:** the `reagent_batch_id` nesting misdescription; an incomplete
  censoring description; the `culture_format` versus well-grid incoherence (266 plate records
  exceeded their declared format capacity); the `assay_controls.value` dictionary line; an
  undeclared `_generator_seed.json` in the data directory; and a note that the LDH release index
  can fall slightly outside [0, 1] and must not be clipped — now documented in the contract.

Running this audit blind was worthwhile: three of those six defects were invisible to the
author's own checks, and one — the well-grid incoherence — was a genuine internal contradiction
that a careful solver would have noticed.

## 9. Everything that was executed

| suite | file | checks | result |
|---|---|---:|---|
| Noise-free design calibration | `authoring/generator/calibrate.py` | 8 compounds × 6 reports | all targets met |
| Reference analysis | `authoring/reference/reference_analysis.py` | — | 8 rows produced |
| Independent cross-check | `authoring/independent/independent_analysis.py` | 13 internal cross-checks | all pass; 6 contract defects found and fixed |
| Verifier on the reference | `authoring/verifier/verify_results.py` | 17 | **17/17 pass** |
| Verifier on the independent implementation | same | 17 | **17/17 pass** |
| Adversarial submissions | `authoring/validation/negative_tests.py` | 25 | **25/25 behaved as intended** |
| Invariance, joins, units, format, balance, missingness, leakage, cross-assay sharing, reference isolation | `authoring/validation/invariance_and_integrity.py` | 75 | **75/75 pass** |
| Identifiability evidence | `authoring/validation/identifiability.py` | 7 sections | all 8 distinctions identifiable |
| Multi-seed stability | `authoring/validation/seed_sweep.py` | 10 seeds × 24 statuses | **240/240 stable** |
| Shortcut analyses | `authoring/validation/shortcut_runner.py` | 6 | 6/6 rejected; 1 honest limitation reported |
| Independent blind audit | `authoring/validation/audit_report.md` | 3 parts | no leakage; 6 defects found and fixed |
| Clean-room extraction | `authoring/validation/clean_room_test.py` | 1 | **pass** |
| Checksums | `SHA256SUMS.txt` | all delivered files | verified with `sha256sum -c` |
