# HVFHV - Data Audit

*Data-quality audit and analysis-inclusion decisions for the High-Volume
For-Hire Vehicle (HVFHV) portion of the NYC CBD congestion-pricing study
(Feb-Jun 2024 vs. Feb-Jun 2025).*

*Companion to
[`hvfhv_dropped_and_engineered_features.md`](hvfhv_dropped_and_engineered_features.md).
Findings here are distilled from
[`notebooks/hvfhv_full_EDA.ipynb`](../notebooks/hvfhv_full_EDA.ipynb),
[`data/processed/qc/validation_row_counts.csv`](../data/processed/qc/validation_row_counts.csv),
and the durable disruption-score outputs under
[`data/processed/disruption_score/`](../data/processed/disruption_score/).*

---

## 1. Data source and study design

- **Source:** NYC TLC HVFHV trip records, standardized by
  [`scripts/standardize_trips.py`](../scripts/standardize_trips.py).
- **Input layout:**
  `data/processed/00_standardized_trips/hvfhv/{2024,2025}/{02,03,04,05,06}.parquet`.
  These full trip-level parquet files are intentionally not committed to GitHub.
- **Study window:** February-June **2024** (pre-policy) vs. February-June
  **2025** (post-policy). January 2025 is excluded because the CBD congestion
  fee began on January 5, 2025 and the partial month is not a steady-state
  comparison period.
- **Reporting rule:** final trip-volume, cost, burden, and zone-ranking claims
  should use full-data aggregates, not small samples.
- **Interpretation:** this track supports descriptive and inferential claims
  about associations between fee burden, exposure, and trip patterns. It is not
  causal proof by itself.

## 2. Row-count coverage

The full-data HVFHV EDA reports 10 standardized monthly parquet files:

| Year | Month | Processed rows |
|---:|---:|---:|
| 2024 | 02 | 19,352,998 |
| 2024 | 03 | 21,279,860 |
| 2024 | 04 | 19,732,410 |
| 2024 | 05 | 20,704,206 |
| 2024 | 06 | 20,122,914 |
| 2025 | 02 | 19,338,054 |
| 2025 | 03 | 20,477,120 |
| 2025 | 04 | 19,741,018 |
| 2025 | 05 | 21,090,841 |
| 2025 | 06 | 19,856,429 |

Totals:

| Year | Rows |
|---:|---:|
| 2024 | 101,192,388 |
| 2025 | 100,503,462 |
| Combined | 201,695,850 |

These totals match
[`data/processed/qc/validation_row_counts.csv`](../data/processed/qc/validation_row_counts.csv).
The full EDA summarizes the combined volume change as about **-0.7%**.

## 3. Key fields used

| Field | Role |
|---|---|
| `pickup_datetime`, `dropoff_datetime` | month, day-of-week, hour, duration checks |
| `PULocationID`, `DOLocationID` | zone-by-direction unit, CRZ/geography exposure, OD summaries |
| `trip_distance_miles` | trip composition, distance buckets, baseline trip-economics control candidate |
| `trip_duration_seconds` | EDA/speed context; use cautiously in models |
| `hvfhs_license_num` / provider label | provider-mix summaries, mainly Uber vs Lyft |
| `shared_request_flag`, `shared_match_flag` | shared-ride regime summaries |
| `base_passenger_fare` | underlying platform fare component |
| `tolls`, `bcf`, `sales_tax`, `congestion_surcharge`, `airport_fee` | mandatory passenger cost components |
| `cbd_congestion_fee` | CBD treatment/exposure numerator |
| `charged_cbd_flag` | 2025 observed charge indicator |
| `passenger_cost_pretip` | reconstructed mandatory passenger cost before voluntary tip |
| `relative_cbd_burden` | fee/current-cost reference burden metric |
| `driver_pay` | driver-side descriptive outcome/context |

## 4. Cost definition and caveat

HVFHV records do **not** include a Yellow-style `total_amount`. The standardized
pipeline reconstructs the pre-tip passenger cost as:

