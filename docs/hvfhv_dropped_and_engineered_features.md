# HVFHV - Feature Selection (Dropped / Kept / Engineered)

*Concrete per-feature decisions for the HVFHV track: what is dropped, kept,
engineered, or used only descriptively, and why.*

*This document mirrors the Yellow Taxi feature-selection memo while keeping the
HVFHV track separate. Data-quality basis is in
[`hvfhv_data_audit.md`](hvfhv_data_audit.md). The general leakage /
manufactured-correlation framework is in
[`presentation/feature_leakage.markdown`](../presentation/feature_leakage.markdown).
Model design is in [`burden_analysis_and_modeling_plan.md`](burden_analysis_and_modeling_plan.md), and evaluation rules
are in [`evaluation_plan.md`](evaluation_plan.md).*

---

## 1. Selection criteria

A feature is dropped, kept, engineered, or demoted to EDA-only on four grounds:

1. **Leakage / over-control:** post-policy variables cannot be explanatory
   controls for post-policy outcomes unless they are the outcome itself.
2. **Redundancy / collinearity:** variables that mechanically duplicate DS_z,
   burden, or the outcome add little independent information.
3. **Reliability:** fields with known construction or interpretation limits are
   used only where those limits do not threaten the claim.
4. **Scope:** the project is inference-focused, not a demand-prediction task.
   Features are kept only if they support burden ranking, exposure-gradient
   analysis, or documented robustness checks.

Operational leakage rule:

```text
Pre-policy variables computed from Feb-Jun 2024 are valid controls.
Post-policy variables computed from Feb-Jun 2025 are not valid controls
for post-policy volume change, unless they are the declared outcome.
```

## 2. Feature pool

The standardized HVFHV feature pool includes:

- time: `pickup_datetime`, `dropoff_datetime`, `year`, `month`;
- geography: `PULocationID`, `DOLocationID`, borough/zone lookup joins;
- trip shape: `trip_distance_miles`, `trip_duration_seconds`;
- provider/regime: `hvfhs_license_num`, provider label, `shared_request_flag`,
  `shared_match_flag`;
- cost components: `base_passenger_fare`, `tolls`, `bcf`, `sales_tax`,
  `congestion_surcharge`, `airport_fee`, `cbd_congestion_fee`;
- reconstructed cost: `passenger_cost_pretip`;
- burden reference: `relative_cbd_burden`;
- driver-side field: `driver_pay`;
- standardized flags: `charged_cbd_flag`, QC flags such as zero-distance and
  very-long-trip flags;
- engineered zone outputs: DS_z, DS_z median, volume change, rank-stability
  summaries, and borough/direction robustness summaries.

## 3. DS_z is a treatment-burden metric, not a generic predictor

HVFHV DS_z is:

```text
DS_z = mean(cbd_congestion_fee / round(passenger_cost_pretip - cbd_congestion_fee, 2))
```

for 2025 charged trips in a zone-by-direction cell, using a $1 base-cost floor.
Because the numerator is usually the flat $1.50 CBD fee, DS_z is mechanically
related to base cost. Same-year 2025 cost, fare, distance, and duration are
therefore not clean controls for DS_z or volume response:

- 2025 cost/fare are post-policy and partly define or mediate the burden.
- 2025 trip count directly determines `pct_volume_change`.
- 2025 duration can be affected by congestion and post-policy traffic patterns.
- `relative_cbd_burden` uses a closely related numerator/denominator pair and
  should not be treated as an independent feature alongside DS_z.

The right use is to treat DS_z as the burden/exposure metric of interest, then
use only pre-policy controls or design-based comparisons to evaluate whether
higher exposure is associated with different volume changes.

## 4. Trip-level fields

Status legend:

- **Keep**: valid core field or pre-policy control candidate.
- **Engineer**: source field for a model-ready aggregate/flag.
- **EDA-only**: useful for descriptive audit, not a current model feature.
- **Drop as control**: should not be used as an explanatory control in Model 1
  or Model 2.

