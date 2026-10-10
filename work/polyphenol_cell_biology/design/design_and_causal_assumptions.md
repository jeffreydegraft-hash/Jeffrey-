# Study design and causal assumptions

**Benchmark:** `polyphenol_cell_biology`
**Status:** authoring document — written and frozen *before* the data generator was finalized.
**Nature of the data:** 100% synthetic. No measured values from any real experiment appear anywhere in
this package. See `PROVENANCE.md` for the AI-assisted synthetic-data disclosure.

---

## 0. Why this document exists

The benchmark grades a solver on quantities that must be *recoverable from the solver-visible files
alone*. That is only possible if the scientific question, the estimand, the comparison conditions and
the decision rules are fixed **before** the simulation is tuned. Otherwise the "right answer" silently
becomes "whatever the generator happened to produce", and hidden generator parameters leak into the
grading contract.

So this document fixes, in order:

1. the scientific question and the four distinct comparisons it decomposes into (§1);
2. the causal model (DAG) and the assumptions each comparison needs (§2);
3. which claims are literature-supported principles and which are invented simulation parameters (§3);
4. the experimental design that makes each comparison identifiable (§4);
5. the estimands, uncertainty convention and classification rules (§5);
6. the competing explanations the dataset must contain, and the contrast that separates each pair (§6);
7. what is deliberately *not* claimable from this design (§7).

`study_specification.json` is the machine-readable, solver-visible projection of §4–§5. Anything in §5
that a solver needs in order to be graded fairly is disclosed there. Nothing in §3's "invented
parameters" table or §6's archetype assignments is disclosed to the solver.

---

## 1. Scientific question, decomposed

**Umbrella question.** For each of eight polyphenol-like candidate compounds (`PP01`–`PP08`), does the
compound produce a genuine, NRF2-dependent improvement in survival of intestinal epithelial cells
subjected to an acute oxidative challenge — as distinguished from (a) compound toxicity,
(b) differences in intracellular exposure, and (c) interference with the assay chemistry itself?

That umbrella question is not a single comparison. It decomposes into four comparisons that answer
**different** questions and require **different** assumptions. Conflating them is the central failure
mode this benchmark is built to detect.

### Q1 — Protection at a fixed administered concentration
> *In wild-type cells, at a stated administered concentration, does pretreatment with the compound
> increase the number of surviving cells after a standardised oxidative challenge, relative to vehicle?*

Units of the comparison: administered concentration (µM in medium). This is the question a
dose-finding experiment answers, and it is the question that matters for "is this compound worth
pursuing at a dose we can actually administer". It makes **no** claim about mechanism.

### Q2 — Protection compared at a common measured intracellular exposure
> *When wild-type and NFE2L2-knockout cells are compared at matched measured intracellular compound
> exposure, does the protective effect differ by genotype?*

Units of the comparison: measured intracellular exposure (pmol per 10^6 cells). This is the question
that isolates the *pathway* contribution from the *delivery* contribution. It is only answerable where
the two genotypes have overlapping measured exposure ranges; where they do not, the honest answer is
"indeterminate", not an extrapolation.

### Q3 — Genotype-specific baseline susceptibility to injury
> *Independently of any compound, how much injury does a given oxidant dose produce in each genotype?*

Units: oxidant dose (µM tert-butyl hydroperoxide). NFE2L2-knockout cells are expected to be
intrinsically more susceptible. This comparison exists so that protection can be put on a scale that
is not confounded by where each genotype sits on its own injury curve. A compound compared across
genotypes **at a common oxidant dose on a raw survival scale** will appear differentially protective
purely because the knockout is nearer the survival floor.

### Q4 — Contribution of NRF2 under the supplied interventions
> *Across the supplied interventions (knockout in two independent lineages, empty-vector controls,
> functional NFE2L2 re-expression, pretreatment with and without washout, measured residual exposure),
> is the protective effect attributable to NRF2 pathway function?*

This is a composite judgement over Q2 plus the rescue and washout arms. It is a claim about *this
experimental system*, not about molecular binding (see §7).

---

## 2. Causal model and the assumptions each comparison needs

### 2.1 Assumed data-generating structure (DAG)

