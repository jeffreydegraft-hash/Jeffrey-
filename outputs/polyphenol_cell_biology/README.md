# `polyphenol_cell_biology` — a synthetic computational-biology benchmark

**Scientific task.** Given a simulated study of eight polyphenol-like candidate compounds in
intestinal epithelial cells, decide for each compound (a) whether it produces a supported
improvement in cell survival after an acute oxidative challenge, (b) whether the observations
support an **NRF2-dependent** contribution to that protection, and (c) whether the compound
**interferes with one or more assay measurements** — while distinguishing genuine biological
protection from compound toxicity, from differences in intracellular exposure, and from
interference with the assay chemistry.

The three findings are reported **separately**, so that a compound which is both genuinely
protective and an assay interferer remains representable, and so that an honest
`indeterminate` is available where the design cannot resolve a question.

**Dataset version** `v1.0.0` · generator seed `20261010` · built 2026-10-10.

> ### All data here is synthetic
> Every value was produced by a stochastic simulation. Nothing was measured in a laboratory.
> `PP01`–`PP08` are **fictional** test articles and the cell line `IEC-SIM` is **fictional**;
> none corresponds to any real polyphenol, natural product or cell line, and the simulated
> activity profiles must not be attributed to any real compound. This package was built with
> **AI assistance throughout**. Full disclosure: `authoring/design/PROVENANCE.md`.

---

## 1. What is delivered

```
outputs/polyphenol_cell_biology/
├── README.md                  this file
├── validation_report.md       every check that was executed, with results
├── SHA256SUMS.txt             checksums of all delivered files
├── solver_inputs.zip          ONLY the solver-visible inputs (11 files)
└── authoring/                 everything a reviewer needs, kept OUT of the archive
    ├── expected_results.csv   the expected answer table
    ├── DEPENDENCIES.txt        runtime and dependency policy
    ├── design/
    │   ├── design_and_causal_assumptions.md   study design, DAG, estimands, limits
    │   └── PROVENANCE.md                      synthetic-data + AI-assistance disclosure
    ├── generator/
    │   ├── simcore.py                  PRIVATE latent model and parameters
    │   ├── simulation_parameters.json  PRIVATE latent parameter dump
    │   ├── generate_dataset.py         builds every solver-visible file from a seed
    │   ├── make_data_dictionary.py     builds data_dictionary.csv, fails on drift
    │   └── calibrate.py                noise-free design-verification report
    ├── reference/reference_analysis.py       reference solver (stdlib only)
    ├── independent/
    │   ├── independent_analysis.py     separately written cross-check (numpy/pandas)
    │   └── NOTES.md                    its ambiguity findings and internal cross-checks
    ├── verifier/verify_results.py            deterministic verifier (stdlib only)
    ├── shortcuts/shortcut_*.py               six deliberately limited analyses
    └── validation/                     the validation suite and all its evidence
        ├── seed_sweep.py                 multi-seed stability + byte reproducibility
        ├── negative_tests.py             malformed and altered submissions
        ├── invariance_and_integrity.py   joins, units, balance, leakage, invariance
        ├── shortcut_runner.py            runs shortcuts and grades them honestly
        ├── clean_room_test.py            extract the archive and rebuild the answer
        ├── audit_report.md               independent blind leakage / coherence audit
        ├── identifiability.py            evidence that each distinction is recoverable
        └── *_report.json  results_*.csv  machine-readable evidence for every check
```

**All authoring material and all expected answers are outside `solver_inputs.zip`.** The
archive contains exactly eleven files and nothing else; `package.py` refuses to build an
archive containing any authoring, expected-result or generator file, and
`validation/invariance_and_integrity.py` separately audits the archive's contents for leakage.

## 2. Solver-visible inputs

Mounted at `/app/data/`. Combined uncompressed size **20.8 MB** across 11 files; largest single
file 9.8 MB — inside the 25 MB target and far inside the 100 MB per-file limit. The delivered
archive compresses to 3.2 MB.