```text
passenger_cost_pretip =
    base_passenger_fare
  + tolls
  + bcf
  + sales_tax
  + congestion_surcharge
  + airport_fee
  + cbd_congestion_fee
```

Tips are excluded. This is the best available TLC-field reconstruction of
mandatory pre-tip passenger cost, but it may not capture platform-specific
discounts, refunds, credits, subscriptions, user-specific app pricing, or other
off-ledger adjustments. HVFHV cost findings should therefore be described as
TLC-recorded/reconstructed passenger cost, not guaranteed final rider wallet
cost.

The CBD fee analyzed here is `cbd_congestion_fee`, not the older
`congestion_surcharge`.

## 5. Cleaning already applied upstream

`standardize_trips.py` applies conservative validity filters before the EDA and
DS_z pipelines read the data:

- invalid timestamps / dropoff not after pickup;
- pickup year-month mismatch with the source file;
- missing pickup or dropoff zone IDs;
- negative distance;
- non-positive duration;
- missing or negative CBD congestion fee, with 2024 pre-policy missing CBD fees
  filled as zero where appropriate;
- non-positive `passenger_cost_pretip`.

Outlier-like rows such as zero distance, very long duration, and very long
distance are flagged rather than automatically dropped at standardization time.
The current evidence files do not contain a final full-data missingness table
for every HVFHV field; missingness claims should therefore be limited to the
standardization/QC checks and the notebook's displayed aggregate diagnostics.

## 6. Full-data EDA findings

### 6.1 Monthly volume, cost, distance, duration, and driver pay

The full EDA reports:

- Total HVFHV volume is roughly flat/slightly down between windows, with a
  combined 2025 change of about **-0.7%**.
- Median passenger pre-tip cost rose in every matched month, ranging from
  **+$0.13** in April to **+$1.93** in March.
- Median base fare rose only in February and March; it was lower in April-June
  2025 than in the matched 2024 months.
- Median driver pay fell slightly in February but rose from March through June.
- Median distance changed only modestly month to month; the full EDA does not
  support treating broad distance shifts as the main result.

These monthly summaries are notebook outputs, not separate durable CSVs in the
committed repo unless regenerated from the notebook.

### 6.2 Provider mix

Provider mix is a core HVFHV composition check. The full EDA reports:

- Uber share fell from about **74.5%** to **72.2%** across the study windows.
- Lyft share rose from about **25.5%** to **27.8%**.
- March volume fell about **-3.8%**, May rose about **+1.9%**, and the other
  months moved more modestly.

Provider fields should be carried as descriptive regime/context variables. They
should not be used to turn the project into a prediction task.

### 6.3 Shared rides

Shared-ride flags identify a meaningful descriptive regime:

- Matched shared rides in 2025 have longer trips, with notebook-reported median
  distance **5.74 miles** and median duration **26.3 minutes**.
- Requested-but-unmatched shared rides have much lower median passenger cost
  (**$14.58** in the notebook output).
- Shared rides should be reported separately where relevant, especially in
  descriptive tables. They are not currently the primary modeling estimand.

### 6.4 Time and seasonality

The full EDA reports strong weekly structure:

- Lag-7 trip-count correlation is **0.825** in 2024 and **0.860** in 2025,
  higher than lag-1 in both years.
- Hourly CBD exposure varies meaningfully. In 2025, about **34.7M** trips were
  charged, or roughly **34.5%** of trips. Hourly exposure peaks around **9 PM**
  at **40.3%** and is lowest around **7 AM** at **27.6%**.
- Median base-cost burden is highest around **7 PM** at about **4.76%** in the
  notebook output.

These time-of-day and seasonality findings are useful for EDA narrative and
robustness discussion. Current Model 1 and Model 2 designs operate at
zone-by-direction or monthly-panel levels, so raw hour/day fields are not
primary model features.

### 6.5 Charged versus uncharged composition

The full EDA reports that 2025 charged trips differ substantially from
uncharged trips:

| Metric | Not charged | Charged |
|---|---:|---:|
| Rows | 65,785,711 | 34,717,751 |
| Median passenger cost | $18.73 | $36.29 |
| Median base fare | $16.40 | $28.10 |
| Median driver pay | $13.25 | $20.18 |
| Median distance | 2.66 mi | 3.76 mi |
| Median duration | 14.1 min | 20.3 min |
| Airport-fee share | 7.6% | 10.2% |

