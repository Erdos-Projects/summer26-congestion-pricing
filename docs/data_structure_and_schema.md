# Data Structure and Standardized Schema

This document describes how raw TLC trip data are organized locally, what the first-step
cleaning pipeline produces, and how each standardized column is derived from Yellow Taxi
and HVFHV (high-volume for-hire vehicle) source fields.

## Study scope

- **Included:** Yellow Taxi and HVFHV monthly trip records for **February–June 2024** and
  **February–June 2025**.
- **Placebo window:** February-June **2023** standardized files are used only for the
  2023-to-2024 no-fee placebo comparisons.
- **Excluded:** Green Taxi and non-HVFHV for-hire vehicle records; these services are outside the
  scope of the current analysis.
- **Policy context:** NYC congestion pricing in the Central Business District (CBD) took
  effect on **January 5, 2025**. We treat **January 2025 as a transition month** and do
  not include it in the primary Feb–Jun comparison windows.

## Folder layout

### Raw data (`data/raw/`)

Raw TLC parquet files are stored locally and are **not** committed to git. Files are
organized by calendar year and month:

```
data/raw/
  2023/
    Feb/   yellow_tripdata_2023-02.parquet, fhvhv_tripdata_2023-02.parquet
    ...
  2024/
    Feb/   yellow_tripdata_2024-02.parquet, fhvhv_tripdata_2024-02.parquet
    Mar/
    Apr/
    May/
    June/
  2025/
    Feb/
    Mar/
    Apr/
    May/
    June/
```

**Never modify files in `data/raw/`.** All cleaning writes to `data/processed/`.

### Processed data (`data/processed/`)

| Path | Purpose |
|------|---------|
| `00_standardized_trips/` | Month-by-month, service-specific trip-level parquet files after conservative cleaning and schema alignment |
| `samples/trip_level_sample.csv` | 100-row balanced CSV for manual teammate inspection |
| `samples/trip_level_sample_20k_representative.csv` | 20,000-row representative CSV for preliminary EDA |
| `samples/trip_level_sample_5k_diagnostic.csv` | Diagnostic CSV for cleaning-rule and anomaly review (target 5,000 rows) |
| `qc/` | Row-count and issue reports from standardization and sampling |

#### Standardized trip output structure

```
data/processed/00_standardized_trips/
  yellow/
    2023/02.parquet ... 06.parquet
    2024/02.parquet ... 06.parquet
    2025/02.parquet ... 06.parquet
  hvfhv/
    2023/02.parquet ... 06.parquet
    2024/02.parquet ... 06.parquet
    2025/02.parquet ... 06.parquet
```

The large standardized files are available through the external package documented in
[`../data/README.md`](../data/README.md). They can also be regenerated from the public TLC files.

