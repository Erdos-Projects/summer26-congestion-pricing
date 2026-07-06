"""
Cross-vehicle Model-3 panel: monthly `zone x direction x vehicle` trip counts for yellow and
HVFHV, aggregated with **identical rules** so the yellow-vs-HVFHV DiD reflects the fee-size
difference ($0.75 vs $1.50), not a methodology difference.

Rules applied to both vehicles (matching the yellow Model-1/2 pipeline):
  * window: Feb-Jun (months 2-6)
  * non-movement drop: zero_distance AND (PU == DO OR duration < 60s)
  * unit: zone x direction (pickup side = PULocationID, dropoff side = DOLocationID)

Vehicle-specific population (deliberate, see modeling_plan.md Model 3):
  * yellow: card/cash only (yellow_card_or_cash_flag) -- excludes Flex so Uber<->yellow-Flex
    substitution does not move volume between the two compared services
  * hvfhv:  all HVFHV trips (no Flex regime)

`charged_share`: pre-year, direction-specific, computed per vehicle from its own trips
(fraction of that zone-side's trips whose pickup or dropoff touches the CRZ).

Two year pairs:
  * default   -> 2024 (pre) vs 2025 (post) = the real fee window -> m3_cross_vehicle_panel.csv
  * --placebo -> 2023 (pre) vs 2024 (post) = a no-fee window     -> m3_placebo_panel_2023_2024.csv

Reproducibility: single-threaded (deterministic float aggregation) + charged_share rounded to 4 dp.

Run from the repo root:
    python scripts/build_m3_panel.py             # 2024 vs 2025
    python scripts/build_m3_panel.py --placebo   # 2023 vs 2024 (placebo)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARDIZED_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"

CRZ_ZONE_IDS = (
    4, 12, 13, 45, 48, 50, 68, 79, 87, 88, 90, 100, 107, 113, 114, 125, 137, 144,
    148, 158, 161, 162, 163, 164, 170, 186, 209, 211, 224, 229, 230, 231, 232, 233,
    234, 246, 249, 261,
)
CRZ_SQL = "(" + ", ".join(str(z) for z in CRZ_ZONE_IDS) + ")"
NON_MOVEMENT_SQL = (
    "(zero_distance_flag AND (PULocationID = DOLocationID OR trip_duration_seconds < 60))"
)

# vehicle -> population filter (SQL predicate on the standardized trips)
VEHICLE_POPULATION = {
    "yellow": "yellow_card_or_cash_flag = TRUE",   # card/cash only for Model 3
    "hvfhv": "TRUE",                                # all HVFHV
}


def _posix(path: Path) -> str:
    return path.resolve().as_posix()


def build_vehicle_panel(
    con: duckdb.DuckDBPyConnection, vehicle: str, population_sql: str, pre_year: int, post_year: int
) -> None:
    glob = f"{_posix(STANDARDIZED_DIR / vehicle)}/*/*.parquet"
    con.execute(f"CREATE OR REPLACE VIEW trips AS SELECT * FROM read_parquet('{glob}')")

    # pre-year direction-specific CRZ exposure, from the same population as the counts
    con.execute(
        f"""
        CREATE OR REPLACE TABLE cs_{vehicle} AS
        WITH nf AS (
            SELECT PULocationID, DOLocationID,
                   (PULocationID IN {CRZ_SQL} OR DOLocationID IN {CRZ_SQL}) AS touches_crz
            FROM trips
            WHERE year = {pre_year} AND month BETWEEN 2 AND 6
              AND {population_sql} AND NOT {NON_MOVEMENT_SQL}
        ),
        pu AS (SELECT PULocationID AS zone, 'pickup'  AS direction,
                      ROUND(AVG(touches_crz::INT), 4) AS charged_share FROM nf GROUP BY PULocationID),
        do_ AS (SELECT DOLocationID AS zone, 'dropoff' AS direction,
                      ROUND(AVG(touches_crz::INT), 4) AS charged_share FROM nf GROUP BY DOLocationID)
        SELECT * FROM pu UNION ALL SELECT * FROM do_
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE panel_{vehicle} AS
        WITH combined AS (
            SELECT year AS yr, month AS mo, PULocationID, DOLocationID
            FROM trips
            WHERE year IN ({pre_year}, {post_year}) AND month BETWEEN 2 AND 6
              AND {population_sql} AND NOT {NON_MOVEMENT_SQL}
        ),
        pu AS (SELECT PULocationID AS zone, 'pickup'  AS direction, yr, mo, COUNT(*) AS n_trips
               FROM combined GROUP BY PULocationID, yr, mo),
        do_ AS (SELECT DOLocationID AS zone, 'dropoff' AS direction, yr, mo, COUNT(*) AS n_trips
               FROM combined GROUP BY DOLocationID, yr, mo),
        p AS (SELECT * FROM pu UNION ALL SELECT * FROM do_)
        SELECT '{vehicle}' AS vehicle, p.zone, p.direction, p.yr AS year, p.mo AS month, p.n_trips,
               z.Borough, COALESCE(z.Zone, 'Zone ' || CAST(p.zone AS VARCHAR)) AS zone_name,
               (p.zone IN {CRZ_SQL}) AS crz_zone, cs.charged_share
        FROM p
        LEFT JOIN zone_lookup z ON p.zone = z.LocationID
        LEFT JOIN cs_{vehicle} cs ON p.zone = cs.zone AND p.direction = cs.direction
        """
    )


def build(pre_year: int, post_year: int, output_path: Path) -> None:
    for vehicle in VEHICLE_POPULATION:
        for yr in (pre_year, post_year):
            if not (STANDARDIZED_DIR / vehicle / str(yr)).exists():
                raise FileNotFoundError(f"Missing standardized data: {STANDARDIZED_DIR / vehicle / str(yr)}")

    con = duckdb.connect()
    con.execute("SET threads TO 1")  # deterministic float aggregation -> byte-reproducible output
    con.execute(
        f"""
        CREATE OR REPLACE VIEW zone_lookup AS
        SELECT LocationID, Borough, Zone, service_zone
        FROM read_csv_auto('{_posix(ZONE_LOOKUP_PATH)}')
        """
    )
    for vehicle, population_sql in VEHICLE_POPULATION.items():
        build_vehicle_panel(con, vehicle, population_sql, pre_year, post_year)
        n = con.execute(f"SELECT COUNT(*) FROM panel_{vehicle}").fetchone()[0]
        print(f"{vehicle} ({pre_year} vs {post_year}): {n:,} rows")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT * FROM panel_yellow
            UNION ALL
            SELECT * FROM panel_hvfhv
            ORDER BY vehicle, zone, direction, year, month
        ) TO '{_posix(output_path)}' (HEADER, DELIMITER ',')
        """
    )
    print(f"wrote {output_path.relative_to(REPO_ROOT).as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the cross-vehicle Model-3 panel.")
    parser.add_argument(
        "--placebo", action="store_true",
        help="build the 2023-vs-2024 (no-fee) placebo panel instead of the 2024-vs-2025 fee window",
    )
    args = parser.parse_args()
    if args.placebo:
        build(2023, 2024, OUTPUT_DIR / "m3_placebo_panel_2023_2024.csv")
    else:
        build(2024, 2025, OUTPUT_DIR / "m3_cross_vehicle_panel.csv")


if __name__ == "__main__":
    main()
