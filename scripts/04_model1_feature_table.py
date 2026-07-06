"""
Build the HVFHV Model 1 zone-direction feature table.

This downstream script does not recompute DS_z. It joins the existing HVFHV
disruption-score outputs to 2024-only controls aggregated from standardized
HVFHV parquet files.

Run from the repository root:
    python scripts/04_model1_feature_table.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DISRUPTION_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"
STANDARDIZED_2024_DIR = (
    REPO_ROOT / "data" / "processed" / "00_standardized_trips" / "hvfhv" / "2024"
)
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
MODELING_DIR = REPO_ROOT / "data" / "processed" / "modeling"

DS_Z_PATH = DISRUPTION_DIR / "hvfhv_zone_disruption_score.csv"
BEHAVIORAL_SHIFT_PATH = DISRUPTION_DIR / "hvfhv_behavioral_shift.csv"
DS_Z_VOLUME_PATH = DISRUPTION_DIR / "hvfhv_ds_z_vs_volume_change.csv"
OUTPUT_PATH = MODELING_DIR / "hvfhv_model1_zone_features.csv"
README_PATH = MODELING_DIR / "README.md"

PRIMARY_FLOOR = 1.00
QUARTILE_LABELS = ["Q1 lowest", "Q2", "Q3", "Q4 highest"]

REQUIRED_COLUMNS = [
    "location_id",
    "direction",
    "Borough",
    "zone_name",
    "service_zone",
    "DS_z",
    "DS_z_median",
    "pct_volume_change",
    "delta_volume",
    "n_trips_2024",
    "n_trips_2025",
    "low_n_flag",
    "avg_base_fare_2024",
    "avg_total_cost_2024",
    "avg_trip_distance_2024",
    "avg_trip_duration_2024",
    "log_n_trips_2024",
    "burden_rank",
    "DS_z_quartile",
]


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _sql_path_list(paths: list[Path]) -> str:
    return "[" + ", ".join(f"'{_sql_path(path)}'" for path in paths) + "]"


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def discover_2024_parquets() -> list[Path]:
    if not STANDARDIZED_2024_DIR.exists():
        raise FileNotFoundError(f"Missing input directory: {STANDARDIZED_2024_DIR}")
    files = sorted(STANDARDIZED_2024_DIR.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found under: {STANDARDIZED_2024_DIR}")
    return files


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")


def aggregate_2024_controls(files_2024: list[Path]) -> pd.DataFrame:
    con = duckdb.connect()
    # Keep AVG() output deterministic; parallel floating-point aggregation can reorder sums.
    con.execute("SET threads TO 1")

    query = f"""
    WITH trips AS (
        SELECT
            PULocationID,
            DOLocationID,
            base_passenger_fare,
            passenger_cost_pretip,
            trip_distance_miles,
            trip_duration_seconds
        FROM read_parquet({_sql_path_list(files_2024)})
    ),
    zone_direction AS (
        SELECT
            PULocationID AS location_id,
            'pickup' AS direction,
            base_passenger_fare,
            passenger_cost_pretip,
            trip_distance_miles,
            trip_duration_seconds
        FROM trips
        UNION ALL
        SELECT
            DOLocationID AS location_id,
            'dropoff' AS direction,
            base_passenger_fare,
            passenger_cost_pretip,
            trip_distance_miles,
            trip_duration_seconds
        FROM trips
    )
    SELECT
        CAST(location_id AS BIGINT) AS location_id,
        direction,
        COUNT(*) AS n_trips_2024_duckdb,
        AVG(base_passenger_fare) AS avg_base_fare_2024,
        AVG(passenger_cost_pretip) AS avg_total_cost_2024,
        AVG(trip_distance_miles) AS avg_trip_distance_2024,
        AVG(trip_duration_seconds) AS avg_trip_duration_2024
    FROM zone_direction
    GROUP BY location_id, direction
    ORDER BY direction, location_id
    """
    try:
        return con.execute(query).fetchdf()
    finally:
        con.close()


def load_primary_dsz() -> pd.DataFrame:
    df = pd.read_csv(DS_Z_PATH)
    required = {
        "denominator_floor",
        "zone",
        "direction",
        "Borough",
        "zone_name",
        "service_zone",
        "DS_z",
        "DS_z_median",
        "DS_z_rank",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{DS_Z_PATH} is missing columns: {sorted(missing)}")

    primary = df[np.isclose(df["denominator_floor"], PRIMARY_FLOOR)].copy()
    if primary.empty:
        raise ValueError(f"No denominator_floor={PRIMARY_FLOOR:.2f} rows in {DS_Z_PATH}")

    primary = primary.rename(
        columns={
            "zone": "location_id",
            "DS_z_rank": "burden_rank",
        }
    )
    keep_cols = [
        "location_id",
        "direction",
        "Borough",
        "zone_name",
        "service_zone",
        "DS_z",
        "DS_z_median",
        "burden_rank",
    ]
    return primary[keep_cols]


def load_volume_outcomes() -> pd.DataFrame:
    df = pd.read_csv(DS_Z_VOLUME_PATH)
    required = {"zone", "direction", "pct_volume_change", "n_2024", "n_2025", "low_n_flag"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{DS_Z_VOLUME_PATH} is missing columns: {sorted(missing)}")

    volume = df.rename(
        columns={
            "zone": "location_id",
            "n_2024": "n_trips_2024",
            "n_2025": "n_trips_2025",
        }
    )
    volume["delta_volume"] = volume["n_trips_2025"] - volume["n_trips_2024"]
    keep_cols = [
        "location_id",
        "direction",
        "pct_volume_change",
        "delta_volume",
        "n_trips_2024",
        "n_trips_2025",
        "low_n_flag",
    ]
    return volume[keep_cols]


def _trip_counts_equal(left: pd.Series, right: pd.Series) -> pd.Series:
    """Compare trip counts, treating missing values as zero for QC only."""
    left_norm = left.fillna(0)
    right_norm = right.fillna(0)
    return left_norm.eq(right_norm)


def validate_behavioral_shift(volume: pd.DataFrame) -> tuple[int, int]:
    behavior = pd.read_csv(BEHAVIORAL_SHIFT_PATH)
    required = {"zone", "direction", "n_2024", "n_2025", "pct_volume_change"}
    missing = required - set(behavior.columns)
    if missing:
        raise ValueError(f"{BEHAVIORAL_SHIFT_PATH} is missing columns: {sorted(missing)}")

    behavior = behavior.rename(
        columns={
            "zone": "location_id",
            "n_2024": "n_2024_behavior",
            "n_2025": "n_2025_behavior",
            "pct_volume_change": "pct_volume_change_behavior",
        }
    )
    check = volume.merge(
        behavior[
            [
                "location_id",
                "direction",
                "n_2024_behavior",
                "n_2025_behavior",
                "pct_volume_change_behavior",
            ]
        ],
        on=["location_id", "direction"],
        how="left",
        validate="one_to_one",
    )
    missing_behavior = int(check["n_2025_behavior"].isna().sum())
    count_mismatch = int(
        (
            ~_trip_counts_equal(check["n_trips_2024"], check["n_2024_behavior"])
            | ~_trip_counts_equal(check["n_trips_2025"], check["n_2025_behavior"])
        ).sum()
    )
    return missing_behavior, count_mismatch


def load_zone_lookup() -> pd.DataFrame:
    zones = pd.read_csv(ZONE_LOOKUP_PATH)
    required = {"LocationID", "Borough", "Zone", "service_zone"}
    missing = required - set(zones.columns)
    if missing:
        raise ValueError(f"{ZONE_LOOKUP_PATH} is missing columns: {sorted(missing)}")
    return zones.rename(
        columns={
            "LocationID": "location_id",
            "Borough": "Borough_lookup",
            "Zone": "zone_name_lookup",
            "service_zone": "service_zone_lookup",
        }
    )


def quartile_by_direction(features: pd.DataFrame) -> pd.Series:
    def assign(group: pd.Series) -> pd.Series:
        labels = pd.qcut(
            group.rank(method="first"),
            q=4,
            labels=QUARTILE_LABELS,
        )
        return labels.astype("string")

    return features.groupby("direction", group_keys=False)["DS_z"].apply(assign)


def build_feature_table() -> pd.DataFrame:
    require_file(DS_Z_PATH)
    require_file(BEHAVIORAL_SHIFT_PATH)
    require_file(DS_Z_VOLUME_PATH)
    require_file(ZONE_LOOKUP_PATH)
    files_2024 = discover_2024_parquets()

    print("Inputs:")
    print(f"  DS_z: {_relative(DS_Z_PATH)}")
    print(f"  Behavioral shift: {_relative(BEHAVIORAL_SHIFT_PATH)}")
    print(f"  DS_z vs volume: {_relative(DS_Z_VOLUME_PATH)}")
    print(f"  2024 parquet files: {len(files_2024)} from {_relative(STANDARDIZED_2024_DIR)}")
    print(f"  Zone lookup: {_relative(ZONE_LOOKUP_PATH)}")

    controls_2024 = aggregate_2024_controls(files_2024)
    dsz = load_primary_dsz()
    volume = load_volume_outcomes()
    missing_behavior, count_mismatch = validate_behavioral_shift(volume)
    zones = load_zone_lookup()

    features = (
        dsz.merge(volume, on=["location_id", "direction"], how="left", validate="one_to_one")
        .merge(
            controls_2024,
            on=["location_id", "direction"],
            how="left",
            validate="one_to_one",
        )
        .merge(zones, on="location_id", how="left", validate="many_to_one")
    )

    label_cols = [
        "Borough",
        "zone_name",
        "service_zone",
        "Borough_lookup",
        "zone_name_lookup",
        "service_zone_lookup",
    ]
    for column in label_cols:
        features[column] = features[column].replace("", pd.NA)

    features["Borough"] = features["Borough"].fillna(features["Borough_lookup"])
    features["zone_name"] = features["zone_name"].fillna(features["zone_name_lookup"])
    features["service_zone"] = features["service_zone"].fillna(
        features["service_zone_lookup"]
    )
    features["Borough"] = features["Borough"].fillna("Unknown")
    features["zone_name"] = features["zone_name"].fillna(
        "Zone " + features["location_id"].astype(str)
    )
    features["service_zone"] = features["service_zone"].fillna("Unknown")
    features = features.drop(
        columns=["Borough_lookup", "zone_name_lookup", "service_zone_lookup"]
    )

    features["n_trips_2024"] = features["n_trips_2024"].fillna(
        features["n_trips_2024_duckdb"]
    )
    features["n_trips_2024"] = features["n_trips_2024"].fillna(0)
    features["n_trips_2025"] = features["n_trips_2025"].fillna(0)
    features["delta_volume"] = features["delta_volume"].fillna(
        features["n_trips_2025"] - features["n_trips_2024"]
    )
    features["low_n_flag"] = features["low_n_flag"].fillna(True).astype(bool)

    mismatched_2024_counts = int(
        (~_trip_counts_equal(features["n_trips_2024"], features["n_trips_2024_duckdb"])).sum()
    )
    if mismatched_2024_counts:
        print(
            "WARNING: "
            f"{mismatched_2024_counts} rows have n_trips_2024 values that differ "
            "between DS_z volume output and DuckDB 2024 aggregation."
        )
    if missing_behavior or count_mismatch:
        print(
            "WARNING: behavioral-shift validation found "
            f"{missing_behavior} unmerged rows and {count_mismatch} count mismatches."
        )

    features["log_n_trips_2024"] = np.nan
    positive_baseline = features["n_trips_2024"] > 0
    features.loc[positive_baseline, "log_n_trips_2024"] = np.log(
        features.loc[positive_baseline, "n_trips_2024"]
    )
    features["DS_z_quartile"] = quartile_by_direction(features)

    features = features[REQUIRED_COLUMNS].sort_values(
        ["direction", "burden_rank", "location_id"], kind="stable"
    )
    return features


def write_readme() -> None:
    README_PATH.write_text(
        """# Modeling Outputs