Each file contains trips from **one service**, **one year**, and **one month** that pass
fundamental validity checks (see [Cleaning rules](#conservative-cleaning-rules)).

#### Sample files

| File | Purpose |
|------|---------|
| `samples/trip_level_sample.csv` | **Balanced 100-row** extract (`random_state=42`) for manual QA only—not for modeling or aggregate statistics |
| `samples/trip_level_sample_20k_representative.csv` | **Representative 20,000-row** extract (`random_state=42`) for preliminary teammate EDA |
| `samples/trip_level_sample_5k_diagnostic.csv` | **Diagnostic** extract (`random_state=42`) for cleaning-rule and anomaly review; target 5,000 rows |

The 20K sample uses **proportional stratified random sampling** by
`service_type × year × month` (largest-remainder allocation to exactly 20,000 rows).
It is **not** balanced across strata and does **not** force a 50/50 split of 2025
charged vs. uncharged CBD trips; it preserves the natural `charged_cbd_flag` distribution
as much as possible. For aggregate estimates from the sample, weight rows by
`sample_weight = stratum_population_n / stratum_sample_n`.

Sampling metadata columns on the 20K file:

| Column | Definition |
|--------|------------|
| `sample_row_id` | Sequential row identifier (1–20,000) |
| `sampling_stratum` | Stratum key, e.g. `yellow_2025_03` |
| `stratum_population_n` | Row count in the standardized monthly file |
| `stratum_sample_n` | Rows drawn from that stratum |
| `sample_weight` | `stratum_population_n / stratum_sample_n` |

Yellow `payment_type` is preserved with label and review flags. March DST spring-forward
rows are flagged (`dst_transition_day_flag`, `dst_transition_window_flag`), not removed.
See [`cleaning_notes.md`](cleaning_notes.md) for HVFHV cost caveats and QC flag scope.

The **5K diagnostic sample** is built from **raw** parquet files (not standardized
outputs). It oversamples anomaly categories (`diagnostic_category`) such as non-positive
passenger cost, negative CBD fees, and payment-review trips. It is **not representative**
and must not be used for aggregate estimates. The local build reaches 5,000 rows
when fill-in from other categories compensates for categories with no raw matches
(e.g. `missing_zone`, `negative_distance` in the current Feb–Jun 2024/2025 window);
see `qc/diagnostic_notes.csv`. QC outputs:
`qc/diagnostic_anomaly_counts.csv`, `qc/diagnostic_sample_composition.csv`,
`qc/diagnostic_notes.csv`.

#### QC reports

| File | Contents |
|------|----------|
| `qc/standardization_row_counts.csv` | Per-file row counts before and after cleaning |
| `qc/standardization_issues.csv` | Skipped files and files with notable row loss |
| `qc/trip_level_sample_notes.csv` | Notes when 100-row sample quota groups could not be fully filled |
| `qc/trip_level_sample_20k_representative_composition.csv` | Per-stratum population, sample size, and weight for the 20K sample |
| `qc/trip_level_sample_20k_representative_notes.csv` | Sampling assumptions, unavailable QC flags, and caveats |
| `qc/diagnostic_anomaly_counts.csv` | Per-flag raw counts and shares by service/year/month from raw files |
| `qc/diagnostic_sample_composition.csv` | Diagnostic sample breakdown by category, service, and flags |
| `qc/diagnostic_notes.csv` | Category targets, shortages, fill-in decisions, and non-representative warning |

## Scripts

| Script | Role |
|--------|------|
| `scripts/standardize_trips.py` | Discover raw parquets, clean and standardize one file at a time, write monthly outputs and QC reports |
| `scripts/make_trip_level_sample.py` | Build the 100-row balanced CSV sample from standardized parquets |
| `scripts/make_representative_sample_20k.py` | Build the 20,000-row representative CSV sample (memory-safe, one monthly file at a time) |
| `scripts/create_diagnostic_sample.py` | Build the diagnostic CSV sample from raw parquets with oversampled anomaly categories |

Run in order:

```bash
python scripts/standardize_trips.py
python scripts/make_trip_level_sample.py
python scripts/make_representative_sample_20k.py
python scripts/create_diagnostic_sample.py
```

---

## Standardized schema

### Core columns (both services)

| Column | Type | Definition |
|--------|------|------------|
| `service_type` | string | `"yellow"` or `"hvfhv"` |
| `year` | int | Calendar year from the source folder/filename (e.g. `2024`, `2025`) |
| `month` | int | Calendar month of the source file (`2`–`6` for Feb–Jun) |
| `pickup_datetime` | timestamp | Trip start time |
| `dropoff_datetime` | timestamp | Trip end time |
| `pickup_date` | date | Date portion of `pickup_datetime` |
| `pickup_hour` | int | Hour of day (0–23) from `pickup_datetime` |
| `day_of_week` | int | Day of week from `pickup_datetime` (Monday = 0, Sunday = 6) |
| `PULocationID` | numeric | TLC taxi zone ID for trip origin |
| `DOLocationID` | numeric | TLC taxi zone ID for trip destination |
| `trip_distance_miles` | float | Trip distance in miles |
| `trip_duration_seconds` | float | Trip duration in seconds |
| `cbd_congestion_fee` | float | CBD congestion pricing fee charged on the trip |
| `charged_cbd_flag` | bool | `True` when `cbd_congestion_fee > 0` |
| `congestion_surcharge` | float | TLC congestion surcharge (distinct from CBD fee) |
| `tolls` | float | Toll amounts passed to the passenger |
| `airport_fee` | float | Airport access fee when applicable |
| `passenger_cost_pretip` | float | Mandatory pre-tip passenger cost (see [Cost definitions](#passenger-cost-definitions)) |
| `relative_cbd_burden` | float | `cbd_congestion_fee / passenger_cost_pretip` when pre-tip cost > 0; otherwise null |
| `source_file` | string | Relative path to the raw parquet file |

### Optional Yellow-specific columns

| Column | Raw source | Notes |
|--------|------------|-------|
| `payment_type` | `payment_type` | TLC payment code; useful for data-quality checks |
| `passenger_count` | `passenger_count` | Reported passenger count |
| `fare_amount` | `fare_amount` | Metered time-and-distance fare only (not total payment) |
| `tip_amount` | `tip_amount` | Tip amount |
| `total_amount` | `total_amount` | Total passenger charge including fare, surcharges, tolls, and tip |
| `RatecodeID` | `RatecodeID` | TLC rate code |

**Derived Yellow flags** (computed in `standardize_trips.py`; they define the analysis populations
used downstream):

| Column | Derived from | Definition |
|--------|--------------|------------|
| `yellow_card_or_cash_flag` | `payment_type` | `True` when `payment_type ∈ {1 credit card, 2 cash}`. The card/cash population used for the fare-based `DS_z` burden metric. |
| `flex_fare_flag` | `payment_type` | `True` when `payment_type = 0` (Flex Fare, upfront-priced). Excluded from the primary Yellow volume outcome because it is a separate pricing regime whose share grew independently of the fee. |
| `irregular_payment_flag` | `payment_type` | `True` when `payment_type ∈ {3, 4, 5, 6}` (no-charge / dispute / unknown / voided). Real rides kept in the non-Flex volume count. |
| `airport_trip_flag` | `airport_fee`, `PU/DOLocationID` | `True` when `airport_fee > 0` **and** pickup or dropoff is JFK (`132`) or LaGuardia (`138`). Newark (`EWR`) is excluded — it carries no NYC airport fee. |

These four flags are the **canonical** standardized columns. The 20K representative sample derives a
few finer `payment_type` fields for QA (splitting `irregular_payment_flag` into no-charge/dispute/void
vs unknown, plus a text label and review flag); those are documented in
[`cleaning_notes.md`](cleaning_notes.md), which references this table as the source of truth.

### Optional HVFHV-specific columns

| Column | Raw source | Notes |
|--------|------------|-------|
| `hvfhs_license_num` | `hvfhs_license_num` | Identifies Uber, Lyft, Via, Juno, etc. (not analyzed by company in this step) |
| `base_passenger_fare` | `base_passenger_fare` | Fare before tolls, tips, taxes, and fees |
| `bcf` | `bcf` | Black car fund fee |
| `sales_tax` | `sales_tax` | Sales tax on the trip |
| `tips` | `tips` | Tip amount (excluded from `passenger_cost_pretip`) |
| `driver_pay` | `driver_pay` | Driver pay field from TLC |
| `shared_request_flag` | `shared_request_flag` | Whether passenger requested a shared ride |
| `shared_match_flag` | `shared_match_flag` | Whether trip was matched as shared |

### QC flag columns (informational)

These flags are attached to rows that **pass** fundamental validity filters. They do not
replace outlier removal in later analysis steps.

| Column | Definition |
|--------|------------|
| `zero_distance_flag` | `trip_distance_miles == 0` |
| `very_long_duration_flag` | `trip_duration_seconds > 24 hours` |
| `very_long_distance_flag` | `trip_distance_miles > 100` |
| `negative_cost_flag` | `passenger_cost_pretip <= 0` (such rows are dropped from output) |

---

## Column derivation by service

### Yellow Taxi

| Standardized column | Raw column(s) | Derivation |
|--------------------|---------------|------------|
| `pickup_datetime` | `tpep_pickup_datetime` | Parsed as datetime |
| `dropoff_datetime` | `tpep_dropoff_datetime` | Parsed as datetime |
| `trip_distance_miles` | `trip_distance` | Renamed |
| `trip_duration_seconds` | `tpep_pickup_datetime`, `tpep_dropoff_datetime` | `(dropoff - pickup)` in seconds |
| `cbd_congestion_fee` | `cbd_congestion_fee` | Present in 2025+ files; **filled with 0** in 2024 (pre-policy) |
| `congestion_surcharge` | `congestion_surcharge` | Direct |
| `tolls` | `tolls_amount` | Renamed |
| `airport_fee` | `Airport_fee` | TLC uses capital `A` in yellow files |
| `passenger_cost_pretip` | `total_amount`, `tip_amount` | `total_amount - tip_amount` |

### HVFHV

| Standardized column | Raw column(s) | Derivation |
|--------------------|---------------|------------|
| `pickup_datetime` | `pickup_datetime` | Parsed as datetime |
| `dropoff_datetime` | `dropoff_datetime` | Parsed as datetime |
| `trip_distance_miles` | `trip_miles` | Renamed |
| `trip_duration_seconds` | `trip_time` | TLC reports duration in seconds |
| `cbd_congestion_fee` | `cbd_congestion_fee` | Present in 2025+ files; **filled with 0** in 2024 |
| `congestion_surcharge` | `congestion_surcharge` | Direct |
| `tolls` | `tolls` | Direct |
| `airport_fee` | `airport_fee` | Direct |
| `passenger_cost_pretip` | `base_passenger_fare`, `tolls`, `bcf`, `sales_tax`, `congestion_surcharge`, `airport_fee`, `cbd_congestion_fee` | Sum of mandatory pre-tip charges (tips excluded) |

---

## Passenger cost definitions

### Yellow Taxi

```
passenger_cost_pretip = total_amount - tip_amount
```

- `fare_amount` is **not** total passenger payment—it is only the metered fare.
- `total_amount` is closer to the full passenger charge.
- Tips are subtracted so pre-tip costs are comparable across services.

### HVFHV

```
passenger_cost_pretip =
    base_passenger_fare
  + tolls
  + bcf
  + sales_tax
  + congestion_surcharge
  + airport_fee
  + cbd_congestion_fee
```

- HVFHV records do not include a `total_amount` field.
- Tips are excluded from this sum.

### Relative CBD burden

```
relative_cbd_burden = cbd_congestion_fee / passenger_cost_pretip   (when passenger_cost_pretip > 0)
relative_cbd_burden = null                                           (otherwise)
```

### Charged CBD flag

```
charged_cbd_flag = (cbd_congestion_fee > 0)
```

---

## Conservative cleaning rules

Applied in `scripts/standardize_trips.py` before writing monthly parquet outputs:

1. Parse `pickup_datetime` and `dropoff_datetime`; drop rows with invalid timestamps.
2. Keep only rows where `dropoff_datetime > pickup_datetime`.
3. Keep only rows where pickup year and month match the source folder/file.
4. Keep only rows where `PULocationID` and `DOLocationID` are not missing.
5. Keep only rows where `trip_distance_miles >= 0` (zero-distance trips retained).
6. Keep only rows where `trip_duration_seconds > 0`.
7. `cbd_congestion_fee` must not be missing; for pre-policy data (**year < 2025**), missing
   values are filled with **0**. For **2025+**, missing values cause the row to be dropped.
8. Keep only rows where `cbd_congestion_fee >= 0`.
9. Keep only rows where `passenger_cost_pretip > 0` (required for burden metrics).

Outlier trips (very long distance/duration) are **not** removed at this stage; they receive
QC flags instead.

---

## Downstream use

The EDA, burden-analysis, and modeling notebooks use these standardized trip files. Smaller
model-ready panels and exported results are tracked separately under `data/processed/` and
`results/`.
