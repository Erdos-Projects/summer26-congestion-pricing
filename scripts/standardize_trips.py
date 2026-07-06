"""
First-step cleaning and standardization for NYC TLC Yellow Taxi and HVFHV trips.

Reads one raw parquet file at a time, applies conservative validity filters,
maps to a shared trip-level schema, and writes monthly standardized parquet files
under data/processed/00_standardized_trips/.

Never modifies files in data/raw/.
"""

from __future__ import annotations

import re
import argparse
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

# --- Paths (relative to repository root) ---
REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips"
QC_DIR = REPO_ROOT / "data" / "processed" / "qc"

# --- Shared output schema ---
STANDARD_COLUMNS = [
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
    "relative_cbd_burden",
    "source_file",
]

YELLOW_OPTIONAL_COLUMNS = [
    "payment_type",
    "passenger_count",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "RatecodeID",
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
    "zero_distance_flag",
    "very_long_duration_flag",
    "very_long_distance_flag",
    "negative_cost_flag",
]

# Yellow-only regime / trip-type flags derived from payment_type and airport fields.
YELLOW_FLAG_COLUMNS = [
    "yellow_card_or_cash_flag",
    "flex_fare_flag",
    "irregular_payment_flag",
    "airport_trip_flag",
]

# TLC LocationIDs for the JFK and LaGuardia airport zones (used for airport_trip_flag).
AIRPORT_ZONE_IDS = {132, 138}

# QC thresholds (flags only; rows are not dropped for these)
VERY_LONG_DURATION_SECONDS = 24 * 60 * 60  # 24 hours
VERY_LONG_DISTANCE_MILES = 100.0

# Month folder names in data/raw/ -> numeric month for output filenames
MONTH_NAME_TO_NUM = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def identify_service_type(filename: str) -> str | None:
    """Classify a raw parquet file as yellow or hvfhv from its filename."""
    name = filename.lower()
    if "yellow" in name:
        return "yellow"
    if "fhvhv" in name or "hvfhv" in name:
        return "hvfhv"
    return None


def parse_year_month_from_path(file_path: Path) -> tuple[int, int] | None:
    """
    Extract (year, month) from folder structure and/or filename.

    Expected layout: data/raw/{year}/{MonthName}/...
    Filename fallback: *_tripdata_YYYY-MM.parquet
    """
    year_match = re.search(r"(20\d{2})", file_path.as_posix())
    year = int(year_match.group(1)) if year_match else None

    month_num = None
    for part in file_path.parts:
        key = part.lower()
        if key in MONTH_NAME_TO_NUM:
            month_num = MONTH_NAME_TO_NUM[key]
            break

    if month_num is None:
        file_match = re.search(r"20\d{2}-(\d{2})", file_path.name)
        if file_match:
            month_num = int(file_match.group(1))

    if year is None or month_num is None:
        return None
    return year, month_num


def _safe_numeric(series: pd.Series) -> pd.Series:
    """Coerce to numeric; invalid values become NaN."""
    return pd.to_numeric(series, errors="coerce")


def _fill_cbd_fee(series: pd.Series | None, year: int, index: pd.Index) -> pd.Series:
    """
    Handle missing cbd_congestion_fee.

    Pre-policy 2024 files do not include this column; filling with 0 is safe
    because the CBD congestion fee did not apply before January 2025.
    """
    if series is None:
        return pd.Series(0.0, index=index)
    filled = _safe_numeric(series).fillna(0.0 if year < 2025 else pd.NA)
    return filled