| Feature | Decision | Reason |
|---|---|---|
| `pickup_datetime`, `dropoff_datetime` | Engineer / EDA-only | Source for year, month, hour, day-of-week, and duration checks. Raw datetimes are not model features. |
| `year`, `month` | Keep | Needed for pre/post indexing and monthly panels. |
| `PULocationID`, `DOLocationID` | Engineer | Defines zone-by-direction unit, CRZ exposure, borough/zone joins, and OD summaries. Use categorically, not as numeric magnitudes. |
| `trip_distance_miles` | Keep as 2024 control candidate; EDA in 2025 | Baseline trip-economics measure. Use pre-policy aggregates in Model 1/2; avoid same-year 2025 distance as a control. |
| `trip_duration_seconds` | EDA-only / drop as main control | Duration is related to distance but can also be affected by congestion and post-policy traffic conditions. Treat cautiously, especially in 2025. |
| `hvfhs_license_num`, provider label | EDA-only or stratification | Provider mix changes between 2024 and 2025. Useful context, but not a primary causal feature unless a provider-specific model is declared. |
| `shared_request_flag`, `shared_match_flag` | EDA-only or stratification | Shared rides are a distinct descriptive regime. Current models do not use shared status as a primary feature. |
| `base_passenger_fare` | Keep only as 2024 baseline control/sensitivity | Underlying platform fare component. 2025 values are post-policy and should not be explanatory controls. |
| `tolls`, `bcf`, `sales_tax`, `congestion_surcharge`, `airport_fee` | Keep in reconstructed cost; EDA-only individually | Components of passenger cost. Individual components are not primary model features in the current plan. |
| `passenger_cost_pretip` | Keep for burden/cost outcomes; 2024 control candidate | Reconstructed mandatory pre-tip cost. Caveat: may miss platform discounts/refunds/credits. |
| `cbd_congestion_fee` | Treatment/exposure numerator | Use to define fee burden and charge status; do not use as an ordinary control. |
| `charged_cbd_flag` | Treatment/exposure indicator for 2025; engineer geography for cross-year work | Observed fee indicator exists only post-policy. For pre/post designs, prefer geography-based exposure that can be computed in 2024. |
| `relative_cbd_burden` | Reference/sensitivity only | Fee/current-cost burden. Related to DS_z; do not include both as independent features unless explicitly labeled sensitivity. |
| `driver_pay` | EDA-only / outcome context | Potentially affected by market and post-policy conditions. Do not use 2025 driver pay as a control for volume change. |
| QC flags | EDA / robustness filters | Use to describe data quality or define sensitivity subsets; do not treat flags as substantive predictors without justification. |
| `source_file` | Drop from modeling | Provenance only. |

## 5. Engineered features

| Feature | Status | Definition / role |
|---|---|---|
| `provider_label` | EDA/context | Human-readable provider grouping, mainly Uber vs Lyft, derived from `hvfhs_license_num` in EDA. |
| `shared_ride_regime` | EDA/context | Combination of request and match flags, e.g. matched shared, requested-unmatched, non-shared. |
| `zone_direction` | Core unit | Zone and side (`pickup` or `dropoff`). Keeps directional asymmetry visible and avoids PU/DO pooling. |
| `base_cost_ex_cbd` | DS_z denominator | `round(passenger_cost_pretip - cbd_congestion_fee, 2)` with floor sensitivity. Not a standalone same-year control. |
| `DS_z` | Primary burden metric | Mean fee/base-cost burden among qualifying 2025 charged trips by zone and direction. |
| `DS_z_median` | Secondary burden metric | Median version of the same trip-level burden. Report alongside mean for robustness. |
| `relative_cbd_burden_current_cost` | Reference burden metric | Fee/current pre-tip cost. More intuitive, but not the primary DS_z metric. |
| `n_2024`, `n_2025` | Baseline and outcome ingredients | `n_2024` is a safe baseline control; `n_2025` is post-policy and should not be used as a control. |
| `pct_volume_change` | Outcome | `n_2025 / n_2024 - 1` where defined. Never a predictor of itself. |
| `avg_distance_2024` | Safe control (trip-level aggregate) | Pre-policy trip-shape baseline for Model 1 or Model 2 sensitivity. Not in current zone CSV exports; aggregate from 2024 standardized parquets if used. |
| `avg_total_cost_2024`, `avg_base_fare_2024` | Safe controls/sensitivities | Pre-policy cost/fare baselines from `hvfhv_behavioral_shift.csv`. Use carefully because they are strongly related to trip length and burden. |
| `avg_total_cost_2025`, `avg_base_fare_2025` | Drop as controls | Post-policy values; may be outcomes or mediators. |
| `charged_share_2024_geo` | Model 2 exposure | Pre-policy geographic exposure share based on CRZ pickup/dropoff geography. Used for HVFHV Model 2. |
| `borough`, `zone_name`, `service_zone` | Controls/context | Use for description, fixed effects, or borough robustness; not numeric features. |
| floor-sensitivity ranks | Robustness outputs | Used to evaluate DS_z stability, not as model predictors. |

## 6. Dropped fields and reasons

Dropped from explanatory-control sets:

- all **2025 post-policy cost/fare aggregates** as controls, including
  `avg_total_cost_2025`, `avg_base_fare_2025`, and related same-year cost
  summaries;
- all **2025 post-policy duration, distance, driver-pay, and trip-count
  aggregates** as controls unless explicitly used as outcomes or descriptive
  summaries;
