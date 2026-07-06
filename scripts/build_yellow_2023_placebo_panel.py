"""
Prepare Yellow Taxi 2023 data and build the Model-2 placebo panel.

This is a local data-prep helper for the Feb-Jun 2023 -> Feb-Jun 2024 placebo
test. It mirrors the Yellow Model-2 counting rules:

* monthly zone x direction counts
* yellow non-Flex population for volume (card/cash + irregular real trips)
* CRZ exposure measured as the pre-placebo share of trips touching the 38 CRZ zones
* output panel under data/processed/disruption_score/

The one-time upgrade step (reading the raw/older 2023 files from the Desktop, adding the current
yellow regime flags, and symlinking the result into the repo's standardized-trip folder) needs the
local raw data. Once that link exists, `build_placebo_panel` reads it via repo-relative paths, so
re-running only rebuilds the panel and does not need the Desktop source — `main` skips the upgrade
when `data/processed/00_standardized_trips/yellow/2023/` is already populated.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from standardize_trips import (
    REPO_ROOT,
    add_derived_and_qc_flags,
    apply_conservative_filters,
    order_columns,
    standardize_yellow,
)
from yellow_ds_pipeline import CRZ_ZONE_IDS


DEFAULT_SOURCE_2023_DIR = Path("/Users/ping/Desktop/data/2023_yellow")
DEFAULT_DESKTOP_PROCESSED_2023_DIR = Path("/Users/ping/Desktop/data/processed/yellow/2023")

YELLOW_STANDARDIZED_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips" / "yellow"
QC_DIR = REPO_ROOT / "data" / "processed" / "qc"
DISRUPTION_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"

CRZ_SQL = "(" + ", ".join(str(z) for z in CRZ_ZONE_IDS) + ")"


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _sql_path_list(paths: list[Path]) -> str:
    return "[" + ", ".join(f"'{_sql_path(p)}'" for p in paths) + "]"


def _prepare_one_2023_file(raw_or_standardized_path: Path, output_dir: Path) -> dict:
    month = int(raw_or_standardized_path.stem)
    source_file = raw_or_standardized_path.as_posix()
    df_raw = pd.read_parquet(raw_or_standardized_path)

    if "tpep_pickup_datetime" in df_raw.columns:
        df = standardize_yellow(df_raw, 2023, month, source_file)
    else:
        # The Desktop 2023 files are already in an older standardized schema.
        df = df_raw.copy()
        df["year"] = 2023
        df["month"] = month
        df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"], errors="coerce")
        df["dropoff_datetime"] = pd.to_datetime(df["dropoff_datetime"], errors="coerce")
        df["pickup_date"] = df["pickup_datetime"].dt.date
        df["pickup_hour"] = df["pickup_datetime"].dt.hour
        df["day_of_week"] = df["pickup_datetime"].dt.dayofweek
        df["source_file"] = source_file

    df = add_derived_and_qc_flags(df)
    df, drop_detail = apply_conservative_filters(df, 2023, month)
    df = order_columns(df, "yellow")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{month:02d}.parquet"
    df.to_parquet(output_path, index=False)

    record = {
        "source_file": source_file,
        "output_file": output_path.as_posix(),
        "service_type": "yellow",
        "year": 2023,
        "month": month,
        "rows_before": len(df_raw),
        "rows_after": len(df),
        "rows_dropped": len(df_raw) - len(df),
    }
    record.update(drop_detail)
    return record


def prepare_2023_standardized(source_dir: Path, output_dir: Path) -> pd.DataFrame:
    files = sorted(source_dir.glob("*.parquet"))
    if len(files) != 5:
        raise FileNotFoundError(f"Expected 5 Feb-Jun parquet files under {source_dir}, found {len(files)}")

    records = [_prepare_one_2023_file(path, output_dir) for path in files]
    qc = pd.DataFrame(records).sort_values(["year", "month"])
    QC_DIR.mkdir(parents=True, exist_ok=True)
    qc.to_csv(QC_DIR / "yellow_2023_placebo_standardization_row_counts.csv", index=False)
    return qc


def link_2023_into_repo(output_dir: Path) -> None:
    repo_2023_dir = YELLOW_STANDARDIZED_DIR / "2023"
    repo_2023_dir.mkdir(parents=True, exist_ok=True)

    for month in range(2, 7):
        src = output_dir / f"{month:02d}.parquet"
        dst = repo_2023_dir / f"{month:02d}.parquet"
        if not src.exists():
            raise FileNotFoundError(src)
        if dst.is_symlink():
            if dst.resolve() == src.resolve():
                continue
            dst.unlink()
        elif dst.exists():
            raise FileExistsError(f"{dst} exists and is not a symlink; not overwriting it")
        dst.symlink_to(src)


def build_placebo_panel() -> Path:
    inputs = []
    for year in (2023, 2024):
        for month in range(2, 7):
            path = YELLOW_STANDARDIZED_DIR / str(year) / f"{month:02d}.parquet"
            if not path.exists():
                raise FileNotFoundError(path)
            inputs.append(path)

    DISRUPTION_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DISRUPTION_DIR / "yellow_2023_placebo_monthly_panel.csv"

    con = duckdb.connect()
    con.execute("SET threads TO 1")
    con.execute(
        f"""
        CREATE OR REPLACE VIEW trips AS
        SELECT * FROM read_parquet({_sql_path_list(inputs)}, union_by_name=true)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW zone_lookup AS
        SELECT LocationID, Borough, Zone, service_zone
        FROM read_csv_auto('{_sql_path(ZONE_LOOKUP_PATH)}')
        """
    )

    for exposure_year in (2023, 2024):
        con.execute(
            f"""
            CREATE OR REPLACE TABLE charged_share_{exposure_year} AS
            WITH nf AS (
                SELECT
                    PULocationID,
                    DOLocationID,
                    (PULocationID IN {CRZ_SQL} OR DOLocationID IN {CRZ_SQL}) AS touches_crz
                FROM trips
                WHERE year = {exposure_year}
                  AND month BETWEEN 2 AND 6
                  AND NOT flex_fare_flag
            ),
            cs_pu AS (
                SELECT PULocationID AS zone, 'pickup' AS direction,
                       ROUND(AVG(touches_crz::INT), 4) AS charged_share_{exposure_year}
                FROM nf GROUP BY PULocationID
            ),
            cs_do AS (
                SELECT DOLocationID AS zone, 'dropoff' AS direction,
                       ROUND(AVG(touches_crz::INT), 4) AS charged_share_{exposure_year}
                FROM nf GROUP BY DOLocationID
            )
            SELECT * FROM cs_pu UNION ALL SELECT * FROM cs_do
            """
        )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE placebo_panel AS
        WITH combined AS (
            SELECT year AS yr, month AS mo, PULocationID, DOLocationID
            FROM trips
            WHERE year IN (2023, 2024)
              AND month BETWEEN 2 AND 6
              AND NOT flex_fare_flag
        ),
        pu AS (
            SELECT PULocationID AS zone, 'pickup' AS direction, yr, mo, COUNT(*) AS n_trips
            FROM combined GROUP BY PULocationID, yr, mo
        ),
        do_ AS (
            SELECT DOLocationID AS zone, 'dropoff' AS direction, yr, mo, COUNT(*) AS n_trips
            FROM combined GROUP BY DOLocationID, yr, mo
        ),
        panel AS (SELECT * FROM pu UNION ALL SELECT * FROM do_)
        SELECT
            p.zone,
            p.direction,
            p.yr AS year,
            p.mo AS month,
            p.n_trips,
            z.Borough,
            COALESCE(z.Zone, 'Zone ' || CAST(p.zone AS VARCHAR)) AS zone_name,
            (p.zone IN {CRZ_SQL}) AS crz_zone,
            cs23.charged_share_2023,
            cs24.charged_share_2024,
            cs23.charged_share_2023 AS charged_share
        FROM panel p
        LEFT JOIN zone_lookup z ON p.zone = z.LocationID
        LEFT JOIN charged_share_2023 cs23 ON p.zone = cs23.zone AND p.direction = cs23.direction
        LEFT JOIN charged_share_2024 cs24 ON p.zone = cs24.zone AND p.direction = cs24.direction
        ORDER BY p.zone, p.direction, p.yr, p.mo
        """
    )
    con.execute(
        f"COPY placebo_panel TO '{_sql_path(output_path)}' (HEADER, DELIMITER ',')"
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-2023-dir", type=Path, default=DEFAULT_SOURCE_2023_DIR)
    parser.add_argument("--output-2023-dir", type=Path, default=DEFAULT_DESKTOP_PROCESSED_2023_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_2023_dir = YELLOW_STANDARDIZED_DIR / "2023"
    already_prepared = all((repo_2023_dir / f"{m:02d}.parquet").exists() for m in range(2, 7))

    # The Desktop upgrade (prepare + link) is a one-time step needing the raw 2023 files. Once the
    # standardized 2023 is linked into the repo, the panel build below reads it via repo-relative
    # paths, so re-runs only rebuild the panel and do not need the Desktop source.
    if already_prepared:
        print(f"Using existing standardized 2023 at {repo_2023_dir} (Desktop upgrade step skipped).")
    else:
        qc = prepare_2023_standardized(args.source_2023_dir, args.output_2023_dir)
        link_2023_into_repo(args.output_2023_dir)
        print("2023 Yellow standardized row counts:")
        print(qc[["month", "rows_before", "rows_after", "rows_dropped"]].to_string(index=False))
        print(f"Linked 2023 parquets into: {repo_2023_dir}")

    panel_path = build_placebo_panel()
    print(f"Placebo panel written to: {panel_path}")


if __name__ == "__main__":
    main()
