# Who Bears the Congestion Price?

Fare Burden and Trip Pattern Shifts in NYC Taxi/FHV Trips

Erdos Institute Data Science Project - Summer 2026

## Team

- Yunpeng Niu
- Dionel Jaime
- Yue Qiu
- Yiding Tian
- Adithya Sathyanarayana

## Introduction

On January 5, 2025, New York City's Central Business District (CBD)
congestion-pricing fee went into effect. Policy surcharge amounts (current **analysis scope:** Yellow Taxi and HVFHV only):

- **Yellow taxis:** $0.75 surcharge for qualifying trips.
- **Green taxis:** same $0.75 surcharge, but Green Taxi trip records are
  **deferred** in this project (see Dataset table below).
- **High-volume for-hire vehicles (HVFHV):** $1.50 per trip to, from, or within
  the Congestion Relief Zone, e.g. large app fleets such as Uber/Lyft.
- **Other FHV:** not used in the current analysis scope.

This project studies how the fee is associated with rider fare burden and trip
pattern shifts across TLC zones. It is an **inference-focused descriptive
analysis**, not a future-demand prediction task. Reported relationships should
be read as associations unless a specific model and robustness check support a
stronger interpretation.

### Research Questions

- How did trip volumes and fare patterns change across TLC zones after the
  congestion fee took effect?
- Which zones show the largest fee burden relative to trip cost?
- Are higher-burden or higher-exposure zones associated with different
  post-policy trip-volume changes?
- Do Yellow Taxi and HVFHV patterns differ enough to motivate later combined
  analysis?

## Dataset