```
                           ┌──────────────────────────────────────────────┐
                           │  BATCH (biological experiment) random effects│
                           └───────┬───────────────┬───────────────┬──────┘
                                   │               │               │
  GENOTYPE ──► NRF2_FUNCTION ──┬──► UPTAKE_CAPACITY ──┐            │
  (WT / KO-A / KO-B /          │                      │            │
   KO+vector / KO+rescue)      │                      ▼            ▼
                               │   ADMIN_CONC ──► INTRACELLULAR_EXPOSURE ──┬──► NRF2_ACTIVATION
                               │                      │   (measured)       │        │
                               │                      │                    │        ▼
                               │                      │                    │   TARGET_GENE
                               │                      │                    │   INDUCTION
                               │                      │                    │   (NQO1, HMOX1,
                               │                      │                    │    GCLC, TXNRD1)
                               │                      │                    │        │
                               │                      │                    │        ▼
                               ├──► BASELINE_GSH/GPX ──────────────────────┼──► ANTIOXIDANT
                               │    CAPACITY                               │    CAPACITY
                               │        │                                  │        │
                               │        ▼                                  ▼        ▼
  OXIDANT_DOSE ─────────────────────► EFFECTIVE OXIDATIVE INSULT ◄── DIRECT SCAVENGING
                                            │                        (needs compound present
                                            ▼                         during challenge)
                                      CELL INJURY / DEATH
                                            │
                      ┌─────────────────────┼─────────────────────┐
                      ▼                     ▼                     ▼
              VIABLE CELL COUNT     MEMBRANE INTEGRITY        MTT SIGNAL
              (primary endpoint)      (LDH release)        (redox-dependent)
                                                                  ▲
                                                                  │
  COMPOUND CHEMISTRY ─────────────────────────────────────────► ASSAY INTERFERENCE
  (reducing capacity, fluorescence,                            (MTT direct reduction;
   quenching)                                                   DCF autofluorescence /
                                                                quenching)
                                                                  │
                                                                  ▼
                                                          OXIDATIVE-STRESS SIGNAL
```

Three structural features of this DAG drive the whole benchmark:

**(a) Exposure is a mediator, not a nuisance, on the genotype→survival path.**
`GENOTYPE → NRF2_FUNCTION → UPTAKE_CAPACITY → EXPOSURE → ... → SURVIVAL` is a causal chain. For a
compound whose uptake depends on an NRF2-regulated transporter, the knockout genuinely receives less
compound. The *total* genotype effect on survival is therefore real and NRF2-mediated — but it is
mediated **through delivery**, not through the protective mechanism.

Consequently:
- Conditioning on measured exposure **blocks a causal path**. It does not remove a confounder.
- The exposure-conditioned contrast (Q2) is a *different estimand* — a controlled direct effect of
  genotype at fixed exposure — and answers "is the protective chemistry NRF2-dependent?"
- The unconditioned contrast (genotype difference at fixed administered concentration) answers
  "does this compound work less well in NRF2-deficient cells as administered?"
- **Both are reported.** Neither is "the" answer, and `study_specification.json` states which one the
  `nrf2_dependence_status` classification is built from, so grading is unambiguous.

This is why the output schema carries *both* `protection_index_ko_primary_conc` (unconditioned) and
`protection_index_ko_exposure_matched` (conditioned), and why the classification is explicitly tied to
the latter.

**(b) Assay interference is a path to the *readouts*, not to survival.**
Compound chemistry reaches `MTT SIGNAL` and `OXIDATIVE-STRESS SIGNAL` without passing through
`CELL INJURY`. So interference can manufacture an apparent benefit with no biological protection, and
can also coexist with real protection. Interference must therefore be a *separate* finding from
protection, and the primary survival endpoint must not be a redox-chemistry assay.

**(c) Baseline susceptibility shifts each genotype along its own injury curve.**
`GENOTYPE → BASELINE_GSH/GPX → EFFECTIVE INSULT` means a common oxidant dose produces different
injury per genotype. A protection scale must be referenced to each genotype's *own* unchallenged and
challenged vehicle controls, or genotype comparisons are compressed/inflated by curve position.

### 2.2 Assumption required by each comparison

