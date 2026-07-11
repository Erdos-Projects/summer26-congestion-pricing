# Who Bears the Congestion Price?

Fare Burden and Trip Pattern Shifts in NYC Taxi/FHV Trips

Erdos Institute Data Science Project - Summer 2026

## Team

- Yunpeng Niu
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

Private cars are the policy's main target, so the reported Manhattan traffic
improvement is largely a private-car story. We study the much smaller per-trip
charge on taxi and Uber/Lyft, and ask two linked questions:

1. **Who bears it?** Even though the fee is small and mostly flat, is it felt
   evenly across riders — or is it regressive?
2. **Did it reduce trips?** Did taxi/Uber-Lyft volume fall after the fee, and
   fall more where a zone was more exposed to the charging zone?

## Dataset

The dataset is sourced from
[NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

| Source | Description | Current project use |
|---|---|---|
| Yellow Taxi trips | Monthly trip records with pickup/dropoff times, locations, fares, and surcharges | **Included**; full pipeline — audit, features, burden analysis, Model 1/2, and Model 3 inputs |
| HVFHV trips | High-volume for-hire vehicle trip records | **Included**; full pipeline — audit, features, burden analysis, Model 1/2 (floor + Manhattan robustness, no-June placebo), and Model 3 inputs |
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
under `data/processed/00_standardized_trips/` and are also not committed. A
[downloadable standardized-data package](data/README.md) provides Yellow and HVFHV files for
February-June 2023-2025; 2023 is used only for no-fee placebo comparisons.

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
- `notebooks/` - EDA, feature, burden, and modeling notebooks (goal-based, per service).
- `scripts/` - standardization, QC, feature engineering, and output generation.
- `results/` - exported tables and figures by stage (eda / features / burden_analysis / modeling).
- `presentation/` - executive summary and presentation materials.

## Reproducing The Analysis

### Environment

```bash
conda env create -f environment.yml
conda activate congestion-pricing
```

### Data

The recommended route is to download the 7.3 GB
[standardized-data package](https://drive.google.com/file/d/1lceqcvCE38_g8thraWwVSv_J1t-7Vatp/view?usp=sharing),
verify its SHA-256 checksums, and copy its `00_standardized_trips/` directory to
`data/processed/`. Follow [`data/README.md`](data/README.md) for the safe extraction procedure and
expected folder layout.

To rebuild the standardized files from the public source data instead:

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
| `data/processed/00_standardized_trips/` | Monthly cleaned parquet files by service (`yellow/`, `hvfhv/`) | No; download externally or regenerate locally |
| `data/processed/samples/trip_level_sample.csv` | 100-row balanced CSV for manual inspection | Yes |
| `data/processed/samples/trip_level_sample_20k_representative.csv` | 20,000-row representative CSV for preliminary EDA | Yes |
| `data/processed/samples/trip_level_sample_5k_diagnostic.csv` | Diagnostic CSV for cleaning-rule review | Yes |
| `data/processed/qc/` | Standardization, validation, sample, and diagnostic QC reports | Yes |

See [`docs/data_structure_and_schema.md`](docs/data_structure_and_schema.md) for
the standardized schema and cleaning rules. Samples are for preliminary EDA and
diagnostics; final zone-level claims should use full-data aggregates.

### Notebooks And Results

Analysis is organized goal-by-goal, symmetric across the two services:

| Stage | Notebooks | Results |
|---|---|---|
| EDA | `{service}_full_EDA`, `{service}_sample_EDA` | `results/eda/` |
| Features | `{service}_feature_selection_and_engineering` | `results/features/` |
| Goal 1 — burden ranking | `{service}_burden_ranking_and_heterogeneity` | `results/burden_analysis/` |
| Goal 2 — volume models | `{service}_model1_model2` | `results/modeling/` |
| Cross-vehicle Model 3 | `model3_cross_vehicle` | `results/modeling/` (`cross_vehicle_model3_*`) |

Each main notebook self-exports its tables and figures to the matching `results/` folder. Pipeline
intermediates (DS_z, panels, exposure validation) live under `data/processed/disruption_score/`. The
executive summary is [`presentation/executive_summary.md`](presentation/executive_summary.md); the reader-facing design
and results write-ups are in [`docs/burden_analysis_and_modeling_plan.md`](docs/burden_analysis_and_modeling_plan.md),
[`docs/burden_analysis_and_modeling_results.md`](docs/burden_analysis_and_modeling_results.md), and
[`docs/causal_interpretation_limitations.md`](docs/causal_interpretation_limitations.md).

## Project Status

**Current phase:** final-deliverable preparation — annotated repo, executive
summary, and presentation.

| Area | Status |
|---|---|
| Raw TLC source data | Publicly available from TLC; not redistributed in the repo |
| Standardization, sampling, diagnostic, and validation scripts | Implemented |
| Standardized parquet outputs | Produced and available through the external package; not committed |
| QC and sample outputs | Produced and tracked where small enough |
| Yellow Taxi audit and feature documentation | Complete enough for final-draft use |
| HVFHV audit and feature documentation | Complete enough for final-draft use |
| Burden analysis (both services) | Complete — top-`DS_z` rankings, floor robustness, and borough/trip-length/airport heterogeneity, exported to `results/burden_analysis/` |
| Model 1/2 (both services) | Complete — Model 1 is a descriptive burden-volume association; Model 2 is a negative exposure-gradient estimate with a no-June placebo warning. Exports in `results/modeling/` |
| Model 3 combined Yellow/HVFHV analysis | Complete as exploratory cross-service DiD-style evidence; the primary CRZ gap is negative, but attenuated triple-difference estimates, a large no-fee placebo, and opposite provider splits prevent a clean causal interpretation |
| Green Taxi integration | Deferred |
| Executive summary | Done (`presentation/executive_summary.md`) |
| Slides / video | Deck drafted; video and repo-side reproducibility entry point pending |

Green Taxi integration and January 2025 transition analysis are later
extensions, not blockers for the current deliverables. Model 3 is included as
exploratory triangulation evidence: HVFHV changed about 5.9% more negatively
than Yellow in the primary CRZ sample, but the triple-difference estimates
attenuate, the continuous-exposure confidence interval includes zero, the
2023-2024 placebo produces large nonzero contrasts, and the Uber/Lyft splits
have opposite signs. The HVFHV Model 2 placebo warning and the Model 3
diagnostics both support cautious association language rather than causal
proof.

## Future Work

See [`docs/future directions.md`](docs/future%20directions.md).
