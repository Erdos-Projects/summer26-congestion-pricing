"""
NYC HVFHV CBD Congestion Fee - Zone Disruption Score (DS_z) Pipeline.

Reads the current standardized HVFHV parquet layout, computes the primary
zone-level disruption score, and writes full-data sensitivity outputs.

Run from the repository root:
    python scripts/EDA_adithya/01_pipeline.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb


REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARDIZED_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips" / "hvfhv"
INPUT_2024_DIR = STANDARDIZED_DIR / "2024"
INPUT_2025_DIR = STANDARDIZED_DIR / "2025"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"

PRIMARY_FLOOR = 1.00
SENSITIVITY_FLOORS = (0.50, 1.00, 2.00, 5.00)
TOP_N_VALUES = (10, 20)


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _sql_path_list(paths: list[Path]) -> str:
    return "[" + ", ".join(f"'{_sql_path(path)}'" for path in paths) + "]"


def _discover_inputs(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Missing input directory: {input_dir}")
    files = sorted(input_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found under: {input_dir}")
    return files


def _copy_csv(con: duckdb.DuckDBPyConnection, table_or_query: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY ({table_or_query}) TO '{_sql_path(output_path)}' (HEADER, DELIMITER ',')"
    )


def build_pipeline() -> None:
    files_2024 = _discover_inputs(INPUT_2024_DIR)
    files_2025 = _discover_inputs(INPUT_2025_DIR)
    if not ZONE_LOOKUP_PATH.exists():
        raise FileNotFoundError(f"Missing zone lookup file: {ZONE_LOOKUP_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    # Keep AVG()/CORR() output reproducible across reruns; parallel FP sums can reorder.
    con.execute("SET threads TO 1")

    print("Input files:")
    print(f"  2024 HVFHV parquet files: {len(files_2024)} from {INPUT_2024_DIR}")
    print(f"  2025 HVFHV parquet files: {len(files_2025)} from {INPUT_2025_DIR}")
    print(f"  Outputs: {OUTPUT_DIR}")

    con.execute(
        f"""
        CREATE OR REPLACE VIEW trips_2024 AS
        SELECT *, 2024 AS yr
        FROM read_parquet({_sql_path_list(files_2024)})
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW trips_2025 AS
        SELECT *, 2025 AS yr
        FROM read_parquet({_sql_path_list(files_2025)})
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW zone_lookup AS
        SELECT LocationID, Borough, Zone, service_zone
        FROM read_csv_auto('{_sql_path(ZONE_LOOKUP_PATH)}')
        """
    )

    print("\nSchema check for 2025 standardized HVFHV data:")
    print(con.sql("DESCRIBE trips_2025"))

    print("\nFee-charged vs non-charged 2025 trips:")
    print(
        con.sql(
            """
            SELECT
                CASE WHEN charged_cbd_flag THEN 'fee_charged' ELSE 'no_fee' END AS grp,
                COUNT(*) AS n,
                AVG(passenger_cost_pretip) AS avg_pretip,
                AVG(trip_distance_miles) AS avg_miles
            FROM trips_2025
            GROUP BY grp
            ORDER BY grp
            """
        )
    )

    print("\nBase-cost denominator QC:")
    print(
        con.sql(
            """
            SELECT
                COUNT(*) AS total_2025_trips,
                SUM(CASE WHEN charged_cbd_flag THEN 1 ELSE 0 END) AS fee_trips,
                SUM(CASE WHEN charged_cbd_flag
                         AND ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) <= 0
                    THEN 1 ELSE 0 END) AS true_zero_or_negative_base,
                SUM(CASE WHEN charged_cbd_flag
                         AND ROUND(passenger_cost_pretip - cbd_congestion_fee, 2)
                             BETWEEN 0.01 AND 0.99
                    THEN 1 ELSE 0 END) AS genuinely_under_1_dollar
            FROM trips_2025
            """
        )
    )

    floor_values_sql = ", ".join(f"({floor:.2f})" for floor in SENSITIVITY_FLOORS)
    top_n_values_sql = ", ".join(f"({n})" for n in TOP_N_VALUES)

    con.execute(
        f"""
        CREATE OR REPLACE TABLE ds_floor_sensitivity_base AS
        WITH floors(denominator_floor) AS (
            VALUES {floor_values_sql}
        ),
        cleaned AS (
            SELECT
                PULocationID,
                DOLocationID,
                ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS base_cost_ex_cbd,
                cbd_congestion_fee
                    / ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS fee_burden
            FROM trips_2025
            WHERE charged_cbd_flag = TRUE
              AND cbd_congestion_fee > 0
              AND passenger_cost_pretip IS NOT NULL
              AND cbd_congestion_fee IS NOT NULL
        ),
        eligible AS (
            SELECT
                f.denominator_floor,
                c.PULocationID,
                c.DOLocationID,
                c.fee_burden
            FROM cleaned c
            JOIN floors f ON c.base_cost_ex_cbd >= f.denominator_floor
        ),
        zone_direction AS (
            SELECT
                denominator_floor,
                PULocationID AS zone,
                'pickup' AS direction,
                fee_burden
            FROM eligible
            UNION ALL
            SELECT
                denominator_floor,
                DOLocationID AS zone,
                'dropoff' AS direction,
                fee_burden
            FROM eligible
        ),
        aggregated AS (
            SELECT
                denominator_floor,
                zone,
                direction,
                COUNT(*) AS N_z,
                AVG(fee_burden) AS DS_z_mean,
                MEDIAN(fee_burden) AS DS_z_median
            FROM zone_direction
            GROUP BY denominator_floor, zone, direction
        )
        SELECT
            a.denominator_floor,
            a.zone,
            a.direction,
            z.Borough,
            COALESCE(z.Zone, 'Zone ' || CAST(a.zone AS VARCHAR)) AS zone_name,
            z.service_zone,
            a.N_z,
            a.DS_z_mean,
            a.DS_z_median,
            RANK() OVER (
                PARTITION BY a.denominator_floor, a.direction
                ORDER BY a.DS_z_mean DESC, a.zone
            ) AS rank_mean,
            RANK() OVER (
                PARTITION BY a.denominator_floor, a.direction
                ORDER BY a.DS_z_median DESC, a.zone
            ) AS rank_median
        FROM aggregated a
        LEFT JOIN zone_lookup z ON a.zone = z.LocationID
        ORDER BY a.denominator_floor, a.direction, rank_mean
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE zone_disruption_score AS
        SELECT
            denominator_floor,
            zone,
            direction,
            Borough,
            zone_name,
            service_zone,
            N_z,
            DS_z_mean AS DS_z,
            DS_z_median,
            rank_mean AS DS_z_rank,
            rank_median AS DS_z_median_rank
        FROM ds_floor_sensitivity_base
        WHERE denominator_floor = {PRIMARY_FLOOR:.2f}
        ORDER BY direction, DS_z_rank
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE behavioral_shift AS
        WITH combined AS (
            SELECT yr, PULocationID, DOLocationID, passenger_cost_pretip, base_passenger_fare
            FROM trips_2024
            UNION ALL
            SELECT yr, PULocationID, DOLocationID, passenger_cost_pretip, base_passenger_fare
            FROM trips_2025
        ),
        pu_stats AS (
            SELECT
                PULocationID AS zone,
                'pickup' AS direction,
                yr,
                COUNT(*) AS n_trips,
                AVG(passenger_cost_pretip) AS avg_total_cost,
                AVG(base_passenger_fare) AS avg_base_fare
            FROM combined
            GROUP BY PULocationID, yr
        ),
        do_stats AS (
            SELECT
                DOLocationID AS zone,
                'dropoff' AS direction,
                yr,
                COUNT(*) AS n_trips,
                AVG(passenger_cost_pretip) AS avg_total_cost,
                AVG(base_passenger_fare) AS avg_base_fare
            FROM combined
            GROUP BY DOLocationID, yr
        ),
        all_stats AS (
            SELECT * FROM pu_stats
            UNION ALL
            SELECT * FROM do_stats
        )
        SELECT
            zone,
            direction,
            MAX(CASE WHEN yr = 2024 THEN n_trips END) AS n_2024,
            MAX(CASE WHEN yr = 2025 THEN n_trips END) AS n_2025,
            MAX(CASE WHEN yr = 2025 THEN n_trips END)::DOUBLE
                / NULLIF(MAX(CASE WHEN yr = 2024 THEN n_trips END), 0) - 1
                AS pct_volume_change,
            MAX(CASE WHEN yr = 2024 THEN avg_total_cost END) AS avg_total_cost_2024,
            MAX(CASE WHEN yr = 2025 THEN avg_total_cost END) AS avg_total_cost_2025,
            MAX(CASE WHEN yr = 2024 THEN avg_base_fare END) AS avg_base_fare_2024,
            MAX(CASE WHEN yr = 2025 THEN avg_base_fare END) AS avg_base_fare_2025,
            CASE
                WHEN COALESCE(MAX(CASE WHEN yr = 2024 THEN n_trips END), 0) < 100
                  OR COALESCE(MAX(CASE WHEN yr = 2025 THEN n_trips END), 0) < 100
                THEN TRUE ELSE FALSE
            END AS low_n_flag
        FROM all_stats
        GROUP BY zone, direction
        ORDER BY zone, direction
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE ds_z_vs_volume_change AS
        SELECT
            d.zone,
            d.direction,
            d.Borough,
            d.zone_name,
            d.service_zone,
            d.DS_z,
            d.DS_z_median,
            d.N_z,
            d.DS_z_rank,
            b.pct_volume_change,
            b.n_2024,
            b.n_2025,
            b.low_n_flag,
            b.avg_total_cost_2024,
            b.avg_total_cost_2025,
            b.avg_base_fare_2024,
            b.avg_base_fare_2025
        FROM zone_disruption_score d
        JOIN behavioral_shift b
          ON d.zone = b.zone AND d.direction = b.direction
        ORDER BY d.direction, d.DS_z_rank
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE ds_definition_ranks AS
        SELECT
            denominator_floor,
            'mean' AS aggregation_method,
            'floor_' || REPLACE(CAST(denominator_floor AS VARCHAR), '.', '_') || '_mean'
                AS definition_key,
            zone,
            direction,
            Borough,
            zone_name,
            N_z,
            DS_z_mean AS ds_value,
            rank_mean AS rank_position
        FROM ds_floor_sensitivity_base
        UNION ALL
        SELECT
            denominator_floor,
            'median' AS aggregation_method,
            'floor_' || REPLACE(CAST(denominator_floor AS VARCHAR), '.', '_') || '_median'
                AS definition_key,
            zone,
            direction,
            Borough,
            zone_name,
            N_z,
            DS_z_median AS ds_value,
            rank_median AS rank_position
        FROM ds_floor_sensitivity_base
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE rank_stability AS
        WITH primary_rank AS (
            SELECT zone, direction, rank_position AS primary_rank
            FROM ds_definition_ranks
            WHERE denominator_floor = {PRIMARY_FLOOR:.2f}
              AND aggregation_method = 'mean'
        ),
        comparisons AS (
            SELECT
                r.definition_key,
                r.denominator_floor,
                r.aggregation_method,
                r.direction,
                r.zone,
                p.primary_rank,
                r.rank_position AS comparison_rank,
                ABS(r.rank_position - p.primary_rank) AS abs_rank_delta
            FROM ds_definition_ranks r
            JOIN primary_rank p
              ON r.zone = p.zone AND r.direction = p.direction
        ),
        by_direction AS (
            SELECT
                definition_key,
                denominator_floor,
                aggregation_method,
                direction,
                COUNT(*) AS n_zone_direction_pairs,
                CORR(primary_rank::DOUBLE, comparison_rank::DOUBLE)
                    AS spearman_rank_corr_vs_primary,
                AVG(abs_rank_delta) AS mean_abs_rank_delta,
                MEDIAN(abs_rank_delta) AS median_abs_rank_delta,
                MAX(abs_rank_delta) AS max_abs_rank_delta
            FROM comparisons
            GROUP BY definition_key, denominator_floor, aggregation_method, direction
        ),
        all_directions AS (
            SELECT
                definition_key,
                denominator_floor,
                aggregation_method,
                'all' AS direction,
                COUNT(*) AS n_zone_direction_pairs,
                CORR(primary_rank::DOUBLE, comparison_rank::DOUBLE)
                    AS spearman_rank_corr_vs_primary,
                AVG(abs_rank_delta) AS mean_abs_rank_delta,
                MEDIAN(abs_rank_delta) AS median_abs_rank_delta,
                MAX(abs_rank_delta) AS max_abs_rank_delta
            FROM comparisons
            GROUP BY definition_key, denominator_floor, aggregation_method
        )
        SELECT * FROM by_direction
        UNION ALL
        SELECT * FROM all_directions
        ORDER BY aggregation_method, denominator_floor, direction
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE top_zone_overlap AS
        WITH top_n(top_n) AS (
            VALUES {top_n_values_sql}
        ),
        primary_rank AS (
            SELECT zone, direction, rank_position AS primary_rank
            FROM ds_definition_ranks
            WHERE denominator_floor = {PRIMARY_FLOOR:.2f}
              AND aggregation_method = 'mean'
        ),
        comparisons AS (
            SELECT
                r.definition_key,
                r.denominator_floor,
                r.aggregation_method,
                r.direction,
                n.top_n,
                SUM(
                    CASE
                        WHEN p.primary_rank <= n.top_n
                         AND r.rank_position <= n.top_n
                        THEN 1 ELSE 0
                    END
                ) AS overlapping_zone_count
            FROM ds_definition_ranks r
            JOIN primary_rank p
              ON r.zone = p.zone AND r.direction = p.direction
            CROSS JOIN top_n n
            GROUP BY
                r.definition_key,
                r.denominator_floor,
                r.aggregation_method,
                r.direction,
                n.top_n
        )
        SELECT
            definition_key,
            denominator_floor,
            aggregation_method,
            direction,
            top_n,
            overlapping_zone_count,
            overlapping_zone_count::DOUBLE / top_n AS overlap_share
        FROM comparisons
        ORDER BY aggregation_method, denominator_floor, direction, top_n
        """
    )

    outputs = {
        "hvfhv_zone_disruption_score.csv": "SELECT * FROM zone_disruption_score",
        "hvfhv_behavioral_shift.csv": "SELECT * FROM behavioral_shift",
        "hvfhv_ds_z_vs_volume_change.csv": "SELECT * FROM ds_z_vs_volume_change",
        "hvfhv_ds_floor_sensitivity.csv": "SELECT * FROM ds_floor_sensitivity_base",
        "hvfhv_ds_rank_stability.csv": "SELECT * FROM rank_stability",
        "hvfhv_ds_top_zone_overlap.csv": "SELECT * FROM top_zone_overlap",
    }
    for filename, query in outputs.items():
        _copy_csv(con, query, OUTPUT_DIR / filename)

    print("\nPrimary top 10 zones by DS_z:")
    print(
        con.sql(
            """
            SELECT direction, DS_z_rank, zone, Borough, zone_name, N_z, DS_z, DS_z_median
            FROM zone_disruption_score
            ORDER BY DS_z DESC
            LIMIT 10
            """
        )
    )

    print("\nRank stability vs primary floor=$1 mean definition:")
    print(
        con.sql(
            """
            SELECT
                definition_key,
                direction,
                n_zone_direction_pairs,
                ROUND(spearman_rank_corr_vs_primary, 4) AS spearman,
                ROUND(mean_abs_rank_delta, 2) AS mean_abs_delta,
                max_abs_rank_delta
            FROM rank_stability
            WHERE direction = 'all'
            ORDER BY aggregation_method, denominator_floor
            """
        )
    )

    print("\nOutput row counts:")
    for filename, query in outputs.items():
        n_rows = con.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]
        print(f"  {filename}: {n_rows:,}")

    print("\nPipeline complete.")


if __name__ == "__main__":
    build_pipeline()
