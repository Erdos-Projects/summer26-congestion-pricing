"""
Build a 20,000-row representative trip-level CSV for teammate EDA.

Uses proportional stratified random sampling by service_type × year × month from
standardized monthly parquet files (one file at a time; memory-safe index sampling).

Does not modify data/raw/ or the existing 100-row balanced sample.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARDIZED_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips"
SAMPLE_PATH = (
    REPO_ROOT / "data" / "processed" / "samples" / "trip_level_sample_20k_representative.csv"
)
COMPOSITION_PATH = (
    REPO_ROOT
    / "data"
    / "processed"
    / "qc"
    / "trip_level_sample_20k_representative_composition.csv"
)
NOTES_PATH = (
    REPO_ROOT / "data" / "processed" / "qc" / "trip_level_sample_20k_representative_notes.csv"
)

SERVICES = ("yellow", "hvfhv")
YEARS = (2024, 2025)
MONTHS = (2, 3, 4, 5, 6)
TARGET_ROWS = 20_000
RANDOM_STATE = 42

DST_SPRING_FORWARD: dict[int, date] = {
    2024: date(2024, 3, 10),
    2025: date(2025, 3, 9),
}

YELLOW_PAYMENT_LABELS: dict[int, str] = {
    0: "Flex Fare",
    1: "Credit card",
    2: "Cash",
    3: "No charge",
    4: "Dispute",
    5: "Unknown",
    6: "Voided trip",
}

REQUIRED_COLUMNS = [
    "service_type",
    "year",
    "month",
    "pickup_datetime",
    "dropoff_datetime",
    "pickup_date",
    "pickup_hour",
    "day_of_week",
    "PULocationID",
    "DOLocationID",
    "trip_distance_miles",
    "trip_duration_seconds",
    "cbd_congestion_fee",
    "charged_cbd_flag",
    "congestion_surcharge",
    "tolls",
    "airport_fee",
    "passenger_cost_pretip",
    "passenger_cost_excl_cbd",
    "relative_cbd_burden",
    "source_file",
]

METADATA_COLUMNS = [
    "sample_row_id",
    "sampling_stratum",
    "stratum_population_n",
    "stratum_sample_n",
    "sample_weight",
]

YELLOW_OPTIONAL_COLUMNS = [
    "payment_type",
    "passenger_count",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "RatecodeID",
    "yellow_payment_type_label",
    "yellow_card_or_cash_flag",
    "flex_fare_flag",
    "irregular_payment_flag",
    "yellow_no_charge_dispute_void_flag",
    "yellow_payment_unknown_flag",
    "yellow_payment_review_flag",
]

HVFHV_OPTIONAL_COLUMNS = [
    "hvfhs_license_num",
    "base_passenger_fare",
    "bcf",
    "sales_tax",
    "tips",
    "driver_pay",
    "shared_request_flag",
    "shared_match_flag",
]

QC_FLAG_COLUMNS = [
    "burden_eligible_flag",
    "passenger_cost_nonpositive_flag",
    "negative_cbd_fee_flag",
    "zero_distance_flag",
    "very_long_duration_flag",
    "very_long_distance_flag",
    "negative_distance_flag",
    "nonpositive_duration_flag",
    "invalid_timestamp_flag",
    "month_mismatch_flag",
    "missing_zone_flag",
    "any_negative_cost_component_flag",
    "possible_refund_or_adjustment_flag",
    "dst_transition_day_flag",
    "dst_transition_window_flag",
]

HVFHV_COST_COMPONENTS = [
    "base_passenger_fare",
    "tolls",
    "bcf",
    "sales_tax",
    "congestion_surcharge",
    "airport_fee",
    "cbd_congestion_fee",
]

UNAVAILABLE_FLAG_NOTES = [
    {
        "topic": "qc_flags_removed_at_standardization",
        "note": (
            "Standardized trip files already drop rows with invalid timestamps, "
            "month mismatches, missing zones, negative distance, non-positive duration, "
            "negative CBD fees, and non-positive passenger_cost_pretip. Those anomaly "
            "types cannot appear in this sample; corresponding flags are included for "
            "schema consistency but will be False unless derivable from retained rows."
        ),
    },
    {
        "topic": "hvfhv_passenger_cost_pretip",
        "note": (
            "HVFHV passenger_cost_pretip is reconstructed from TLC fee components and "
            "may not capture app-specific discounts, refunds, credits, or user-specific "
            "pricing adjustments."
        ),
    },
    {
        "topic": "possible_refund_or_adjustment_flag",
        "note": (
            "This flag marks rows for manual review only; it does not assert that a "
            "refund or discount definitely occurred."
        ),
    },
    {
        "topic": "dst_transition_flags",
        "note": (
            "March DST spring-forward rows are flagged (not removed). "
            "2024 transition date: 2024-03-10; 2025 transition date: 2025-03-09. "
            "dst_transition_window_flag is True when pickup or dropoff hour is 1–3 AM "
            "on a transition day."
        ),
    },
    {
        "topic": "aggregate_analysis",
        "note": (
            "Use sample_weight for aggregate estimates from this sample. Final zone-level "
            "and OD-level analysis should eventually use full-data aggregates, not only "
            "this 20K extract."
        ),
    },
]


def stratum_key(service: str, year: int, month: int) -> str:
    return f"{service}_{year}_{month:02d}"


def parquet_path(service: str, year: int, month: int) -> Path:
    return STANDARDIZED_DIR / service / str(year) / f"{month:02d}.parquet"


def discover_strata() -> list[tuple[str, int, int, Path]]:
    """Return (service, year, month, path) for each expected monthly file."""
    strata: list[tuple[str, int, int, Path]] = []
    for service in SERVICES:
        for year in YEARS:
            for month in MONTHS:
                path = parquet_path(service, year, month)
                strata.append((service, year, month, path))
    return strata


def count_parquet_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return pq.ParquetFile(path).metadata.num_rows


def largest_remainder_allocation(
    populations: dict[str, int], target: int
) -> dict[str, int]:
    """
    Allocate `target` rows across strata proportional to population counts.

    Uses largest-remainder rounding for a deterministic total of exactly `target`.
    Caps each stratum at its population and redistributes any shortfall iteratively.
    """
    keys = sorted(populations.keys())
    pops = [populations[k] for k in keys]
    total_pop = sum(pops)
    if total_pop == 0:
        return {k: 0 for k in keys}

    raw = [target * p / total_pop for p in pops]
    alloc = [int(r) for r in raw]
    remainder = target - sum(alloc)
    frac_order = sorted(
        range(len(keys)),
        key=lambda i: (raw[i] - alloc[i], pops[i], keys[i]),
        reverse=True,
    )
    for i in range(remainder):
        alloc[frac_order[i]] += 1

    result = {k: alloc[i] for i, k in enumerate(keys)}

    while True:
        shortfall = 0
        eligible: list[str] = []
        for k in keys:
            pop = populations[k]
            if result[k] > pop:
                shortfall += result[k] - pop
                result[k] = pop
            elif result[k] < pop:
                eligible.append(k)

        if shortfall == 0:
            break
        if not eligible:
            break

        headroom = {k: populations[k] - result[k] for k in eligible}
        headroom_total = sum(headroom.values())
        if headroom_total == 0:
            break

        add_raw = {k: shortfall * headroom[k] / headroom_total for k in eligible}
        add_floor = {k: int(add_raw[k]) for k in eligible}
        to_add = sum(add_floor.values())
        add_order = sorted(
            eligible,
            key=lambda k: (add_raw[k] - add_floor[k], headroom[k], k),
            reverse=True,
        )
        for i in range(shortfall - to_add):
            add_floor[add_order[i % len(add_order)]] += 1
        for k in eligible:
            result[k] += add_floor[k]

    return result


def sample_rows_from_parquet(path: Path, n: int, seed: int) -> pd.DataFrame:
    """Draw n random rows without replacement using global row indices."""
    pf = pq.ParquetFile(path)
    population = pf.metadata.num_rows
    if population == 0 or n <= 0:
        return pd.DataFrame()

    n = min(n, population)
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(population, size=n, replace=False))

    parts: list[pd.DataFrame] = []
    idx_pos = 0
    offset = 0
    for rg in range(pf.num_row_groups):
        rg_rows = pf.metadata.row_group(rg).num_rows
        rg_end = offset + rg_rows
        local_indices: list[int] = []
        while idx_pos < len(indices) and indices[idx_pos] < rg_end:
            if indices[idx_pos] >= offset:
                local_indices.append(int(indices[idx_pos] - offset))
            idx_pos += 1
        if local_indices:
            df = pf.read_row_group(rg).to_pandas()
            parts.append(df.iloc[local_indices])
        offset = rg_end
        if idx_pos >= len(indices):
            break

    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def add_yellow_payment_flags(df: pd.DataFrame) -> pd.DataFrame:
    if "payment_type" not in df.columns:
        return df

    pt = _safe_numeric(df["payment_type"])
    df["yellow_payment_type_label"] = pt.map(YELLOW_PAYMENT_LABELS)
    df["yellow_card_or_cash_flag"] = pt.isin([1, 2])
    df["flex_fare_flag"] = pt.eq(0)                       # 0 = Flex Fare
    df["irregular_payment_flag"] = pt.isin([3, 4, 5, 6])  # no-charge / dispute / unknown / voided
    df["yellow_no_charge_dispute_void_flag"] = pt.isin([3, 4, 6])
    df["yellow_payment_unknown_flag"] = pt == 5
    df["yellow_payment_review_flag"] = pt.isin([0, 3, 4, 5, 6])
    return df


def _any_negative_components(row: pd.Series, cols: list[str]) -> bool:
    for col in cols:
        if col not in row.index:
            continue
        val = row[col]
        if pd.notna(val) and float(val) < 0:
            return True
    return False


def enrich_sample(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived cost fields, QC flags, and service-specific labels."""
    out = df.copy()

    if "passenger_cost_excl_cbd" not in out.columns:
        out["passenger_cost_excl_cbd"] = (
            _safe_numeric(out["passenger_cost_pretip"])
            - _safe_numeric(out["cbd_congestion_fee"]).fillna(0)
        )

    pretip = _safe_numeric(out["passenger_cost_pretip"])
    cbd = _safe_numeric(out["cbd_congestion_fee"])
    if "burden_eligible_flag" not in out.columns:
        out["burden_eligible_flag"] = (pretip > 0) & (cbd >= 0)

    out["passenger_cost_nonpositive_flag"] = pretip <= 0
    out["negative_cbd_fee_flag"] = cbd < 0
    if "zero_distance_flag" not in out.columns:
        out["zero_distance_flag"] = _safe_numeric(out["trip_distance_miles"]) == 0
    if "very_long_duration_flag" not in out.columns:
        out["very_long_duration_flag"] = (
            _safe_numeric(out["trip_duration_seconds"]) > 24 * 60 * 60
        )
    if "very_long_distance_flag" not in out.columns:
        out["very_long_distance_flag"] = _safe_numeric(out["trip_distance_miles"]) > 100
    out["negative_distance_flag"] = _safe_numeric(out["trip_distance_miles"]) < 0
    out["nonpositive_duration_flag"] = _safe_numeric(out["trip_duration_seconds"]) <= 0

    pickup_dt = pd.to_datetime(out["pickup_datetime"], errors="coerce")
    dropoff_dt = pd.to_datetime(out["dropoff_datetime"], errors="coerce")
    out["invalid_timestamp_flag"] = pickup_dt.isna() | dropoff_dt.isna()
    out["month_mismatch_flag"] = (
        pickup_dt.dt.year != out["year"]
    ) | (pickup_dt.dt.month != out["month"])
    out["missing_zone_flag"] = (
        out["PULocationID"].isna() | out["DOLocationID"].isna()
    )

    if "pickup_date" not in out.columns:
        out["pickup_date"] = pickup_dt.dt.date
    if "dropoff_date" not in out.columns:
        out["dropoff_date"] = dropoff_dt.dt.date

    dst_dates = set(DST_SPRING_FORWARD.values())
    pickup_on_dst = out["pickup_date"].isin(dst_dates)
    dropoff_on_dst = out["dropoff_date"].isin(dst_dates)
    out["dst_transition_day_flag"] = pickup_on_dst | dropoff_on_dst

    pickup_hour = pickup_dt.dt.hour
    dropoff_hour = dropoff_dt.dt.hour
    near_transition_hour = {1, 2, 3}
    out["dst_transition_window_flag"] = out["dst_transition_day_flag"] & (
        pickup_hour.isin(near_transition_hour) | dropoff_hour.isin(near_transition_hour)
    )

    hvfhv_mask = out["service_type"] == "hvfhv"
    if hvfhv_mask.any():
        hvfhv_cols = [c for c in HVFHV_COST_COMPONENTS if c in out.columns]
        neg_component = out.loc[hvfhv_mask].apply(
            lambda row: _any_negative_components(row, hvfhv_cols), axis=1
        )
        out.loc[hvfhv_mask, "any_negative_cost_component_flag"] = neg_component.values

        base_fare = _safe_numeric(out.get("base_passenger_fare", pd.NA))
        refund_mask = (
            (pretip <= 0)
            | (base_fare < 0)
            | (cbd < 0)
            | out["any_negative_cost_component_flag"].fillna(False)
        )
        out.loc[hvfhv_mask, "possible_refund_or_adjustment_flag"] = refund_mask[hvfhv_mask]
    else:
        out["any_negative_cost_component_flag"] = False
        out["possible_refund_or_adjustment_flag"] = False

    yellow_mask = out["service_type"] == "yellow"
    if yellow_mask.any():
        yellow_cost_cols = [
            c
            for c in ["fare_amount", "congestion_surcharge", "tolls", "airport_fee", "cbd_congestion_fee"]
            if c in out.columns
        ]
        neg_yellow = out.loc[yellow_mask].apply(
            lambda row: _any_negative_components(row, yellow_cost_cols), axis=1
        )
        out.loc[yellow_mask, "any_negative_cost_component_flag"] = neg_yellow.values
        out.loc[yellow_mask, "possible_refund_or_adjustment_flag"] = (
            (pretip <= 0) | (cbd < 0) | out["any_negative_cost_component_flag"].fillna(False)
        )[yellow_mask]

    out = add_yellow_payment_flags(out)

    for col in QC_FLAG_COLUMNS:
        if col not in out.columns:
            out[col] = False

    return out


