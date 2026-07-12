"""
Zone lookup merge for the HVFHV DS_z scatter data.

Uses the local TLC zone lookup file and the current disruption-score output
folder. Run from the repository root:
    python scripts/02_zone_lookup_merge.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"
INPUT_PATH = OUTPUT_DIR / "hvfhv_ds_z_vs_volume_change.csv"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
OUTPUT_PATH = OUTPUT_DIR / "hvfhv_scatter_data.json"


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing {INPUT_PATH}. Run scripts/01_pipeline.py first."
        )
    if not ZONE_LOOKUP_PATH.exists():
        raise FileNotFoundError(f"Missing local zone lookup file: {ZONE_LOOKUP_PATH}")

    df = pd.read_csv(INPUT_PATH)
    zones = pd.read_csv(ZONE_LOOKUP_PATH)

    if {"Borough", "zone_name"}.issubset(df.columns):
        merged = df.copy()
    else:
        merged = df.merge(zones, left_on="zone", right_on="LocationID", how="left")
        merged["zone_name"] = merged["Zone"].fillna("Zone " + merged["zone"].astype(str))
        merged["Borough"] = merged["Borough"].fillna("Other")

    # Match the formal HVFHV Model 1 sample used by the notebook and result tables.
    if "low_n_flag" in merged.columns:
        merged = merged.loc[~merged["low_n_flag"].astype(bool)].copy()
    merged = merged.loc[merged["pct_volume_change"].notna()].copy()

    print(merged[["DS_z", "pct_volume_change"]].describe())
    print(merged["Borough"].value_counts(dropna=False))

    keep_cols = [
        "zone",
        "direction",
        "DS_z",
        "DS_z_median",
        "N_z",
        "pct_volume_change",
        "n_2024",
        "n_2025",
        "zone_name",
        "Borough",
    ]
    present_cols = [col for col in keep_cols if col in merged.columns]
    merged[present_cols].to_json(OUTPUT_PATH, orient="records")
    print(f"Exported {len(merged):,} rows to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