def standardize_yellow(
    df: pd.DataFrame, year: int, month: int, source_file: str
) -> pd.DataFrame:
    """Map Yellow Taxi raw columns to the shared standardized schema."""
    out = pd.DataFrame(index=df.index)

    out["service_type"] = "yellow"
    out["year"] = year
    out["month"] = month
    out["pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"], errors="coerce")
    out["dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"], errors="coerce")
    out["pickup_date"] = out["pickup_datetime"].dt.date
    out["pickup_hour"] = out["pickup_datetime"].dt.hour
    out["day_of_week"] = out["pickup_datetime"].dt.dayofweek

    out["PULocationID"] = _safe_numeric(df["PULocationID"])
    out["DOLocationID"] = _safe_numeric(df["DOLocationID"])
    out["trip_distance_miles"] = _safe_numeric(df["trip_distance"])

    # Yellow has no trip_time; derive duration from pickup/dropoff timestamps.
    out["trip_duration_seconds"] = (
        out["dropoff_datetime"] - out["pickup_datetime"]
    ).dt.total_seconds()

    cbd_col = df["cbd_congestion_fee"] if "cbd_congestion_fee" in df.columns else None
    out["cbd_congestion_fee"] = _fill_cbd_fee(cbd_col, year, df.index)

    out["congestion_surcharge"] = _safe_numeric(df.get("congestion_surcharge", pd.NA))
    out["tolls"] = _safe_numeric(df.get("tolls_amount", pd.NA))

    # TLC uses Airport_fee (capital A) in yellow files.
    airport_col = df["Airport_fee"] if "Airport_fee" in df.columns else df.get("airport_fee")
    out["airport_fee"] = _safe_numeric(airport_col)

    tip_amount = _safe_numeric(df.get("tip_amount", 0)).fillna(0)
    total_amount = _safe_numeric(df.get("total_amount", pd.NA))
    # Pre-tip passenger cost: total charge minus voluntary tip.
    out["passenger_cost_pretip"] = total_amount - tip_amount

    out["source_file"] = source_file

    # Optional Yellow-specific helper columns
    for col in YELLOW_OPTIONAL_COLUMNS:
        if col in df.columns:
            out[col] = df[col]

    return out


def standardize_hvfhv(
    df: pd.DataFrame, year: int, month: int, source_file: str
) -> pd.DataFrame:
    """Map HVFHV raw columns to the shared standardized schema."""
    out = pd.DataFrame(index=df.index)

    out["service_type"] = "hvfhv"
    out["year"] = year
    out["month"] = month
    out["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"], errors="coerce")
    out["dropoff_datetime"] = pd.to_datetime(df["dropoff_datetime"], errors="coerce")
    out["pickup_date"] = out["pickup_datetime"].dt.date
    out["pickup_hour"] = out["pickup_datetime"].dt.hour
    out["day_of_week"] = out["pickup_datetime"].dt.dayofweek

    out["PULocationID"] = _safe_numeric(df["PULocationID"])
    out["DOLocationID"] = _safe_numeric(df["DOLocationID"])
    out["trip_distance_miles"] = _safe_numeric(df["trip_miles"])
    out["trip_duration_seconds"] = _safe_numeric(df["trip_time"])

    cbd_col = df["cbd_congestion_fee"] if "cbd_congestion_fee" in df.columns else None
    out["cbd_congestion_fee"] = _fill_cbd_fee(cbd_col, year, df.index)

    out["congestion_surcharge"] = _safe_numeric(df.get("congestion_surcharge", pd.NA))
    out["tolls"] = _safe_numeric(df.get("tolls", pd.NA))
    out["airport_fee"] = _safe_numeric(df.get("airport_fee", pd.NA))

    base_fare = _safe_numeric(df.get("base_passenger_fare", 0)).fillna(0)
    tolls = _safe_numeric(df.get("tolls", 0)).fillna(0)
    bcf = _safe_numeric(df.get("bcf", 0)).fillna(0)
    sales_tax = _safe_numeric(df.get("sales_tax", 0)).fillna(0)
    congestion_surcharge = _safe_numeric(df.get("congestion_surcharge", 0)).fillna(0)
    airport_fee = _safe_numeric(df.get("airport_fee", 0)).fillna(0)
    cbd_fee = _safe_numeric(out["cbd_congestion_fee"]).fillna(0)

    # Pre-tip passenger cost: base fare plus mandatory fees/taxes, excluding tips.
    out["passenger_cost_pretip"] = (
        base_fare
        + tolls
        + bcf
        + sales_tax
        + congestion_surcharge
        + airport_fee
        + cbd_fee
    )

    out["source_file"] = source_file

    for col in HVFHV_OPTIONAL_COLUMNS:
        if col in df.columns:
            out[col] = df[col]

    return out


