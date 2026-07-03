"""
Build the 20,000-row representative Yellow-only trip-level sample (proportional stratified
by year x month, fixed seed). Reuses the sampling/enrichment helpers from
`make_representative_sample_20k.py`, reads the standardized yellow parquet, and writes the
sample CSV plus its composition and sampling notes under data/processed/{samples,qc}/.

Run from the repo root:
    python scripts/make_yellow_sample_20k.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the combined maker's tested helpers so flag/enrichment logic has one source of truth.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from make_representative_sample_20k import (  # noqa: E402
    MONTHS,
    RANDOM_STATE,
    REPO_ROOT,
    STANDARDIZED_DIR,
    TARGET_ROWS,
    YEARS,
    count_parquet_rows,
    enrich_sample,
    largest_remainder_allocation,
    output_column_order,
    parquet_path,
    sample_rows_from_parquet,
)

SERVICE = "yellow"

SAMPLE_PATH = (
    REPO_ROOT
    / "data"
    / "processed"
    / "samples"
    / "yellow_taxi_trip_level_sample_20k_representative.csv"
)
COMPOSITION_PATH = (
    REPO_ROOT
    / "data"
    / "processed"
    / "qc"
    / "yellow_taxi_trip_level_sample_20k_representative_composition.csv"
)
NOTES_PATH = (
    REPO_ROOT
    / "data"
    / "processed"
    / "qc"
    / "yellow_taxi_trip_level_sample_20k_representative_notes.csv"
)


def stratum_key(year: int, month: int) -> str:
    return f"{SERVICE}_{year}_{month:02d}"


def build_yellow_sample(seed: int = RANDOM_STATE) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Two-pass stratified sample over yellow year x month: count, allocate, then draw."""
    notes: list[dict] = []
    populations: dict[str, int] = {}
    meta: dict[str, tuple[int, int, Path]] = {}

    for year in YEARS:
        for month in MONTHS:
            key = stratum_key(year, month)
            path = parquet_path(SERVICE, year, month)
            meta[key] = (year, month, path)
            if not path.exists():
                populations[key] = 0
                notes.append(
                    {
                        "topic": "skipped_file",
                        "note": f"Missing standardized file: {path.relative_to(REPO_ROOT).as_posix()}",
                    }
                )
                continue
            populations[key] = count_parquet_rows(path)

    allocation = largest_remainder_allocation(populations, TARGET_ROWS)
    parts: list[pd.DataFrame] = []
    composition_rows: list[dict] = []

    for i, key in enumerate(sorted(allocation.keys())):
        year, month, path = meta[key]
        pop_n = populations[key]
        sample_n = allocation[key]
        composition_rows.append(
            {
                "service_type": SERVICE,
                "year": year,
                "month": month,
                "sampling_stratum": key,
                "stratum_population_n": pop_n,
                "stratum_sample_n": sample_n,
                "sample_weight": (pop_n / sample_n) if sample_n > 0 else pd.NA,
            }
        )
        if sample_n <= 0 or pop_n == 0:
            continue

        draw_seed = seed + i * 9973
        drawn = sample_rows_from_parquet(path, sample_n, draw_seed)
        actual_n = len(drawn)
        if actual_n < sample_n:
            notes.append(
                {
                    "topic": "shortage",
                    "note": f"Stratum {key}: requested {sample_n}, drew {actual_n} (population {pop_n:,}).",
                }
            )
            composition_rows[-1]["stratum_sample_n"] = actual_n
            composition_rows[-1]["sample_weight"] = pop_n / actual_n if actual_n > 0 else pd.NA

        drawn["sampling_stratum"] = key
        drawn["stratum_population_n"] = pop_n
        drawn["stratum_sample_n"] = actual_n
        drawn["sample_weight"] = pop_n / actual_n if actual_n > 0 else pd.NA
        parts.append(drawn)

    sample = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    sample = enrich_sample(sample)

    if len(sample) > TARGET_ROWS:
        sample = sample.sample(n=TARGET_ROWS, random_state=RANDOM_STATE).reset_index(drop=True)
        notes.append(
            {"topic": "trim", "note": f"Trimmed oversample to exactly {TARGET_ROWS:,} rows."}
        )

    if len(sample):
        sample.insert(0, "sample_row_id", np.arange(1, len(sample) + 1))

    composition = pd.DataFrame(composition_rows).sort_values(["year", "month"])
    notes.append(
        {
            "topic": "sampling_method",
            "note": (
                "Proportional stratified random sampling by year x month over standardized "
                f"yellow trips; random_state={seed}; per-stratum seed = {seed} + i*9973; "
                f"target rows={TARGET_ROWS:,}. Not balanced; preserves natural charged_cbd_flag mix."
            ),
        }
    )
    return sample, composition, notes


def main() -> None:
    if not STANDARDIZED_DIR.exists():
        raise FileNotFoundError(
            f"{STANDARDIZED_DIR} not found. Run scripts/standardize_trips.py first."
        )

    sample, composition, notes = build_yellow_sample()

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPOSITION_PATH.parent.mkdir(parents=True, exist_ok=True)

    out_cols = output_column_order(sample)
    sample[out_cols].to_csv(SAMPLE_PATH, index=False)
    composition.to_csv(COMPOSITION_PATH, index=False)
    pd.DataFrame(notes).to_csv(NOTES_PATH, index=False)

    print(f"1. Yellow 20K representative sample: {SAMPLE_PATH.relative_to(REPO_ROOT).as_posix()}")
    print(f"2. Row count: {len(sample):,}")
    if len(sample):
        comp = (
            sample.groupby(["year", "month"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(["year", "month"])
        )
        print("\n3. Counts by year x month:")
        print(comp.to_string(index=False))


if __name__ == "__main__":
    main()