This composition difference is important: charged trips are not merely the same
rides plus a fee. They are longer, more expensive, and more airport-exposed.
The difference supports controlling or stratifying by pre-policy trip
characteristics where the model design allows it.

### 6.6 Burden distribution and distance pattern

The full EDA reports two burden definitions for charged 2025 trips:

| Definition | Median | p95 | p99 |
|---|---:|---:|---:|
| Fee / current pre-tip cost | 4.13% | 9.40% | 11.55% |
| Fee / base cost excluding CBD, $1 floor | 4.31% | 10.37% | 13.05% |

Shorter trips carry higher relative burden. The notebook reports 0-1 mile trips
at **9.62%** median base-cost burden, with longer trips showing lower relative
burden even when CBD exposure is higher.

The $0.50/$1/$2/$5 trip-level floor sensitivity in the notebook retains more
than **99.997%** of charged trips. The durable rank-stability outputs also show
that zone rankings are highly stable across denominator floors.

### 6.7 Driver-side metrics

HVFHV exposes `driver_pay`, so the EDA includes driver-side checks. Current
findings should be treated as descriptive:

- Driver pay does not simply mirror base fare.
- Median driver pay per mile and per hour are higher in every matched 2025
  month in the notebook output, even though base fare is lower from April
  through June.
- Driver pay may be an outcome or mediator of post-policy market conditions; it
  should not be used as a post-policy explanatory control for volume change.

### 6.8 Geography and OD rankings

The notebook reports that top charged pickups are concentrated in core
Manhattan zones, led by East Village, Times Sq/Theatre District, and Midtown
Center. The largest charged dropoff total is Outside of NYC, and the largest
charged OD corridor is Times Sq/Theatre District to Outside of NYC.

These geography results are notebook EDA outputs unless regenerated into
durable project tables. They are useful for narrative and map/table work, but
the authoritative DS_z ranking is the committed disruption-score CSV.

## 7. DS_z outputs and robustness artifacts

The downstream full-data artifacts under
[`data/processed/disruption_score/`](../data/processed/disruption_score/) are
the durable outputs for zone disruption analysis. They are produced by
[`scripts/01_pipeline.py`](../scripts/01_pipeline.py)
(with Manhattan robustness from
[`scripts/03_manhattan_robustness.py`](../scripts/03_manhattan_robustness.py)).
See also [`data/processed/disruption_score/README.md`](../data/processed/disruption_score/README.md).

Primary definition:

```text
DS_z = mean(cbd_congestion_fee / round(passenger_cost_pretip - cbd_congestion_fee, 2))
```

computed by zone and direction over 2025 trips with `charged_cbd_flag = true`,
positive CBD fee, and rounded base cost of at least $1.00.

Key outputs:

| Output | Role |
|---|---|
| `hvfhv_zone_disruption_score.csv` | primary zone-direction DS_z ranking |
| `hvfhv_behavioral_shift.csv` | 2024 vs 2025 volume and fare summaries |
| `hvfhv_ds_z_vs_volume_change.csv` | descriptive join of DS_z with volume change |
| `hvfhv_ds_floor_sensitivity.csv` | DS_z under $0.50/$1/$2/$5 denominator floors |
| `hvfhv_ds_rank_stability.csv` | rank stability across floor/aggregation definitions |
| `hvfhv_ds_top_zone_overlap.csv` | top-10/top-20 overlap across definitions |
| `hvfhv_borough_correlation.csv` | all-zone, borough, and direction correlations |
| `hvfhv_within_manhattan_correlation.csv` | Manhattan-focused robustness subset |
| `hvfhv_monthly_panel.csv` | Model 2 monthly zone-direction panel with 2024 geography-based exposure |
| `hvfhv_model2_exposure_validation.csv` | diagnostic comparison of geography-based exposure against the 2025 observed fee flag |
| `hvfhv_pretrend_2024_diagnostic.csv` | no-June 2024 pretrend diagnostic |
| `hvfhv_placebo_2023_2024_results.csv` | no-June 2023→2024 placebo results |