def add_derived_and_qc_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Compute burden fields and basic QC flags (informational, not filters)."""
    df = df.copy()

    df["charged_cbd_flag"] = df["cbd_congestion_fee"] > 0

    # Relative burden only when pre-tip cost is strictly positive.
    df["relative_cbd_burden"] = pd.NA
    valid_cost = df["passenger_cost_pretip"] > 0
    df.loc[valid_cost, "relative_cbd_burden"] = (
        df.loc[valid_cost, "cbd_congestion_fee"] / df.loc[valid_cost, "passenger_cost_pretip"]
    )

    df["zero_distance_flag"] = df["trip_distance_miles"] == 0
    df["very_long_duration_flag"] = df["trip_duration_seconds"] > VERY_LONG_DURATION_SECONDS
    df["very_long_distance_flag"] = df["trip_distance_miles"] > VERY_LONG_DISTANCE_MILES
    df["negative_cost_flag"] = df["passenger_cost_pretip"] <= 0

    # Yellow-only regime / trip-type flags. payment_type is a Yellow field
    # (HVFHV files never carry it), so its presence marks a Yellow frame.
    if "payment_type" in df.columns:
        pt = _safe_numeric(df["payment_type"])
        df["yellow_card_or_cash_flag"] = pt.isin([1, 2])          # 1 = credit card, 2 = cash
        df["flex_fare_flag"] = pt.eq(0)                            # 0 = Flex Fare
        df["irregular_payment_flag"] = pt.isin([3, 4, 5, 6])      # no-charge / dispute / unknown / voided
        # Airport trip = airport fee charged AND a pickup/dropoff at JFK or LaGuardia.
        df["airport_trip_flag"] = (_safe_numeric(df["airport_fee"]) > 0) & (
            df["PULocationID"].isin(AIRPORT_ZONE_IDS)
            | df["DOLocationID"].isin(AIRPORT_ZONE_IDS)
        )

    return df


def apply_conservative_filters(
    df: pd.DataFrame, year: int, month: int
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Apply fundamental validity checks. Returns cleaned DataFrame and drop counts
    by reason (for the cleaning report).
    """
    drops: dict[str, int] = {}
    n_start = len(df)

    def _drop(mask: pd.Series, reason: str) -> None:
        nonlocal df
        n = int(mask.sum())
        if n:
            drops[reason] = drops.get(reason, 0) + n
            df = df.loc[~mask]

    # 1–2. Valid pickup and dropoff datetimes.
    _drop(df["pickup_datetime"].isna(), "invalid_pickup_datetime")
    _drop(df["dropoff_datetime"].isna(), "invalid_dropoff_datetime")

    # 3. Dropoff must be strictly after pickup.
    _drop(df["dropoff_datetime"] <= df["pickup_datetime"], "dropoff_not_after_pickup")

    # 4. Pickup year/month must match the source folder.
    _drop(
        (df["pickup_datetime"].dt.year != year) | (df["pickup_datetime"].dt.month != month),
        "pickup_year_month_mismatch",
    )

    # 5. Zone IDs must be present.
    _drop(df["PULocationID"].isna() | df["DOLocationID"].isna(), "missing_zone_id")

    # 6. Distance cannot be negative (zero-distance trips are kept).
    _drop(df["trip_distance_miles"] < 0, "negative_distance")

    # 7. Duration must be strictly positive.
    _drop(df["trip_duration_seconds"] <= 0, "non_positive_duration")

    # 8–9. CBD fee must be present and non-negative.
    # (2024 missing values were already filled with 0 in standardize_*.)
    _drop(df["cbd_congestion_fee"].isna(), "missing_cbd_congestion_fee")
    _drop(df["cbd_congestion_fee"] < 0, "negative_cbd_congestion_fee")

    # 10. Pre-tip passenger cost must be positive for burden outputs.
    _drop(df["passenger_cost_pretip"] <= 0, "non_positive_passenger_cost_pretip")

    drops["rows_before"] = n_start
    drops["rows_after"] = len(df)
    drops["rows_dropped"] = n_start - len(df)
    return df, drops


