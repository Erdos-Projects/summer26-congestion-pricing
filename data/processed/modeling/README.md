# Modeling Outputs

This folder contains small modeling-ready CSV outputs built from committed
disruption-score summaries and local standardized parquet files.

## `hvfhv_model1_zone_features.csv`

Zone-direction feature table for the HVFHV Model 1 burden-vs-volume analysis.
The table joins the existing HVFHV DS_z outputs to 2024-only controls. It does
not rerun or change DS_z.

### Outcomes

- `pct_volume_change`: 2025 vs 2024 trip-count percent change.
- `delta_volume`: `n_trips_2025 - n_trips_2024`.
- `n_trips_2025`: post-policy trip count. Included for outcome accounting, not
  as an explanatory control.

### Allowed 2024 Controls

- `n_trips_2024`
- `log_n_trips_2024`
- `avg_base_fare_2024`
- `avg_total_cost_2024`
- `avg_trip_distance_2024`
- `avg_trip_duration_2024`

All allowed controls are computed only from Feb-Jun 2024 standardized HVFHV
parquets. Duration is included as a baseline control candidate but should be
used cautiously because traffic conditions can affect duration.

### Descriptive Fields

- `location_id`, `direction`, `Borough`, `zone_name`, `service_zone`
- `DS_z`, `DS_z_median`, `burden_rank`, `DS_z_quartile`
- `low_n_flag`

Rows with no 2024 baseline (`n_trips_2024 = 0`) keep `pct_volume_change` and 2024
average controls missing because the percent change and baseline averages are
undefined. They remain in the table for transparency and should be treated as
low-N edge cases.

### Regeneration

From the repository root (requires local Feb-Jun 2024 HVFHV standardized
parquets under `data/processed/00_standardized_trips/hvfhv/2024/`):

```bash
python scripts/04_model1_feature_table.py
```

DuckDB aggregation uses `SET threads TO 1` for deterministic float averages.

### Forbidden Post-Policy Controls

Do not use 2025 post-policy cost, fare, distance, duration, driver pay, trip
counts, `pct_volume_change`, or `delta_volume` as explanatory controls. Do not
include both DS_z and `relative_cbd_burden` as independent features unless the
run is explicitly labeled as a sensitivity check. Treat `cbd_congestion_fee` as
treatment/exposure, not a normal control.

These features support descriptive and inferential Model 1 analysis. They are
not causal proof.
