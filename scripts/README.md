# NYC HVFHV CBD Congestion Fee Analysis - Code Package

**Authoritative run documentation:** [`data/processed/disruption_score/README.md`](../../data/processed/disruption_score/README.md) (inputs, outputs, definitions, interpretation warnings).

Run from the repository root, in order:

1. `python scripts/01_pipeline.py` - DuckDB pipeline. Reads standardized HVFHV parquet under `data/processed/00_standardized_trips/hvfhv/`, joins `data/taxi_zone_lookup.csv`, computes DS_z and sensitivity outputs, and writes CSVs to `data/processed/disruption_score/`.

2. `python scripts/02_zone_lookup_merge.py` - Builds `hvfhv_scatter_data.json` from the pipeline join export (optional; for charts).

3. `python scripts/03_manhattan_robustness.py` - Runs within-Manhattan, borough-level, direction-level, and borough-direction robustness checks from the DS_z versus volume-change output.

4. `python scripts/04_build_chart.py` - Standalone HTML scatter chart (DS_z vs. trip volume change) from Step 2 output. Pulls Chart.js from a CDN at render time.

5. `python scripts/04_model1_feature_table.py` - Builds the small HVFHV Model 1 zone feature table.

6. `python scripts/hvfhv_model2_monthly_panel.py` - Builds the small HVFHV Model 2 monthly panel and exposure validation outputs.

7. `python scripts/hvfhv_pretrend_placebo.py` - Builds the no-June HVFHV pretrend and placebo diagnostics.

See [`docs/methodology_notes.md`](../../docs/methodology_notes.md) for the reasoning behind data-quality and formula decisions.
