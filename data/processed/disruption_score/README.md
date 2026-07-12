# Disruption Score & DiD Panel Outputs

This directory holds three groups of CSVs: **HVFHV** DS_z (documented first, below), the **yellow**
DS_z outputs, and the **Model-2 / Model-3 DiD panels**. Each file's generating script is named in its
section. See also [`docs/burden_analysis_and_modeling_plan.md`](../../../docs/burden_analysis_and_modeling_plan.md) and
[`docs/evaluation_plan.md`](../../../docs/evaluation_plan.md).

## HVFHV DS_z (`scripts/01_pipeline.py`)

Authoritative run guide for `scripts/01_pipeline.py` and related exports. See also
[`docs/hvfhv_data_audit.md`](../../../docs/hvfhv_data_audit.md) and
[`docs/burden_analysis_and_modeling_plan.md`](../../../docs/burden_analysis_and_modeling_plan.md).

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
- `hvfhv_placebo_2023_2024_panel.csv`: no-June 2023→2024 placebo panel.
- `hvfhv_placebo_2023_2024_results.csv`: no-June 2023→2024 placebo regression results.
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
pretrend diagnostic and 2023→2024 placebo results.

The Model 2 exposure-gradient estimate is negative under the stated
assumptions. However, the no-June 2023→2024 placebo estimate is also
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

---

## Yellow DS_z (`scripts/yellow_ds_pipeline.py`)

Same DS_z definition as HVFHV, on `data/processed/00_standardized_trips/yellow/{2024,2025}/*.parquet`.
**Yellow-specific rules:** burden (`DS_z`) uses **2025 charged card/cash** trips; volume uses **non-Flex**
trips; **non-movement** rows are dropped (`zero_distance AND (PU==DO OR trip_duration < 60s)`); window
**Feb–Jun**; single-threaded + rounded so re-runs are byte-reproducible.

- `yellow_zone_disruption_score.csv`: primary zone × direction DS_z table (mean + median, `DS_z_rank`, `low_n_flag`), per base-cost floor.
- `yellow_behavioral_shift.csv`: non-Flex volume + avg cost/distance per zone × direction, 2024 vs 2025.
- `yellow_ds_z_vs_volume_change.csv`: DS_z + rank joined to the 2024→2025 volume change — the **Model-1** input.
- `yellow_ds_floor_sensitivity.csv`, `yellow_ds_rank_stability.csv`: DS_z at $0.50 / $1 / $2 / $5 floors + rank stability.
- `yellow_charged_geo_validation.csv`: agreement of the geographic CRZ rule vs the 2025 `charged_cbd_flag`.
- `yellow_monthly_panel.csv`: the **Model-2** input — non-Flex trip counts per `zone × direction × month × year` (Feb–Jun 2024/2025), with `crz_zone` (binary CRZ membership) and `charged_share` (2024, direction-specific CRZ exposure).

## Model 2 / Model 3 DiD panels

Monthly trip-count panels for the difference-in-differences volume analysis. **All aggregated with
matched rules:** the 38 CRZ zones, the non-movement drop, Feb–Jun, single-threaded for reproducibility.
Shared columns: `n_trips`, `crz_zone`, `charged_share` (pre-year direction-specific CRZ exposure), plus
`vehicle` for the cross-vehicle panels.

- `m3_cross_vehicle_panel.csv` — `scripts/build_m3_panel.py`. yellow (**card/cash**) + HVFHV (**all**),
  unit `zone × direction × vehicle × month × year`, 2024/2025 — the **Model-3** input.
- `m3_placebo_panel_2023_2024.csv` — `scripts/build_m3_panel.py --placebo`. Same structure but the
  no-fee **2023 vs 2024** pair (exposure computed from 2023) — the **Model-3 placebo** input.
- `yellow_2023_placebo_monthly_panel.csv` — `scripts/build_yellow_2023_placebo_panel.py`. Yellow
  non-Flex, **2023 vs 2024**, carrying both `charged_share_2023` (no-leakage) and `charged_share_2024` —
  the **Model-2 placebo** input.

The per-model estimates and interpretation live in the notebooks
([`yellow_model1_model2.ipynb`](../../../notebooks/yellow_model1_model2.ipynb),
[`model3_cross_vehicle.ipynb`](../../../notebooks/model3_cross_vehicle.ipynb)), not here.