def build_sample() -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Two-pass stratified sample: count populations, allocate, then draw."""
    notes: list[dict] = list(UNAVAILABLE_FLAG_NOTES)
    strata = discover_strata()

    populations: dict[str, int] = {}
    stratum_meta: dict[str, tuple[str, int, int, Path]] = {}
    for service, year, month, path in strata:
        key = stratum_key(service, year, month)
        stratum_meta[key] = (service, year, month, path)
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
        service, year, month, path = stratum_meta[key]
        pop_n = populations[key]
        sample_n = allocation[key]
        composition_rows.append(
            {
                "service_type": service,
                "year": year,
                "month": month,
                "sampling_stratum": key,
                "stratum_population_n": pop_n,
                "stratum_sample_n": sample_n,
                "sample_weight": (pop_n / sample_n) if sample_n > 0 else pd.NA,
            }
        )

        if sample_n <= 0:
            if pop_n == 0:
                continue
            notes.append(
                {
                    "topic": "zero_allocation",
                    "note": f"Stratum {key} received zero sample allocation despite population {pop_n:,}.",
                }
            )
            continue

        if pop_n == 0:
            notes.append(
                {
                    "topic": "shortage",
                    "note": f"Requested {sample_n} rows from {key} but population is 0.",
                }
            )
            continue

        seed = RANDOM_STATE + i * 9973
        drawn = sample_rows_from_parquet(path, sample_n, seed)
        actual_n = len(drawn)
        if actual_n < sample_n:
            notes.append(
                {
                    "topic": "shortage",
                    "note": (
                        f"Stratum {key}: requested {sample_n}, drew {actual_n} "
                        f"(population {pop_n:,})."
                    ),
                }
            )
            composition_rows[-1]["stratum_sample_n"] = actual_n
            composition_rows[-1]["sample_weight"] = (
                pop_n / actual_n if actual_n > 0 else pd.NA
            )

        drawn["sampling_stratum"] = key
        drawn["stratum_population_n"] = pop_n
        drawn["stratum_sample_n"] = actual_n
        drawn["sample_weight"] = pop_n / actual_n if actual_n > 0 else pd.NA
        parts.append(drawn)

    sample = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    sample = enrich_sample(sample)

    # Reconcile to exactly TARGET_ROWS if rounding/shortage left a gap or surplus.
    if len(sample) > TARGET_ROWS:
        sample = sample.sample(n=TARGET_ROWS, random_state=RANDOM_STATE).reset_index(drop=True)
        notes.append(
            {
                "topic": "trim",
                "note": f"Trimmed oversample to exactly {TARGET_ROWS:,} rows.",
            }
        )
    elif len(sample) < TARGET_ROWS:
        deficit = TARGET_ROWS - len(sample)
        notes.append(
            {
                "topic": "shortage",
                "note": (
                    f"Final sample has {len(sample):,} rows ({deficit:,} short of "
                    f"{TARGET_ROWS:,}). Redistributing by drawing extra rows from strata "
                    "with remaining headroom."
                ),
            }
        )
        for i, key in enumerate(sorted(allocation.keys())):
            if deficit <= 0:
                break
            service, year, month, path = stratum_meta[key]
            pop_n = populations[key]
            already = int((sample["sampling_stratum"] == key).sum()) if len(sample) else 0
            headroom = pop_n - already
            if headroom <= 0 or not path.exists():
                continue
            extra_n = min(deficit, headroom)
            seed = RANDOM_STATE + 50000 + i * 9973
            extra = sample_rows_from_parquet(path, extra_n, seed)
            if len(extra):
                extra["sampling_stratum"] = key
                extra["stratum_population_n"] = pop_n
                extra["stratum_sample_n"] = extra_n
                extra["sample_weight"] = pop_n / extra_n
                sample = pd.concat([sample, enrich_sample(extra)], ignore_index=True)
                deficit -= len(extra)

        if len(sample) > TARGET_ROWS:
            sample = sample.sample(n=TARGET_ROWS, random_state=RANDOM_STATE).reset_index(
                drop=True
            )

    sample.insert(0, "sample_row_id", np.arange(1, len(sample) + 1))

    composition = pd.DataFrame(composition_rows)
    if len(sample):
        actual_comp = (
            sample.groupby("sampling_stratum", as_index=False)
            .agg(
                actual_sample_n=("sample_row_id", "count"),
                stratum_population_n=("stratum_population_n", "first"),
            )
            .merge(
                composition[
                    ["sampling_stratum", "service_type", "year", "month", "stratum_sample_n"]
                ],
                on="sampling_stratum",
                how="right",
            )
        )
        actual_comp["stratum_sample_n"] = actual_comp["actual_sample_n"].fillna(0).astype(int)
        actual_comp["sample_weight"] = np.where(
            actual_comp["stratum_sample_n"] > 0,
            actual_comp["stratum_population_n"] / actual_comp["stratum_sample_n"],
            np.nan,
        )
        composition = actual_comp[
            [
                "service_type",
                "year",
                "month",
                "sampling_stratum",
                "stratum_population_n",
                "stratum_sample_n",
                "sample_weight",
            ]
        ].sort_values(["service_type", "year", "month"])

    notes.append(
        {
            "topic": "sampling_method",
            "note": (
                "Proportional stratified random sampling by service_type × year × month; "
                f"random_state={RANDOM_STATE}; target rows={TARGET_ROWS:,}. "
                "Not balanced across strata; preserves natural charged_cbd_flag mix."
            ),
        }
    )

    return sample, composition, notes


def output_column_order(df: pd.DataFrame) -> list[str]:
    """Order columns for the teammate CSV."""
    ordered: list[str] = []
    for col in METADATA_COLUMNS + REQUIRED_COLUMNS:
        if col in df.columns and col not in ordered:
            ordered.append(col)
    for col in YELLOW_OPTIONAL_COLUMNS + HVFHV_OPTIONAL_COLUMNS + QC_FLAG_COLUMNS:
        if col in df.columns and col not in ordered:
            ordered.append(col)
    # airport_trip_flag is emitted by standardize_trips.py but intentionally held out of
    # the sample schema (the sample is not used for airport-specific analysis).
    held_out = {"dropoff_date", "airport_trip_flag"}
    for col in df.columns:
        if col not in ordered and col not in held_out:
            ordered.append(col)
    return ordered


def main() -> None:
    if not STANDARDIZED_DIR.exists():
        raise FileNotFoundError(
            f"{STANDARDIZED_DIR} not found. Run scripts/standardize_trips.py first."
        )

    sample, composition, notes = build_sample()

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPOSITION_PATH.parent.mkdir(parents=True, exist_ok=True)

    out_cols = output_column_order(sample)
    sample[out_cols].to_csv(SAMPLE_PATH, index=False)
    composition.to_csv(COMPOSITION_PATH, index=False)
    pd.DataFrame(notes).to_csv(NOTES_PATH, index=False)

    rel_sample = SAMPLE_PATH.relative_to(REPO_ROOT).as_posix()
    print(f"1. 20K representative sample: {rel_sample}")
    print(f"2. Actual row count: {len(sample):,}")

    print("\n3. Counts by service_type × year × month:")
    if len(sample):
        comp = (
            sample.groupby(["service_type", "year", "month"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(["service_type", "year", "month"])
        )
        print(comp.to_string(index=False))

        print("\n4. charged_cbd_flag counts (2025 only):")
        charged_2025 = (
            sample[sample["year"] == 2025]
            .groupby(["service_type", "charged_cbd_flag"], dropna=False)
            .size()
            .reset_index(name="count")
        )
        print(charged_2025.to_string(index=False))

        print("\n5. burden_eligible_flag counts:")
        burden = sample["burden_eligible_flag"].value_counts(dropna=False)
        print(burden.to_string())

        yellow = sample[sample["service_type"] == "yellow"]
        print("\n6. Yellow payment_type label counts:")
        if len(yellow) and "yellow_payment_type_label" in yellow.columns:
            pay = yellow["yellow_payment_type_label"].value_counts(dropna=False)
            print(pay.to_string())
        else:
            print("  (no yellow rows or payment labels)")

        dst_window = int(sample["dst_transition_window_flag"].sum())
        print(f"\n7. DST transition-window rows: {dst_window}")

        refund = int(sample["possible_refund_or_adjustment_flag"].sum())
        print(f"8. possible_refund_or_adjustment rows: {refund}")

    print("\n9. Skipped files, shortages, and assumptions:")
    for note in notes:
        if note.get("topic") not in {
            "qc_flags_removed_at_standardization",
            "hvfhv_passenger_cost_pretip",
            "possible_refund_or_adjustment_flag",
            "dst_transition_flags",
            "aggregate_analysis",
            "sampling_method",
        }:
            print(f"  - [{note.get('topic')}] {note.get('note')}")
    print(f"  - Full notes: {NOTES_PATH.relative_to(REPO_ROOT).as_posix()}")
    print(f"  - Composition QC: {COMPOSITION_PATH.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