The dataset is sourced from
[NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

| Source | Description | Current project use |
|---|---|---|
| Yellow Taxi trips | Monthly trip records with pickup/dropoff times, locations, fares, and surcharges | **Included**; audit, feature documentation, DS_z outputs, and first-pass Model 1/2 work exist |
| HVFHV trips | High-volume for-hire vehicle trip records | **Included**; audit, feature documentation, full-data DS_z outputs, Model 1/2 notebook, floor sensitivity, Manhattan robustness, and no-June placebo diagnostic exist |
| Green Taxi trips | Boro taxi trip records | Deferred for later robustness checks |
| FHV trips | Smaller for-hire vehicle records | Not used in current scope |
| TLC taxi zone lookup | Zone IDs and geographic definitions | Used for zone-level outputs and robustness summaries |

### Study Window

- **Primary comparison:** February-June **2024** (pre-policy) vs.
  February-June **2025** (post-policy).
- **Transition month:** January 2025 is excluded because the fee began on
  January 5, 2025.
- **Geography:** TLC zone x direction, with pickup and dropoff sides analyzed
  separately for zone disruption metrics.

Raw TLC parquet files are stored locally under `data/raw/` by year and month
and are not committed due to size. Standardized parquet files are generated
under `data/processed/00_standardized_trips/` and are also not committed.

### Passenger Cost Definitions

| Service | `passenger_cost_pretip` |
|---|---|
| Yellow Taxi | `total_amount - tip_amount` |
| HVFHV | `base_passenger_fare + tolls + bcf + sales_tax + congestion_surcharge + airport_fee + cbd_congestion_fee` |

HVFHV passenger cost is reconstructed from TLC components and may miss
platform-specific discounts, refunds, credits, or user-specific app pricing.

## Key Performance Indicators

KPIs are tracked in [`kpis.md`](kpis.md). Current metrics emphasize burden,
volume change, exposure, cost, and robustness rather than predictive accuracy.

| KPI | Role |
|---|---|
| Zone disruption score (`DS_z`) | Zone-by-direction fee burden among charged trips |
| Relative CBD burden | Fee share of current pre-tip passenger cost |
| Trip volume change | Feb-Jun 2025 vs. Feb-Jun 2024 trip-count change |
| Charged share / geographic exposure | Treatment exposure for descriptive summaries and possible DiD |
| Average pre-tip passenger cost | Rider-facing cost trend, with service-specific caveats |
| Distance/time controls | Pre-policy trip-shape controls and EDA context |
| Robustness metrics | Floor sensitivity, rank stability, and Manhattan-only correlations |

## Current Analysis Docs

- Yellow Taxi audit: [`docs/yellow_data_audit.md`](docs/yellow_data_audit.md)
- Yellow Taxi feature decisions:
  [`docs/yellow_dropped_and_engineered_features.md`](docs/yellow_dropped_and_engineered_features.md)
- HVFHV audit: [`docs/hvfhv_data_audit.md`](docs/hvfhv_data_audit.md)
- HVFHV feature decisions:
  [`docs/hvfhv_dropped_and_engineered_features.md`](docs/hvfhv_dropped_and_engineered_features.md)
- Burden analysis and modeling plan:
  [`docs/burden_analysis_and_modeling_plan.md`](docs/burden_analysis_and_modeling_plan.md)
- Evaluation plan: [`docs/evaluation_plan.md`](docs/evaluation_plan.md)
- HVFHV DS_z outputs guide:
  [`data/processed/disruption_score/README.md`](data/processed/disruption_score/README.md)

## Deliverables

Intended deliverables include:

- `README.md` - project description, current state, and reproduction notes.
- `kpis.md` - KPI definitions and status.
- `docs/` - audit, feature-selection, modeling, and evaluation documentation.
- `notebooks/` - exploratory and first-pass modeling notebooks.
- `scripts/` - standardization, QC, feature engineering, and output generation.
- `presentation/` - stakeholder summary materials.

## Reproducing The Analysis

### Environment

```bash
conda env create -f environment.yml
conda activate congestion-pricing
```

### Data

1. Download monthly TLC trip record files from the
   [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
   page.
2. Place raw parquet files in `data/raw/{year}/{Month}/`, for example
   `data/raw/2024/Feb/yellow_tripdata_2024-02.parquet`.
3. Run first-step standardization and sample/QC scripts:

```bash
python scripts/standardize_trips.py
python scripts/make_trip_level_sample.py
python scripts/make_representative_sample_20k.py
python scripts/create_diagnostic_sample.py
python scripts/validate_standardized_trips.py
```

Outputs:

| Output | Description | Committed to git? |
|---|---|---|
| `data/processed/00_standardized_trips/` | Monthly cleaned parquet files by service (`yellow/`, `hvfhv/`) | No, too large; regenerate locally |
| `data/processed/samples/trip_level_sample.csv` | 100-row balanced CSV for manual inspection | Yes |
| `data/processed/samples/trip_level_sample_20k_representative.csv` | 20,000-row representative CSV for preliminary EDA | Yes |
| `data/processed/samples/trip_level_sample_5k_diagnostic.csv` | Diagnostic CSV for cleaning-rule review | Yes |
| `data/processed/qc/` | Standardization, validation, sample, and diagnostic QC reports | Yes |

See [`docs/data_structure_and_schema.md`](docs/data_structure_and_schema.md) for
the standardized schema and cleaning rules. Samples are for preliminary EDA and
diagnostics; final zone-level claims should use full-data aggregates.

### Analysis Outputs

Tracked disruption-score outputs live under `data/processed/disruption_score/`.
HVFHV outputs include DS_z, behavioral-shift joins, denominator-floor
sensitivity, rank stability, top-zone overlap, borough correlations, and
Manhattan robustness. HVFHV Model 1 and Model 2 are summarized in
`notebooks/hvfhv_model1_model2.ipynb`; Model 2 is estimated under assumptions
and has a no-June 2023-vs-2024 placebo warning. Yellow outputs include DS_z,
behavioral-shift joins, floor sensitivity, rank stability, geographic-charge
validation, and a monthly panel used in first-pass Model 1/2 work.

## Project Status

**Current phase:** checkpoint documentation, first-pass modeling, and
final-deliverable preparation.

| Area | Status |
|---|---|
| Raw data download, Feb-Jun 2024 and 2025 Yellow + HVFHV | Complete locally |
| Standardization, sampling, diagnostic, and validation scripts | Implemented |
| Standardized parquet outputs | Produced locally; not committed |
| QC and sample outputs | Produced and tracked where small enough |
| Yellow Taxi audit and feature documentation | Complete enough for final-draft use |
| HVFHV audit and feature documentation | Complete enough for final-draft use |
| HVFHV DS_z outputs | Produced, including floor sensitivity, rank stability, top-zone overlap, borough correlations, and Manhattan robustness |
| HVFHV Model 1/2 notebook | Produced; Model 1 shows a strong descriptive burden-volume association, while Model 2 is a negative exposure-gradient estimate with a placebo warning |
| Yellow Taxi DS_z and Model 1/2 first pass | Outputs and notebook exist; report as first-pass/inferential, not causal proof |
| Model 3 combined Yellow/HVFHV analysis | Deferred until separate Yellow and HVFHV analyses are complete |
| Green Taxi integration | Deferred |
| Final slides/video/report | Pending |

Green Taxi integration, January 2025 transition analysis, and combined
Yellow/HVFHV Model 3 are later robustness or extension work, not blockers for
the current separate-service deliverables. The HVFHV no-June 2023-vs-2024
placebo diagnostic is complete and weakens a clean causal reading of Model 2,
so final HVFHV claims should emphasize association and burden ranking.

## Future Work

See [`docs/future directions.md`](docs/future%20directions.md).