This folder contains small modeling-ready CSV outputs built from committed
disruption-score summaries and local standardized parquet files.

## `hvfhv_model1_zone_features.csv`

Zone-direction feature table for the HVFHV Model 1 burden-vs-volume analysis.
The table joins the existing HVFHV DS_z outputs to 2024-only controls. It does
not rerun or change DS_z.

### Outcomes

- `pct_volume_change`: 2025 vs 2024 trip-count percent change.
- `delta_volume`: `n_trips_2025 - n_trips_2024`.
- `n_trips_2025`: post-policy trip count. Included for outcome accounting, not
  as an explanatory control.

### Allowed 2024 Controls

- `n_trips_2024`
- `log_n_trips_2024`
- `avg_base_fare_2024`
- `avg_total_cost_2024`
- `avg_trip_distance_2024`
- `avg_trip_duration_2024`

All allowed controls are computed only from Feb-Jun 2024 standardized HVFHV
parquets. Duration is included as a baseline control candidate but should be
used cautiously because traffic conditions can affect duration.

### Descriptive Fields

- `location_id`, `direction`, `Borough`, `zone_name`, `service_zone`
- `DS_z`, `DS_z_median`, `burden_rank`, `DS_z_quartile`
- `low_n_flag`

Rows with no 2024 baseline (`n_trips_2024 = 0`) keep `pct_volume_change` and 2024
average controls missing because the percent change and baseline averages are
undefined. They remain in the table for transparency and should be treated as
low-N edge cases.

