# HVFHV Zone Disruption Score Outputs

Authoritative run guide for `scripts/01_pipeline.py` and related exports. See also [`docs/methodology_notes.md`](../../docs/methodology_notes.md) for full methodology.

Run from the repository root:

```bash
python scripts/01_pipeline.py
python scripts/hvfhv_model2_monthly_panel.py
python scripts/hvfhv_pretrend_placebo.py
```

## Inputs

- `data/processed/00_standardized_trips/hvfhv/2024/*.parquet`
- `data/processed/00_standardized_trips/hvfhv/2025/*.parquet`
- `data/taxi_zone_lookup.csv`

## Outputs

- `hvfhv_zone_disruption_score.csv`: primary zone-direction DS_z table.
- `hvfhv_behavioral_shift.csv`: 2024 vs 2025 zone-direction volume and fare summaries.
- `hvfhv_ds_z_vs_volume_change.csv`: descriptive join of DS_z and volume change.
- `hvfhv_ds_floor_sensitivity.csv`: DS_z under denominator floors of $0.50, $1.00, $2.00, and $5.00, with mean and median rankings.
- `hvfhv_ds_rank_stability.csv`: Spearman rank correlations and rank deltas versus the primary definition.
- `hvfhv_ds_top_zone_overlap.csv`: top-10 and top-20 overlap versus the primary definition.
- `hvfhv_borough_correlation.csv`: Pearson and Spearman correlations between DS_z and pct_volume_change across all zones, Manhattan/non-Manhattan splits, boroughs, directions, and borough-direction groups.
- `hvfhv_within_manhattan_correlation.csv`: Manhattan-focused subset of the borough robustness correlations.
- `hvfhv_monthly_panel.csv`: HVFHV Model 2 monthly zone-direction panel with 2024 geography-based exposure.
- `hvfhv_model2_exposure_validation.csv`: diagnostic comparison of geography-based exposure against the 2025 observed fee flag.
- `hvfhv_pretrend_2024_diagnostic.csv`: no-June 2024 exposure-quartile pretrend diagnostic.
- `hvfhv_placebo_2023_2024_panel.csv`: no-June 2023-vs-2024 placebo panel.
- `hvfhv_placebo_2023_2024_results.csv`: no-June 2023-vs-2024 placebo regression results.
- `hvfhv_model2_panel_notes.md` and `hvfhv_pretrend_placebo_notes.md`: compact regeneration and interpretation notes.

## Definition

For zone `z`, direction `pickup` or `dropoff`, and qualifying 2025 HVFHV trips:

```text
DS_z = mean(cbd_congestion_fee / round(passenger_cost_pretip - cbd_congestion_fee, 2))
```

The primary definition uses trips with `charged_cbd_flag = true`, positive
`cbd_congestion_fee`, and a rounded base-cost denominator of at least $1.00.
The median of the same trip-level burden is also reported.

## Manhattan Robustness Check

Run `python scripts/03_manhattan_robustness.py` after the DS_z pipeline outputs already exist. This small downstream script uses `hvfhv_ds_z_vs_volume_change.csv`, attaches TLC borough and zone names if needed, excludes rows with null `pct_volume_change`, and reports Pearson and Spearman correlations within Manhattan, outside Manhattan, by borough, by pickup/dropoff direction, and by borough-direction groups. Groups with fewer than 3 rows omit correlations (`sufficient_n = false` in the CSV). Spearman is Pearson correlation on pandas average ranks (`rank(method="average")`), matching `Series.corr(..., method="spearman")`. These correlations are descriptive robustness checks only and should not be interpreted causally.

## Model 2 And Placebo Diagnostics

Run `python scripts/hvfhv_model2_monthly_panel.py` to regenerate the HVFHV
Model 2 monthly panel and geography-exposure validation outputs. Run
`python scripts/hvfhv_pretrend_placebo.py` to regenerate the no-June 2024
pretrend diagnostic and 2023-vs-2024 placebo results.

The Model 2 exposure-gradient estimate is negative under the stated
assumptions. However, the no-June 2023-vs-2024 placebo estimate is also
negative and similar in magnitude, so Model 2 should be presented as suggestive
association rather than clean causal evidence.

## Interpretation Warnings

These outputs are descriptive/inferential, not causal proof. DS_z measures the
relative rider burden among observed post-policy fee-charged trips; it is not a
randomized treatment assignment.

Do not regress `pct_volume_change` on a disruption score that includes volume
change. The current DS_z definition does not include volume change directly, but
downstream models should still use pre-policy controls only when explaining
post-policy outcomes.
