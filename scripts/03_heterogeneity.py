"""
Heterogeneity analysis
======================
Two analyses:

A) Borough stratification — does the DS_z vs. volume-change correlation
   hold within Manhattan alone, or is it a borough composition artifact?

B) Trip-length disaggregation — does the fee burden → volume decline
   relationship differ for short vs. medium vs. long trips?

Requires: duckdb, output files from 01_pipeline.py, taxi_zone_lookup.csv
Input:    output/ds_z.parquet, output/behavioral_shift.parquet,
          data/2025-*.parquet (for trip-length DS_z recomputation)
Output:   output/ds_z_by_length.parquet, printed correlation tables
"""

import duckdb
import os

con = duckdb.connect()
os.makedirs("output", exist_ok=True)

FILES_2025 = "data/2025-*.parquet"   # same as 01_pipeline.py

con.sql("CREATE VIEW ds_z AS SELECT * FROM read_parquet('output/ds_z.parquet')")
con.sql("CREATE VIEW bs AS SELECT * FROM read_parquet('output/behavioral_shift.parquet')")
con.sql("CREATE TABLE zone_lookup AS SELECT * FROM read_csv('taxi_zone_lookup.csv')")

# ── A) Borough stratification ──────────────────────────────────────────────────
# Airport zones (1=EWR, 132=JFK, 138=LaGuardia) are treated as a separate class
# — captive demand, near-zero average volume change, n=5 (too small to interpret).
print("=== A) Building analysis table ===")
con.sql("""
    CREATE OR REPLACE TABLE analysis AS
    SELECT
        d.zone, d.direction, d.DS_z_median, d.DS_z_mean, d.N_z,
        b.pct_volume_change, b.n_2024, b.n_2025, b.low_n_flag,
        z.Borough AS borough, z.Zone AS zone_name, z.service_zone,
        CASE
            WHEN d.zone IN (1, 132, 138) THEN 'airport'
            WHEN z.Borough = 'Manhattan'  THEN 'manhattan'
            ELSE 'outer_borough'
        END AS zone_type
    FROM ds_z d
    JOIN bs b          ON d.zone = b.zone AND d.direction = b.direction
    JOIN zone_lookup z ON d.zone = z.LocationID
    WHERE b.pct_volume_change IS NOT NULL
      AND b.low_n_flag = FALSE
""")

print("\n=== A) Stratified correlation ===")
print(con.sql("""
    SELECT
        zone_type,
        COUNT(*) AS n_zone_dirs,
        CORR(DS_z_median, pct_volume_change) AS pearson_r,
        AVG(DS_z_median) AS avg_DS_z,
        AVG(pct_volume_change) AS avg_vol_change
    FROM analysis
    GROUP BY zone_type
    ORDER BY zone_type
"""))

print("\n=== A) Quartile breakdown by stratum ===")
print(con.sql("""
    WITH quartiled AS (
        SELECT *,
            NTILE(4) OVER (PARTITION BY zone_type, direction ORDER BY DS_z_median)
                AS ds_quartile
        FROM analysis
    )
    SELECT zone_type, direction, ds_quartile,
           COUNT(*) AS n, AVG(DS_z_median) AS avg_DS_z,
           AVG(pct_volume_change) AS avg_vol_change
    FROM quartiled
    GROUP BY zone_type, direction, ds_quartile
    ORDER BY zone_type, direction, ds_quartile
"""))

# Manhattan pickup Q1 outlier check (Randalls Island, zone 194)
print("\n=== A) Manhattan pickup Q1 zones (checking for outliers) ===")
print(con.sql("""
    WITH quartiled AS (
        SELECT *,
            NTILE(4) OVER (PARTITION BY direction ORDER BY DS_z_median) AS ds_quartile
        FROM analysis WHERE zone_type = 'manhattan'
    )
    SELECT zone, zone_name, DS_z_median, pct_volume_change, N_z
    FROM quartiled
    WHERE direction = 'pickup' AND ds_quartile = 1
    ORDER BY pct_volume_change DESC
"""))

print("\n=== A) Manhattan correlation excluding zone 194 (Randalls Island) ===")
print(con.sql("""
    SELECT
        CORR(DS_z_median, pct_volume_change) AS r_manhattan_excl_194,
        COUNT(*) AS n
    FROM analysis
    WHERE zone_type = 'manhattan' AND zone != 194
"""))


# ── B) Trip-length disaggregation ─────────────────────────────────────────────
# Threshold: p25 = 1.80 miles, p75 = 7.86 miles (from 2025 fee-charged trips).
# Recompute DS_z separately for short / medium / long trips within each zone.
# Only ~213 zone×direction pairs have >= 30 short trips; the missing ones are
# exclusively outer-borough (confirmed by inspection). Trip-length results
# therefore apply to Manhattan only.

THRESHOLD_P25 = 1.80   # miles
THRESHOLD_P75 = 7.86   # miles
MIN_N_SHORT   = 30     # minimum short trips for stable median

print("\n\n=== B) Trip-length thresholds (verify against your data) ===")
print(con.sql(f"""
    SELECT
        PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY trip_distance_miles) AS median_miles,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY trip_distance_miles) AS p25_miles,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY trip_distance_miles) AS p75_miles,
        AVG(trip_distance_miles) AS mean_miles,
        COUNT(*) AS n
    FROM read_parquet('{FILES_2025}')
    WHERE charged_cbd_flag = 1
      AND ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) > 0
"""))