| Comparison | Identifying assumptions | How the design supports them | Residual threat |
|---|---|---|---|
| **Q1** protection at fixed admin conc, WT | Vehicle-challenged and vehicle-unchallenged controls are exchangeable with treated wells apart from the compound; technical replicates nested in biological experiments; no interference in the primary endpoint | Matched vehicle arms in every experiment × genotype × schedule; primary endpoint is a direct count, not a redox assay; cell-free controls characterise interference separately | Compound could alter cell adhesion/counting efficiency — addressed by the second independent survival endpoint (membrane integrity / LDH) |
| **Q2** protection at matched exposure | A measured-exposure stratum exists in both genotypes with overlapping ranges; exposure is measured on the same scale and at the same sampling time in both; exposure is a sufficient summary of delivery | Nine-point administered-concentration ladder in every genotype, deliberately extended above the WT working range so knockout cells can be dosed up to matched exposure; exposure measured as pmol/10^6 cells at a fixed sampling time | If no overlapping stratum exists, Q2 is **not** answerable → disclosed rule returns `indeterminate` rather than extrapolating |
| **Q3** baseline susceptibility | The oxidant dose–response is measured in each genotype in the same experiments as the compound panel | Dedicated vehicle-only oxidant titration arm (6 doses × 7 cell models) inside every biological experiment; genotype-specific isoeffective dose derived from it | Doses were chosen from the titration curves so that every cell model sustains a closely comparable insult (vehicle-challenged survival 0.493-0.508); the large underlying susceptibility difference remains fully visible in the titration arm and in the common-dose arm |
| **Q4** NRF2 contribution | Knockout removes NRF2 function; re-expression restores it; observed differences are not clone artefacts; schedule arms separate persistent cellular adaptation from transient extracellular chemistry | Two independently derived knockout lineages (KO-A, KO-B); empty-vector controls in WT and KO; functional re-expression in both knockout lineages; pretreatment ± washout; measured residual exposure after washout; cell-free oxidant-neutralisation control | Re-expression is partial (~85–90% of WT function) by design, as in real rescue experiments; the decision rule therefore requires rescue to restore protection rather than to match WT exactly |

### 2.3 Specific confounders that are *designed in* and must be handled

1. **Toxicity masquerading as absence of protection, and high doses masquerading as toxicity.** A
   compound can be protective at a tolerated concentration and frankly toxic above it. The
   concentration-selection rule (disclosed) picks the highest tolerated concentration in WT, so
   protection is never evaluated inside the toxic range.
2. **Residual compound after washout.** "Washout-resistant protection" is only evidence of persistent
   cellular adaptation if the compound is actually gone. Residual intracellular exposure is measured
   after washout so a solver can check this instead of assuming it.
3. **Extracellular oxidant neutralisation.** A compound that chemically consumes the oxidant in the
   medium protects without doing anything to the cell. A cell-free oxidant-neutralisation control
   (ferrous-oxidation/xylenol-orange style peroxide assay) measures this directly.
4. **Batch structure.** Every biological experiment contains every cell model and every treatment
   level, so genotype and treatment are never nested inside batch. Plates within a batch each carry
   multiple cell models, so genotype is not inseparable from plate either.
5. **Technical vs biological replication.** Technical replicates (3 wells, or 3 qPCR reaction wells, or
   2 LC-MS injections) are nested inside biological experiments (5 independent experiments; 3 for
   LC-MS). Treating technical replicates as independent inflates n by 3× and shrinks intervals by
   ~1.7×, which flips borderline classifications. The manifest labels both levels explicitly.

---

## 3. Literature-supported principles vs invented simulation parameters

This separation is required: the benchmark must not present invented numbers as measured properties of
real compounds, and must not claim that its *quantitative* parameters are literature-derived.

### 3.1 Literature-supported qualitative principles used as modelling scaffolding

These are standard, textbook-level statements about the biology/assay chemistry. They are used only as
*structure*; no numeric value is taken from any source.

| Principle | Role in the model |
|---|---|
| NRF2 (gene `NFE2L2`) is a transcription factor that, on electrophilic/oxidative stress, induces a battery of cytoprotective genes including `NQO1`, `HMOX1`, `GCLC` and `TXNRD1` | Defines which genes are "pathway-response" genes and that their induction should be abolished by `NFE2L2` knockout |
| `GCLC` encodes the catalytic subunit of glutamate–cysteine ligase, rate-limiting for glutathione synthesis | Makes the GCLC arm, not the total target-gene response, the arm that couples to peroxide detoxification |
| Organic hydroperoxides such as tert-butyl hydroperoxide are detoxified largely by glutathione-dependent peroxidase activity | Justifies glutathione capacity as the mediator between pathway induction and survival, so a compound can induce other targets without protecting |
| `HMOX1` is inducible by several stress-responsive pathways, not only NRF2 | Justifies a small NRF2-independent `HMOX1` component, so KO cells are not uniformly flat |
| MTT/formazan assays report cellular reductive capacity, and reducing compounds can reduce the tetrazolium directly in the absence of cells | Justifies the cell-free MTT interference control as the correct detector |
| DCFH-DA–type fluorescent probes are vulnerable to compound autofluorescence and to quenching/inner-filter effects | Justifies the two cell-free oxidative-stress controls (dye-free and fixed-standard) |
| Phenolic compounds commonly have both direct radical-scavenging chemistry and indirect pathway-inducing activity, and these can be separated by whether the compound is present during the insult | Justifies the ±washout schedule as the separating contrast |
| qPCR quantification uses ΔΔCt against validated reference genes; reference-gene stability must be demonstrated, not assumed | Justifies supplying raw Ct for two reference genes and keeping them treatment-invariant |
| CRISPR knockout phenotypes require independent lineages and functional re-expression to exclude clone-specific effects | Justifies KO-A/KO-B plus vector and rescue arms |
| LC-MS quantification has a lower limit of quantification below which values are reported as censored | Justifies the `below_lloq` censoring convention |

