# Independent second implementation — notes

Implementation: `/home/user/Jeffrey-/work/polyphenol_cell_biology/independent/independent_analysis.py`
Output: `/home/user/Jeffrey-/work/polyphenol_cell_biology/validation/results_independent.csv`

Written only from `data/study_specification.json`, `data/output_schema.json` and
`data/data_dictionary.csv`. The generator, private parameters, reference solver,
design and verifier directories were not read.

Run as:

```
python3 independent/independent_analysis.py --data data \
        --out validation/results_independent.csv
```

A `--diagnostics <path.json>` flag is also available; it dumps the per-compound
tox-ratio ladder, per-experiment PI values, exposure-matching ladder with the
E_KO/E_WT ratio and censoring verdict for every rung, the rescue and lineage
sub-decisions, and the three interference indices. It was used for the
cross-checks below and is not needed to produce the results.

---

## 1. Points where the specification felt ambiguous, and what I chose

### 1.1 The input files were regenerated mid-task, with a different n

This is the most important thing for the benchmark author to know. When I started,
`data/` held **6 biological experiments and 3 technical replicate wells**, and the
spec declared six experiments with `t_quantile_for_graded_quantities = 2.570581836`.
Partway through, the CSVs were rewritten to **7 biological experiments and 4
viability wells per condition**; about a minute later `study_specification.json`,
`output_schema.json` and `data_dictionary.csv` caught up (7 experiments,
`t = 2.446911851`, `sqrt(7)`, evidence lists of 7–30 ids, `technical_replicate`
documented as 1–4). For roughly a minute the CSVs and the contract disagreed.

I therefore wrote the implementation so that it **reads from the specification at
run time** rather than hard-coding a snapshot: the concentration ladder, the
compound list, the Student-t table, `theta_P` / `theta_D` / the interference
threshold, the primary condition (cell model, challenge, schedule, panel, readout
time), the declared set of biological experiments, the NA token and the required
row count all come out of the two JSON files. The t quantile is looked up by
`dof = n - 1` where `n` is the number of biological experiments that actually
contributed, exactly as `uncertainty_convention.formula` and `t_table_note`
prescribe. The script warns on stderr if the experiments present in the data
differ from the declared set, or if the spec's
`t_quantile_for_graded_quantities` is not the table entry for the declared n.
On the current data neither warning fires and n = 7 everywhere.

**Recommendation:** regenerate the CSVs and the three contract documents in one
atomic step, so a solver can never observe a mismatched pair.

### 1.2 Stale "5 biological experiments" / "five differences" in the contract

Three places still carry a figure from an earlier parameterisation, and they
contradict the rest of the contract:

| Location | Stale text | What the rest of the contract says |
|---|---|---|
| `classification.protection_status.input` | "its 95% Student-t interval over the **5** biological experiments" | 7 |
| `exposure_matching_rule.aggregation` | "fewer than 3 of the **5** biological experiments yield a measured value" | 7 |
| `output_schema` `nrf2_dependence_contrast_ci_low` | "the **five** paired per-experiment differences: mean - 2.446911851 * SD / sqrt(7)" | 7, and the formula in the same sentence is the n = 7 one |

I resolved all three in favour of the self-consistent machinery:
`n` = number of biological experiments contributing (7 here), `t` indexed by
`n - 1`. For the exposure censoring rule I kept the literal **count 3** as the
minimum number of experiments with a measured value, and treated the "of the 5"
as the stale part. Note that with 7 experiments the rule now means "at least 3 of
7", which is a weaker requirement than "at least 3 of 5"; if the intent was a
*fraction* of experiments, the rule should say so.

### 1.3 `tox_ratio` is a ratio of means, while the protection index is a mean of ratios

`effect_scale.aggregation` is emphatic that the PI point estimate is a mean of
per-experiment ratios and not a ratio of means. `concentration_selection_rule`
then defines `tox_ratio` the other way round — "mean over biological experiments
of Lbar(...) divided by mean over biological experiments of Lbar(VEH, 0, ...)",
i.e. a ratio of means. Both statements are explicit, so I implemented each
literally as written. It reads as an inconsistency of style rather than of intent;
if the author wants one convention throughout, the selection rule is the sentence
to change. It makes no practical difference here (see cross-check 9).

### 1.4 Which wells supply the cell-based denominator of the MTT interference index

