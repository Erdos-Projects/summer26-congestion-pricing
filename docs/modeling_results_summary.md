# Modeling Results Summary

Last updated: 2026-07-08

This note pulls together our current modeling conclusions across Yellow Taxi, HVFHV, and the
cross-vehicle comparison. The goal is to keep the team aligned before report/presentation writing:
what we found, how strong each result is, and where we need cautious language.

Source notebooks:

- `notebooks/yellow_burden_ranking_and_heterogeneity.ipynb`
- `notebooks/hvfhv_burden_ranking_and_heterogeneity.ipynb`
- `notebooks/yellow_model1_model2.ipynb`
- `notebooks/hvfhv_model1_model2.ipynb`
- `notebooks/model3_cross_vehicle.ipynb`
- `notebooks/yellow_taxi_full_EDA.ipynb`
- `notebooks/hvfhv_full_EDA.ipynb`

Companion docs:

- `docs/burden_analysis_and_modeling_plan.md`
- `docs/evaluation_plan.md`
- `docs/yellow_data_audit.md`
- `docs/hvfhv_data_audit.md`
- `docs/report_adithya_eda.md`
- `docs/eda_summary.md`
- `docs/NYC_HVFHV_Zone_Disruption_Final_Report.markdown`

## Team Takeaway

The modeling work is solid, but the causal conclusion is cautious.

We can confidently say that the congestion fee created different relative burdens across zones. The
burden ranking, `DS_z`, is meaningful and stable, especially for identifying short,
lower-base-cost trips in dense Manhattan zones where a fixed per-trip fee is a larger share of the
fare.

For the volume question, our conclusion is more limited. The negative volume patterns are real in
several specifications, but the placebo and robustness checks show that similar spatial or
cross-vehicle differences existed before the fee. We are therefore not treating the current evidence
as clean proof that the CBD congestion fee caused Yellow Taxi or HVFHV trip volumes to fall.

Our shared bottom line is:

> The fee burden is measurable and uneven across zones. Higher-burden or higher-exposure areas often
> show weaker volume performance, especially for HVFHV, but the models do not isolate a clean causal
> fee effect on trip volume.

This is still a useful result, not a failed result. The policy's main target is private passenger-car
congestion, while the TLC per-trip fees are much smaller: $0.75 for Yellow Taxi and $1.50 for HVFHV.
Not finding a clean taxi/HVFHV volume drop is plausible, and we can report that directly.

## Current Claims

We can state confidently:

- `DS_z` is a useful zone-level burden metric: fee divided by base passenger cost, computed separately
  for pickup and dropoff zone-sides.
- The burden ranking is stable under floor sensitivity checks and is concentrated in dense Manhattan
  zones.
- Yellow and HVFHV need different interpretation. Yellow is affected by the Flex Fare regime shift;
  HVFHV is affected by provider composition and Uber/Lyft dynamics.
- HVFHV shared rides remain small enough for the main rider-level summaries to pool them, but they
  should be treated as a sensitivity issue for vehicle-volume interpretation.
- HVFHV has a strong descriptive burden-volume relationship.
- The DiD-style models are useful diagnostics, but the placebo checks prevent a clean causal claim.

We can describe as suggestive, but not causal:

- HVFHV higher-exposure zone-sides show lower 2024->2025 volume growth in Model 2.
- In Model 3, HVFHV loses more volume than Yellow inside the CRZ, consistent with a possible fee-size
  response.

We should not present as established:

- A clean statement that the CBD fee caused Yellow trip volume to fall.
- A clean statement that the CBD fee caused HVFHV trip volume to fall.
- A per-dollar fee elasticity estimate.
- A claim that Model 1 is causal. Model 1 is a descriptive burden-volume association (the ranking
  itself is the Goal-1 deliverable), not identification.

## Model 1: Descriptive Burden-Volume Association

