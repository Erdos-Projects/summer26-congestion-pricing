# Who Bears the Congestion Price?

Fare burden and trip-pattern shifts in NYC taxi and Uber/Lyft trips under the 2025 CBD congestion fee.

*Erdős Institute Data Science Project — Summer 2026*

## Team

- Yunpeng Niu
- Yue Qiu
- Yiding Tian
- Adithya Sathyanarayana

## TL;DR

On **January 5, 2025**, New York became the first US city to charge vehicles for entering a defined
zone — the Manhattan Central Business District south of 60th Street. Using **~37M Yellow taxi and
~202M Uber/Lyft** public TLC trips (February–June 2024 vs. the same months of 2025), we ask **who
bears this fee** and **whether it reduced trips**.

- **The burden is uneven, and the finding is stable.** A flat per-trip fee is a much larger share of
  short, low-cost trips (concentrated in the dense Manhattan core) than of long airport trips. The
  zone ranking holds across every robustness check — a reusable, reproducible burden metric (`DS_z`).
- **A causal volume effect is not cleanly identifiable.** Three regression-with-controls designs each
  find a negative signal, but each fails a no-fee placebo test — so we report an **association, not a
  causal effect**.

**Start here → [`presentation/executive_summary.md`](presentation/executive_summary.md)** (one-page
summary). Detailed write-ups are in [`docs/`](docs/).

## Background & Research Questions

The congestion fee depends on the vehicle: **private cars pay \$9/day**, every **taxi** ride pays
**\$0.75**, and every **Uber/Lyft** ride pays **\$1.50**. Manhattan traffic was reported to be lighter
afterward — but given the fee structure, private cars are the main target, so that improvement is
largely a *private-car* story. We instead study the much smaller per-trip charge on **taxi and
Uber/Lyft**, and ask two linked questions:

1. **Who bears it?** Even though the fee is small and mostly flat, is it felt evenly across riders, or
   does it weigh more heavily on some trips than others?
2. **Did it reduce trips?** Did taxi/Uber-Lyft volume fall after the fee, and fall more where a zone
   was more exposed to the charging zone?

This is an **inference-focused, descriptive analysis**, not a demand-prediction task. Reported
relationships are associations unless a specific design and robustness check support a stronger claim.

## Data & Scope