**No real polyphenol is named anywhere in the package, and no compound in this dataset corresponds to
any real natural product.** `PP01`–`PP08` are neutral identifiers for fictional candidates with
invented physicochemical properties.

### 3.2 Invented simulation parameters (private; never disclosed to the solver)

Everything below is a free parameter chosen by the author to produce a specific, distinguishable
pattern. These values are **not** literature-derived and carry no scientific claim. They live in
`authoring/simulation_parameters.json` and are consumed only by the generator.

- Per-compound uptake capacity (`Emax`, `Km`) and its genotype dependence.
- Per-compound washout retention fraction.
- Per-compound NRF2 activation potency and the per-gene coupling coefficients (including the deliberate
  decoupling of the `GCLC` arm for one archetype).
- Per-compound direct-scavenging rate constant.
- Per-compound intrinsic-toxicity parameters.
- Per-compound MTT direct-reduction coefficient and oxidative-stress-probe autofluorescence/quenching
  coefficients.
- Genotype baseline susceptibility multipliers and rescue efficiency.
- All variance components (batch, plate, well, assay noise), the injury Hill parameters, and the
  assay calibration constants.

**Rule enforced throughout:** every graded quantity is a function of *observable* columns in the
solver-visible CSVs. Generator truth is used only to diagnose whether the simulation produced the
intended pattern, never as the accepted answer. The reference analysis never reads
`simulation_parameters.json`; this is enforced by a check in the validation suite.

---

## 4. Experimental design

### 4.1 Cell models (7)

| id | lineage | NFE2L2 status | transgene | purpose |
|---|---|---|---|---|
| `CM_WT` | IEC-SIM parental | wild type | none | reference genotype |
| `CM_WT_VEC` | IEC-SIM parental | wild type | empty lentiviral vector | controls for transduction/selection per se in WT |
| `CM_KO_A` | clone A | biallelic `NFE2L2` disruption | none | primary knockout |
| `CM_KO_A_VEC` | clone A | biallelic `NFE2L2` disruption | empty lentiviral vector | vector control for the rescue |
| `CM_KO_A_RES` | clone A | biallelic `NFE2L2` disruption | `NFE2L2` coding sequence (functional re-expression) | functional rescue |
| `CM_KO_B` | clone B (independently derived, different guide) | biallelic `NFE2L2` disruption | none | independent lineage — excludes clone-specific effects |
| `CM_KO_B_RES` | clone B | biallelic `NFE2L2` disruption | `NFE2L2` coding sequence | rescue in the second lineage |

Rescue is **partial** by design (functional NRF2 activity ≈ 0.85 of WT in lineage A, ≈ 0.90 in
lineage B), as is typical of re-expression experiments. Decision rules must therefore not require
rescue to equal WT.

Isoeffective oxidant doses actually used (published in `cell_models.csv`), chosen so that the
realised insult, and hence the vehicle-challenged survival, is closely comparable across models:

| cell model | isoeffective dose (µM) | vehicle-challenged survival |
|---|---:|---:|
| `CM_WT` | 200 | 0.503 |
| `CM_WT_VEC` | 194 | 0.497 |
| `CM_KO_A` | 118 | 0.493 |
| `CM_KO_A_VEC` | 115 | 0.496 |
| `CM_KO_A_RES` | 179 | 0.499 |
| `CM_KO_B` | 123 | 0.508 |
| `CM_KO_B_RES` | 185 | 0.502 |

The ~1.7-fold spread in dose is the baseline-susceptibility difference. It is directly measurable
from the vehicle-only titration arm, where at 150 µM the wild type retains 0.660 of its unchallenged
density against 0.365 for `CM_KO_A`.

### 4.2 Factors