| file | rows | cols | bytes | what it holds |
|---|---:|---:|---:|---|
| `compounds.csv` | 9 | 13 | 1,350 | physicochemical descriptors, vehicle, stock, LC-MS transition, limits of quantification |
| `cell_models.csv` | 7 | 16 | 1,909 | genotypes, edits, guides, transgenes, selection, immunoblot verification, challenge doses |
| `sample_manifest.csv` | 76,160 | 20 | 9,774,310 | the join hub: one row per sample, linking every measurement to compound, concentration, cell model, schedule, challenge, batch, plate, biological experiment and technical replicate |
| `viability_readouts.csv` | 51,044 | 9 | 2,614,369 | live/dead nuclei counts, supernatant LDH, MTT absorbances (570 and 630 nm) |
| `oxidative_stress_readouts.csv` | 12,264 | 8 | 527,085 | probe fluorescence with matched dye-free background wells |
| `qpcr_ct_values.csv` | 58,212 | 6 | 1,906,352 | raw Ct for four pathway-response genes, the `NFE2L2` amplicon and two reference genes, at 6 h and 18 h |
| `exposure_measurements.csv` | 30,240 | 12 | 3,282,784 | LC-MS/MS amounts in lysate and medium at four sampling conditions, with LLOQ censoring |
| `assay_controls.csv` | 16,282 | 16 | 2,664,771 | cell-free MTT; cell-free probe ± dye; fixed-fluorophore quench standard; cell-free oxidant neutralisation + peroxide calibration; LDH blank and maximum lysis; qPCR no-template/no-RT; LC-MS calibration and spike recovery |
| `data_dictionary.csv` | 100 | 6 | 20,928 | every column of every file: unit, type, allowed values, meaning |
| `study_specification.json` | — | — | 32,121 | the full evaluation contract (see §3) |
| `output_schema.json` | — | — | 11,578 | the required schema of `/app/results.csv` |

### Design at a glance

- **7 cell models**: wild type; empty-vector wild type; two **independently derived**
  `NFE2L2` knockout clones (different guide RNAs); an empty-vector knockout; and functional
  `NFE2L2` re-expression in **both** knockout lineages.
- **9-point administered-concentration ladder** (1–600 µM), identical for every compound and
  every cell model, extending deliberately above the wild-type working range so that cell
  models which take up a compound less can be dosed up to **matched measured exposure**
  instead of compared by extrapolation.
- **Challenge arms**: unchallenged; a cell-model-specific **isoeffective** oxidant dose; a
  single **common** oxidant dose for every model; and a vehicle-only **oxidant titration**
  that characterises each model's baseline susceptibility.
- **Schedules**: 18 h pretreatment with the compound retained through the challenge, and with
  the compound **washed out** before it — plus measured **residual exposure after washout**,
  so washout-resistant protection need not be assumed.
- **7 independent biological experiments** (the units of inference) with **4 technical
  replicate wells** nested inside each for the primary endpoint, 3 for the probe panel and 1
  for the dye-free probe background wells. Every experiment contains every cell model and every
  treatment level; no plate carries only one cell model or only one compound, so neither is
  inseparable from batch or plate. Culture formats (96-, 24- and 12-well) each carry well
  positions and a per-plate well count consistent with that format.
- **Connected measurements**: direct live/dead counts, LDH release, a redox-dependent MTT
  readout with matched cell-free controls, a fluorescent oxidative-stress probe with dye-free
  and cell-free controls, raw qPCR Ct values with validated reference genes, and LC-MS/MS
  exposure. Observations from the same biological experiment share latent factors (culture
  vigour, realised injury severity, instrument gain) — the tables are **not** generated
  independently.

## 3. The evaluation contract

`study_specification.json` discloses everything needed to be graded fairly, so no solver has
to guess a convention: the **primary endpoint** (live-cell count at 24 h, deliberately *not* a
redox assay); the **effect scale** (protection index = fraction of the challenge-induced
viability deficit recovered, computed inside each cell model against that model's own matched
controls, as a mean of per-experiment ratios and explicitly **not** a ratio of means); the
**primary condition**; the **concentration-selection rule**; the **exposure-matching rule**
including what to do when no overlapping exposure stratum exists; the **uncertainty
convention** with a published Student-t table so no statistics library is needed; the
**classification thresholds and rule order**; the **NA token**; the **censoring conventions**;
the **evidence-reference format**; and the **grading tolerances**.

`output_schema.json` fixes `/app/results.csv`: one row per compound, 17 columns, carrying the
evaluated concentration and exposure, the protection effects in wild-type / knockout / rescue
conditions, the exposure-matched knockout effect, the NRF2-dependence contrast with its
interval, three independent status fields, and supporting record identifiers.

**Causal note, stated in the contract.** Intracellular exposure can *mediate* a genotype
effect: where uptake depends on an NRF2-regulated process, knockout cells genuinely receive
less compound. Conditioning on measured exposure therefore blocks a causal path rather than
removing a confounder, and answers a different question from the unconditioned comparison.
Both comparisons are reported; the contract states which one the NRF2-dependence
classification is built from.

## 4. Reproducing everything

Python 3.13; `numpy` and `pandas` for the generator and validation suite. **The graded path —
the reference analysis and the verifier — uses the Python standard library only**, so it runs
in a clean interpreter with nothing installed. See `authoring/DEPENDENCIES.txt`.

All commands are run from the repository root.