Model 1 asks whether higher-burden zone-sides lost more trips from Feb-Jun 2024 to Feb-Jun 2025.
The burden ranking itself is the Goal-1 deliverable and now lives in the
`*_burden_ranking_and_heterogeneity` notebooks; Model 1 is the first descriptive check of whether
that ranking lines up with volume change. It is not a clean causal design for volume effects because
high `DS_z`, short trips, dense Manhattan geography, and CRZ charging are closely related.

### Yellow Taxi

Yellow Model 1 gives a weak and non-identified burden-volume relationship.

- Cross-zone `DS_z` vs volume change is weak: Pearson about -0.170 and Spearman about -0.163.
- The highest-burden quartile is the only quartile with a volume decline: Q1 about +3.8 percent,
  Q4 about -1.4 percent.
- The coefficient is unstable under controls: raw -2.04; with borough +0.95; with distance -5.11;
  with both -3.61.
- Within Manhattan alone, the correlation is small and positive, about +0.07 Pearson / +0.14
  Spearman, with confidence intervals including zero.

How we read this: Yellow Model 1 gives the burden ranking, not a reliable volume effect. The weak
correlation and specification swings show that the dense-core geography confound cannot be resolved
with simple controls.

Top Yellow burden examples from the processed DS_z table:

| Zone | Direction | DS_z | Volume change |
|---|---|---:|---:|
| Kips Bay | Dropoff | 4.76 percent | -3.0 percent |
| Flatiron | Dropoff | 4.73 percent | -0.6 percent |
| Union Sq | Dropoff | 4.71 percent | +4.2 percent |
| West Village | Dropoff | 4.67 percent | +1.3 percent |
| Gramercy | Dropoff | 4.64 percent | -2.5 percent |

The top Yellow burden zones are recognizable Manhattan core zones, but their volume changes are mixed.
That is why the ranking is useful while the volume interpretation remains cautious.

### HVFHV

HVFHV Model 1 gives a much stronger descriptive association.

- Among 519 usable zone-direction pairs, Pearson is -0.610 and Spearman is -0.643.
- The quartile gradient is monotone: Q1 averages about +4.5 percent volume change, while Q4 averages
  about -5.1 percent.
- The relationship survives robustness summaries: all-zone Spearman about -0.633, Manhattan-only
  Pearson about -0.540, Manhattan dropoff about -0.550, and Manhattan pickup about -0.560.
- Distance and fare control variants keep the `DS_z` coefficient negative, roughly from -3.25 to
  -1.37 across reported specifications.
- The newer heterogeneity analysis keeps the main pattern within Manhattan: excluding Randalls
  Island, the within-Manhattan correlation is about -0.50. Trip-length disaggregation shows short,
  medium, and long trips all have negative gradients, suggesting a zone-level demand pattern rather
  than only a short-trip response.
- Shared rides are not driving the main EDA population: in 2025, shared requests are 3.06 percent of
  HVFHV rows and matched shared rides are 1.69 percent. They are cheaper within distance buckets, so
  they need caveating for burden/vehicle-volume interpretation, but the share is small enough for a
  sensitivity check rather than a full rebuild.

How we read this: HVFHV Model 1 is strong descriptive evidence that higher-burden zones had weaker
volume growth. We still do not call it causal because the highest-burden zones are concentrated in
dense Manhattan areas with distinctive demand trends.

Top HVFHV burden examples from the processed DS_z table:

| Zone | Direction | DS_z | Volume change |
|---|---|---:|---:|
| Alphabet City | Dropoff | 6.38 percent | -10.8 percent |
| Stuy Town/Peter Cooper Village | Dropoff | 6.31 percent | -12.6 percent |
| East Village | Dropoff | 6.25 percent | -11.5 percent |
| West Village | Dropoff | 6.19 percent | -9.4 percent |
| Greenwich Village South | Dropoff | 6.17 percent | -10.2 percent |

This is the Model 1 material we can foreground in the report/presentation: ranked zones, quartiles,
Manhattan-only robustness, and the Yellow-vs-HVFHV contrast.

## Model 2: CRZ Exposure DiD