- **Compound:** `VEH` (vehicle, DMSO) + `PP01`…`PP08`.
- **Administered concentration (µM):** nine-point ladder `1, 3, 10, 30, 50, 100, 200, 300, 600`.
  The ladder deliberately extends far above the WT working range so that knockout cells — which take up
  some compounds less — can be dosed **up to matched measured exposure** rather than compared by
  extrapolation. The ladder is identical for all compounds and all cell models, so its shape leaks
  nothing about which compound matters.
- **Oxidative challenge:** `CHAL_NONE`; `CHAL_ISO` (genotype-specific isoeffective tert-butyl
  hydroperoxide dose, taken from the titration arm and fixed per cell model in `cell_models.csv`);
  `CHAL_COMMON` (300 µM for every cell model — the *same administered oxidant dose* arm);
  and titration levels `CHAL_T050 … CHAL_T700` (50, 75, 150, 250, 400, 700 µM) used only with vehicle.
- **Treatment schedule:** `PRE_NOWASH` (18 h pretreatment, compound retained through the challenge) and
  `PRE_WASH` (18 h pretreatment, two medium washes, challenge in compound-free medium).
- **Time:** pretreatment 18 h (plus a 6 h pretreatment interim for transcript kinetics); survival and
  injury endpoints 24 h after challenge; oxidative-stress probe 1 h after challenge; exposure sampled at
  end of pretreatment (pre-wash), 0.5 h after washout, and 24 h after challenge.
- **Replication:** 7 independent biological experiments (`BIO01`–`BIO07`) — the units of inference —
  with 4 technical replicate wells per condition for the viability panel (the primary endpoint), 3 for
  the probe panel and 1 for the dye-free probe background wells. LC-MS exposure is run in all 7
  experiments with 2 injection replicates per lysate. qPCR uses 3 reaction replicates per sample.
  Replication was raised from an initial 5 x 3 to 7 x 4 during validation, because the paired
  NRF2-dependence contrast at 5 x 3 could not reliably exclude the classification threshold for the
  non-NRF2-dependent compounds: see `validation_report.md` section 4.2.

### 4.3 Panels (why the design is not a single full factorial)

A single full factorial over all factors would be gratuitously large without adding identifying power.
The design is a union of purpose-built panels; each panel exists to make one comparison identifiable.

| Panel | Purpose (comparison served) | Cell models | Treatments | Challenge | Schedule |
|---|---|---|---|---|---|
| **A_TITRATION** oxidant titration | **Q3** baseline susceptibility; derivation of the isoeffective doses | all 7 | `VEH` only | `T050`–`T700` | `PRE_NOWASH` |
| **B_DOSE_RESPONSE** dose–response | **Q1** protection, concentration selection and toxicity; **Q2** overlapping exposure ranges; washout mechanism | all 7 (`PRE_NOWASH`); `CM_WT`, `CM_KO_A`, `CM_KO_A_VEC`, `CM_KO_A_RES` (`PRE_WASH`) | `VEH` + 8 × the **full 9-point ladder** | `CHAL_NONE`, `CHAL_ISO` | `PRE_NOWASH`, `PRE_WASH` |
| **D_COMMON_DOSE** common-oxidant-dose arm | makes the baseline-susceptibility error *visible and testable* | all 7 | `VEH` + 8 × (`10,30,100`) | `CHAL_COMMON` | `PRE_NOWASH` |
| **R_PROBE** oxidative-stress probe | interference in the probe channel; oxidant load | `CM_WT`, `CM_KO_A`, `CM_KO_A_RES` | `VEH` + 8 × the full ladder, with matched dye-free wells | `CHAL_NONE`, `CHAL_ISO` | `PRE_NOWASH` |
| **Q_TRANSCRIPT** pathway response | pathway induction and its NRF2 dependence; kinetics | 6 (all but `CM_WT_VEC`) | `VEH` + 8 × (`10,50,100,300`) at 6 h and 18 h of pretreatment | `CHAL_NONE` | `PRE_NOWASH` |
| **X_EXPOSURE** compound exposure | **Q2** matched exposure; residual compound after washout | 5 (`CM_WT`, `CM_KO_A`, `CM_KO_A_VEC`, `CM_KO_A_RES`, `CM_KO_B`) | 8 × the full ladder at 4 sampling conditions | `CHAL_NONE`, `CHAL_ISO` | `PRE_NOWASH`, `PRE_WASH` |

