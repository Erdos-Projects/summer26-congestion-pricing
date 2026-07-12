#!/usr/bin/env bash
# run.sh — regenerate the full analysis end to end: standardized trips -> DS_z pipelines and
# modeling panels -> notebooks -> results/, then the presentation summary notebook.
#
# ============================================================================================
# DATA ROUTES — read before running
# ============================================================================================
# The notebooks and pipelines read standardized parquet from
#   data/processed/00_standardized_trips/{yellow,hvfhv}/
# You can get that directory in one of two ways. Pick ONE.
#
#   Route A — use the processed data package (recommended, no raw download).
#     Download the standardized-data package and copy its 00_standardized_trips/ directory
#     into data/processed/ (see data/README.md for the link and checksums), then run:
#         ./run.sh
#
#   Route B — rebuild from raw public TLC files.
#     Download monthly TLC parquet into data/raw/{year}/{Month}/ (Yellow + HVFHV, the
#     study windows in README.md), then run with STANDARDIZE=1 so step 0 rebuilds the
#     standardized parquet from raw before the pipelines:
#         STANDARDIZE=1 ./run.sh
#
# Either route reproduces the analysis tables and figures under results/, including the figures
# used in the presentation deck. It does not rebuild the PowerPoint or PDF deck itself:
#   EDA (slide 5)     results/eda/figures/yellow_full_charged_vs_uncharged.png
#                     results/eda/figures/yellow_full_burden_by_distance.png
#                     results/eda/figures/hvfhv_full_distance_exposure_2025.png
#   Burden (slide 7)  results/burden_analysis/figures/yellow_dsz_choropleth.png
#                     results/burden_analysis/figures/hvfhv_dsz_choropleth.png
#   Volume (slide 9)  results/modeling/figures/hvfhv_model1_dsz_vs_volume.png
# and re-runs notebooks/final_results.ipynb, which collects the presentation numbers and
# figures into results/final/.
#
# Prerequisites:  conda env create -f environment.yml && conda activate congestion-pricing
# Notes: the full-data notebooks read tens of millions of trips; run on a machine with enough
# memory. Override the interpreter with e.g.  PYTHON=/path/to/python ./run.sh
# ============================================================================================

set -euo pipefail
cd "$(dirname "$0")"                        # repo root
PYTHON="${PYTHON:-python}"
STANDARDIZE="${STANDARDIZE:-0}"
export MPLBACKEND="${MPLBACKEND:-Agg}"

# --- [0/4] Route B only: rebuild standardized parquet from raw TLC files ---
if [ "$STANDARDIZE" = "1" ]; then
  echo "==> [0/4] Standardizing raw TLC parquet (STANDARDIZE=1)"
  "$PYTHON" scripts/standardize_trips.py
fi

if [ ! -d data/processed/00_standardized_trips/yellow ] || [ ! -d data/processed/00_standardized_trips/hvfhv ]; then
  echo "ERROR: standardized parquet not found under data/processed/00_standardized_trips/." >&2
  echo "       Route A: download the data package (data/README.md) and copy 00_standardized_trips/ in." >&2
  echo "       Route B: place raw TLC files under data/raw/ and re-run with STANDARDIZE=1." >&2
  exit 1
fi

echo "==> [1/4] DS_z pipelines and modeling panels"
"$PYTHON" scripts/yellow_ds_pipeline.py              # Yellow DS_z, exposure, monthly panel
"$PYTHON" scripts/build_yellow_2023_placebo_panel.py # Yellow Model-2 placebo panel (2023->2024)
"$PYTHON" scripts/01_pipeline.py                     # HVFHV DS_z and sensitivity outputs
"$PYTHON" scripts/02_zone_lookup_merge.py            # HVFHV chart input
"$PYTHON" scripts/04_build_chart.py                  # Standalone HVFHV HTML bubble chart
"$PYTHON" scripts/03_manhattan_robustness.py         # HVFHV within-Manhattan / borough robustness
"$PYTHON" scripts/04_model1_feature_table.py         # HVFHV Model-1 zone feature table
"$PYTHON" scripts/hvfhv_model2_monthly_panel.py      # HVFHV Model-2 panel + exposure validation
"$PYTHON" scripts/hvfhv_pretrend_placebo.py          # HVFHV no-June pretrend + 2023->2024 placebo
"$PYTHON" scripts/build_m3_panel.py                  # Cross-vehicle Model-3 panel
"$PYTHON" scripts/build_m3_panel.py --placebo        # Cross-vehicle Model-3 placebo panel

echo "==> [2/4] Notebooks (each self-exports its tables and figures to results/)"
NB=("$PYTHON" "-m" "jupyter" "nbconvert" "--to" "notebook" "--execute" "--inplace"
    "--ExecutePreprocessor.kernel_name=python3" "--ExecutePreprocessor.timeout=3600")
for nb in \
  notebooks/yellow_taxi_full_EDA.ipynb \
  notebooks/hvfhv_full_EDA.ipynb \
  notebooks/yellow_feature_selection_and_engineering.ipynb \
  notebooks/hvfhv_feature_selection_and_engineering.ipynb \
  notebooks/yellow_burden_ranking_and_heterogeneity.ipynb \
  notebooks/hvfhv_burden_ranking_and_heterogeneity.ipynb \
  notebooks/yellow_model1_model2.ipynb \
  notebooks/hvfhv_model1_model2.ipynb \
  notebooks/model3_cross_vehicle.ipynb ; do
  echo "    - $nb"
  "${NB[@]}" "$nb"
done

# Reapply the shared HTML-style bubble-chart renderer so both service figures use identical styling.
"$PYTHON" scripts/model1_bubble_chart.py

echo "==> [3/4] Presentation summary notebook (reads results/, writes results/final/)"
"${NB[@]}" notebooks/final_results.ipynb

echo "==> [4/4] Done. Regenerated results/ and results/final/ (see results/README.md)."