Model 2 asks whether more-exposed zone-sides changed differently after the fee than less-exposed
zone-sides. The key exposure is pre-policy geography-based `charged_share_2024_geo`, not observed
2025 charge status.

### Yellow Taxi

Yellow Model 2 is a fragile geographic association.

- Equal-weighted high-exposure estimate is about -11.1 percent, with confidence interval excluding
  zero.
- Volume weighting moves the estimate to about +1.4 percent with confidence interval including zero.
- Within-Manhattan is close to zero.
- The 2023->2024 no-fee placebo is strongly negative, about -25.8 percent.

How we read this: the equal-weighted negative estimate is a per-zone-side pattern, not a robust
trip-weighted fee effect. Because the no-fee placebo is even more negative, high-exposure Yellow
zone-sides were already losing relative volume before the policy.

### HVFHV

HVFHV Model 2 is negative but not clean causal evidence.

- Main panel after dropping missing exposure rows has 5,233 rows and 525 zone-direction units.
- Simple `post:charged_share_2024_geo` estimate: -0.1591, cluster-zone SE 0.0355, 95 percent CI
  [-0.2287, -0.0895].
- FE-style estimate: -0.1136, cluster-zone SE 0.0075, 95 percent CI [-0.1282, -0.0990], about
  -10.7 percent for a zero-to-full exposure contrast.
- Low-volume trim gives about -0.1158.
- WLS weighted by 2024 baseline volume gives about -0.0969.
- The 2023->2024 no-June placebo is also negative and similar in magnitude.

Exposure validation is strong but not perfect:

- 2025 observed charged share: 34.5 percent.
- Geography-exposed share: 32.9 percent.
- Match rate: 97.7 percent.
- Precision: 99.0 percent.
- Recall: 94.4 percent.
- Share of observed charged trips missed by the geography rule: 5.6 percent.

How we read this: HVFHV Model 2 shows a consistent negative exposure-gradient association, but the
placebo warning means it should be reported as suggestive rather than causal. Pre-existing spatial
demand trends in high-exposure HVFHV zones may be part of the observed pattern.

## Model 3: Cross-Vehicle DiD

Model 3 asks whether the higher-fee service, HVFHV at $1.50, changed more than the lower-fee service,
Yellow at $0.75, inside the same exposed zones.

Main results:

- Within CRZ, HVFHV lost about 5.9 percent more volume than Yellow from 2024 to 2025.
- This primary gap is stable to weighting, a zone-shock control, vehicle-specific seasonality, and
  CRZ bottom-volume trimming.
- Triple-diff reduces the estimate to about -2 percent in the binary specification.
- Dropping June gives roughly -6.4 percent for the primary within-CRZ estimate and about -4.3
  percent in the binary triple-diff specification.

Diagnostics limiting the causal interpretation:

- The 2023->2024 placebo gives a large opposite-signed CRZ-specific contrast: triple-diff about
  +7.5 percent in a no-fee period.
- The placebo magnitude is larger than the 2024->2025 no-June estimate.
- Provider split is inconsistent: Yellow-vs-Uber is about -11.4 percent, while Yellow-vs-Lyft is
  about +10.3 percent, even though Uber and Lyft face the same $1.50 fee.

How we read this: Model 3 is suggestive that something changed in 2025, and the sign is consistent
with a possible fee-size response. But the same design is too volatile in the placebo period and too
provider-dependent to support a clean causal estimate.

## Combined Story Across Models

The three models do not clear the evaluation plan's bar for a clean fee-related volume reduction.

The reporting decision rule says a clean volume claim should be negative, stable, reported with a
confidence interval, absent in placebo, and not dependent on a partly exposed comparison group. The
current evidence fails mainly on the placebo and robustness dimensions:

- Yellow Model 2 has a negative equal-weighted estimate, but the 2023->2024 placebo is also strongly
  negative and volume weighting weakens the result.