def discover_raw_parquet_files(
    year: int | None = None,
    months: set[int] | None = None,
    services: set[str] | None = None,
) -> list[Path]:
    """Find Yellow and HVFHV parquet files under data/raw/, optionally scoped."""
    files = sorted(RAW_DIR.rglob("*.parquet"))
    scoped_files: list[Path] = []
    for file_path in files:
        service_type = identify_service_type(file_path.name)
        year_month = parse_year_month_from_path(file_path)
        if service_type is None or year_month is None:
            continue
        file_year, file_month = year_month
        if year is not None and file_year != year:
            continue
        if months is not None and file_month not in months:
            continue
        if services is not None and service_type not in services:
            continue
        scoped_files.append(file_path)
    return scoped_files


def output_path_for(service_type: str, year: int, month: int) -> Path:
    """Build processed output path: .../00_standardized_trips/{service}/{year}/{MM}.parquet"""
    return PROCESSED_DIR / service_type / str(year) / f"{month:02d}.parquet"


def order_columns(df: pd.DataFrame, service_type: str) -> pd.DataFrame:
    """Place standard columns first, then service-specific optional columns, then QC flags."""
    optional = YELLOW_OPTIONAL_COLUMNS if service_type == "yellow" else HVFHV_OPTIONAL_COLUMNS
    cols = [c for c in STANDARD_COLUMNS if c in df.columns]
    cols += [c for c in optional if c in df.columns]
    cols += [c for c in QC_FLAG_COLUMNS if c in df.columns]
    cols += [c for c in YELLOW_FLAG_COLUMNS if c in df.columns]
    return df[cols]


def align_to_reference_schema(
    df: pd.DataFrame, service_type: str, month: int, reference_year: int | None
) -> pd.DataFrame:
    """Optionally align output columns to an existing processed reference year."""
    if reference_year is None:
        return df

    reference_path = output_path_for(service_type, reference_year, month)
    if not reference_path.exists():
        raise FileNotFoundError(
            f"Missing reference schema file: {reference_path.relative_to(REPO_ROOT)}"
        )

    reference_columns = pq.read_schema(reference_path).names
    missing_columns = [col for col in reference_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Cannot align {service_type} {month:02d} to {reference_year}: "
            f"missing columns {missing_columns}"
        )
    return df[reference_columns]


def process_one_file(raw_path: Path, match_schema_year: int | None = None) -> dict:
    """Read, standardize, clean, and save one raw parquet file."""
    raw_path = raw_path.resolve()
    service_type = identify_service_type(raw_path.name)
    year_month = parse_year_month_from_path(raw_path)
    rel_source = raw_path.relative_to(REPO_ROOT).as_posix()

    record: dict = {
        "source_file": rel_source,
        "service_type": service_type,
        "status": "ok",
    }

    if service_type is None:
        record["status"] = "skipped"
        record["skip_reason"] = "unrecognized_service_type"
        return record

    if year_month is None:
        record["status"] = "skipped"
        record["skip_reason"] = "could_not_parse_year_month"
        return record

    year, month = year_month
    record["year"] = year
    record["month"] = month

    print(f"Processing {rel_source} ({service_type}, {year}-{month:02d}) ...")

    df_raw = pd.read_parquet(raw_path)
    record["rows_before"] = len(df_raw)

    if service_type == "yellow":
        df = standardize_yellow(df_raw, year, month, rel_source)
    else:
        df = standardize_hvfhv(df_raw, year, month, rel_source)

    df = add_derived_and_qc_flags(df)
    df, drop_detail = apply_conservative_filters(df, year, month)
    record.update(drop_detail)

    df = order_columns(df, service_type)
    df = align_to_reference_schema(df, service_type, month, match_schema_year)

    out_path = output_path_for(service_type, year, month)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    record["output_file"] = out_path.relative_to(REPO_ROOT).as_posix()

    print(
        f"  {record['rows_before']:,} -> {record['rows_after']:,} rows "
        f"({record['rows_dropped']:,} dropped)"
    )
    return record