- **Source:** public [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
- **Scope:** **Yellow Taxi and HVFHV (Uber/Lyft) only.** Green Taxi and other FHV are outside the
  scope of this project.
- **Window:** February–June **2024** (pre-policy) vs. February–June **2025** (post-policy); the same
  months are compared so seasonality cancels, and **January 2025 is excluded** as a transition month.
  (February–June **2023** is used only as a no-fee placebo comparison.)
- **Unit of analysis:** **zone × direction** — each TLC zone is scored separately on its pickup and
  dropoff side, because a zone can behave differently depending on whether trips start or end there.
- **Services analyzed separately:** Yellow and HVFHV cost fields are constructed differently, and
  Yellow has a Flex-fare regime shift that distorts its raw volume, so the two markets are not pooled.

| Service | `passenger_cost_pretip` |
|---|---|
| Yellow Taxi | `total_amount - tip_amount` |
| HVFHV | `base_passenger_fare + tolls + bcf + sales_tax + congestion_surcharge + airport_fee + cbd_congestion_fee` (reconstructed from TLC components; may miss app-side discounts/refunds/credits) |

## What We Did

- **Burden metric — the Zone Disruption Score, `DS_z`:** for each charged trip, the CBD fee as a
  share of what the trip would otherwise cost, averaged by zone × direction. It ranks where the fee is
  a large share of the fare. Robustness is checked across denominator-floor and mean/median choices.
- **Volume — an evidence ladder of three regressions with controls**, each fixing the previous one's
  weakness and each stress-tested against a no-fee (2023→2024) placebo year:
  - **Model 1:** cross-zone burden ↔ volume-change association.
  - **Model 2:** difference-in-differences on pre-policy CRZ exposure.
  - **Model 3:** cross-vehicle difference-in-differences (Yellow vs. Uber/Lyft in the same zones).

KPIs are defined in [`kpis.md`](kpis.md); the full design and evaluation plan are in
[`docs/burden_analysis_and_modeling_plan.md`](docs/burden_analysis_and_modeling_plan.md) and
[`docs/evaluation_plan.md`](docs/evaluation_plan.md).

## Findings

- **Burden (clear).** The fee is a much larger share of short, low-cost trips; highest-burden
  zone-sides are the dense Manhattan core for both services, and airport trips carry far less. The
  ranking is stable across all robustness checks.
- **Volume (cautious).** Every model produces a negative signal, and every model fails a test it
  should pass (coefficients flip with controls; a no-fee year still shows a large negative estimate;
  Uber and Lyft move in opposite directions under the identical fee). We therefore report the volume
  evidence as an association, not a causal effect — an informative result, since the small per-trip
  fee makes a hard-to-detect response plausible, and the bottleneck is identification, not model
  complexity.

Numbers and figures: [`presentation/executive_summary.md`](presentation/executive_summary.md),
[`docs/burden_analysis_and_modeling_results.md`](docs/burden_analysis_and_modeling_results.md), and
the exported tables/figures under [`results/`](results/).

## Repository Structure

```text
├── presentation/          Executive summary (start here) + presentation figures
├── notebooks/             Analysis notebooks, goal-based and symmetric per service:
│     {service}_full_EDA / _sample_EDA                    exploratory data analysis
│     {service}_feature_selection_and_engineering         feature decisions
│     {service}_burden_ranking_and_heterogeneity          Goal 1 — burden ranking
│     {service}_model1_model2                             Goal 2 — volume models 1 & 2
│     model3_cross_vehicle                                cross-vehicle Model 3
├── scripts/               Standardization, DS_z pipelines, panel builders, QC/sampling
├── src/                   Reusable helpers and feature notes
├── data/                  Raw (not committed) + processed/ (standardized trips, DS_z, panels)
├── results/               Exported outputs by stage: eda / features / burden_analysis / modeling
├── docs/                  Data audits, feature decisions, modeling plan, results, limitations
├── kpis.md                KPI definitions
└── environment.yml        Conda environment
```

Each main notebook self-exports its tables and figures to the matching `results/` folder; pipeline
intermediates (DS_z, monthly panels, exposure validation) live under
`data/processed/disruption_score/`.

## Reproducing the Analysis

**Environment**

```bash
conda env create -f environment.yml
conda activate congestion-pricing
```

**Data.** The standardized parquet files are large and not committed. The recommended route is to
download the standardized-data package
([Google Drive, ~7.3 GB](https://drive.google.com/file/d/1lceqcvCE38_g8thraWwVSv_J1t-7Vatp/view?usp=sharing)),
verify its checksums, and copy its `00_standardized_trips/` directory into `data/processed/`. See
[`data/README.md`](data/README.md) for the exact layout and safe extraction steps.

**Regenerate all results.** With the environment active and the standardized parquet in place, one
command reruns the DS_z pipelines and every notebook, rewriting all tables and figures under
`results/` (including the figures used in the presentation):

```bash
./run.sh
```

To rebuild the standardized files from the public source instead: download monthly TLC parquet files
into `data/raw/{year}/{Month}/`, then run the standardization and pipeline scripts:

```bash
python scripts/standardize_trips.py          # raw → standardized parquet
python scripts/yellow_ds_pipeline.py         # Yellow DS_z, exposure, monthly panel
python scripts/01_pipeline.py                # HVFHV DS_z and outputs
python scripts/build_m3_panel.py             # cross-vehicle Model 3 panel
```

Then run the notebooks (each writes its outputs to `results/`). Data structure and cleaning rules are
documented in [`docs/data_structure_and_schema.md`](docs/data_structure_and_schema.md).

## Documentation

- **Data:** [`docs/data_structure_and_schema.md`](docs/data_structure_and_schema.md),
  [`docs/cleaning_notes.md`](docs/cleaning_notes.md),
  [`docs/yellow_data_audit.md`](docs/yellow_data_audit.md),
  [`docs/hvfhv_data_audit.md`](docs/hvfhv_data_audit.md).
- **Features:** [`docs/yellow_dropped_and_engineered_features.md`](docs/yellow_dropped_and_engineered_features.md),
  [`docs/hvfhv_dropped_and_engineered_features.md`](docs/hvfhv_dropped_and_engineered_features.md),
  [`docs/feature_leakage_and_post_policy_controls.md`](docs/feature_leakage_and_post_policy_controls.md).
- **EDA:** [`docs/eda_summary.md`](docs/eda_summary.md).
- **Design, evaluation, results:** [`docs/burden_analysis_and_modeling_plan.md`](docs/burden_analysis_and_modeling_plan.md),
  [`docs/evaluation_plan.md`](docs/evaluation_plan.md),
  [`docs/burden_analysis_and_modeling_results.md`](docs/burden_analysis_and_modeling_results.md).

## Limitations & Future Work

The volume conclusion is deliberately cautious: TLC data show only completed trips (not
mode-switching, cancellations, or trips that never happened), high-burden zones are not random (they
are the dense Manhattan core), and the difference-in-differences designs are weakened by no-fee
placebo checks. The full discussion is in
[`docs/causal_interpretation_limitations.md`](docs/causal_interpretation_limitations.md), and
directions for a stronger evaluation are in [`docs/future directions.md`](docs/future%20directions.md).
