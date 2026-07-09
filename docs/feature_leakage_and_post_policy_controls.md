# Feature Leakage and Post-Policy Controls

This note defines the project's general rule for leakage and post-policy controls. It is not a full
feature-selection summary. Service-specific feature decisions are documented separately in the Yellow
Taxi and HVFHV feature-selection notes.

## Why This Note Exists

This project is not a prediction task with a standard train/test split, so the usual machine-learning
definition of feature leakage does not map perfectly. The relevant concern is simpler:

> Do not explain a post-policy outcome using variables that were themselves created or changed after
> the policy.

For this project, that means 2025 fare, cost, duration, driver-pay, and trip-count variables should
not be used as explanatory controls for 2024-to-2025 volume change unless they are explicitly the
outcome being measured.

## Operational Rule

Use this rule across both Yellow Taxi and HVFHV:

```text
Pre-policy variables computed from Feb-Jun 2024 can be used as baseline controls or descriptive
context.

Post-policy variables computed from Feb-Jun 2025 should not be used as explanatory controls for
post-policy volume change, unless they are the declared outcome.
```

Examples:

| Variable type | Status | Reason |
|---|---|---|
| `n_2024` | usable baseline | Pre-policy trip volume |
| 2024 average distance or cost | usable baseline/context | Describes pre-policy trip structure |
| 2025 trip count | outcome ingredient | Directly determines volume change |
| 2025 average fare or cost | post-policy variable | May reflect both baseline trip economics and market response |
| 2025 duration or driver pay | post-policy variable | May reflect traffic, supply, matching, or market response |
| `pct_volume_change` | outcome | Cannot also be an explanatory control |

## Burden Metrics And Manufactured Correlation

The burden metric is:

```text
DS_z = mean(congestion fee / base passenger cost)
```

where base passenger cost excludes the congestion fee and applies the project's denominator floor.

Because the fee is nearly flat within each service, `DS_z` is mechanically related to trip cost:
shorter or lower-cost trips tend to have higher measured burden. This is the point of the burden
metric, but it also means same-year cost fields are not independent controls for `DS_z`.

The practical rules are:

- Use `DS_z` as the burden metric, not as a generic predictive feature.
- Do not include `DS_z`, `DS_z_median`, and `relative_cbd_burden` as if they were independent
  explanatory variables in the same model.
- Do not control for 2025 average cost, fare, or distance in a way that defines away the burden
  contrast.
- If cost, distance, or geography is used to check robustness, prefer pre-policy or explicitly
  baseline versions and describe the comparison being made.

## `DS_z` And Volume Change Are Not The Same Quantity

`DS_z` and volume change are not algebraically identical:

| Quantity | Main input | What it measures |
|---|---|---|
| `DS_z` | 2025 charged trips | Fee burden relative to trip cost |
| `pct_volume_change` | 2024 and 2025 trip counts | Change in completed trip volume |

A correlation between `DS_z` and volume change is therefore not guaranteed by formula alone.
However, it is still not automatically causal. High-`DS_z` zone-sides are often dense,
short-trip, Manhattan-core zone-sides, and those places can have different demand trends for reasons
other than the fee.

## Observed-Trip Selection

`DS_z` is computed from observed 2025 charged trips. If the fee changed which trips still occurred,
then the observed 2025 burden distribution may differ from the burden distribution that would have
existed without the fee.

This cannot be fully solved with the public TLC trip records because the data do not observe trips
that were considered but not taken. The project treats this as an interpretation limit rather than a
resolved adjustment.

## How This Note Is Used

This note supports the feature-selection documents and the modeling plan:

- Yellow-specific field decisions are in
  [`yellow_dropped_and_engineered_features.md`](yellow_dropped_and_engineered_features.md).
- HVFHV-specific field decisions are in
  [`hvfhv_dropped_and_engineered_features.md`](hvfhv_dropped_and_engineered_features.md).
- Model design choices are in
  [`burden_analysis_and_modeling_plan.md`](burden_analysis_and_modeling_plan.md).