Top primary DS_z rows in `hvfhv_zone_disruption_score.csv` are Manhattan
dropoff zones such as Alphabet City, Stuy Town/Peter Cooper Village, East
Village, West Village, Greenwich Village South, and Kips Bay.

Robustness outputs support ranking stability:

- Mean DS_z rankings are almost unchanged across $0.50, $1, $2, and $5
  denominator floors.
- Top-10 and top-20 mean-DS_z overlap is 100% for pickup and dropoff across the
  tested floors.
- Median-based rankings are also very stable, though not identical to the mean
  ranking; this is expected because mean and median answer slightly different
  burden-summary questions.

Correlation outputs are descriptive, not causal:

- All-zone Spearman correlation between DS_z and percent volume change is about
  **-0.633** in the borough robustness CSV.
- Manhattan-only Pearson correlation is about **-0.540**.
- Manhattan dropoff and pickup Pearson correlations are about **-0.550** and
  **-0.560**, respectively.

The full EDA notebook also reports a low-N-filtered DS_z vs. percent-volume
Pearson correlation of **-0.610** with **n = 519**. Because that figure is a
notebook summary using its own filter, cite the durable CSV correlations when a
committed source is preferred.

**Reproducibility:** regenerate durable DS_z CSVs with DuckDB
`SET threads TO 1` so floating-point averages are deterministic across runs.
This is already set in the full EDA notebook and `01_pipeline.py`; see also
Section 12 of the companion features doc.

## 8. Analysis-inclusion rules

| Question / outcome | Rows or fields used |
|---|---|
| Broad monthly HVFHV market summary | all standardized HVFHV rows after upstream cleaning |
| Charged-trip composition | 2025 rows split by `charged_cbd_flag` |
| Burden distribution | 2025 charged trips; report fee/current-cost and fee/base-cost definitions separately |
| DS_z | 2025 charged trips with rounded base cost >= $1; zone × direction |
| Volume change | all standardized trips by zone × direction, 2024 vs 2025; no fee filter |
| Provider/shared-ride description | provider label and shared flags, reported as regimes/context |
| Driver-pay description | descriptive outcome/context only; not a post-policy control |
| Model controls | pre-policy 2024 features only |

## 9. Interpretation limits

1. HVFHV passenger cost is reconstructed from TLC components and may miss
   platform-specific discounts, refunds, credits, or user-level app pricing.
2. DS_z is computed from observed 2025 charged trips, not from a counterfactual
   population of trips that would have existed absent the policy.
3. High DS_z zones are often dense, short-trip Manhattan zones; density, trip
   length, borough, and local demand remain plausible confounders.
4. `relative_cbd_burden` and DS_z are related but not identical: the former uses
   fee/current pre-tip cost, while DS_z uses fee/base cost excluding the CBD fee.
5. Correlations between DS_z and volume change are empirical associations, not
   causal estimates.
6. Notebook-only tables and figures should be cited as EDA evidence unless they
   are regenerated into durable CSVs.

## 10. Decisions carried into feature engineering

1. Keep HVFHV separate from Yellow Taxi for documentation and modeling until
   each track has complete standalone analysis.
2. Use Feb-Jun 2024 vs Feb-Jun 2025; exclude January 2025.
3. Use reconstructed `passenger_cost_pretip` with the platform-cost caveat.
4. Use `cbd_congestion_fee` as the CBD policy field; do not confuse it with the
   older `congestion_surcharge`.
5. Use DS_z as the primary zone burden metric, with mean and median reported.
6. Use pre-policy 2024 characteristics as controls; do not control for 2025
   post-policy costs, fares, duration, driver pay, trip counts, or volume-change
   fields.
7. Treat provider and shared-ride fields as descriptive regimes/context unless a
   specific model explicitly justifies them.
8. Treat driver pay and duration cautiously because both can be affected by
   post-policy traffic or market conditions.
9. Report HVFHV findings as descriptive/inferential associations, not causal
   proof.