def write_qc_reports(
    row_records: list[dict], issue_records: list[dict], filename_suffix: str = ""
) -> None:
    """Write row-count and issue summaries to data/processed/qc/."""
    QC_DIR.mkdir(parents=True, exist_ok=True)

    counts_df = pd.DataFrame(row_records)
    counts_path = QC_DIR / f"standardization_row_counts{filename_suffix}.csv"
    counts_df.to_csv(counts_path, index=False)

    issues_df = pd.DataFrame(issue_records)
    issues_path = QC_DIR / f"standardization_issues{filename_suffix}.csv"
    issues_df.to_csv(issues_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standardize raw TLC Yellow and HVFHV parquet files one file at a time."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Optional source year filter, for example 2023.",
    )
    parser.add_argument(
        "--months",
        nargs="+",
        type=int,
        default=None,
        help="Optional numeric month filter, for example --months 2 3 4 5 6.",
    )
    parser.add_argument(
        "--service",
        nargs="+",
        choices=["yellow", "hvfhv"],
        default=None,
        help="Optional service filter. Defaults to both services.",
    )
    parser.add_argument(
        "--qc-suffix",
        default=None,
        help=(
            "Optional suffix for QC filenames, such as _2023. "
            "Defaults to _YEAR when --year is supplied."
        ),
    )
    parser.add_argument(
        "--match-existing-schema-year",
        type=int,
        default=None,
        help=(
            "Optional processed year to use as the output column reference. "
            "Useful when adding a new year without rewriting existing years."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    month_filter = set(args.months) if args.months is not None else None
    service_filter = set(args.service) if args.service is not None else None
    qc_suffix = args.qc_suffix
    if qc_suffix is None:
        qc_suffix = f"_{args.year}" if args.year is not None else ""

    raw_files = discover_raw_parquet_files(
        year=args.year,
        months=month_filter,
        services=service_filter,
    )
    row_records: list[dict] = []
    issue_records: list[dict] = []
    created_outputs: list[str] = []

    scope_bits = []
    if args.year is not None:
        scope_bits.append(f"year={args.year}")
    if month_filter is not None:
        scope_bits.append(f"months={sorted(month_filter)}")
    if service_filter is not None:
        scope_bits.append(f"services={sorted(service_filter)}")
    scope = f" ({', '.join(scope_bits)})" if scope_bits else ""

    print(f"Found {len(raw_files)} raw Yellow/HVFHV parquet file(s) under {RAW_DIR}{scope}\n")

    for raw_path in raw_files:
        record = process_one_file(
            raw_path, match_schema_year=args.match_existing_schema_year
        )
        row_records.append(record)

        if record["status"] == "skipped":
            issue_records.append(
                {
                    "source_file": record.get("source_file"),
                    "issue": record.get("skip_reason"),
                }
            )
        elif record.get("rows_dropped", 0) > 0:
            issue_records.append(
                {
                    "source_file": record.get("source_file"),
                    "issue": "rows_dropped_during_cleaning",
                    "rows_before": record.get("rows_before"),
                    "rows_after": record.get("rows_after"),
                    "rows_dropped": record.get("rows_dropped"),
                }
            )

        if record.get("output_file"):
            created_outputs.append(record["output_file"])

    write_qc_reports(row_records, issue_records, filename_suffix=qc_suffix)

    # --- Summary for teammates ---
    print("\n" + "=" * 60)
    print("STANDARDIZATION SUMMARY")
    print("=" * 60)
    print(f"1. Raw files processed: {sum(1 for r in row_records if r['status'] == 'ok')}")
    print(f"   Raw files found:    {len(raw_files)}")
    print(f"2. Standardized parquet files created: {len(created_outputs)}")

    print("\n3. Row counts before and after cleaning (by service/year/month):")
    ok_records = [r for r in row_records if r["status"] == "ok"]
    if ok_records:
        summary = pd.DataFrame(ok_records)[
            ["service_type", "year", "month", "rows_before", "rows_after", "rows_dropped"]
        ].sort_values(["service_type", "year", "month"])
        print(summary.to_string(index=False))

    print("\n4. 100-row sample CSV: run scripts/make_trip_level_sample.py after this step.")
    print(f"   Target path: data/processed/samples/trip_level_sample.csv")

    skipped = [r for r in row_records if r["status"] == "skipped"]
    print(f"\n5. Files skipped: {len(skipped)}")
    for r in skipped:
        print(f"   - {r.get('source_file')}: {r.get('skip_reason')}")

    print(f"\nQC reports written to: {QC_DIR.relative_to(REPO_ROOT).as_posix()}/")


if __name__ == "__main__":
    main()
