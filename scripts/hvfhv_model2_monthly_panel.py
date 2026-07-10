"""
Build the HVFHV Model 2 monthly exposure-gradient panel.

This script creates a zone-direction-month-year panel for the HVFHV Model 2
design. The treatment exposure is geography-based and computed from 2024 only:
the share of pre-policy trips in a zone-direction cell whose pickup or dropoff
touched the Congestion Relief Zone (CRZ).

Run from the repository root:
    python scripts/hvfhv_model2_monthly_panel.py

Outputs:
    data/processed/disruption_score/hvfhv_monthly_panel.csv
    data/processed/disruption_score/hvfhv_model2_exposure_validation.csv
    data/processed/disruption_score/hvfhv_model2_panel_notes.md
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARDIZED_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips" / "hvfhv"
INPUT_2024_DIR = STANDARDIZED_DIR / "2024"
INPUT_2025_DIR = STANDARDIZED_DIR / "2025"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"

PANEL_OUTPUT_PATH = OUTPUT_DIR / "hvfhv_monthly_panel.csv"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "hvfhv_model2_exposure_validation.csv"
NOTES_OUTPUT_PATH = OUTPUT_DIR / "hvfhv_model2_panel_notes.md"

EXPECTED_MONTHS = ("02", "03", "04", "05", "06")

# Source: scripts/yellow_ds_pipeline.py. CRZ = Congestion Relief Zone
# (Manhattan south of 60th St), 38 data-driven TLC LocationIDs.
CRZ_ZONE_IDS = (
    4,
    12,
    13,
    45,
    48,
    50,
    68,
    79,
    87,
    88,
    90,
    100,
    107,
    113,
    114,
    125,
    137,
    144,
    148,
    158,
    161,
    162,
    163,
    164,
    170,
    186,
    209,
    211,
    224,
    229,
    230,
    231,
    232,
    233,
    234,
    246,
    249,
    261,
)
CRZ_SQL = "(" + ", ".join(str(zone_id) for zone_id in CRZ_ZONE_IDS) + ")"


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _sql_path_list(paths: list[Path]) -> str:
    return "[" + ", ".join(f"'{_sql_path(path)}'" for path in paths) + "]"


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _discover_monthly_inputs(input_dir: Path, year: int) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Missing input directory: {input_dir}")

    files = sorted(input_dir.glob("*.parquet"))
    found_months = {path.stem for path in files}
    expected = set(EXPECTED_MONTHS)
    missing = sorted(expected - found_months)
    extra = sorted(found_months - expected)
    if missing:
        raise FileNotFoundError(
            f"Missing {year} HVFHV parquet month files under {input_dir}: {missing}"
        )
    if extra:
        print(f"Warning: ignoring unexpected {year} parquet month files: {extra}")

    return [input_dir / f"{month}.parquet" for month in EXPECTED_MONTHS]


def _copy_csv(con: duckdb.DuckDBPyConnection, query: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({query}) TO '{_sql_path(output_path)}' (HEADER, DELIMITER ',')")


def _format_int(value: object) -> str:
    if pd.isna(value):
        return "NA"
    return f"{int(value):,}"


def _format_float(value: object, digits: int = 4) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def _write_notes(panel: pd.DataFrame, validation: pd.DataFrame, files_2024: list[Path], files_2025: list[Path]) -> None:
    overall = validation[validation["validation_level"].eq("overall")].iloc[0]
    month_rows = validation[validation["validation_level"].eq("month")].copy()

    missing_exposure_rows = int(panel["charged_share_2024_geo"].isna().sum())
    low_n_rows = int((panel["n_trips"] < 30).sum())
    balanced_units = int(
        panel.groupby(["zone", "direction"]).size().loc[lambda s: s.eq(10)].shape[0]
    )

    lines = [
        "# HVFHV Model 2 Monthly Panel Notes",
        "",
        "## Inputs",
        "",
        f"- 2024 standardized HVFHV parquets: {len(files_2024)} files under `{_relative(INPUT_2024_DIR)}`.",
        f"- 2025 standardized HVFHV parquets: {len(files_2025)} files under `{_relative(INPUT_2025_DIR)}`.",
        f"- Zone lookup: `{_relative(ZONE_LOOKUP_PATH)}`.",
        "",
        "## CRZ Zone Source",
        "",
        "- Reused `CRZ_ZONE_IDS` from `scripts/yellow_ds_pipeline.py`.",
        "- Definition in that script: Congestion Relief Zone, Manhattan south of 60th St, 38 TLC LocationIDs.",
        f"- CRZ zone count: {len(CRZ_ZONE_IDS)}.",
        "",
        "## Panel Construction",
        "",
        "- Unit: zone x direction x year x month.",
        "- Directions are constructed separately from pickup and dropoff zones.",
        "- Main exposure is `charged_share_2024_geo`: the 2024 share of trips in the zone-direction cell whose pickup or dropoff touched the CRZ by geography.",
        "- `charged_share_2024_geo` is attached to both 2024 and 2025 rows.",
        "- `charged_cbd_flag` is not used to create the main exposure.",
        "- No Model 2 regression is run here.",
        "",
        "## Output Summary",
        "",
        f"- Panel rows: {len(panel):,}.",
        f"- Zone-direction units: {panel[['zone', 'direction']].drop_duplicates().shape[0]:,}.",
        f"- Balanced 10-month zone-direction units: {balanced_units:,}.",
        f"- Rows with missing `charged_share_2024_geo`: {missing_exposure_rows:,}.",
        f"- Rows with `n_trips < 30`: {low_n_rows:,}.",
        "",
        "## Exposure Validation Against 2025 Observed Fee Flag",
        "",
        "- Validation uses 2025 `charged_cbd_flag` only as a diagnostic.",
        f"- Overall 2025 trips checked: {_format_int(overall['n_trips_2025'])}.",
        f"- Match rate: {_format_float(overall['match_rate'])}.",
        f"- False positives, geography exposed but not observed charged: {_format_int(overall['false_positives_geo_not_charged'])}.",
        f"- False negatives, observed charged but not geography exposed: {_format_int(overall['false_negatives_charged_not_geo'])}.",
        f"- Share of observed charged trips missed by geography-only exposure: {_format_float(overall['share_observed_charged_missed_by_geo'])}.",
        f"- Geography precision: {_format_float(overall['geography_precision'])}.",
        f"- Geography recall: {_format_float(overall['geography_recall'])}.",
        "",
        "Monthly validation:",
        "",
        "| month | n_trips_2025 | match_rate | false_positives | false_negatives | missed_observed_charged_share |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in month_rows.itertuples(index=False):
        lines.append(
            f"| {int(row.month)} | {_format_int(row.n_trips_2025)} | "
            f"{_format_float(row.match_rate)} | "
            f"{_format_int(row.false_positives_geo_not_charged)} | "
            f"{_format_int(row.false_negatives_charged_not_geo)} | "
            f"{_format_float(row.share_observed_charged_missed_by_geo)} |"
        )

    lines.extend(
        [
            "",
            "## Leakage Notes",
            "",
            "- Use `charged_share_2024_geo` as the Model 2 exposure.",
            "- Do not use 2025 observed charged shares as the treatment in the Model 2 regression.",
            "- Do not use 2025 cost, fare, duration, driver pay, or volume-change fields as controls.",
            "- This panel is for HVFHV Model 2 only; Model 3 uses a separate cross-vehicle panel.",
            "",
        ]
    )

    NOTES_OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def build_panel() -> None:
    files_2024 = _discover_monthly_inputs(INPUT_2024_DIR, 2024)
    files_2025 = _discover_monthly_inputs(INPUT_2025_DIR, 2025)
    if not ZONE_LOOKUP_PATH.exists():
        raise FileNotFoundError(f"Missing zone lookup file: {ZONE_LOOKUP_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads TO 1")

    print("Input files:")
    print(f"  2024 HVFHV parquet files: {len(files_2024)} from {INPUT_2024_DIR}")
    print(f"  2025 HVFHV parquet files: {len(files_2025)} from {INPUT_2025_DIR}")
    print(f"  CRZ source: scripts/yellow_ds_pipeline.py ({len(CRZ_ZONE_IDS)} zones)")
    print(f"  Outputs: {OUTPUT_DIR}")

    con.execute(
        f"""
        CREATE OR REPLACE VIEW trips AS
        SELECT * FROM read_parquet({_sql_path_list(files_2024 + files_2025)})
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW zone_lookup AS
        SELECT
            CAST(LocationID AS BIGINT) AS LocationID,
            COALESCE(NULLIF(NULLIF(Borough, ''), 'N/A'), 'Unknown') AS Borough,
            COALESCE(NULLIF(NULLIF(Zone, ''), 'N/A'), 'Unknown Zone ' || CAST(LocationID AS VARCHAR)) AS Zone,
            COALESCE(NULLIF(NULLIF(service_zone, ''), 'N/A'), 'Unknown Service Zone') AS service_zone
        FROM read_csv_auto('{_sql_path(ZONE_LOOKUP_PATH)}')
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE exposure_2024 AS
        WITH trips_2024 AS (
            SELECT
                PULocationID,
                DOLocationID,
                (PULocationID IN {CRZ_SQL} OR DOLocationID IN {CRZ_SQL}) AS geography_exposed
            FROM trips
            WHERE year = 2024
        ),
        pickup AS (
            SELECT
                PULocationID AS zone,
                'pickup' AS direction,
                ROUND(AVG(geography_exposed::INT), 4) AS charged_share_2024_geo
            FROM trips_2024
            GROUP BY PULocationID
        ),
        dropoff AS (
            SELECT
                DOLocationID AS zone,
                'dropoff' AS direction,
                ROUND(AVG(geography_exposed::INT), 4) AS charged_share_2024_geo
            FROM trips_2024
            GROUP BY DOLocationID
        )
        SELECT * FROM pickup
        UNION ALL
        SELECT * FROM dropoff
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE monthly_panel AS
        WITH pickup AS (
            SELECT
                PULocationID AS zone,
                'pickup' AS direction,
                year,
                month,
                COUNT(*) AS n_trips
            FROM trips
            GROUP BY PULocationID, year, month
        ),
        dropoff AS (
            SELECT
                DOLocationID AS zone,
                'dropoff' AS direction,
                year,
                month,
                COUNT(*) AS n_trips
            FROM trips
            GROUP BY DOLocationID, year, month
        ),
        panel AS (
            SELECT * FROM pickup
            UNION ALL
            SELECT * FROM dropoff
        )
        SELECT
            CAST(p.zone AS BIGINT) AS zone,
            p.direction,
            CAST(p.year AS BIGINT) AS year,
            CAST(p.month AS BIGINT) AS month,
            CAST(p.n_trips AS BIGINT) AS n_trips,
            LN(p.n_trips) AS log_n_trips,
            CASE WHEN p.year = 2025 THEN 1 ELSE 0 END AS post,
            z.Borough,
            COALESCE(z.Zone, 'Zone ' || CAST(p.zone AS VARCHAR)) AS zone_name,
            z.service_zone,
            (p.zone IN {CRZ_SQL}) AS crz_zone,
            e.charged_share_2024_geo
        FROM panel p
        LEFT JOIN zone_lookup z ON p.zone = z.LocationID
        LEFT JOIN exposure_2024 e ON p.zone = e.zone AND p.direction = e.direction
        ORDER BY p.zone, p.direction, p.year, p.month
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE exposure_validation AS
        WITH validation_base AS (
            SELECT
                year,
                month,
                charged_cbd_flag AS observed_charged,
                (PULocationID IN {CRZ_SQL} OR DOLocationID IN {CRZ_SQL}) AS geography_exposed
            FROM trips
            WHERE year = 2025
        ),
        grouped AS (
            SELECT
                'month' AS validation_level,
                CAST(month AS BIGINT) AS month,
                COUNT(*) AS n_trips_2025,
                SUM(CASE WHEN observed_charged THEN 1 ELSE 0 END) AS observed_charged_trips,
                SUM(CASE WHEN geography_exposed THEN 1 ELSE 0 END) AS geography_exposed_trips,
                SUM(CASE WHEN geography_exposed AND observed_charged THEN 1 ELSE 0 END) AS true_positives,
                SUM(CASE WHEN geography_exposed AND NOT observed_charged THEN 1 ELSE 0 END) AS false_positives_geo_not_charged,
                SUM(CASE WHEN NOT geography_exposed AND observed_charged THEN 1 ELSE 0 END) AS false_negatives_charged_not_geo,
                SUM(CASE WHEN NOT geography_exposed AND NOT observed_charged THEN 1 ELSE 0 END) AS true_negatives
            FROM validation_base
            GROUP BY month
            UNION ALL
            SELECT
                'overall' AS validation_level,
                NULL AS month,
                COUNT(*) AS n_trips_2025,
                SUM(CASE WHEN observed_charged THEN 1 ELSE 0 END) AS observed_charged_trips,
                SUM(CASE WHEN geography_exposed THEN 1 ELSE 0 END) AS geography_exposed_trips,
                SUM(CASE WHEN geography_exposed AND observed_charged THEN 1 ELSE 0 END) AS true_positives,
                SUM(CASE WHEN geography_exposed AND NOT observed_charged THEN 1 ELSE 0 END) AS false_positives_geo_not_charged,
                SUM(CASE WHEN NOT geography_exposed AND observed_charged THEN 1 ELSE 0 END) AS false_negatives_charged_not_geo,
                SUM(CASE WHEN NOT geography_exposed AND NOT observed_charged THEN 1 ELSE 0 END) AS true_negatives
            FROM validation_base
        )
        SELECT
            validation_level,
            month,
            CAST(n_trips_2025 AS BIGINT) AS n_trips_2025,
            CAST(observed_charged_trips AS BIGINT) AS observed_charged_trips,
            CAST(geography_exposed_trips AS BIGINT) AS geography_exposed_trips,
            CAST(true_positives AS BIGINT) AS true_positives,
            CAST(false_positives_geo_not_charged AS BIGINT) AS false_positives_geo_not_charged,
            CAST(false_negatives_charged_not_geo AS BIGINT) AS false_negatives_charged_not_geo,
            CAST(true_negatives AS BIGINT) AS true_negatives,
            ROUND((true_positives + true_negatives)::DOUBLE / NULLIF(n_trips_2025, 0), 6) AS match_rate,
            ROUND(false_positives_geo_not_charged::DOUBLE / NULLIF(n_trips_2025, 0), 6) AS false_positive_share,
            ROUND(false_negatives_charged_not_geo::DOUBLE / NULLIF(n_trips_2025, 0), 6) AS false_negative_share,
            ROUND(false_negatives_charged_not_geo::DOUBLE / NULLIF(observed_charged_trips, 0), 6) AS share_observed_charged_missed_by_geo,
            ROUND(true_positives::DOUBLE / NULLIF(geography_exposed_trips, 0), 6) AS geography_precision,
            ROUND(true_positives::DOUBLE / NULLIF(observed_charged_trips, 0), 6) AS geography_recall,
            ROUND(observed_charged_trips::DOUBLE / NULLIF(n_trips_2025, 0), 6) AS observed_charged_share,
            ROUND(geography_exposed_trips::DOUBLE / NULLIF(n_trips_2025, 0), 6) AS geography_exposed_share
        FROM grouped
        ORDER BY CASE WHEN validation_level = 'overall' THEN 0 ELSE 1 END, month
        """
    )

    _copy_csv(con, "SELECT * FROM monthly_panel", PANEL_OUTPUT_PATH)
    _copy_csv(con, "SELECT * FROM exposure_validation", VALIDATION_OUTPUT_PATH)

    panel = con.execute("SELECT * FROM monthly_panel").fetchdf()
    validation = con.execute("SELECT * FROM exposure_validation").fetchdf()
    _write_notes(panel, validation, files_2024, files_2025)

    print("\nOutput files:")
    print(f"  {_relative(PANEL_OUTPUT_PATH)}")
    print(f"  {_relative(VALIDATION_OUTPUT_PATH)}")
    print(f"  {_relative(NOTES_OUTPUT_PATH)}")

    print("\nPanel summary:")
    print(f"  rows: {len(panel):,}")
    print(f"  zone-direction units: {panel[['zone', 'direction']].drop_duplicates().shape[0]:,}")
    print(f"  missing charged_share_2024_geo rows: {int(panel['charged_share_2024_geo'].isna().sum()):,}")
    print(f"  rows with n_trips < 30: {int((panel['n_trips'] < 30).sum()):,}")

    print("\nExposure validation:")
    print(validation.to_string(index=False))


if __name__ == "__main__":
    build_panel()
