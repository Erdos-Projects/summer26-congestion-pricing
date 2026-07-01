"""
Manhattan and within-borough robustness checks for HVFHV DS_z correlations.

This is a small downstream check using the existing DS_z vs. volume-change
export. It does not rerun the disruption-score pipeline or change the DS_z
definition. Run from the repository root:
    python scripts/EDA_adithya/03_manhattan_robustness.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"
INPUT_PATH = OUTPUT_DIR / "hvfhv_ds_z_vs_volume_change.csv"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
BOROUGH_OUTPUT_PATH = OUTPUT_DIR / "hvfhv_borough_correlation.csv"
MANHATTAN_OUTPUT_PATH = OUTPUT_DIR / "hvfhv_within_manhattan_correlation.csv"

MIN_N_FOR_CORRELATION = 3
X_COL = "DS_z"
Y_COL = "pct_volume_change"


def ensure_zone_fields(df: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """Attach Borough and zone_name from the TLC lookup when missing."""
    missing_borough = "Borough" not in df.columns
    missing_zone_name = "zone_name" not in df.columns
    missing_service_zone = "service_zone" not in df.columns

    if not (missing_borough or missing_zone_name or missing_service_zone):
        return df.copy()

    lookup_cols = ["LocationID", "Borough", "Zone", "service_zone"]
    missing_lookup_cols = set(lookup_cols) - set(zones.columns)
    if missing_lookup_cols:
        raise ValueError(
            "Zone lookup is missing required columns: "
            + ", ".join(sorted(missing_lookup_cols))
        )

    lookup = zones[lookup_cols].rename(
        columns={
            "Borough": "Borough_lookup",
            "Zone": "Zone_lookup",
            "service_zone": "service_zone_lookup",
        }
    )
    merged = df.merge(
        lookup,
        left_on="zone",
        right_on="LocationID",
        how="left",
    )

    if missing_borough:
        merged["Borough"] = merged["Borough_lookup"].fillna("Other")
    else:
        merged["Borough"] = merged["Borough"].fillna(merged["Borough_lookup"])

    if missing_zone_name:
        merged["zone_name"] = merged["Zone_lookup"].fillna(
            "Zone " + merged["zone"].astype(str)
        )
    else:
        merged["zone_name"] = merged["zone_name"].fillna(merged["Zone_lookup"])

    if missing_service_zone:
        merged["service_zone"] = merged["service_zone_lookup"]
    else:
        merged["service_zone"] = merged["service_zone"].fillna(
            merged["service_zone_lookup"]
        )

    drop_cols = [
        col
        for col in ["LocationID", "Borough_lookup", "Zone_lookup", "service_zone_lookup"]
        if col in merged.columns
    ]
    return merged.drop(columns=drop_cols)


def pearson_on_ranks(data: pd.DataFrame) -> float:
    """Spearman: Pearson correlation on average ranks (pandas default)."""
    ranks = data[[X_COL, Y_COL]].rank(method="average")
    return ranks[X_COL].corr(ranks[Y_COL], method="pearson")


def correlation_row(
    data: pd.DataFrame,
    group_type: str,
    group_name: str,
    borough: str | None = None,
    direction: str | None = None,
) -> dict[str, object]:
    n_rows = len(data)
    sufficient_n = n_rows >= MIN_N_FOR_CORRELATION

    if sufficient_n:
        pearson = data[X_COL].corr(data[Y_COL], method="pearson")
        spearman = pearson_on_ranks(data)
    else:
        pearson = pd.NA
        spearman = pd.NA

    return {
        "group_type": group_type,
        "group_name": group_name,
        "borough": borough,
        "direction": direction,
        "n_rows": n_rows,
        "pearson_corr": pearson,
        "spearman_corr": spearman,
        "sufficient_n": sufficient_n,
    }


def build_correlations(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    rows.append(correlation_row(df, "all_zones", "all zones"))

    manhattan = df[df["Borough"] == "Manhattan"]
    non_manhattan = df[df["Borough"] != "Manhattan"]
    rows.append(
        correlation_row(
            manhattan,
            "manhattan_split",
            "Manhattan only",
            borough="Manhattan",
        )
    )
    rows.append(
        correlation_row(non_manhattan, "manhattan_split", "non-Manhattan only")
    )

    for borough, borough_df in df.groupby("Borough", dropna=False, sort=True):
        borough_name = "Missing Borough" if pd.isna(borough) else str(borough)
        rows.append(
            correlation_row(
                borough_df,
                "borough",
                borough_name,
                borough=borough_name,
            )
        )

    for direction, direction_df in df.groupby("direction", dropna=False, sort=True):
        direction_name = "Missing direction" if pd.isna(direction) else str(direction)
        rows.append(
            correlation_row(
                direction_df,
                "direction",
                f"{direction_name} only",
                direction=direction_name,
            )
        )

    for (borough, direction), group_df in df.groupby(
        ["Borough", "direction"], dropna=False, sort=True
    ):
        borough_name = "Missing Borough" if pd.isna(borough) else str(borough)
        direction_name = "Missing direction" if pd.isna(direction) else str(direction)
        rows.append(
            correlation_row(
                group_df,
                "borough_direction",
                f"{borough_name} {direction_name}",
                borough=borough_name,
                direction=direction_name,
            )
        )

    return pd.DataFrame(rows)


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing {INPUT_PATH}. Run scripts/EDA_adithya/01_pipeline.py first."
        )
    if not ZONE_LOOKUP_PATH.exists():
        raise FileNotFoundError(f"Missing local zone lookup file: {ZONE_LOOKUP_PATH}")

    df = pd.read_csv(INPUT_PATH)
    zones = pd.read_csv(ZONE_LOOKUP_PATH)
    df = ensure_zone_fields(df, zones)

    required_cols = {"zone", "direction", "Borough", X_COL, Y_COL}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(
            "Input table is missing required columns: "
            + ", ".join(sorted(missing_cols))
        )

    input_rows = len(df)
    df = df[df[Y_COL].notna()].copy()
    excluded_rows = input_rows - len(df)

    correlations = build_correlations(df)
    correlations.to_csv(BOROUGH_OUTPUT_PATH, index=False)

    manhattan_correlations = correlations[
        (correlations["borough"] == "Manhattan")
        | (correlations["group_name"] == "Manhattan only")
    ].copy()
    manhattan_correlations.to_csv(MANHATTAN_OUTPUT_PATH, index=False)

    print(f"Input rows: {input_rows:,}")
    print(f"Excluded rows with null {Y_COL}: {excluded_rows:,}")
    print(f"Rows used for correlations: {len(df):,}")
    print(f"Wrote {len(correlations):,} rows to {BOROUGH_OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(
        "Wrote "
        f"{len(manhattan_correlations):,} rows to "
        f"{MANHATTAN_OUTPUT_PATH.relative_to(REPO_ROOT)}"
    )

    display_cols = ["group_type", "group_name", "n_rows", "pearson_corr", "spearman_corr"]
    print(correlations[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
