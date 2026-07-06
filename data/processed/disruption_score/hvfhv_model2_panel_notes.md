# HVFHV Model 2 Monthly Panel Notes

## Inputs

- 2024 standardized HVFHV parquets: 5 files under `data/processed/00_standardized_trips/hvfhv/2024`.
- 2025 standardized HVFHV parquets: 5 files under `data/processed/00_standardized_trips/hvfhv/2025`.
- Zone lookup: `data/taxi_zone_lookup.csv`.

Regeneration command:

```bash
python scripts/hvfhv_model2_monthly_panel.py
```

## CRZ Zone Source

- Reused `CRZ_ZONE_IDS` from `scripts/yellow_ds_pipeline.py`.
- Definition in that script: Congestion Relief Zone, Manhattan south of 60th St, 38 TLC LocationIDs.
- CRZ zone count: 38.

## Panel Construction

- Unit: zone x direction x year x month.
- Directions are constructed separately from pickup and dropoff zones.
- Main exposure is `charged_share_2024_geo`: the 2024 share of trips in the zone-direction cell whose pickup or dropoff touched the CRZ by geography.
- `charged_share_2024_geo` is attached to both 2024 and 2025 rows.
- `charged_cbd_flag` is not used to create the main exposure.
- No Model 2 regression is run here.

## Output Summary

- Panel rows: 5,236.
- Zone-direction units: 527.
- Balanced 10-month zone-direction units: 522.
- Rows with missing `charged_share_2024_geo`: 3.
- Rows with `n_trips < 30`: 52.

## Exposure Validation Against 2025 Observed Fee Flag

- Validation uses 2025 `charged_cbd_flag` only as a diagnostic.
- Overall 2025 trips checked: 100,503,462.
- Match rate: 0.9771.
- False positives, geography exposed but not observed charged: 343,409.
- False negatives, observed charged but not geography exposed: 1,958,462.
- Share of observed charged trips missed by geography-only exposure: 0.0564.
- Geography precision: 0.9896.
- Geography recall: 0.9436.

Monthly validation:

| month | n_trips_2025 | match_rate | false_positives | false_negatives | missed_observed_charged_share |
|---:|---:|---:|---:|---:|---:|
| 2 | 19,338,054 | 0.9781 | 61,329 | 361,480 | 0.0530 |
| 3 | 20,477,120 | 0.9778 | 68,067 | 386,841 | 0.0550 |
| 4 | 19,741,018 | 0.9778 | 60,820 | 377,937 | 0.0546 |
| 5 | 21,090,841 | 0.9756 | 76,957 | 438,474 | 0.0606 |
| 6 | 19,856,429 | 0.9763 | 76,236 | 393,730 | 0.0588 |

## Leakage Notes

- Use `charged_share_2024_geo` as the Model 2 exposure.
- Do not use 2025 observed charged shares as the treatment in the Model 2 regression.
- Do not use 2025 cost, fare, duration, driver pay, or volume-change fields as controls.
- Model 3 remains postponed and is not touched by this output.
