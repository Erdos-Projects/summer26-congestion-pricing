# Cleaning and Sampling Notes

Supplementary notes for teammates using processed trip data. For the full standardized
schema and conservative cleaning rules, see [`data_structure_and_schema.md`](data_structure_and_schema.md).

## Representative 20K sample

**Path:** `data/processed/samples/trip_level_sample_20k_representative.csv`

**Script:** `scripts/make_representative_sample_20k.py`

**QC outputs:**

- `data/processed/qc/trip_level_sample_20k_representative_composition.csv` — per-stratum population, draw size, and weight
- `data/processed/qc/trip_level_sample_20k_representative_notes.csv` — assumptions and caveats

### Sampling method

- **Strata:** `service_type × year × month` (Yellow and HVFHV; February–June 2024 and 2025)
- **Target size:** 20,000 rows (`random_state=42`)
- **Allocation:** Proportional to each stratum’s row count in `data/processed/00_standardized_trips/`, with largest-remainder rounding so the total is exactly 20,000
- **Not balanced:** Strata are not forced to equal sizes; 2025 charged and uncharged CBD trips are not forced to 50/50

This sample is **better for preliminary EDA** than the 100-row balanced sample
(`trip_level_sample.csv`), which was designed for manual QA with equal service/year quotas.

### Using `sample_weight`

For aggregate estimates from the 20K sample (means, totals, shares by stratum):

```
sample_weight = stratum_population_n / stratum_sample_n
```

Weight rows when extrapolating to the full standardized population. The final **zone-level**
and **origin–destination** analyses use **full-data aggregates**, not only this extract.

The representative sample covers the primary 2024-2025 comparison. Separate 2023 standardized
files support the no-fee placebo analyses; see [`../data/README.md`](../data/README.md) for the full
data layout.

## Yellow payment type

The **canonical** standardized payment flags — `yellow_card_or_cash_flag`, `flex_fare_flag`,
`irregular_payment_flag` — are defined in
[`data_structure_and_schema.md`](data_structure_and_schema.md) (they live in the standardized
parquet). The 20K sample additionally carries these finer `payment_type` fields for QA, where
`irregular_payment_flag` (codes 3–6) is split into `yellow_no_charge_dispute_void_flag` (3, 4, 6) and
`yellow_payment_unknown_flag` (5):

| Column | Definition |
|--------|------------|
| `yellow_payment_type_label` | Text label from TLC code |
| `yellow_card_or_cash_flag` | `payment_type` in {1, 2} |
| `yellow_no_charge_dispute_void_flag` | `payment_type` in {3, 4, 6} |
| `yellow_payment_unknown_flag` | `payment_type == 5` |
| `yellow_payment_review_flag` | `payment_type` in {0, 3, 4, 5, 6} |

TLC mapping: 0 = Flex Fare, 1 = Credit card, 2 = Cash, 3 = No charge, 4 = Dispute,
5 = Unknown, 6 = Voided trip.

## HVFHV passenger cost

`passenger_cost_pretip` for HVFHV is **reconstructed** in standardization as:

```
base_passenger_fare + tolls + bcf + sales_tax + congestion_surcharge + airport_fee + cbd_congestion_fee
```

This sum may **not** capture app-specific discounts, refunds, credits, or user-specific
pricing adjustments visible only inside Uber/Lyft (or other) apps.

`possible_refund_or_adjustment_flag` marks rows for manual review when cost components
or totals look anomalous; it does **not** assert that a refund or discount definitely
occurred.

## DST transition rows

March spring-forward DST dates in the study window:

| Year | Date |
|------|------|
| 2024 | 2024-03-10 |
| 2025 | 2025-03-09 |

- `dst_transition_day_flag` — pickup or dropoff date is a transition day
- `dst_transition_window_flag` — transition day **and** pickup or dropoff hour is 1–3 AM

These rows are **flagged, not removed**.

## QC flags in standardized and sample data

The standardization pipeline (`scripts/standardize_trips.py`) **drops** rows with (the canonical rule
list is in [`data_structure_and_schema.md`](data_structure_and_schema.md) § Conservative cleaning
rules):