The exposure-matching extension originally planned as a separate panel was folded into
`B_DOSE_RESPONSE` by giving that panel the full nine-point ladder, which is simpler and removes an
asymmetry. The transcript panel's concentration set (`10,50,100,300`) was chosen so that it contains
**every compound's primary concentration**, so the pathway response can always be read at the
concentration the protection endpoint is evaluated at; an earlier set omitting 50 µM left two
compounds without transcript data at their own primary concentration.

Panel boundaries are uniform across compounds: no compound receives a panel, concentration or control
that another does not. Panel membership therefore carries no information about which compounds are
protective.

### 4.4 Measurements (five connected assay tables)

1. **`viability_readouts.csv`** — per well: live cell density and dead cell density from imaging-based
   live/dead counting (membrane-impermeant nuclear dye exclusion), total counted field area, LDH
   activity in the supernatant plus the matched maximum-lysis control, and MTT absorbance. The direct
   count is the **primary** endpoint; LDH is an independent injury endpoint; MTT is the
   interference-vulnerable redox endpoint.
2. **`oxidative_stress_readouts.csv`** — DCFH-DA-style probe fluorescence 1 h post challenge, with
   matched dye-free (background) wells.
3. **`qpcr_ct_values.csv`** — raw Ct for `NQO1`, `HMOX1`, `GCLC`, `TXNRD1` and reference genes `ACTB`,
   `RPLP0`, plus the `NFE2L2` amplicon itself for model verification, at 6 h and 18 h of
   pretreatment, in 6 cell models.
4. **`exposure_measurements.csv`** — LC-MS/MS intracellular amount **on column, in pmol**, together
   with the **cell equivalents analysed**, so the exposure on the disclosed per-cell basis has to be
   derived rather than read off; plus the medium concentration (µM). Four sampling conditions (end of
   pretreatment; 0.5 h after washout; 24 h after challenge with and without washout), with LLOQ
   censoring.
5. **`assay_controls.csv`** — cell-free MTT ± compound ± oxidant; cell-free probe fluorescence
   ± dye ± compound; fixed-fluorescein-standard quench test; cell-free oxidant-neutralisation
   (residual peroxide) test; LDH blanks and maximum-lysis standards; qPCR no-template and no-RT
   controls; LC-MS calibration standards and spike-recovery samples.

**Shared variation across assays is modelled, not independently resampled.** Each biological
experiment draws latent factors — a culture-vigour factor, a realised-injury-severity factor, a
transduction/plating factor — and every table from that experiment is generated from those same draws.
A solver that notices correlated batch structure across tables is seeing a real feature of the
simulation, not an artefact.

---

## 5. Estimands, uncertainty, and classification (the graded contract)

All of §5 is disclosed to the solver in `study_specification.json`.

### 5.1 Primary endpoint

Viable cell density, `live_cell_density_1e3_per_well`, 24 h after challenge, `PRE_NOWASH` schedule.
Rationale: a direct count is not a redox measurement, so it cannot be inflated by a compound that
reduces tetrazolium or fluoresces.

### 5.2 Protection index (effect scale)

For a given cell model `g`, compound `c`, concentration `d`, and biological experiment `b`, let
`L̄(·)` denote the mean over technical replicate wells within that experiment. Define

```
PI(g, c, d, b) =  ( L̄(g,c,d,b, CHAL_ISO)  -  L̄(g,VEH,0,b, CHAL_ISO) )
                  ───────────────────────────────────────────────────────
                  ( L̄(g,VEH,0,b, CHAL_NONE) -  L̄(g,VEH,0,b, CHAL_ISO) )
```

i.e. **the fraction of the challenge-induced viability deficit that is recovered**, computed inside each
biological experiment and each cell model, against that cell model's own matched controls.

Why this scale:
- It is genotype-internal, so it is not distorted by different baseline susceptibility (Q3), by any
  residual imperfection in the isoeffective matching, or by the position of a cell model on its own
  injury curve in the common-dose arm.
- It is dimensionless and bounded in a way that makes a single classification threshold meaningful
  across genotypes.
- It is computed per biological experiment *before* aggregation, so the biological experiment stays the
  unit of inference.

Point estimate = mean of `PI` over the 7 biological experiments. This is a mean of 5 ratios, **not** a
ratio of means — disclosed explicitly, because the two differ and both are defensible in the abstract.

### 5.3 Uncertainty convention

Student-*t* interval on the biological-experiment-level values:

```
CI = mean ± t(0.975, n-1) · SD / sqrt(n),    n = number of biological experiments (7 → t = 2.446911851)
```

