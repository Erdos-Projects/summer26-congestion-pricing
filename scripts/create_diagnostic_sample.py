"""
Build a 5,000-row diagnostic trip sample from raw TLC parquet files.

Oversamples anomaly categories so the team can inspect cleaning-rule impacts.
Reads one raw monthly file at a time (memory-safe). Does not modify data/raw/
or overwrite existing 100-row / 20K representative samples.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from standardize_trips import (  # noqa: E402
    identify_service_type,
    parse_year_month_from_path,
    standardize_hvfhv,
    standardize_yellow,
    _safe_numeric,
)

REPO_ROOT = SCRIPTS_DIR.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "samples" / "trip_level_sample_5k_diagnostic.csv"
ANOMALY_COUNTS_PATH = REPO_ROOT / "data" / "processed" / "qc" / "diagnostic_anomaly_counts.csv"
COMPOSITION_PATH = REPO_ROOT / "data" / "processed" / "qc" / "diagnostic_sample_composition.csv"
NOTES_PATH = REPO_ROOT / "data" / "processed" / "qc" / "diagnostic_notes.csv"

STUDY_YEARS = (2024, 2025)
STUDY_MONTHS = (2, 3, 4, 5, 6)
TARGET_ROWS = 5_000
RANDOM_STATE = 42

VERY_LONG_DURATION_SECONDS = 4 * 60 * 60
VERY_LONG_DISTANCE_MILES = 100.0

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

RAW_CATEGORY_TARGETS: dict[str, int] = {
    "nonpositive_passenger_cost": 700,
    "negative_cbd_fee": 700,
    "yellow_payment_review": 600,
    "hvfhv_possible_refund_or_adjustment": 600,
    "invalid_or_nonpositive_duration": 400,
    "missing_zone": 300,
    "negative_distance": 300,
    "zero_distance": 300,
    "very_long_duration": 300,
    "very_long_distance": 300,
    "dst_transition_window": 300,
    "normal_reference": 500,
}

CATEGORY_ORDER = list(RAW_CATEGORY_TARGETS.keys())

HVFHV_COST_COMPONENTS = [
    "base_passenger_fare",
    "tolls",
    "bcf",
    "sales_tax",
    "congestion_surcharge",
    "airport_fee",
    "cbd_congestion_fee",
]

COUNT_FLAG_COLUMNS = [
    "passenger_cost_nonpositive_flag",
    "negative_cbd_fee_flag",
    "yellow_payment_review_flag",
    "possible_refund_or_adjustment_flag",
    "invalid_timestamp_flag",
    "nonpositive_duration_flag",
    "missing_zone_flag",
    "negative_distance_flag",
    "zero_distance_flag",
    "very_long_duration_flag",
    "very_long_distance_flag",
    "dst_transition_day_flag",
    "dst_transition_window_flag",
    "burden_eligible_flag",
    "any_negative_cost_component_flag",
]

YELLOW_RAW_COLUMNS = [
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "trip_distance",
    "cbd_congestion_fee",
    "congestion_surcharge",
    "tolls_amount",
    "Airport_fee",
    "tip_amount",
    "total_amount",
    "payment_type",
    "passenger_count",
    "fare_amount",
    "RatecodeID",
]

HVFHV_RAW_COLUMNS = [
    "pickup_datetime",
    "dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "trip_miles",
    "trip_time",
    "cbd_congestion_fee",
    "congestion_surcharge",
    "tolls",
    "airport_fee",
    "base_passenger_fare",
    "bcf",
    "sales_tax",
    "tips",
    "driver_pay",
    "hvfhs_license_num",
    "shared_request_flag",
    "shared_match_flag",
]


def largest_remainder_scale(raw_targets: dict[str, int], total: int) -> dict[str, int]:
    keys = list(raw_targets.keys())
    raw_sum = sum(raw_targets.values())
    scaled = [total * raw_targets[k] / raw_sum for k in keys]
    alloc = [int(v) for v in scaled]
    remainder = total - sum(alloc)
    order = sorted(
        range(len(keys)),
        key=lambda i: (scaled[i] - alloc[i], raw_targets[keys[i]], keys[i]),
        reverse=True,
    )
    for i in range(remainder):
        alloc[order[i]] += 1
    return {keys[i]: alloc[i] for i in range(len(keys))}


CATEGORY_TARGETS = largest_remainder_scale(RAW_CATEGORY_TARGETS, TARGET_ROWS)


def discover_study_raw_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(RAW_DIR.rglob("*.parquet")):
        if identify_service_type(path.name) is None:
            continue
        ym = parse_year_month_from_path(path)
        if ym is None:
            continue
        year, month = ym
        if year in STUDY_YEARS and month in STUDY_MONTHS:
            files.append(path)
    return files


def _available_columns(parquet_path: Path) -> set[str]:
    return set(pq.ParquetFile(parquet_path).schema_arrow.names)


def _select_raw_columns(available: set[str], service: str) -> list[str]:
    wanted = YELLOW_RAW_COLUMNS if service == "yellow" else HVFHV_RAW_COLUMNS
    return [c for c in wanted if c in available]


def _any_negative(raw: pd.DataFrame, cols: list[str]) -> pd.Series:
    neg = pd.Series(False, index=raw.index)
    for col in cols:
        if col in raw.columns:
            neg = neg | (_safe_numeric(raw[col]) < 0)
    return neg


def fast_compute_flags(
    raw: pd.DataFrame, service: str, year: int, month: int
) -> pd.DataFrame:
    """
    Lightweight flag computation from raw columns (pass 1 counting / pre-filter).
    """
    flags = pd.DataFrame(index=raw.index)
    flags["service_type"] = service
    flags["year"] = year
    flags["month"] = month

    if service == "yellow":
        pickup = pd.to_datetime(raw["tpep_pickup_datetime"], errors="coerce")
        dropoff = pd.to_datetime(raw["tpep_dropoff_datetime"], errors="coerce")
        dist = _safe_numeric(raw["trip_distance"])
        tip = _safe_numeric(raw.get("tip_amount", 0)).fillna(0)
        pretip = _safe_numeric(raw.get("total_amount")) - tip
        raw_cbd = (
            _safe_numeric(raw["cbd_congestion_fee"])
            if "cbd_congestion_fee" in raw.columns
            else pd.Series(np.nan, index=raw.index)
        )
        dur = (dropoff - pickup).dt.total_seconds()
        pu_zone = _safe_numeric(raw["PULocationID"])
        do_zone = _safe_numeric(raw["DOLocationID"])
        pt = _safe_numeric(raw["payment_type"]) if "payment_type" in raw.columns else pd.Series(np.nan, index=raw.index)
    else:
        pickup = pd.to_datetime(raw["pickup_datetime"], errors="coerce")
        dropoff = pd.to_datetime(raw["dropoff_datetime"], errors="coerce")
        dist = _safe_numeric(raw["trip_miles"])
        dur = _safe_numeric(raw["trip_time"])
        raw_cbd = (
            _safe_numeric(raw["cbd_congestion_fee"])
            if "cbd_congestion_fee" in raw.columns
            else pd.Series(np.nan, index=raw.index)
        )
        base = _safe_numeric(raw.get("base_passenger_fare", 0)).fillna(0)
        tolls = _safe_numeric(raw.get("tolls", 0)).fillna(0)
        bcf = _safe_numeric(raw.get("bcf", 0)).fillna(0)
        tax = _safe_numeric(raw.get("sales_tax", 0)).fillna(0)
        cong = _safe_numeric(raw.get("congestion_surcharge", 0)).fillna(0)
        ap = _safe_numeric(raw.get("airport_fee", 0)).fillna(0)
        cbd_fill = raw_cbd.fillna(0)
        pretip = base + tolls + bcf + tax + cong + ap + cbd_fill
        pu_zone = _safe_numeric(raw["PULocationID"])
        do_zone = _safe_numeric(raw["DOLocationID"])
        pt = pd.Series(np.nan, index=raw.index)

    flags["passenger_cost_nonpositive_flag"] = pretip <= 0
    flags["negative_cbd_fee_flag"] = raw_cbd < 0
    flags["burden_eligible_flag"] = (pretip > 0) & (raw_cbd.fillna(0) >= 0)
    flags["invalid_timestamp_flag"] = pickup.isna() | dropoff.isna()
    flags["nonpositive_duration_flag"] = (
        flags["invalid_timestamp_flag"] | (dropoff <= pickup) | (dur <= 0)
    )
    flags["missing_zone_flag"] = pu_zone.isna() | do_zone.isna()
    flags["negative_distance_flag"] = dist < 0
    flags["zero_distance_flag"] = dist == 0
    flags["very_long_duration_flag"] = dur > VERY_LONG_DURATION_SECONDS
    flags["very_long_distance_flag"] = dist > VERY_LONG_DISTANCE_MILES

    pickup_date = pickup.dt.date
    dropoff_date = dropoff.dt.date
    dst_dates = set(DST_SPRING_FORWARD.values())
    flags["dst_transition_day_flag"] = pickup_date.isin(dst_dates) | dropoff_date.isin(
        dst_dates
    )
    flags["dst_transition_window_flag"] = flags["dst_transition_day_flag"] & (
        pickup.dt.hour.isin({1, 2, 3}) | dropoff.dt.hour.isin({1, 2, 3})
    )

    flags["yellow_payment_review_flag"] = (
        pt.isin([0, 3, 4, 5, 6])
        if service == "yellow"
        else pd.Series(False, index=raw.index)
    )

    if service == "yellow":
        ycols = [c for c in ["fare_amount", "congestion_surcharge", "tolls_amount", "Airport_fee", "cbd_congestion_fee"] if c in raw.columns]
        flags["any_negative_cost_component_flag"] = _any_negative(raw, ycols)
    else:
        hcols = [c for c in HVFHV_COST_COMPONENTS if c in raw.columns]
        flags["any_negative_cost_component_flag"] = _any_negative(raw, hcols)

    if service == "hvfhv":
        base = _safe_numeric(raw.get("base_passenger_fare"))
        flags["possible_refund_or_adjustment_flag"] = (
            (pretip <= 0)
            | (base < 0)
            | (raw_cbd < 0)
            | flags["any_negative_cost_component_flag"]
        )
    else:
        flags["possible_refund_or_adjustment_flag"] = (
            (pretip <= 0) | (raw_cbd < 0) | flags["any_negative_cost_component_flag"]
        )

    return flags


def map_raw_chunk(
    raw: pd.DataFrame, service: str, year: int, month: int, source_file: str
) -> tuple[pd.DataFrame, pd.Series]:
    if service == "yellow":
        out = standardize_yellow(raw, year, month, source_file)
        raw_cbd = (
            _safe_numeric(raw["cbd_congestion_fee"])
            if "cbd_congestion_fee" in raw.columns
            else pd.Series(np.nan, index=raw.index)
        )
    else:
        out = standardize_hvfhv(raw, year, month, source_file)
        raw_cbd = (
            _safe_numeric(raw["cbd_congestion_fee"])
            if "cbd_congestion_fee" in raw.columns
            else pd.Series(np.nan, index=raw.index)
        )
    return out, raw_cbd


def add_diagnostic_fields(
    df: pd.DataFrame, raw_cbd: pd.Series, year: int, month: int
) -> pd.DataFrame:
    out = df.copy()
    pretip = _safe_numeric(out["passenger_cost_pretip"])
    cbd = _safe_numeric(out["cbd_congestion_fee"])

    out["passenger_cost_excl_cbd"] = pretip - cbd.fillna(0)
    out["charged_cbd_flag"] = cbd.fillna(0) > 0
    out["relative_cbd_burden"] = pd.NA
    valid = pretip > 0
    out.loc[valid, "relative_cbd_burden"] = cbd[valid] / pretip[valid]

    fast = fast_compute_flags_from_standardized(out, raw_cbd, year, month)
    for col in COUNT_FLAG_COLUMNS + [
        "month_mismatch_flag",
        "yellow_payment_type_label",
        "yellow_no_charge_dispute_void_flag",
        "yellow_payment_unknown_flag",
    ]:
        if col in fast.columns:
            out[col] = fast[col]

    return out


def fast_compute_flags_from_standardized(
    df: pd.DataFrame, raw_cbd: pd.Series, year: int, month: int
) -> pd.DataFrame:
    """Full flag set on an already-standardized chunk."""
    flags = fast_compute_flags_hybrid(df, raw_cbd, year, month)
    pickup_dt = pd.to_datetime(df["pickup_datetime"], errors="coerce")
    flags["month_mismatch_flag"] = (pickup_dt.dt.year != year) | (pickup_dt.dt.month != month)

    if "payment_type" in df.columns:
        pt = _safe_numeric(df["payment_type"])
        flags["yellow_payment_type_label"] = pt.map(YELLOW_PAYMENT_LABELS)
        flags["yellow_no_charge_dispute_void_flag"] = pt.isin([3, 4, 6])
        flags["yellow_payment_unknown_flag"] = pt == 5
    else:
        flags["yellow_payment_type_label"] = pd.NA
        flags["yellow_no_charge_dispute_void_flag"] = False
        flags["yellow_payment_unknown_flag"] = False
    return flags


def fast_compute_flags_hybrid(
    df: pd.DataFrame, raw_cbd: pd.Series, year: int, month: int
) -> pd.DataFrame:
    """Flags from standardized columns (used in pass 2)."""
    flags = pd.DataFrame(index=df.index)
    pretip = _safe_numeric(df["passenger_cost_pretip"])
    cbd = _safe_numeric(df["cbd_congestion_fee"])
    pickup = pd.to_datetime(df["pickup_datetime"], errors="coerce")
    dropoff = pd.to_datetime(df["dropoff_datetime"], errors="coerce")
    dist = _safe_numeric(df["trip_distance_miles"])
    dur = _safe_numeric(df["trip_duration_seconds"])

    flags["service_type"] = df["service_type"]
    flags["passenger_cost_nonpositive_flag"] = pretip <= 0
    flags["negative_cbd_fee_flag"] = raw_cbd < 0
    flags["burden_eligible_flag"] = (pretip > 0) & (cbd.fillna(0) >= 0)
    flags["invalid_timestamp_flag"] = pickup.isna() | dropoff.isna()
    flags["nonpositive_duration_flag"] = (
        flags["invalid_timestamp_flag"] | (dropoff <= pickup) | (dur <= 0)
    )
    flags["missing_zone_flag"] = df["PULocationID"].isna() | df["DOLocationID"].isna()
    flags["negative_distance_flag"] = dist < 0
    flags["zero_distance_flag"] = dist == 0
    flags["very_long_duration_flag"] = dur > VERY_LONG_DURATION_SECONDS
    flags["very_long_distance_flag"] = dist > VERY_LONG_DISTANCE_MILES

    pickup_date = pickup.dt.date
    dropoff_date = dropoff.dt.date
    dst_dates = set(DST_SPRING_FORWARD.values())
    flags["dst_transition_day_flag"] = pickup_date.isin(dst_dates) | dropoff_date.isin(
        dst_dates
    )
    flags["dst_transition_window_flag"] = flags["dst_transition_day_flag"] & (
        pickup.dt.hour.isin({1, 2, 3}) | dropoff.dt.hour.isin({1, 2, 3})
    )

    if "payment_type" in df.columns:
        pt = _safe_numeric(df["payment_type"])
        flags["yellow_payment_review_flag"] = pt.isin([0, 3, 4, 5, 6])
    else:
        flags["yellow_payment_review_flag"] = False

    yellow_mask = df["service_type"] == "yellow"
    hvfhv_mask = df["service_type"] == "hvfhv"
    flags["any_negative_cost_component_flag"] = False
    if yellow_mask.any():
        ycols = ["fare_amount", "congestion_surcharge", "tolls", "airport_fee", "cbd_congestion_fee"]
        for col in ycols:
            if col in df.columns:
                flags.loc[yellow_mask, "any_negative_cost_component_flag"] |= (
                    _safe_numeric(df.loc[yellow_mask, col]) < 0
                ).values
    if hvfhv_mask.any():
        for col in HVFHV_COST_COMPONENTS:
            if col in df.columns:
                flags.loc[hvfhv_mask, "any_negative_cost_component_flag"] |= (
                    _safe_numeric(df.loc[hvfhv_mask, col]) < 0
                ).values

    flags["possible_refund_or_adjustment_flag"] = (
        (pretip <= 0) | (raw_cbd < 0) | flags["any_negative_cost_component_flag"]
    )
    if hvfhv_mask.any() and "base_passenger_fare" in df.columns:
        flags.loc[hvfhv_mask, "possible_refund_or_adjustment_flag"] |= (
            _safe_numeric(df.loc[hvfhv_mask, "base_passenger_fare"]) < 0
        ).values

    return flags


def category_mask(flags: pd.DataFrame, category: str) -> pd.Series:
    if category == "nonpositive_passenger_cost":
        return flags["passenger_cost_nonpositive_flag"]
    if category == "negative_cbd_fee":
        return flags["negative_cbd_fee_flag"]
    if category == "yellow_payment_review":
        return flags["yellow_payment_review_flag"] & (flags["service_type"] == "yellow")
    if category == "hvfhv_possible_refund_or_adjustment":
        return flags["possible_refund_or_adjustment_flag"] & (flags["service_type"] == "hvfhv")
    if category == "invalid_or_nonpositive_duration":
        return flags["invalid_timestamp_flag"] | flags["nonpositive_duration_flag"]
    if category == "missing_zone":
        return flags["missing_zone_flag"]
    if category == "negative_distance":
        return flags["negative_distance_flag"]
    if category == "zero_distance":
        return flags["zero_distance_flag"]
    if category == "very_long_duration":
        return flags["very_long_duration_flag"]
    if category == "very_long_distance":
        return flags["very_long_distance_flag"]
    if category == "dst_transition_window":
        return flags["dst_transition_window_flag"]
    if category == "normal_reference":
        anomaly = (
            flags["passenger_cost_nonpositive_flag"]
            | flags["negative_cbd_fee_flag"]
            | (flags["yellow_payment_review_flag"] & (flags["service_type"] == "yellow"))
            | (
                flags["possible_refund_or_adjustment_flag"]
                & (flags["service_type"] == "hvfhv")
            )
            | flags["invalid_timestamp_flag"]
            | flags["nonpositive_duration_flag"]
            | flags["missing_zone_flag"]
            | flags["negative_distance_flag"]
            | flags["zero_distance_flag"]
            | flags["very_long_duration_flag"]
            | flags["very_long_distance_flag"]
            | flags["dst_transition_window_flag"]
        )
        return ~anomaly
    raise ValueError(f"Unknown category: {category}")


def iter_raw_row_groups(raw_path: Path):
    """Yield (raw_chunk, service, year, month, source_rel, row_offset)."""
    service = identify_service_type(raw_path.name)
    ym = parse_year_month_from_path(raw_path)
    if service is None or ym is None:
        return
    year, month = ym
    if year not in STUDY_YEARS or month not in STUDY_MONTHS:
        return

    source_rel = raw_path.relative_to(REPO_ROOT).as_posix()
    available = _available_columns(raw_path)
    columns = _select_raw_columns(available, service)
    if not columns:
        return

    pf = pq.ParquetFile(raw_path)
    offset = 0
    for rg in range(pf.num_row_groups):
        raw = pf.read_row_group(rg, columns=columns).to_pandas()
        yield raw, service, year, month, source_rel, offset
        offset += len(raw)


def pass1_count_flags(raw_files: list[Path]) -> tuple[pd.DataFrame, list[dict]]:
    """Scan raw files once; count diagnostic flags by service/year/month."""
    notes: list[dict] = []
    monthly_totals: dict[tuple[str, int, int], int] = {}
    monthly_flag_counts: dict[tuple[str, int, int, str], int] = {}

    for i, raw_path in enumerate(raw_files, start=1):
        rel = raw_path.relative_to(REPO_ROOT).as_posix()
        print(f"  [count pass] {i}/{len(raw_files)}: {rel}")
        try:
            for raw, service, year, month, _source, _offset in iter_raw_row_groups(raw_path):
                flags = fast_compute_flags(raw, service, year, month)
                key = (service, year, month)
                monthly_totals[key] = monthly_totals.get(key, 0) + len(flags)
                for flag in COUNT_FLAG_COLUMNS:
                    n_flag = int(flags[flag].sum())
                    fk = (service, year, month, flag)
                    monthly_flag_counts[fk] = monthly_flag_counts.get(fk, 0) + n_flag
        except Exception as exc:  # noqa: BLE001
            notes.append({"topic": "skipped_file", "note": f"{rel}: {exc}"})

    rows = []
    for (service, year, month, flag), raw_count in sorted(monthly_flag_counts.items()):
        total = monthly_totals.get((service, year, month), 0)
        rows.append(
            {
                "service_type": service,
                "year": year,
                "month": month,
                "diagnostic_flag": flag,
                "raw_count": raw_count,
                "monthly_row_total": total,
                "share_of_monthly_rows": raw_count / total if total else np.nan,
            }
        )
    return pd.DataFrame(rows), notes


def pass2_sample_rows(
    raw_files: list[Path], category_targets: dict[str, int]
) -> tuple[list[pd.DataFrame], list[dict]]:
    """
    Second pass: use fast flags to find matches, standardize only sampled rows.
    """
    notes: list[dict] = []
    remaining = dict(category_targets)
    used_keys: set[str] = set()
    parts: list[pd.DataFrame] = []
    rng = np.random.default_rng(RANDOM_STATE)

    for i, raw_path in enumerate(raw_files, start=1):
        if sum(remaining.values()) <= 0:
            break
        rel = raw_path.relative_to(REPO_ROOT).as_posix()
        print(f"  [sample pass] {i}/{len(raw_files)}: {rel}")
        try:
            for raw, service, year, month, source_rel, offset in iter_raw_row_groups(raw_path):
                if sum(remaining.values()) <= 0:
                    break

                fast = fast_compute_flags(raw, service, year, month)
                row_keys = pd.Series(
                    [f"{source_rel}::{offset + j}" for j in range(len(raw))],
                    index=raw.index,
                )

                for cat in CATEGORY_ORDER:
                    if remaining[cat] <= 0:
                        continue
                    mask = category_mask(fast, cat) & ~row_keys.isin(used_keys)
                    if not mask.any():
                        continue
                    take = min(remaining[cat], int(mask.sum()))
                    chosen_idx = raw.loc[mask].sample(
                        n=take, random_state=int(rng.integers(0, 2**31))
                    ).index
                    raw_sub = raw.loc[chosen_idx]
                    mapped, raw_cbd = map_raw_chunk(
                        raw_sub, service, year, month, source_rel
                    )
                    full = add_diagnostic_fields(mapped, raw_cbd, year, month)
                    full["diagnostic_category"] = cat
                    parts.append(full)
                    used_keys.update(row_keys.loc[chosen_idx].tolist())
                    remaining[cat] -= take

        except Exception as exc:  # noqa: BLE001
            notes.append({"topic": "skipped_file", "note": f"{rel}: {exc}"})

    parts, used_keys, remaining, fill_notes = _fill_remaining_rows(
        parts, used_keys, remaining, raw_files, rng
    )
    notes.extend(fill_notes)

    for cat, need in remaining.items():
        got = category_targets[cat] - need
        if got < category_targets[cat]:
            notes.append(
                {
                    "topic": "shortage",
                    "category": cat,
                    "target": category_targets[cat],
                    "actual": got,
                    "note": (
                        f"Category {cat}: target {category_targets[cat]}, "
                        f"sampled {got} unique rows."
                    ),
                }
            )

    return parts, notes


def _fill_remaining_rows(
    parts: list[pd.DataFrame],
    used_keys: set[str],
    remaining: dict[str, int],
    raw_files: list[Path],
    rng: np.random.Generator,
) -> tuple[list[pd.DataFrame], set[str], dict[str, int], list[dict]]:
    """Fill toward TARGET_ROWS from anomaly categories with unfilled slots."""
    notes: list[dict] = []
    collected = sum(len(p) for p in parts)
    deficit = TARGET_ROWS - collected
    if deficit <= 0:
        return parts, used_keys, remaining, notes

    notes.append(
        {
            "topic": "fill_in",
            "note": (
                f"Primary sampling yielded {collected:,} rows; "
                f"filling up to {deficit:,} from other anomaly categories."
            ),
        }
    )

    fill_order = [c for c in CATEGORY_ORDER if c != "normal_reference"] + ["normal_reference"]

    for raw_path in raw_files:
        if deficit <= 0:
            break
        rel = raw_path.relative_to(REPO_ROOT).as_posix()
        try:
            for raw, service, year, month, source_rel, offset in iter_raw_row_groups(raw_path):
                if deficit <= 0:
                    break
                fast = fast_compute_flags(raw, service, year, month)
                row_keys = pd.Series(
                    [f"{source_rel}::{offset + j}" for j in range(len(raw))],
                    index=raw.index,
                )
                for cat in fill_order:
                    if deficit <= 0:
                        break
                    extra_need = remaining.get(cat, 0)
                    if extra_need <= 0 and cat != "normal_reference":
                        continue
                    mask = category_mask(fast, cat) & ~row_keys.isin(used_keys)
                    if not mask.any():
                        continue
                    take = min(deficit, extra_need if extra_need > 0 else deficit, int(mask.sum()))
                    if take <= 0:
                        continue
                    chosen_idx = raw.loc[mask].sample(
                        n=take, random_state=int(rng.integers(0, 2**31))
                    ).index
                    raw_sub = raw.loc[chosen_idx]
                    mapped, raw_cbd = map_raw_chunk(
                        raw_sub, service, year, month, source_rel
                    )
                    full = add_diagnostic_fields(mapped, raw_cbd, year, month)
                    full["diagnostic_category"] = cat
                    parts.append(full)
                    used_keys.update(row_keys.loc[chosen_idx].tolist())
                    remaining[cat] = max(0, remaining.get(cat, 0) - take)
                    deficit -= take
        except Exception as exc:  # noqa: BLE001
            notes.append({"topic": "fill_pass_error", "note": f"{rel}: {exc}"})

    if deficit > 0:
        notes.append(
            {
                "topic": "fill_in",
                "note": f"Could not fill all slots; final deficit {deficit:,} rows.",
            }
        )

    return parts, used_keys, remaining, notes


def build_output_dataframe(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    if "_row_key" in df.columns:
        df = df.drop(columns=["_row_key"])
    df.insert(0, "diagnostic_row_id", np.arange(1, len(df) + 1))

    col_order = [
        "diagnostic_row_id",
        "diagnostic_category",
        "service_type",
        "year",
        "month",
        "source_file",
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
        "payment_type",
        "yellow_payment_type_label",
        "passenger_count",
        "fare_amount",
        "tip_amount",
        "total_amount",
        "RatecodeID",
        "hvfhs_license_num",
        "base_passenger_fare",
        "bcf",
        "sales_tax",
        "tips",
        "driver_pay",
        "shared_request_flag",
        "shared_match_flag",
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
        "yellow_payment_review_flag",
        "yellow_no_charge_dispute_void_flag",
        "yellow_payment_unknown_flag",
    ]
    present = [c for c in col_order if c in df.columns]
    extra = [c for c in df.columns if c not in present]
    return df[present + extra]


def build_composition(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame()
    group_cols = [
        "diagnostic_category",
        "service_type",
        "year",
        "month",
        "charged_cbd_flag",
        "burden_eligible_flag",
    ]
    if "yellow_payment_type_label" in df.columns and (df["service_type"] == "yellow").any():
        group_cols = group_cols + ["yellow_payment_type_label"]
    return (
        df.groupby(group_cols, dropna=False)
        .size()
        .reset_index(name="row_count")
        .sort_values(group_cols)
    )


def build_notes(sample_df: pd.DataFrame, scan_notes: list[dict], sample_notes: list[dict]) -> pd.DataFrame:
    rows: list[dict] = [
        {
            "topic": "non_representative_warning",
            "category": "",
            "target_rows": "",
            "actual_rows": "",
            "note": (
                "This diagnostic sample intentionally oversamples problematic records. "
                "Do not use for aggregate estimates."
            ),
        },
        {
            "topic": "relationship_to_other_samples",
            "category": "",
            "target_rows": "",
            "actual_rows": "",
            "note": (
                "trip_level_sample_20k_representative.csv is for preliminary EDA; "
                "trip_level_sample_5k_diagnostic.csv is for cleaning diagnostics."
            ),
        },
        {
            "topic": "scaled_targets",
            "category": "",
            "target_rows": sum(RAW_CATEGORY_TARGETS.values()),
            "actual_rows": len(sample_df),
            "note": "Raw category targets summed to 5,300; scaled to 5,000 via largest-remainder.",
        },
    ]
    for cat in CATEGORY_ORDER:
        actual = int((sample_df["diagnostic_category"] == cat).sum()) if len(sample_df) else 0
        rows.append(
            {
                "topic": "category_allocation",
                "category": cat,
                "target_rows": CATEGORY_TARGETS[cat],
                "actual_rows": actual,
                "note": f"Raw approximate target: {RAW_CATEGORY_TARGETS[cat]}",
            }
        )
    for note in scan_notes + sample_notes:
        rows.append(
            {
                "topic": note.get("topic", "note"),
                "category": note.get("category", ""),
                "target_rows": note.get("target", ""),
                "actual_rows": note.get("actual", ""),
                "note": note.get("note", str(note)),
            }
        )
    rows.extend(
        [
            {
                "topic": "cleaning_implication",
                "category": "",
                "target_rows": "",
                "actual_rows": "",
                "note": "Review non-positive passenger cost and negative CBD-fee rows before final exclusion rules.",
            },
            {
                "topic": "cleaning_implication",
                "category": "",
                "target_rows": "",
                "actual_rows": "",
                "note": "Yellow payment_type may matter for burden analysis.",
            },
            {
                "topic": "cleaning_implication",
                "category": "",
                "target_rows": "",
                "actual_rows": "",
                "note": (
                    "HVFHV passenger_cost_pretip is reconstructed and may not capture "
                    "discounts, refunds, credits, or app-specific pricing."
                ),
            },
            {
                "topic": "cleaning_implication",
                "category": "",
                "target_rows": "",
                "actual_rows": "",
                "note": "DST transition-window rows are flagged, not removed.",
            },
            {
                "topic": "assumption",
                "category": "",
                "target_rows": "",
                "actual_rows": "",
                "note": f"random_state={RANDOM_STATE}; very_long_duration threshold = 4 hours.",
            },
        ]
    )
    return pd.DataFrame(rows)


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"{RAW_DIR} not found.")

    raw_files = discover_study_raw_files()
    if not raw_files:
        raise FileNotFoundError("No study-window raw parquet files found.")

    print(f"Pass 1: counting diagnostic flags across {len(raw_files)} file(s) ...")
    counts_df, scan_notes = pass1_count_flags(raw_files)

    print(f"\nPass 2: sampling up to {TARGET_ROWS:,} diagnostic rows ...")
    parts, sample_notes = pass2_sample_rows(raw_files, CATEGORY_TARGETS)
    sample_df = build_output_dataframe(parts)

    composition_df = build_composition(sample_df)
    notes_df = build_notes(sample_df, scan_notes, sample_notes)

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample_df.to_csv(SAMPLE_PATH, index=False)
    counts_df.to_csv(ANOMALY_COUNTS_PATH, index=False)
    composition_df.to_csv(COMPOSITION_PATH, index=False)
    notes_df.to_csv(NOTES_PATH, index=False)

    rel = SAMPLE_PATH.relative_to(REPO_ROOT).as_posix()
    print(f"\n1. Diagnostic sample: {rel}")
    print(f"2. Actual rows: {len(sample_df):,}")

    if len(sample_df):
        print("\n3. Count by diagnostic_category:")
        print(sample_df["diagnostic_category"].value_counts().to_string())

        print("\n4. Count by service_type × year × month:")
        sym = (
            sample_df.groupby(["service_type", "year", "month"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(["service_type", "year", "month"])
        )
        print(sym.to_string(index=False))

        print(f"\n5. Non-positive passenger_cost rows: {int(sample_df['passenger_cost_nonpositive_flag'].sum())}")
        print(f"6. Negative CBD-fee rows: {int(sample_df['negative_cbd_fee_flag'].sum())}")
        print(f"7. Yellow payment-review rows: {int(sample_df['yellow_payment_review_flag'].sum())}")
        hvfhv_refund = int(
            (
                sample_df["possible_refund_or_adjustment_flag"]
                & (sample_df["service_type"] == "hvfhv")
            ).sum()
        )
        print(f"8. HVFHV possible refund/adjustment rows: {hvfhv_refund}")
        print(f"9. DST transition-window rows: {int(sample_df['dst_transition_window_flag'].sum())}")

    print("\n10. Shortages / fallback decisions:")
    for note in sample_notes:
        print(f"  - {note.get('note', note)}")
    print(f"  - Full notes: {NOTES_PATH.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