- Invalid timestamps or dropoff not after pickup
- Pickup year/month mismatch with source file
- Missing zone IDs
- Negative distance, non-positive duration
- Missing or negative CBD fee (2025+)
- Non-positive `passenger_cost_pretip`

Therefore, several QC flags on the 20K sample (`invalid_timestamp_flag`,
`month_mismatch_flag`, `missing_zone_flag`, `negative_distance_flag`,
`nonpositive_duration_flag`, `negative_cbd_fee_flag`, `passenger_cost_nonpositive_flag`)
are included for schema consistency but **cannot be true** for rows that passed
standardization. Do not treat always-false flags as evidence that those anomaly types
never exist in raw TLC data—they were removed earlier.

Outlier trips (zero distance, very long distance/duration) are **retained** in
standardized files and carry informational flags where applicable.

## Derived fields on the 20K sample

| Field | Definition |
|-------|------------|
| `passenger_cost_excl_cbd` | `passenger_cost_pretip - cbd_congestion_fee` |
| `burden_eligible_flag` | `passenger_cost_pretip > 0` and `cbd_congestion_fee >= 0` |

## 100-row balanced sample (unchanged)

`data/processed/samples/trip_level_sample.csv` remains the small balanced extract for
manual spot-checking. It is **not** overwritten by the 20K or diagnostic scripts.

## Diagnostic 5K sample (cleaning-rule review)

**Path:** `data/processed/samples/trip_level_sample_5k_diagnostic.csv`

**Script:** `scripts/create_diagnostic_sample.py`

**QC outputs:**

- `data/processed/qc/diagnostic_anomaly_counts.csv` — per-flag counts and shares from raw monthly files
- `data/processed/qc/diagnostic_sample_composition.csv` — sample breakdown by `diagnostic_category`, service, year, month, and key flags
- `data/processed/qc/diagnostic_notes.csv` — category targets, shortages, fill-in decisions, assumptions

### Purpose

The diagnostic sample is for **anomaly inspection and cleaning-rule discussion**. It is
built from **raw** Yellow and HVFHV parquet files (Feb–Jun 2024 and 2025), not from
standardized outputs, so rows dropped during standardization—such as non-positive
`passenger_cost_pretip` and negative `cbd_congestion_fee`—can still be reviewed.

### Non-representative warning

This sample **intentionally oversamples** problematic records across twelve
`diagnostic_category` values (e.g. `nonpositive_passenger_cost`, `negative_cbd_fee`,
`yellow_payment_review`, `hvfhv_possible_refund_or_adjustment`, `dst_transition_window`,
`normal_reference`). **Do not use for aggregate estimates.**

### Relationship to other samples

| Sample | Use |
|--------|-----|
| `trip_level_sample_20k_representative.csv` | Preliminary EDA and descriptive analysis (representative; use `sample_weight`) |
| `trip_level_sample_5k_diagnostic.csv` | Cleaning diagnostics and anomaly review (non-representative) |
| `trip_level_sample.csv` | Manual QA spot-check (balanced 100 rows) |

### Cleaning implications to review

- **Non-positive passenger cost** and **negative CBD-fee** rows should be reviewed before finalizing exclusion rules.
- **Yellow `payment_type`** may matter for burden analysis (review flags included).
- **HVFHV `passenger_cost_pretip`** is reconstructed and may not capture discounts, refunds, credits, or user-specific app pricing.
- **DST transition-window** rows are flagged, not removed (`dst_transition_day_flag`, `dst_transition_window_flag`).

Each row has one primary `diagnostic_category` (the bucket used for sampling) plus boolean
columns for all diagnostic flags; a row may satisfy multiple flags simultaneously.

### Current local status

| Item | Status |
|------|--------|
| Script | `scripts/create_diagnostic_sample.py` — implemented |
| Sample path | `data/processed/samples/trip_level_sample_5k_diagnostic.csv` |
| Target rows | 5,000 (`random_state=42`) |
| Current local row count | 5,000 (see `qc/diagnostic_notes.csv`) |
| Categories with zero raw matches | `missing_zone`, `negative_distance` (filled from other categories) |
| Regenerate | `python scripts/create_diagnostic_sample.py` (requires raw parquets under `data/raw/`) |

The 100-row and 20K representative samples are unchanged by the diagnostic script.