For the NRF2-dependence contrast, the two genotypes are measured in the **same** biological
experiments, so the contrast is computed **paired**: per-experiment difference first, then mean ± t·SE
on those 7 differences. The required *t* quantiles are tabulated in `study_specification.json` so no
solver needs a statistics library, and no two legitimate implementations can disagree on them.

### 5.4 Concentration-selection rule

The **primary administered concentration** for a compound is the highest concentration on the ladder at
which the compound is tolerated in wild-type cells, where "tolerated" is:

```
tox_ratio = mean_b[ L̄(CM_WT, c, d, b, CHAL_NONE, PRE_NOWASH) ] / mean_b[ L̄(CM_WT, VEH, 0, b, CHAL_NONE, PRE_NOWASH) ]  >=  0.85
```

(point estimate only — no interval — so the rule is deterministic). If no concentration qualifies, the
compound has no primary concentration and all protection fields are reported as not evaluable.

### 5.5 Exposure-matching rule

Let `E_WT` be the mean measured intracellular exposure in `CM_WT` at the primary concentration
(`PRE_NOWASH`, `CHAL_NONE`, end-of-pretreatment sampling, averaged over injections then over
biological experiments). A knockout concentration `d'` **qualifies** as exposure-matched if

```
0.70  <=  E(CM_KO_A, c, d') / E_WT  <=  1.4286
```

Among qualifying concentrations, choose the one minimising `|ln( E(CM_KO_A,c,d') / E_WT )|`; ties break
to the lower concentration. **If no concentration qualifies, there is no exposure-matched stratum**, and
the NRF2-dependence status is `indeterminate` — the design cannot separate pathway dependence from
delivery dependence for that compound, and the contract says so rather than demanding certainty.

### 5.6 Classification rules

`protection_status` (from `PI` in `CM_WT` at the primary concentration, threshold `θ_P = 0.15`):
- `protected` if CI lower bound > 0.15
- `not_protected` if CI upper bound < 0.15
- `indeterminate` otherwise

`nrf2_dependence_status` (threshold `θ_D = 0.15`):
- `not_assessable` if `protection_status != protected`
- else `indeterminate` if no exposure-matched stratum exists (§5.5)
- else `indeterminate` if the two independent knockout lineages disagree (see below)
- else, with `Δ = PI(CM_WT, primary conc) − PI(CM_KO_A, exposure-matched conc)` computed paired:
  - `nrf2_dependent` if `Δ` CI lower bound > 0.15 **and** the rescue criterion holds
  - `not_nrf2_dependent` if `Δ` CI upper bound < 0.15
  - `indeterminate` otherwise (including: `Δ` is large but rescue fails, which cannot exclude a
    clone-specific effect)
- **Rescue criterion:** `PI(CM_KO_A_RES, primary conc)` CI lower bound > 0.15.
- **Independent-lineage corroboration:** a lineage "shows protection" when its `PI` interval lower
  bound at the primary administered concentration exceeds `θ_P`. If `CM_KO_A` and `CM_KO_B` disagree on
  that single boolean, the status is `indeterminate`. The test is placed **before** both `Δ` tests in
  the rule order, so a lineage disagreement yields `indeterminate` whichever side of the threshold `Δ`
  falls on. (An earlier draft placed it only inside the `nrf2_dependent` branch, which contradicted the
  stated rule order; the independent implementation found that gap and it was closed.)

Note that `tox_ratio` above is a **ratio of means** while the protection index is a **mean of ratios**.
The difference is deliberate — the selection rule is a screening criterion on a point estimate, the
protection index is an effect estimate whose unit of inference is the biological experiment — and it is
now documented as such in the solver-visible contract so it cannot read as an oversight.

`interference_flags` — assessed **independently of protection**, from cell-free controls at the primary
concentration, each with a 10% relative threshold and a Student-*t* interval over biological
experiments:
- `mtt` if the cell-free MTT absorbance increment attributable to the compound exceeds 10% of the
  vehicle-treated cellular MTT signal (CI lower bound > 0.10);
- `ros` if **either** the cell-free probe fluorescence increment **or** the magnitude of the
  fixed-standard quench deviation exceeds 10% of the corresponding vehicle-treated cellular signal
  (CI lower bound > 0.10);
- `none` if neither.

A compound may be `protected` **and** carry interference flags. Interference is a statement about the
*measurement*, not a disqualification of the *biology*.

### 5.7 Why these three findings stay separate

- A compound can interfere with MTT and not protect (apparent benefit).
- A compound can protect and interfere (real biology plus a corrupted secondary readout).
- A compound can protect without NRF2 (direct chemistry).
- A compound can induce the pathway and not protect.
Collapsing any of these into a single "hit/no-hit" verdict destroys the distinction. The output
therefore carries three independent status fields, each with its own `indeterminate`/`not_assessable`
value.

