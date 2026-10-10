# Provenance, AI-assistance disclosure, and eligibility status

**Package:** `polyphenol_cell_biology` synthetic computational-biology benchmark
**Build date:** 2026-10-10
**Dataset version:** `v1.0.0`, generator seed `20261010`

---

## 1. Synthetic-data disclosure

**Every value in this package is synthetic.** The dataset was produced by a stochastic
simulation (`authoring/generator/generate_dataset.py` driving `authoring/generator/simcore.py`)
from a single integer seed. No value was measured in any laboratory, by anyone, at any time.

Specifically:

- The cell line `IEC-SIM` does not exist. It is a fictional simulated human intestinal
  epithelial line. Its properties — doubling times, seeding densities, susceptibility to the
  oxidant, knockout clone behaviour — are invented simulation parameters.
- The compounds `PP01`–`PP08` do not exist. They are fictional synthetic test articles with
  invented molecular weights, logP values, solubilities, purities, LC-MS transitions and
  limits of quantification. **They do not correspond to, and must not be attributed to, any
  real polyphenol or any other named natural product.** No real compound is named anywhere in
  the package.
- All simulated activity profiles — protection, NRF2 dependence, uptake, toxicity, assay
  interference — are author-chosen free parameters. They are **not** measured properties of
  anything, and they are not literature values.
- The knockout clones, vector controls, rescue lines, plate maps, batch structure and all
  observations are simulated.

## 2. What is literature-supported and what is invented

The package separates these deliberately, and the separation is documented in full in
`authoring/design/design_and_causal_assumptions.md` §3.

**Literature-supported, used only as qualitative structure** (textbook-level statements, used
to decide the *shape* of the model; no numeric value is taken from any source):

that NRF2 (gene `NFE2L2`) induces a battery of cytoprotective genes including `NQO1`, `HMOX1`,
`GCLC` and `TXNRD1`; that `GCLC` is rate-limiting for glutathione synthesis; that organic
hydroperoxides are detoxified largely by glutathione-dependent peroxidase activity; that
`HMOX1` is inducible by several stress pathways and not only by NRF2; that tetrazolium
(MTT/formazan) assays report reductive capacity and can be reduced directly by reducing
compounds in the absence of cells; that DCFH-DA-type fluorescent probes are vulnerable to
compound autofluorescence and to quenching; that phenolic compounds commonly have both direct
radical-scavenging chemistry and indirect pathway-inducing activity, separable by whether the
compound is present during the insult; that qPCR quantification requires validated reference
genes whose stability must be demonstrated; that CRISPR knockout phenotypes require
independent lineages and functional re-expression to exclude clone-specific effects; and that
LC-MS quantification is left-censored below a limit of quantification.

**Invented free parameters** (author-chosen, carrying no scientific claim): every numeric
value in `authoring/generator/simulation_parameters.json`, including all per-compound uptake,
potency, gene-coupling, scavenging, toxicity and interference coefficients; the genotype
susceptibility multipliers and rescue efficiencies; the injury Hill parameters; all variance
components; and all assay calibration constants.

**Enforced rule:** no graded answer depends on a hidden generator parameter. Every graded
quantity is a function of observable columns in the solver-visible CSVs, computed under the
contract published in `study_specification.json`. The reference analysis does not read the
simulation parameters, and a validation check asserts that it does not.

## 3. AI assistance

This package was **built with AI assistance throughout**. An AI coding assistant (Claude,
Anthropic) was used to author the design document, the simulation core, the generator, the
contract documents, the reference analysis, the verifier, the validation suite and the
reporting. The independent second analysis, the six shortcut analyses and the leakage audit
were produced by separate AI agent instances that were given access only to the
solver-visible files and were explicitly denied access to the generator, the simulation
parameters and the reference solver (the independence constraint is recorded in
`authoring/independent/NOTES.md`).

A human directed the work, set the requirements, and is responsible for the result. **No part
of this package should be described as entirely human-created.** Any submission or
publication that includes it should carry an AI-assistance disclosure equivalent to this
section.

## 4. Reused material, external code, and licences

- **No prior customer dataset, confidential material, or proprietary document was consulted
  or copied.**
- **No copyrighted figure, table, or dataset was copied.** No text, figure or table was
  reproduced from any publication. The literature-supported statements in §2 are
  textbook-level facts expressed in the author's own words; none is a quotation, and none
  carries a numeric value taken from a source.
- **No external code was vendored.** All code in `authoring/` was written for this package.
- **Third-party runtime dependencies** (used, not redistributed) are listed with their
  versions in `authoring/DEPENDENCIES.txt`. The generator and the validation suite use
  `numpy` and `pandas` (both BSD-3-Clause). The reference analysis and the verifier use only
  the Python standard library (PSF licence), so the graded path has no third-party
  dependency at all.
- **Gene symbols** (`NFE2L2`, `NQO1`, `HMOX1`, `GCLC`, `TXNRD1`, `ACTB`, `RPLP0`) are
  standard HGNC identifiers, used as nomenclature. **Chemical names** (`tert-butyl
  hydroperoxide`, `DMSO`, `MTT`, `DCFH-DA`, `fluorescein`, `puromycin`, `Triton X-100`) are
  generic names of common laboratory reagents, used as nomenclature. Neither constitutes
  reused copyrighted material.

## 5. Benchmark-platform guideline review and eligibility

**TerminalBench guidelines were not available in this environment.** A search of the build
environment found no TerminalBench guideline document, rule set, or submission template
(`find / -iname "*terminal*bench*"` returned nothing; no `/app` directory and no guideline
file existed at build time). The package was therefore built against the requirements given
by the requester, not against a platform rule set.

**Unresolved restrictions that a reviewer must check before any submission.** These could not
be resolved locally and are stated as open questions, not as cleared items:

1. **Are fully synthetic inputs eligible?** Some benchmark platforms require tasks to be
   grounded in real data or real software, and may exclude simulated datasets. This package
   is 100% synthetic by design.
2. **Is AI-assisted authoring permitted, and how must it be disclosed?** This package is
   AI-assisted throughout (§3). Platforms differ on whether that is allowed, whether it must
   be declared, and in what form.
3. **Are there limits on input size, file count, runtime, or offline operation** that this
   package's ~20 MB of inputs across 11 files would breach?
4. **Is the required output contract (a single `/app/results.csv`) the expected shape**, and
   is an externally supplied verifier script acceptable?
5. **Is a task whose correct answer includes an `indeterminate` verdict acceptable**, or do
   platform rules require every item to have a definite answer? One compound's
   NRF2-dependence status is correctly `indeterminate`, by design.

**No claim of submission eligibility or platform approval is made.** This package has not
been reviewed or approved by any benchmark platform, and nothing here should be read as
asserting that it has.

## 6. What was deliberately NOT done

- **No material was uploaded anywhere.** The entire build is local.
- **No external model trial was initiated.** No agent was run against the task to measure
  difficulty, and no frontier-difficulty claim is made. See `validation_report.md` §
  "Difficulty-testing status": frontier difficulty is **unmeasured**.
- **The solver-facing submission prompt was deliberately left unwritten**, as requested. The
  package contains the data, the contract, the reference analysis, the verifier and the
  evidence; it does not contain the instruction text that would be handed to a solver.