- HVFHV Model 2 has a negative estimate, but the 2023->2024 placebo is also negative and similar.
- Model 3 has a negative cross-vehicle gap in 2024->2025, but the no-fee placebo is large and
  opposite-signed, and the Uber/Lyft split goes in opposite directions.

So our shared modeling conclusion is:

> We find clear evidence that the CBD fee burden is uneven across zones and that high-burden or
> high-exposure areas often show weaker volume performance. However, the placebo and robustness
> checks show that these models also pick up pre-existing spatial and provider-specific demand
> patterns. We therefore do not claim a clean causal volume reduction for Yellow Taxi or HVFHV.

## Relationship To The Older HVFHV EDA Report

`docs/report_adithya_eda.md` remains useful for the original HVFHV DS_z construction and the first
Layer A/Layer B burden-volume story. The main Model 1 finding from that report is still retained:
HVFHV `DS_z` is negatively associated with 2024->2025 volume change.

Several next steps listed in that older report are now completed or superseded:

- Base-cost floor sensitivity has been completed.
- Manhattan-only robustness has been completed.
- Pearson and Spearman robustness tables have been completed.
- HVFHV Model 2 has been implemented in `hvfhv_model1_model2.ipynb`.
- Model 3 has been implemented in `model3_cross_vehicle.ipynb`.
- A newer HVFHV-focused zone disruption report now exists in
  `docs/NYC_HVFHV_Zone_Disruption_Final_Report.markdown`; it should be treated as the updated
  technical write-up for the HVFHV Model 1 heterogeneity checks.

If we keep `report_adithya_eda.md` as a final-facing document, we should update it or clearly mark
it as a historical HVFHV Model 1 report so it does not conflict with the newer modeling results.

## Presentation/Report Framing

A coherent structure for the final materials is:

1. Policy and data window: Feb-Jun 2024 vs Feb-Jun 2025; January 2025 excluded.
2. Burden metric: `DS_z = fee / base passenger cost`, by zone and direction.
3. EDA finding: fixed fees matter most for short, lower-base-cost trips.
4. Model 1: burden ranking and descriptive burden-volume association.
5. Model 2: exposure-gradient DiD, negative but weakened by placebo.
6. Model 3: cross-vehicle comparison, suggestive but weakened by placebo and provider split.
7. Final conclusion: uneven burden is clear; causal volume reduction is not cleanly established.

Phrasing we can use:

- "The strongest result is the burden ranking, not a causal volume estimate."
- "HVFHV shows a strong descriptive burden-volume association."
- "The DiD models are informative diagnostics, but the placebo checks prevent a clean causal claim."
- "Provider dynamics, especially Uber vs Lyft, matter enough that pooled HVFHV cannot be read as only
  a fee response."

Phrasing we should avoid:

- "The fee caused taxi volume to drop."
- "The fee caused HVFHV volume to drop."
- "Model 3 proves the higher HVFHV fee had a larger effect."
- "The Yellow and HVFHV estimates are directly comparable without caveats."

## Team Next Steps

High priority:

- Use this file as the main modeling-results narrative, or fold it into the final report.
- Update or archive stale parts of `docs/report_adithya_eda.md` so old "next steps" do not look
  unfinished.
- Select the final Model 1 tables/figures from `results/figures/`, `results/eda/figures/`, and the
  model result CSVs.
- Select the final Model 2 and Model 3 coefficient/diagnostic tables from `results/tables/` for
  presentation.
- Standardize notation across final materials: use `DS_z` consistently, since the new HVFHV report
  sometimes renders the metric as `DSₐ`.

Medium priority:

- Move any remaining final-facing plots from notebook-only outputs into `results/` rather than
  `artifacts/`, since `artifacts/` is ignored.
- HVFHV airport-vs-non-airport burden is now covered in
  `hvfhv_burden_ranking_and_heterogeneity.ipynb`, matching the yellow burden notebook; no separate
  `airport_trip_flag` build is needed for the presentation.
- Check that all final materials use the same causal language: "suggestive association" rather than
  "causal effect" unless the claim is only about burden ranking.