`mtt_interference_index` names its denominator as "mean mtt_signal of
vehicle-treated CM_WT cells at CHAL_NONE, PRE_NOWASH" without naming a panel or a
readout time. In this dataset only `B_DOSE_RESPONSE` contains CM_WT / VEH /
CHAL_NONE / PRE_NOWASH viability wells (`A_TITRATION` carries only the CHAL_Tnnn
levels, `D_COMMON_DOSE` only CHAL_COMMON), so the reference is unique in practice.
I used the primary panel at the 24 h readout. Worth naming the panel explicitly in
the spec in case a future parameterisation adds a second source of such wells.

### 1.5 The lineage-corroboration rule sits in two places that can disagree

`independent_lineage_corroboration` says a disagreement between CM_KO_B and
CM_KO_A "**forces** the status to 'indeterminate'". But the rule list places the
lineage test only inside the `nrf2_dependent` branch, and `evaluation_order` says
the first matching rule wins. So if Delta's CI upper bound were below `theta_D`
*and* the lineages disagreed, the ordered rules would return
`not_nrf2_dependent` while the prose demands `indeterminate`.

I followed `evaluation_order`, as instructed. The two readings cannot differ on
this data: the lineages agree for all eight compounds (cross-check 12). To close
the gap, either move the lineage test ahead of the `not_nrf2_dependent` rule or
drop the word "forced".

### 1.6 Binarising a three-valued rule for the lineage comparison

The lineage test asks whether "one shows protection by the protection_status rule
and the other does not", but that rule has three outcomes. I binarised it as
`CI lower bound > theta_P` versus not, so an `indeterminate` lineage counts as
*not* showing protection. The alternative (treating `indeterminate` on either side
as a disagreement) would sometimes differ. It never bites here — both lineages
land on the same side for every compound.

### 1.7 Is `E_WT` itself subject to the censoring rule?

`exposure_matching_rule.aggregation` states the "fewer than 3 experiments" test
for the candidate concentrations. It does not say whether the same test guards the
reference quantity `E_WT`. I did not apply a censoring test to `E_WT`; I simply
average the experiments that yielded a measured value. All eight compounds have
7/7 measured experiments at their primary concentration, so the choice is inert.

### 1.8 The `not_evaluable` branch leaves two fields undefined

`concentration_selection_rule.if_none_qualifies` says to report
`primary_concentration_um = NA` and "every protection, dependence and interference
field as NA, with `protection_status = 'not_evaluable'`". It does not say what
`nrf2_dependence_status` should be, and that column is `nullable: false` with a
closed value set that does not include NA. Applying the rule order gives
`not_assessable` (protection_status is not 'protected'), which is what I emit.
`interference_flags` is likewise `nullable: false` in the schema but covered by
"every ... interference field as NA" in the spec; I emit NA there. Neither branch
is exercised — all eight compounds have a tolerated concentration.

### 1.9 Boundary handling

The classification rules are written with strict inequalities on both sides, which
leaves exact equality with a threshold falling through to `indeterminate`. I
implemented them exactly as written. `grading_tolerances.classification_margin_note`
promises every compound sits well clear of every boundary, and that holds: the
closest approach to a status boundary in my output is PP05's Delta upper bound at
0.0985 against `theta_D = 0.15`.

---

## 2. Internal cross-checks run

All of these pass on the current data.

1. **Output structure.** Header matches `output_schema.json` exactly and in order;
   8 rows, one per PP01..PP08, no VEH; every `number` field either parses as a
   float or is the literal `NA`; no empty cell. Both confidence intervals bracket
   their point estimate in every row.
2. **Technical-replicate counts are what the spec claims.** Viability: exactly 4
   wells per condition per experiment, and exactly 7 experiments for all 1022
   viability conditions. Probe: 3 dye-loaded wells and 1 dye-free well per
   condition per experiment. qPCR: 3 reaction replicates per (sample, gene).
   LC-MS: 2 injection replicates per cell-lysate sample. Cell-free MTT controls:
   3 technical replicates per (compound, concentration, experiment, challenge,
   measured quantity). Every count matches
   `experimental_design.replication.technical_replication`, and no graded quantity
   treats a technical replicate as an independent unit — technical replicates are
   collapsed into `Lbar` before any experiment-level statistic is taken.
3. **Reference-gene stability.** Spread of mean Ct across all treatment levels:
   ACTB 0.176 cycles, RPLP0 0.185 cycles — against NQO1 1.841 and HMOX1 1.603 for
   the pathway-response genes. The reference genes are flat and the inducible genes
   move, so the normaliser choice in `delta_delta_ct` is justified rather than
   assumed. (The transcript data is not used by any graded output; this is a
   sanity check on the dataset.)