- `n_2025`, `delta_volume`, `pct_volume_change`, or any direct function of the
  target as a feature to explain volume change;
- `relative_cbd_burden` as an independent model feature when DS_z is already
  included;
- `DS_z_median` as an independent feature alongside `DS_z` in the same model;
- raw `PULocationID` and `DOLocationID` as numeric variables;
- `source_file`;
- raw datetimes as model features after extracting the required index fields.

Not dropped from the data:

- `driver_pay`, provider, shared-ride flags, duration, and distance remain useful
  for EDA and robustness discussion. The drop decision is about explanatory
  model controls, not about deleting columns.

## 7. Safe pre-policy controls

Safe controls are computed from Feb-Jun 2024 only:

- baseline trip volume: `n_2024`;
- baseline trip distance: `avg_distance_2024`, median distance, or a single
  declared trip-economics proxy;
- baseline passenger cost or base fare: `avg_total_cost_2024`,
  `avg_base_fare_2024`, used only with a clear collinearity caveat;
- borough, zone, and direction labels;
- pre-policy geographic exposure share for Model 2:
  `charged_share_2024_geo`;
- provider or shared-regime baseline composition, only if the model explicitly
  asks a provider/shared-regime question.

Use one trip-economics control at a time unless the model is explicitly a
sensitivity decomposition. Distance, fare, duration, and burden all partly
measure the short-trip/dense-core structure and can make coefficients unstable.

## 8. Treatment and exposure variables

| Variable | Use |
|---|---|
| `cbd_congestion_fee` | Treatment numerator; not an ordinary control. |
| `charged_cbd_flag` | 2025 observed fee indicator; useful for charged/uncharged composition. |
| `DS_z` | Main Model 1 burden score / treatment-intensity metric. |
| `DS_z_median` | Robustness/reporting companion to mean DS_z. |
| `relative_cbd_burden` | Secondary burden reference, not independent from DS_z. |
| `charged_share_2024_geo` | Preferred Model 2 exposure in the HVFHV monthly panel. |
| `borough` / Manhattan subset | Robustness and confounding diagnostics, not treatment by itself. |

## 9. Outcome variables

| Outcome | Use |
|---|---|
| `pct_volume_change` | Model 1 outcome: zone-direction trip-count change from 2024 to 2025. |
| `log_n_trips` / monthly trip count | Model 2 monthly-panel outcome. |
| passenger-cost movement | Descriptive cost outcome, not a control in the volume model. |
| driver-pay movement | Descriptive driver-side outcome/context. |
| provider/share composition changes | Descriptive market-composition outcomes. |

Outcome variables must not be reused as explanatory features in the same model.

## 10. Model-specific recommendations

### Model 1: DS_z versus volume change

Recommended:

- unit: zone x direction;
- burden metric: `DS_z` mean, with `DS_z_median` reported as robustness;
- outcome: `pct_volume_change`;
- controls/sensitivities: 2024 baseline distance or 2024 baseline cost/fare
  one at a time, plus borough or Manhattan-only diagnostics;
- reporting: Pearson, Spearman, quartiles, confidence intervals or clear
  descriptive uncertainty where available.

Do not:

- control for 2025 cost, fare, duration, driver pay, or trip counts;
- include both DS_z and `relative_cbd_burden` as if they were independent;
- describe the cross-zone association as causal proof.

Current evidence:

- Durable HVFHV DS_z, rank-stability, top-overlap, borough-correlation, and
  Manhattan-correlation CSVs already exist.
- The full EDA notebook reports a low-N-filtered DS_z/volume Pearson
  correlation of -0.610; durable robustness CSVs report all-zone Spearman about
  -0.633 and Manhattan-only Pearson about -0.540.

### Model 2: geographic exposure-gradient DiD

Implemented design:

- unit: zone x direction x month x year;
- treatment exposure: pre-policy geography-based `charged_share_2024_geo`,
  not the 2025 observed `charged_cbd_flag`;
- outcome: monthly trip count or `log_n_trips`;
- fixed effects: zone-direction and month;
- coefficient of interest: `post:charged_share_2024_geo`;
- standard errors: cluster by zone where possible;
- report equal-weighted and baseline-volume-weighted estimates separately
  because the weighting changes the estimand.

Completed diagnostics:

- HVFHV monthly panel and 2024 geography-based exposure are available.
- Geography-based exposure is validated against the 2025 observed fee flag as a
  diagnostic, not proof of clean assignment.
- The no-June 2024 pretrend diagnostic shows weak/no clear pretrend signal.
- The no-June 2023-vs-2024 placebo is negative and similar in magnitude to the
  2024-vs-2025 Model 2 estimate.
- Therefore Model 2 should be presented as suggestive association, not clean
  causal evidence; the placebo warning may indicate pre-existing spatial demand
  trends in high-exposure HVFHV zones.