### Regeneration

From the repository root (requires local Feb-Jun 2024 HVFHV standardized
parquets under `data/processed/00_standardized_trips/hvfhv/2024/`):

```bash
python scripts/04_model1_feature_table.py
```

DuckDB aggregation uses `SET threads TO 1` for deterministic float averages.

### Forbidden Post-Policy Controls

Do not use 2025 post-policy cost, fare, distance, duration, driver pay, trip
counts, `pct_volume_change`, or `delta_volume` as explanatory controls. Do not
include both DS_z and `relative_cbd_burden` as independent features unless the
run is explicitly labeled as a sensitivity check. Treat `cbd_congestion_fee` as
treatment/exposure, not a normal control.

These features support descriptive and inferential Model 1 analysis. They are
not causal proof.
""",
        encoding="utf-8",
    )


def main() -> None:
    MODELING_DIR.mkdir(parents=True, exist_ok=True)
    features = build_feature_table()
    features.to_csv(OUTPUT_PATH, index=False)
    write_readme()

    missing_summary = features.isna().sum()
    nonzero_missing = missing_summary[missing_summary > 0]

    print("\nOutputs:")
    print(f"  Wrote {len(features):,} rows to {_relative(OUTPUT_PATH)}")
    print(f"  Wrote README to {_relative(README_PATH)}")
    print("\nMissing values by required column:")
    if nonzero_missing.empty:
        print("  None")
    else:
        for column, n_missing in nonzero_missing.items():
            print(f"  {column}: {int(n_missing):,}")

    allowed_controls = [
        "n_trips_2024",
        "log_n_trips_2024",
        "avg_base_fare_2024",
        "avg_total_cost_2024",
        "avg_trip_distance_2024",
        "avg_trip_duration_2024",
    ]
    print("\nAllowed 2024 controls:")
    for column in allowed_controls:
        print(f"  - {column}")

    print("\nLeakage warning:")
    print("  Use 2024 controls only. Treat 2025 counts and volume change as outcomes.")


if __name__ == "__main__":
    main()