4. **Cell-model verification from the NFE2L2 amplicon.** Mean Ct: CM_WT 24.82,
   CM_KO_A 27.54, CM_KO_A_VEC 27.56, CM_KO_B 27.27 (knockouts shifted late), and
   the rescues earlier than wild type at 21.88 / 21.75 — consistent with
   over-expressed re-introduced CDS and with the immunoblot column in
   `cell_models.csv`.
5. **Vehicle protection index is ~0.** A protection index computed directly on
   vehicle wells is identically zero by construction (its numerator is the same
   quantity twice), so that is not a real test. Instead I split the vehicle
   CHAL_ISO technical replicates in half within each (cell model, experiment) and
   used one half as pseudo-treated against the other half as control: mean
   pseudo-PI 0.0039, SD 0.0273, largest absolute value 0.0546 over 49 cell-model ×
   experiment strata. The PI scale carries no offset, and its well-level noise is
   an order of magnitude below the protective effects reported (~0.52–0.60).
6. **Challenge-induced deficit denominator.** `Lbar(VEH, CHAL_NONE) -
   Lbar(VEH, CHAL_ISO)` is positive in all 49 strata, and the deficit fraction is
   0.49–0.51 of the unchallenged density in every one of the seven cell models —
   so the isoeffective matching really is close to isoeffective, and no PI is
   produced by a near-zero or sign-flipped denominator.
7. **Censoring occurs only where the spec says it does.** `below_lloq` at
   END_PRETREAT_NOWASH appears exclusively at the lowest ladder rung (1 uM, 152
   rows); the rest of the censoring is in POST_WASH_0P5H and the two
   POST_CHALLENGE conditions. Censored observations are dropped, never imputed and
   never read as zero — in the code they are filtered out before any averaging.
8. **Exposure is monotone in administered concentration** for CM_WT for all eight
   compounds, so the exposure-matching search is over a well-behaved ladder. The
   E_KO/E_WT ratio ladders also explain each matching verdict: PP08's knockout
   exposure saturates at 0.271 of E_WT even at 600 uM, so no rung can enter the
   0.70–1.4286 window and the NA / `indeterminate` outcome is forced by the data,
   not by a coding accident. PP03 is the informative case where the matched
   knockout concentration (50 uM, ratio 1.032) differs from the wild-type primary
   concentration (10 uM) — and there the exposure-conditioned PI (0.518) is far
   above the same-dose PI (0.265), which is exactly the mediation the spec's
   `causal_note` warns about.
9. **Mean of ratios vs ratio of means.** I implemented the mean of per-experiment
   ratios as instructed. The ratio-of-means alternative differs by at most
   9.5e-4 in `protection_index_wt` across the eight compounds — well inside the
   0.03 tolerance. So the convention is stated for good reason but is not
   load-bearing on this dataset; it would not discriminate a solver that got it
   wrong.
10. **Concentration selection is unambiguous.** Every compound's selected rung has
    a tox_ratio of 0.939–0.956 and the next rung up falls to 0.549–0.761. No
    compound sits near the 0.85 criterion, so the selection is robust and the
    "point estimate only" instruction never has to arbitrate a close call.
11. **Evidence identifiers.** For every compound all 7 ids exist in the manifest,
    all satisfy the seven required field constraints, together they cover
    BIO01..BIO07, and the list length (7) is inside the required 7–30.
12. **Decision inputs.** n = 7 contributes to every graded quantity (wild-type PI,
    the paired contrast, E_WT) for every compound. The two knockout lineages agree
    for all eight compounds, so the corroboration rule never changes an outcome
    here — meaning the ordering ambiguity in note 1.5 is currently untestable, and
    the dataset does not exercise that branch. The rescue criterion does bite: it
    holds for the four protected compounds and fails for PP01/PP04/PP07, which are
    `not_assessable` anyway.
13. **Determinism.** Two consecutive runs produce byte-identical output.

---

## 3. Final table

`protection_index_*` and the contrast are dimensionless fractions of the
challenge-induced viability deficit; `E_WT` is pmol per 1e6 cells; concentrations
are uM administered. Values are shown rounded here; the CSV carries 6 decimals.