Do not:

- use 2025 realized fare/cost/duration/driver-pay variables as controls;
- treat a binary CRZ/non-CRZ split as clean without measuring exposure
  contamination;
- describe the negative exposure-gradient estimate as a clean causal effect.

### Model 3: Yellow versus HVFHV

Model 3 has been implemented in
[`model3_cross_vehicle.ipynb`](../notebooks/model3_cross_vehicle.ipynb). It is
a combined Yellow-versus-HVFHV design, so the HVFHV feature decisions above
carry into Model 3 with additional cross-service alignment rules.

Implemented design:

- unit: zone x direction x vehicle x month x year;
- HVFHV population: all standardized HVFHV trips, with provider and shared-ride
  fields retained for diagnostics;
- Yellow comparison population: matched Yellow population defined in the Yellow
  feature and audit documents;
- treatment contrast: HVFHV as the higher-fee service versus Yellow as the
  lower-fee service, within CRZ-exposed zone-sides;
- outcome: monthly trip count or `log_n_trips`;
- coefficient of interest: `post:hvfhv` in the within-CRZ comparison, with a
  triple-diff specification using CRZ exposure as the stricter diagnostic.

Completed diagnostics:

- The primary within-CRZ estimate is negative, with HVFHV losing more volume
  than Yellow from 2024 to 2025.
- The no-fee 2023-vs-2024 placebo produces a large opposite-signed
  CRZ-specific contrast, which limits causal interpretation.
- The provider split is inconsistent: Yellow-versus-Uber and Yellow-versus-Lyft
  move in opposite directions even though Uber and Lyft face the same HVFHV fee.
- Low-exposure checks are supportive but underpowered.

Feature implications:

- `provider_label` and `hvfhs_license_num` remain EDA/context fields in the
  main HVFHV feature set, but they are important Model 3 diagnostics because the
  Uber/Lyft split reveals provider-specific movement.
- `shared_request_flag` and `shared_match_flag` remain descriptive/sensitivity
  fields. Matched shared rides are a small share of HVFHV rows, but they can
  affect vehicle-volume interpretation because one vehicle movement can create
  multiple passenger records.
- Model 3 should be reported as a suggestive cross-vehicle association, not a
  clean causal fee estimate or a per-dollar fee elasticity.

## 11. Leakage rules to carry forward

1. Do not use 2025 post-policy cost, fare, duration, driver pay, trip counts, or
   volume-change fields as explanatory controls.
2. Do not use `pct_volume_change`, `delta_volume`, `n_2025`, or any target
   derivative as a predictor of volume change.
3. Do not include both DS_z and `relative_cbd_burden` as independent features in
   the same model unless the run is explicitly labeled a sensitivity check.
4. Treat `cbd_congestion_fee` as treatment/exposure/numerator, not as a normal
   control.
5. Treat duration cautiously because congestion and post-policy traffic
   conditions can affect it.
6. Distinguish descriptive controls from causal controls. Provider and shared
   status can describe composition; they do not automatically identify a causal
   effect.
7. Keep Yellow and HVFHV feature sets separate except inside the dedicated
   combined Model 3 design, where populations, zone-direction units, months, and
   volume definitions must be aligned before comparison.

## 12. Reproducibility note

DuckDB aggregation outputs that use floating-point averages can differ at tiny
decimal levels under multi-threaded execution. HVFHV DS_z outputs should be
generated with:

```sql
SET threads TO 1
```

This is already used in the HVFHV full EDA notebook and
[`scripts/01_pipeline.py`](../scripts/01_pipeline.py).
Keep it in any future HVFHV aggregation script that writes durable CSVs,
especially DS_z, burden, correlation, or rank-stability outputs.

## 13. Summary lists

**Primary burden/exposure features:** `DS_z`, `DS_z_median`,
`cbd_congestion_fee`, `charged_cbd_flag`, `relative_cbd_burden` as reference,
and `charged_share_2024_geo` for Model 2.

**Safe controls:** `n_2024`, `avg_distance_2024`, possibly
`avg_total_cost_2024`/`avg_base_fare_2024`, borough, zone-direction, and declared
pre-policy provider/shared composition if needed.

**Outcomes:** `pct_volume_change`, monthly trip count / `log_n_trips`, cost movement,
driver-pay movement, provider-mix changes.

**Dropped as controls:** all 2025 post-policy cost/fare/distance/duration/
driver-pay/trip-count aggregates, target-derived volume-change fields,
duplicate burden metrics in the same model, raw numeric zone IDs, raw datetimes,
and provenance fields.

**EDA-only:** provider mix, shared-ride regimes, hourly/day-of-week patterns,
driver-pay summaries, OD rankings, and trip-level anomaly flags unless a
specific robustness analysis declares them.
