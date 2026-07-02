# NYC HVFHV CBD Congestion Fee Analysis — Code Package

**Authoritative run documentation:** [`data/processed/disruption_score/README.md`](../../data/processed/disruption_score/README.md) (inputs, outputs, definitions, interpretation warnings).

Run from the repository root, in order:

1. `python scripts/EDA_adithya/01_pipeline.py` — DuckDB pipeline. Reads standardized HVFHV parquet under `data/processed/00_standardized_trips/hvfhv/`, joins `data/taxi_zone_lookup.csv`, computes DS_z and sensitivity outputs, and writes CSVs to `data/processed/disruption_score/`.

2. `python scripts/EDA_adithya/02_zone_lookup_merge.py` — Builds `hvfhv_scatter_data.json` from the pipeline join export (optional; for charts).

3. `python scripts/EDA_adithya/03_manhattan_robustness.py` — Runs within-Manhattan, borough-level, direction-level, and borough-direction robustness checks from the DS_z versus volume-change output.

4. `python scripts/EDA_adithya/04_build_chart.py` — Standalone HTML scatter chart (DS_z vs. trip volume change) from Step 2 output. Pulls Chart.js from a CDN at render time.

See [`docs/methodology_notes.md`](../../docs/methodology_notes.md) for the reasoning behind data-quality and formula decisions.
