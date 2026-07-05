"""
NYC Yellow Taxi CBD Congestion Fee — Zone Disruption Score (DS_z) pipeline.

It applies the yellow-specific analysis rules decided in the EDA (see docs/yellow_data_audit.md and
docs/yellow_dropped_and_engineered_features.md) and writes full-data outputs.

Key yellow-specific differences vs. the HVFHV pipeline:
  * DS_z (burden) uses **2025 charged card/cash** trips only (payment_type 1,2), and drops
    **non-movement** rows (zero distance AND (PU==DO OR duration<60s)).
  * Volume (behavioral shift) uses **non-Flex** trips (card/cash + irregular real trips);
    Flex is excluded because its adoption boom / Aug-2024 pilot→permanent launch confounds it.
  * `charged_geo` (PU or DO in the 38 CRZ zones) is built and validated against the 2025
    `charged_cbd_flag`.
  * Yellow does not use `base_passenger_fare`; behavioral shift reports avg `passenger_cost_pretip`.

Data is the local full processed yellow set (too large for GitHub). Run from the repo root:
    python scripts/yellow_ds_pipeline.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
# Repo-relative path (same convention as the HVFHV pipeline). The parquet files themselves
# are gitignored (too large for GitHub) — place the full processed yellow data locally under
# this path, e.g. symlink it: data/processed/00_standardized_trips/yellow/{2024,2025}/*.parquet
YELLOW_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips" / "yellow"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"

PRIMARY_FLOOR = 1.00
SENSITIVITY_FLOORS = (0.50, 1.00, 2.00, 5.00)
TOP_N_VALUES = (10, 20)

# CRZ = Congestion Relief Zone (Manhattan south of 60th St), 38 data-driven TLC LocationIDs
# (see crz validation: ~96.5% agreement with 2025 charged_cbd_flag).
CRZ_ZONE_IDS = (
    4, 12, 13, 45, 48, 50, 68, 79, 87, 88, 90, 100, 107, 113, 114, 125, 137, 144,
    148, 158, 161, 162, 163, 164, 170, 186, 209, 211, 224, 229, 230, 231, 232, 233,
    234, 246, 249, 261,
)

# Reusable SQL fragments for the yellow analysis rules.
CRZ_SQL = "(" + ", ".join(str(z) for z in CRZ_ZONE_IDS) + ")"
NON_MOVEMENT_SQL = (
    "(zero_distance_flag AND (PULocationID = DOLocationID OR trip_duration_seconds < 60))"
)


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _copy_csv(con: duckdb.DuckDBPyConnection, query: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({query}) TO '{_sql_path(output_path)}' (HEADER, DELIMITER ',')")


def build_pipeline() -> None:
    if not YELLOW_DIR.exists():
        raise FileNotFoundError(
            f"Missing yellow data dir: {YELLOW_DIR} (download the full processed data)."
        )
    if not ZONE_LOOKUP_PATH.exists():
        raise FileNotFoundError(f"Missing zone lookup: {ZONE_LOOKUP_PATH}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads TO 1")  # fixed aggregation order -> byte-reproducible outputs
    glob = f"{_sql_path(YELLOW_DIR)}/*/*.parquet"
    con.execute(f"CREATE OR REPLACE VIEW trips AS SELECT * FROM read_parquet('{glob}')")
    con.execute(
        f"""
        CREATE OR REPLACE VIEW zone_lookup AS
        SELECT LocationID, Borough, Zone, service_zone
        FROM read_csv_auto('{_sql_path(ZONE_LOOKUP_PATH)}')
        """
    )
    n_rows = con.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
    print(f"Yellow trips loaded: {n_rows:,} from {YELLOW_DIR}")
    print(f"Outputs -> {OUTPUT_DIR}")

    # ---- charged_geo construction + validation (vs 2025 charged_cbd_flag) ----
    con.execute(
        f"""
        CREATE OR REPLACE TABLE charged_geo_validation AS
        WITH cc25 AS (
            SELECT
                charged_cbd_flag AS truth,
                (PULocationID IN {CRZ_SQL} OR DOLocationID IN {CRZ_SQL}) AS charged_geo
            FROM trips
            WHERE year = 2025 AND yellow_card_or_cash_flag = TRUE
        )
        SELECT
            COUNT(*) AS n_2025_card_cash,
            ROUND(AVG(CASE WHEN charged_geo = truth THEN 1.0 ELSE 0.0 END), 4) AS agreement,
            SUM(CASE WHEN charged_geo AND truth THEN 1 ELSE 0 END) AS tp,
            SUM(CASE WHEN charged_geo AND NOT truth THEN 1 ELSE 0 END) AS fp_geo_not_charged,
            SUM(CASE WHEN NOT charged_geo AND truth THEN 1 ELSE 0 END) AS fn_charged_through_only,
            ROUND(SUM(CASE WHEN charged_geo AND truth THEN 1 ELSE 0 END)::DOUBLE
                / NULLIF(SUM(CASE WHEN charged_geo THEN 1 ELSE 0 END), 0), 4) AS precision_,
            ROUND(SUM(CASE WHEN charged_geo AND truth THEN 1 ELSE 0 END)::DOUBLE
                / NULLIF(SUM(CASE WHEN truth THEN 1 ELSE 0 END), 0), 4) AS recall_
        FROM cc25
        """
    )

    # ---- DS_z at multiple floors (2025 charged card/cash, non-movement dropped) ----
    floors_sql = ", ".join(f"({f:.2f})" for f in SENSITIVITY_FLOORS)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE ds_floor_sensitivity_base AS
        WITH floors(denominator_floor) AS (VALUES {floors_sql}),
        cleaned AS (
            SELECT
                PULocationID, DOLocationID,
                ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS base_cost_ex_cbd,
                cbd_congestion_fee
                    / ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS fee_burden
            FROM trips
            WHERE year = 2025
              AND charged_cbd_flag = TRUE
              AND yellow_card_or_cash_flag = TRUE          -- card/cash burden population
              AND NOT {NON_MOVEMENT_SQL}                   -- drop non-movement (audit §4.2)
              AND cbd_congestion_fee > 0
              AND passenger_cost_pretip IS NOT NULL
        ),
        eligible AS (
            SELECT f.denominator_floor, c.PULocationID, c.DOLocationID, c.fee_burden
            FROM cleaned c JOIN floors f ON c.base_cost_ex_cbd >= f.denominator_floor
        ),
        zone_direction AS (
            SELECT denominator_floor, PULocationID AS zone, 'pickup'  AS direction, fee_burden FROM eligible
            UNION ALL
            SELECT denominator_floor, DOLocationID AS zone, 'dropoff' AS direction, fee_burden FROM eligible
        ),
        aggregated AS (
            SELECT denominator_floor, zone, direction,
                   COUNT(*) AS N_z, ROUND(AVG(fee_burden), 4) AS DS_z_mean, ROUND(MEDIAN(fee_burden), 4) AS DS_z_median
            FROM zone_direction GROUP BY denominator_floor, zone, direction
        )
        SELECT
            a.denominator_floor, a.zone, a.direction, z.Borough,
            COALESCE(z.Zone, 'Zone ' || CAST(a.zone AS VARCHAR)) AS zone_name,
            z.service_zone, a.N_z, (a.N_z < 100) AS low_n_flag, a.DS_z_mean, a.DS_z_median,
            -- rank low-N zones (N_z<100, unstable) below all sufficient-data zones
            RANK() OVER (PARTITION BY a.denominator_floor, a.direction
                         ORDER BY (a.N_z >= 100) DESC, a.DS_z_mean DESC, a.zone) AS rank_mean,
            RANK() OVER (PARTITION BY a.denominator_floor, a.direction
                         ORDER BY (a.N_z >= 100) DESC, a.DS_z_median DESC, a.zone) AS rank_median
        FROM aggregated a LEFT JOIN zone_lookup z ON a.zone = z.LocationID
        ORDER BY a.denominator_floor, a.direction, rank_mean
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE zone_disruption_score AS
        SELECT denominator_floor, zone, direction, Borough, zone_name, service_zone, N_z, low_n_flag,
               DS_z_mean AS DS_z, DS_z_median, rank_mean AS DS_z_rank, rank_median AS DS_z_median_rank
        FROM ds_floor_sensitivity_base
        WHERE denominator_floor = {PRIMARY_FLOOR:.2f}
        ORDER BY direction, DS_z_rank
        """
    )

    # ---- behavioral shift: non-Flex volume per zone x direction ----
    con.execute(
        """
        CREATE OR REPLACE TABLE behavioral_shift AS
        WITH combined AS (
            SELECT year AS yr, PULocationID, DOLocationID, passenger_cost_pretip, trip_distance_miles
            FROM trips WHERE NOT flex_fare_flag          -- non-Flex real trips (card/cash + irregular)
        ),
        pu AS (
            SELECT PULocationID AS zone, 'pickup' AS direction, yr,
                   COUNT(*) AS n_trips, ROUND(AVG(passenger_cost_pretip), 2) AS avg_total_cost,
                   ROUND(AVG(trip_distance_miles) FILTER (WHERE trip_distance_miles BETWEEN 0 AND 100), 3) AS avg_distance
            FROM combined GROUP BY PULocationID, yr
        ),
        do_ AS (
            SELECT DOLocationID AS zone, 'dropoff' AS direction, yr,
                   COUNT(*) AS n_trips, ROUND(AVG(passenger_cost_pretip), 2) AS avg_total_cost,
                   ROUND(AVG(trip_distance_miles) FILTER (WHERE trip_distance_miles BETWEEN 0 AND 100), 3) AS avg_distance
            FROM combined GROUP BY DOLocationID, yr
        ),
        all_stats AS (SELECT * FROM pu UNION ALL SELECT * FROM do_)
        SELECT
            zone, direction,
            MAX(CASE WHEN yr = 2024 THEN n_trips END) AS n_2024,
            MAX(CASE WHEN yr = 2025 THEN n_trips END) AS n_2025,
            ROUND(MAX(CASE WHEN yr = 2025 THEN n_trips END)::DOUBLE
                / NULLIF(MAX(CASE WHEN yr = 2024 THEN n_trips END), 0) - 1, 4) AS pct_volume_change,
            MAX(CASE WHEN yr = 2024 THEN avg_total_cost END) AS avg_total_cost_2024,
            MAX(CASE WHEN yr = 2025 THEN avg_total_cost END) AS avg_total_cost_2025,
            MAX(CASE WHEN yr = 2024 THEN avg_distance END) AS avg_distance_2024,
            MAX(CASE WHEN yr = 2025 THEN avg_distance END) AS avg_distance_2025,
            CASE WHEN COALESCE(MAX(CASE WHEN yr = 2024 THEN n_trips END), 0) < 100
                   OR COALESCE(MAX(CASE WHEN yr = 2025 THEN n_trips END), 0) < 100
                 THEN TRUE ELSE FALSE END AS low_n_flag
        FROM all_stats GROUP BY zone, direction ORDER BY zone, direction
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE ds_z_vs_volume_change AS
        SELECT d.zone, d.direction, d.Borough, d.zone_name, d.service_zone,
               d.DS_z, d.DS_z_median, d.N_z, d.DS_z_rank,
               b.pct_volume_change, b.n_2024, b.n_2025, b.low_n_flag,
               b.avg_total_cost_2024, b.avg_total_cost_2025,
               b.avg_distance_2024, b.avg_distance_2025
        FROM zone_disruption_score d
        JOIN behavioral_shift b ON d.zone = b.zone AND d.direction = b.direction
        ORDER BY d.direction, d.DS_z_rank
        """
    )

    # ---- floor-sensitivity rank stability ----
    con.execute(
        """
        CREATE OR REPLACE TABLE ds_definition_ranks AS
        SELECT denominator_floor, 'mean' AS aggregation_method,
               'floor_' || REPLACE(CAST(denominator_floor AS VARCHAR), '.', '_') || '_mean' AS definition_key,
               zone, direction, N_z, DS_z_mean AS ds_value, rank_mean AS rank_position
        FROM ds_floor_sensitivity_base
        UNION ALL
        SELECT denominator_floor, 'median' AS aggregation_method,
               'floor_' || REPLACE(CAST(denominator_floor AS VARCHAR), '.', '_') || '_median' AS definition_key,
               zone, direction, N_z, DS_z_median AS ds_value, rank_median AS rank_position
        FROM ds_floor_sensitivity_base
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE rank_stability AS
        WITH primary_rank AS (
            SELECT zone, direction, rank_position AS primary_rank
            FROM ds_definition_ranks
            WHERE denominator_floor = {PRIMARY_FLOOR:.2f} AND aggregation_method = 'mean'
        ),
        comparisons AS (
            SELECT r.definition_key, r.denominator_floor, r.aggregation_method, r.direction, r.zone,
                   p.primary_rank, r.rank_position AS comparison_rank,
                   ABS(r.rank_position - p.primary_rank) AS abs_rank_delta
            FROM ds_definition_ranks r
            JOIN primary_rank p ON r.zone = p.zone AND r.direction = p.direction
        )
        SELECT definition_key, denominator_floor, aggregation_method, direction,
               COUNT(*) AS n_pairs,
               CORR(primary_rank::DOUBLE, comparison_rank::DOUBLE) AS spearman_rank_corr_vs_primary,
               AVG(abs_rank_delta) AS mean_abs_rank_delta, MAX(abs_rank_delta) AS max_abs_rank_delta
        FROM comparisons GROUP BY definition_key, denominator_floor, aggregation_method, direction
        UNION ALL
        SELECT definition_key, denominator_floor, aggregation_method, 'all' AS direction,
               COUNT(*) AS n_pairs,
               CORR(primary_rank::DOUBLE, comparison_rank::DOUBLE) AS spearman_rank_corr_vs_primary,
               AVG(abs_rank_delta) AS mean_abs_rank_delta, MAX(abs_rank_delta) AS max_abs_rank_delta
        FROM comparisons GROUP BY definition_key, denominator_floor, aggregation_method
        ORDER BY aggregation_method, denominator_floor, direction
        """
    )

    # ---- monthly panel + 2024 charged-share exposure (Model 2 DiD) ----
    # charged_share is direction-specific (matches the zone x direction unit) and computed from
    # 2024 (pre-policy) so exposure is not itself a result of the fee.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE charged_share_2024 AS
        WITH nf24 AS (
            SELECT PULocationID, DOLocationID,
                   (PULocationID IN {CRZ_SQL} OR DOLocationID IN {CRZ_SQL}) AS touches_crz
            FROM trips WHERE year = 2024 AND NOT flex_fare_flag
        ),
        cs_pu AS (
            SELECT PULocationID AS zone, 'pickup' AS direction,
                   ROUND(AVG(touches_crz::INT), 4) AS charged_share
            FROM nf24 GROUP BY PULocationID
        ),
        cs_do AS (
            SELECT DOLocationID AS zone, 'dropoff' AS direction,
                   ROUND(AVG(touches_crz::INT), 4) AS charged_share
            FROM nf24 GROUP BY DOLocationID
        )
        SELECT * FROM cs_pu UNION ALL SELECT * FROM cs_do
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE monthly_panel AS
        WITH combined AS (
            SELECT year AS yr, month AS mo, PULocationID, DOLocationID
            FROM trips WHERE NOT flex_fare_flag
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
        SELECT p.zone, p.direction, p.yr AS year, p.mo AS month, p.n_trips,
               z.Borough, COALESCE(z.Zone, 'Zone ' || CAST(p.zone AS VARCHAR)) AS zone_name,
               (p.zone IN {CRZ_SQL}) AS crz_zone, cs.charged_share
        FROM panel p
        LEFT JOIN zone_lookup z ON p.zone = z.LocationID
        LEFT JOIN charged_share_2024 cs ON p.zone = cs.zone AND p.direction = cs.direction
        ORDER BY p.zone, p.direction, p.yr, p.mo
        """
    )

    outputs = {
        "yellow_zone_disruption_score.csv": "SELECT * FROM zone_disruption_score",
        "yellow_monthly_panel.csv": "SELECT * FROM monthly_panel",
        "yellow_behavioral_shift.csv": "SELECT * FROM behavioral_shift",
        "yellow_ds_z_vs_volume_change.csv": "SELECT * FROM ds_z_vs_volume_change",
        "yellow_ds_floor_sensitivity.csv": "SELECT * FROM ds_floor_sensitivity_base",
        "yellow_ds_rank_stability.csv": "SELECT * FROM rank_stability",
        "yellow_charged_geo_validation.csv": "SELECT * FROM charged_geo_validation",
    }
    for filename, query in outputs.items():
        _copy_csv(con, query, OUTPUT_DIR / filename)

    # ---- console summary ----
    print("\ncharged_geo validation (2025 card/cash vs charged_cbd_flag):")
    print(con.sql("SELECT n_2025_card_cash, ROUND(agreement,4) AS agreement, "
                  "ROUND(precision_,4) AS precision, ROUND(recall_,4) AS recall, "
                  "fn_charged_through_only FROM charged_geo_validation"))
    print("\nTop 10 zones by DS_z (primary $1 floor, N_z>=100):")
    print(con.sql("SELECT direction, DS_z_rank, zone_name, Borough, N_z, "
                  "ROUND(DS_z,4) AS DS_z, ROUND(DS_z_median,4) AS DS_z_median "
                  "FROM zone_disruption_score WHERE NOT low_n_flag ORDER BY DS_z_rank LIMIT 10"))
    print(f"  (low-N zones flagged & ranked below sufficient-data zones: "
          f"{con.execute('SELECT SUM(CASE WHEN low_n_flag THEN 1 ELSE 0 END) FROM zone_disruption_score').fetchone()[0]} of "
          f"{con.execute('SELECT COUNT(*) FROM zone_disruption_score').fetchone()[0]})")
    print("\nFloor-sensitivity rank stability (all directions, vs $1 mean):")
    print(con.sql("SELECT definition_key, n_pairs, ROUND(spearman_rank_corr_vs_primary,4) AS spearman, "
                  "ROUND(mean_abs_rank_delta,2) AS mean_abs_delta, max_abs_rank_delta "
                  "FROM rank_stability WHERE direction='all' ORDER BY aggregation_method, denominator_floor"))
    print("\nOutput row counts:")
    for filename, query in outputs.items():
        print(f"  {filename}: {con.execute(f'SELECT COUNT(*) FROM ({query})').fetchone()[0]:,}")
    print("\nPipeline complete.")


if __name__ == "__main__":
    build_pipeline()