---

## 6. Competing explanations the dataset must contain, and the separating contrast

The generator assigns each compound a *latent archetype* (private). The requirement is not that labels
exist, but that **each archetype is distinguishable from its neighbours using supplied observations**.
The table below is the identifiability contract; the validation suite checks each row empirically.

| # | Explanation present in the data | Separating evidence available to the solver |
|---|---|---|
| 1 | NRF2-dependent protective contribution | Protection in WT; absent in KO-A **and** KO-B; restored by functional re-expression but not by empty vector; target-gene induction present in WT/rescue and absent in KO; protection survives washout; residual exposure after washout confirms washout actually removed most compound; cell-free oxidant-neutralisation negative |
| 2 | Protection that persists without NRF2 | Comparable protection in WT and KO at matched measured exposure; little or no target-gene induction; protection largely abolished by washout; cell-free oxidant-neutralisation positive |
| 3 | Apparent benefit caused primarily by assay interference | Large MTT and probe-fluorescence "improvement" with **no** improvement in direct live-cell count and no reduction in LDH release; cell-free MTT ± compound reproduces the entire MTT signal without cells; cell-free probe controls reproduce the fluorescence shift |
| 4 | Genuine protection accompanied by assay interference | Direct count **and** LDH both improve (so protection is real and NRF2-dependent by the arms in row 1), while the cell-free fixed-standard quench test shows the probe readout is independently corrupted |
| 5 | Pathway-response gene induction without improved survival | Strong, NRF2-dependent induction of `NQO1`/`HMOX1`/`TXNRD1` with little `GCLC` induction; no improvement in live-cell count or LDH at any tolerated concentration; no interference |
| 6 | Dose-dependent toxicity / absence of supported protection | Monotone fall in unchallenged live-cell density and rise in LDH with concentration; concentration-selection rule forces evaluation at a low concentration where protection is absent |
| 7 | Apparent genotype difference that changes interpretation once exposure is considered | Protection in WT but not KO **at equal administered concentration**, while measured intracellular exposure in KO is several-fold lower at that concentration; at the exposure-matched knockout concentration the protection is fully restored → the genotype difference is delivery, not pathway |
| 8 | Genotype difference that **cannot** be resolved (→ `indeterminate`) | Protection in WT, none in KO, rescue restores — but measured KO exposure *saturates* below the WT working exposure across the whole nine-point ladder, so no exposure-matched stratum exists and pathway dependence cannot be separated from delivery dependence |

Rows 7 and 8 are the pair that forces an honest `indeterminate`: identical qualitative patterns at fixed
administered concentration, opposite correct conclusions, separated **only** by whether the measured
exposure ranges overlap.

Archetype→compound-identifier assignment is shuffled (private, recorded in
`authoring/simulation_parameters.json`) so the identifier order carries no pattern. Identifier
permutation invariance is tested in the validation suite.

---

## 7. Limits of interpretation — what this design does *not* support

Stated here, and restated in the solver-visible specification, because overclaiming is itself a
scientific error the benchmark should not reward:

1. **No molecular-binding claim.** Nothing in this dataset measures a physical interaction between a
   compound and KEAP1, NRF2, or any other protein. "NRF2-dependent" here means *"the protective effect
   requires NFE2L2 gene function under the supplied interventions"* — a genetic-dependence statement
   about this system, nothing more.
2. **No clinical or dietary inference.** Submicromolar-to-high-micromolar concentrations applied to a
   simulated immortalised epithelial monolayer for 18 h say nothing about achievable human exposure,
   bioavailability, or benefit.
3. **No claim about real compounds.** `PP01`–`PP08` are fictional. Their simulated activity profiles
   must not be attributed to any named natural product.
4. **No causal claim beyond the supplied interventions.** Rescue restores NRF2 function *and* the
   NRF2-dependent transporter; where exposure cannot be matched, the design cannot attribute the
   genotype effect to one or the other, and the contract requires `indeterminate`.
5. **Mechanistic resolution is bounded by the assays supplied.** The dataset distinguishes
   adaptive-cellular from extracellular-chemical protection, and pathway-dependent from
   pathway-independent protection. It does not distinguish *which* NRF2 target gene product is
   proximally responsible, and no output asks a solver to claim that.
6. **Single simulated cell system, single oxidant.** No generalisation across injury models is
   supported.