|  cmp | prim_uM |    E_WT | koMatch |   PI_wt | PI_wt_lo | PI_wt_hi | PI_ko_adm | PI_ko_exp | PI_resc |   Delta |    D_lo |   D_hi |   prot_status |        nrf2_status |   flags |
|------|---------|---------|---------|---------|----------|----------|-----------|-----------|---------|---------|---------|--------|---------------|--------------------|---------|
| PP01 |     100 | 274.382 |     100 |  0.0116 |  -0.0238 |   0.0470 |   -0.0492 |   -0.0492 |  0.0073 |  0.0608 | -0.0001 | 0.1217 | not_protected |     not_assessable |    none |
| PP02 |      50 | 149.325 |      50 |  0.6026 |   0.5646 |   0.6405 |   -0.0388 |   -0.0388 |  0.5330 |  0.6414 |  0.5991 | 0.6837 |     protected |     nrf2_dependent |    none |
| PP03 |      10 | 30.4331 |      50 |  0.5195 |   0.4839 |   0.5551 |    0.2653 |    0.5179 |  0.5293 |  0.0016 | -0.0418 | 0.0450 |     protected | not_nrf2_dependent |    none |
| PP04 |     300 | 432.845 |     300 | -0.0032 |  -0.0276 |   0.0213 |   -0.0150 |   -0.0150 | -0.0080 |  0.0118 | -0.0431 | 0.0667 | not_protected |     not_assessable | mtt;ros |
| PP05 |     100 | 280.945 |     100 |  0.5611 |   0.5306 |   0.5916 |    0.5147 |    0.5147 |  0.5663 |  0.0464 | -0.0057 | 0.0985 |     protected | not_nrf2_dependent |    none |
| PP06 |     100 | 235.339 |     100 |  0.5842 |   0.5452 |   0.6233 |   -0.0373 |   -0.0373 |  0.5214 |  0.6216 |  0.5639 | 0.6793 |     protected |     nrf2_dependent |     ros |
| PP07 |      10 |  24.993 |      10 | -0.0037 |  -0.0297 |   0.0223 |    0.0055 |    0.0055 |  0.0056 | -0.0092 | -0.0727 | 0.0543 | not_protected |     not_assessable |    none |
| PP08 |      50 | 376.746 |      NA |  0.5568 |   0.5214 |   0.5923 |    0.0049 |        NA |  0.5163 |      NA |      NA |     NA |     protected |      indeterminate |    none |

### Interference indices behind the `flags` column

Mean and 95% CI lower bound per index; a flag is raised when the lower bound
exceeds 0.10.

| cmp | MTT mean / lo | autofluorescence mean / lo | quench mean / lo | flags |
|---|---|---|---|---|
| PP01 | -0.005 / -0.018 |  0.000 / -0.003 | 0.000 / -0.020 | none |
| PP02 | -0.001 / -0.015 | -0.001 / -0.004 | -0.006 / -0.025 | none |
| PP03 | -0.007 / -0.021 |  0.000 / -0.004 | -0.011 / -0.034 | none |
| PP04 |  0.498 /  0.471 |  0.115 /  0.106 | 0.329 / 0.315 | mtt;ros |
| PP05 | -0.006 / -0.016 |  0.001 / -0.002 | 0.027 / 0.012 | none |
| PP06 |  0.002 / -0.013 | -0.015 / -0.018 | 0.337 / 0.329 | ros |
| PP07 | -0.005 / -0.015 |  0.000 / -0.004 | 0.000 / -0.016 | none |
| PP08 | -0.005 / -0.018 |  0.001 / -0.004 | 0.001 / -0.027 | none |

PP06's `ros` flag comes from quenching alone (0.337) with no autofluorescence,
and PP06 is simultaneously `protected` and `nrf2_dependent` — the mixed finding
the spec's `separate_findings` clause is designed to keep representable. PP04
triggers both flags and is `not_protected`: a compound that moves the redox
readouts without moving the direct count. PP05's quench lower bound (0.012) is the
nearest miss to the 0.10 interference threshold, still comfortably clear.

### Evidence sample ids

```
PP01  SMP036680;SMP027306;SMP070564;SMP073269;SMP000166;SMP020679;SMP070375
PP02  SMP010538;SMP012490;SMP006566;SMP037883;SMP000068;SMP072350;SMP032770
PP03  SMP037818;SMP029928;SMP042080;SMP031480;SMP027928;SMP070179;SMP075463
PP04  SMP045570;SMP059257;SMP037792;SMP014536;SMP043428;SMP018044;SMP069018
PP05  SMP022754;SMP026452;SMP023765;SMP001482;SMP022192;SMP038697;SMP067364
PP06  SMP041712;SMP024602;SMP057798;SMP072529;SMP023166;SMP022828;SMP064501
PP07  SMP023942;SMP029006;SMP004782;SMP009612;SMP072949;SMP032798;SMP066936
PP08  SMP015482;SMP070491;SMP003359;SMP044135;SMP036585;SMP059556;SMP005421
```

One identifier per biological experiment, taken as the lowest-numbered technical
replicate in each, so the list demonstrates that the experiment was the unit of
inference.