print("\n=== B) Computing DS_z by trip length (full 2025 parquet scan) ===")
con.sql(f"""
    CREATE OR REPLACE TABLE ds_z_by_length AS
    WITH cleaned AS (
        SELECT
            PULocationID, DOLocationID,
            CASE
                WHEN trip_distance_miles < {THRESHOLD_P25}  THEN 'short'
                WHEN trip_distance_miles <= {THRESHOLD_P75} THEN 'medium'
                ELSE                                             'long'
            END AS trip_length,
            cbd_congestion_fee
                / ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS fee_burden
        FROM read_parquet('{FILES_2025}')
        WHERE charged_cbd_flag = 1
          AND ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) > 0
    ),
    pickup AS (
        SELECT PULocationID AS zone, 'pickup' AS direction, trip_length,
               MEDIAN(fee_burden) AS DS_z_median, COUNT(*) AS N_z
        FROM cleaned GROUP BY PULocationID, trip_length
    ),
    dropoff AS (
        SELECT DOLocationID AS zone, 'dropoff' AS direction, trip_length,
               MEDIAN(fee_burden) AS DS_z_median, COUNT(*) AS N_z
        FROM cleaned GROUP BY DOLocationID, trip_length
    )
    SELECT * FROM pickup UNION ALL SELECT * FROM dropoff
    ORDER BY zone, direction, trip_length
""")
print(con.sql("SELECT trip_length, COUNT(*) AS zone_dirs FROM ds_z_by_length GROUP BY trip_length"))

print("\n=== B) Correlation by trip length (Manhattan, n_short >= 30) ===")
print(con.sql(f"""
    WITH pivoted AS (
        SELECT zone, direction,
               MAX(CASE WHEN trip_length='short'  THEN DS_z_median END) AS DS_z_short,
               MAX(CASE WHEN trip_length='medium' THEN DS_z_median END) AS DS_z_medium,
               MAX(CASE WHEN trip_length='long'   THEN DS_z_median END) AS DS_z_long,
               MAX(CASE WHEN trip_length='short'  THEN N_z END)         AS n_short
        FROM ds_z_by_length GROUP BY zone, direction
    ),
    joined AS (
        SELECT p.*, b.pct_volume_change, z.Borough
        FROM pivoted p
        JOIN bs b          ON p.zone = b.zone AND p.direction = b.direction
        JOIN zone_lookup z ON p.zone = z.LocationID
        WHERE b.pct_volume_change IS NOT NULL
          AND b.low_n_flag = FALSE
          AND z.Borough = 'Manhattan'
          AND p.n_short >= {MIN_N_SHORT}
    )
    SELECT
        direction,
        CORR(DS_z_short,  pct_volume_change) AS r_short,
        CORR(DS_z_medium, pct_volume_change) AS r_medium,
        CORR(DS_z_long,   pct_volume_change) AS r_long,
        CORR(DS_z_short - DS_z_long, pct_volume_change) AS r_differential,
        COUNT(*) AS n
    FROM joined
    GROUP BY direction
    ORDER BY direction
"""))

print("\n=== B) Quartile breakdown by trip length (Manhattan) ===")
print(con.sql(f"""
    WITH pivoted AS (
        SELECT zone, direction,
               MAX(CASE WHEN trip_length='short'  THEN DS_z_median END) AS DS_z_short,
               MAX(CASE WHEN trip_length='medium' THEN DS_z_median END) AS DS_z_medium,
               MAX(CASE WHEN trip_length='long'   THEN DS_z_median END) AS DS_z_long,
               MAX(CASE WHEN trip_length='short'  THEN N_z END)         AS n_short
        FROM ds_z_by_length GROUP BY zone, direction
    ),
    joined AS (
        SELECT p.*, b.pct_volume_change, z.Borough
        FROM pivoted p
        JOIN bs b          ON p.zone = b.zone AND p.direction = b.direction
        JOIN zone_lookup z ON p.zone = z.LocationID
        WHERE b.pct_volume_change IS NOT NULL
          AND b.low_n_flag = FALSE
          AND z.Borough = 'Manhattan'
          AND p.n_short >= {MIN_N_SHORT}
    ),
    quartiled AS (
        SELECT *,
            NTILE(4) OVER (ORDER BY DS_z_short)  AS q_short,
            NTILE(4) OVER (ORDER BY DS_z_medium) AS q_medium,
            NTILE(4) OVER (ORDER BY DS_z_long)   AS q_long
        FROM joined
    )
    SELECT 'short'  AS length, q_short  AS quartile, COUNT(*) AS n,
           AVG(DS_z_short)  AS avg_DS_z, AVG(pct_volume_change) AS avg_vol_change
    FROM quartiled GROUP BY q_short
    UNION ALL
    SELECT 'medium', q_medium, COUNT(*),
           AVG(DS_z_medium), AVG(pct_volume_change)
    FROM quartiled GROUP BY q_medium
    UNION ALL
    SELECT 'long', q_long, COUNT(*),
           AVG(DS_z_long), AVG(pct_volume_change)
    FROM quartiled GROUP BY q_long
    ORDER BY length, quartile
"""))

# Export
con.sql("COPY ds_z_by_length TO 'output/ds_z_by_length.parquet' (FORMAT PARQUET)")
print("\nHeterogeneity analysis complete. Outputs written to output/")
