# HVFHV No-June Pretrend And Placebo Diagnostics

Diagnostic only. These checks exclude June and do not prove or disprove parallel trends.

## Inputs

- Standardized HVFHV parquet files for Feb-May 2023 and Feb-May 2024
- Existing `hvfhv_monthly_panel.csv` for the 2024-only pretrend exposure
- CRZ zone list reused from `scripts/yellow_ds_pipeline.py`
- `data/taxi_zone_lookup.csv`

Regeneration command:

```bash
python scripts/hvfhv_pretrend_placebo.py
```

## 2024 Pretrend Diagnostic

Formula: `log_n_trips ~ month_index * charged_share_2024_geo`

- coefficient on `month_index:charged_share_2024_geo`: -0.012863
- standard error: 0.020331
- 95 percent CI: [-0.052711, 0.026984]
- rows: 2095
- units: 525

The pretrend output is a diagnostic visualization table, not proof of parallel trends.

## 2023→2024 Placebo

Main exposure: `charged_share_2023_geo`, computed only from 2023 geography.

Reference for interpretation only: existing HVFHV Model 2 FE-style coefficient approximately -0.1136. Model 2 is not rerun here.

Primary placebo result, `placebo_unit_fe`:

- coefficient on `placebo_post:charged_share_2023_geo`: -0.101224
- standard error: 0.010633
- 95 percent CI: [-0.122064, -0.080383]
- rows: 4186
- interpretation flag: weakens_causal_interpretation

The no-June placebo coefficient is negative and similar in magnitude to the existing Model 2 reference estimate, so this diagnostic weakens a causal interpretation. This is diagnostic evidence, not proof.

## Coverage

- Missing expected months: none
- Placebo panel rows: 4187
- Placebo panel units: 525
- Missing placebo exposure rows: 1
- Placebo rows with `n_trips < 30`: 44

## Outputs

- `data/processed/disruption_score/hvfhv_pretrend_2024_diagnostic.csv`
- `data/processed/disruption_score/hvfhv_placebo_2023_2024_panel.csv`
- `data/processed/disruption_score/hvfhv_placebo_2023_2024_results.csv`