```bash
WORK=work/polyphenol_cell_biology

# 1. Regenerate the dataset from the seed (byte-reproducible) and rebuild the dictionary
cd $WORK/generator
python3 generate_dataset.py --seed 20261010 --out ../data
python3 make_data_dictionary.py --data ../data
cd -

# 2. Noise-free design-verification report (reads PRIVATE parameters; authoring only)
python3 $WORK/generator/calibrate.py

# 3. Reference analysis — reads ONLY the solver-visible files
python3 $WORK/reference/reference_analysis.py --data $WORK/data \
    --out $WORK/validation/results_reference.csv

# 4. Independently written cross-check — does not import the reference solver
python3 $WORK/independent/independent_analysis.py --data $WORK/data \
    --out $WORK/validation/results_independent.csv

# 5. Verify both (must both pass)
python3 $WORK/verifier/verify_results.py --results $WORK/validation/results_reference.csv \
    --data $WORK/data --expected $WORK/validation/expected_results.csv
python3 $WORK/verifier/verify_results.py --results $WORK/validation/results_independent.csv \
    --data $WORK/data --expected $WORK/validation/expected_results.csv

# 6. Validation suite
python3 $WORK/validation/seed_sweep.py --workdir /tmp/sweep \
    --seeds 20261010 7 101 20240229 31337 555 20260601 1 999983 42
python3 $WORK/validation/negative_tests.py --workdir /tmp/neg
python3 $WORK/validation/invariance_and_integrity.py --workdir /tmp/inv
python3 $WORK/validation/shortcut_runner.py --workdir /tmp/sc

# 7. Build the package, then prove the answer is recoverable from the archive alone
python3 $WORK/package.py --workdir /tmp/pkg
python3 $WORK/validation/clean_room_test.py \
    --zip outputs/polyphenol_cell_biology/solver_inputs.zip \
    --reference outputs/polyphenol_cell_biology/authoring/reference/reference_analysis.py \
    --verifier  outputs/polyphenol_cell_biology/authoring/verifier/verify_results.py \
    --expected  outputs/polyphenol_cell_biology/authoring/expected_results.csv \
    --workdir /tmp/cr

# 8. Checksums
cd outputs/polyphenol_cell_biology && sha256sum -c SHA256SUMS.txt
```

To run the task the way a solver would: extract `solver_inputs.zip` to `/app/data/` and write
`/app/results.csv`.

## 5. Limitations and honest caveats

**Difficulty is unmeasured.** No agent trial was run. The package has been shown to be
scientifically coherent and to have reproducibly recoverable answers; **neither of those
establishes that strong agents find it hard.** No failure rate is claimed and the task is not
described as frontier-stumping. See `validation_report.md` § "Difficulty-testing status".

**Interpretation limits built into the task.** The contract states these, and a correct answer
respects them:
- "NRF2-dependent" means only *"the protective effect requires `NFE2L2` gene function under
  the supplied interventions"*. Nothing here measures molecular binding to KEAP1, NRF2 or any
  protein.
- No clinical, dietary or bioavailability inference is supported.
- Where measured exposure ranges do not overlap between genotypes, the design **cannot**
  separate pathway dependence from delivery dependence, and the required answer is
  `indeterminate`. One compound is in exactly that position by design.
- A single simulated cell system and a single oxidant; no generalisation across injury models.
- The design distinguishes adaptive cellular protection from extracellular oxidant chemistry,
  and pathway-dependent from pathway-independent protection. It does **not** identify which
  target gene product is proximally responsible, and no output asks a solver to claim that.

**Known limitations of the package itself** (detailed with evidence in `validation_report.md`):
- One of the six shortcut methods — counting technical replicates as independent biological
  experiments — reaches every correct categorical conclusion and is caught **only** because the
  confidence-interval bounds are graded per row. Had the task graded only point estimates and
  statuses it would have passed undetected. Reported as measured, not papered over.
- One convention the contract insists on (mean of ratios, not ratio of means) turns out not to
  be load-bearing on this dataset: the two estimators differ by ≤9.5×10⁻⁴ here.
- An independent blind audit found six real defects — a misdescribed batch structure, an
  incomplete censoring description, a `culture_format` that disagreed with the well grid, a
  wrong dictionary line, an undeclared generator artefact in the data directory, and an
  undocumented property of the LDH index. All six are fixed; they are listed in
  `validation_report.md` §8 rather than quietly dropped.
- The independent-knockout-lineage corroboration rule exists and is implemented, but this
  dataset never exercises its disagreement branch — the two lineages agree for all eight
  compounds.
- The `not_evaluable` branch of the concentration-selection rule is defined but never taken,
  since every compound has a tolerated concentration.
- Benchmark-platform guidelines were not available in this environment, so platform
  eligibility is **unresolved**; `authoring/design/PROVENANCE.md` § 5 lists the specific open
  questions a reviewer must check.

**The solver-facing submission prompt is deliberately not written**, as requested.
