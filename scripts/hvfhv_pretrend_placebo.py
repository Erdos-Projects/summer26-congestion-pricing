"""
HVFHV no-June pretrend and placebo diagnostics for Model 2.

This script is diagnostic only. It excludes June to avoid possible June-specific
shocks and does not rebuild the existing 2024-2025 Model 2 panel.

Inputs:
  - Standardized HVFHV parquet files for Feb-May 2023 and 2024
  - Existing hvfhv_monthly_panel.csv for the 2024-only pretrend exposure
  - taxi_zone_lookup.csv
  - CRZ zone list from scripts/yellow_ds_pipeline.py

Outputs:
  - data/processed/disruption_score/hvfhv_pretrend_2024_diagnostic.csv
  - data/processed/disruption_score/hvfhv_placebo_2023_2024_panel.csv
  - data/processed/disruption_score/hvfhv_placebo_2023_2024_results.csv
  - data/processed/disruption_score/hvfhv_pretrend_placebo_notes.md
"""

from __future__ import annotations

from pathlib import Path
import sys

import duckdb
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.yellow_ds_pipeline import CRZ_ZONE_IDS  # noqa: E402

HVFHV_DIR = REPO_ROOT / "data" / "processed" / "00_standardized_trips" / "hvfhv"
ZONE_LOOKUP_PATH = REPO_ROOT / "data" / "taxi_zone_lookup.csv"
DS_DIR = REPO_ROOT / "data" / "processed" / "disruption_score"
MODEL2_PANEL_PATH = DS_DIR / "hvfhv_monthly_panel.csv"

PRETREND_OUTPUT = DS_DIR / "hvfhv_pretrend_2024_diagnostic.csv"
PLACEBO_PANEL_OUTPUT = DS_DIR / "hvfhv_placebo_2023_2024_panel.csv"
PLACEBO_RESULTS_OUTPUT = DS_DIR / "hvfhv_placebo_2023_2024_results.csv"
NOTES_OUTPUT = DS_DIR / "hvfhv_pretrend_placebo_notes.md"

MONTHS = (2, 3, 4, 5)
MONTH_LABELS = {2: "Feb", 3: "Mar", 4: "Apr", 5: "May"}
CRZ_SQL = "(" + ", ".join(str(z) for z in CRZ_ZONE_IDS) + ")"

# Existing HVFHV Model 2 FE-style coefficient from the final Model 2 notebook.
# It is used only to label placebo diagnostic strength; Model 2 is not rerun.
MODEL2_REFERENCE_COEF = -0.1136


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def parquet_list_sql(paths: list[Path]) -> str:
    quoted = ", ".join(f"'{sql_path(path)}'" for path in paths)
    return f"[{quoted}]"


def required_hvfhv_paths(years: tuple[int, ...]) -> list[Path]:
    paths = []
    for year in years:
        for month in MONTHS:
            path = HVFHV_DIR / str(year) / f"{month:02d}.parquet"
            if not path.exists():
                raise FileNotFoundError(f"Missing required input: {path.relative_to(REPO_ROOT)}")
            paths.append(path)
    return paths


def require_inputs() -> None:
    required_hvfhv_paths((2023, 2024))
    if not MODEL2_PANEL_PATH.exists():
        raise FileNotFoundError(f"Missing required input: {MODEL2_PANEL_PATH.relative_to(REPO_ROOT)}")
    if not ZONE_LOOKUP_PATH.exists():
        raise FileNotFoundError(f"Missing required input: {ZONE_LOOKUP_PATH.relative_to(REPO_ROOT)}")
    DS_DIR.mkdir(parents=True, exist_ok=True)


def write_pretrend_2024() -> dict[str, float | int | str]:
    panel = pd.read_csv(MODEL2_PANEL_PATH)
    pre = panel[
        (panel["year"].eq(2024))
        & (panel["month"].isin(MONTHS))
        & (panel["charged_share_2024_geo"].notna())
        & (panel["n_trips"] > 0)
    ].copy()
    pre["unit_id"] = pre["zone"].astype(str) + "_" + pre["direction"].astype(str)
    pre["month_index"] = pre["month"].map({month: idx for idx, month in enumerate(MONTHS)})

    unit_exposure = pre.drop_duplicates("unit_id")[["unit_id", "charged_share_2024_geo"]].copy()
    unit_exposure["exposure_quartile"] = pd.qcut(
        unit_exposure["charged_share_2024_geo"],
        4,
        labels=["Q1 low", "Q2", "Q3", "Q4 high"],
        duplicates="drop",
    )
    pre = pre.merge(unit_exposure[["unit_id", "exposure_quartile"]], on="unit_id", how="left")

    baseline = pre.groupby("unit_id", observed=True)["n_trips"].mean().rename("unit_avg_2024")
    pre = pre.merge(baseline, on="unit_id", how="left")
    pre["indexed_unit_volume"] = pre["n_trips"] / pre["unit_avg_2024"]

    diagnostic = (
        pre.groupby(["exposure_quartile", "month"], observed=True)
        .agg(
            indexed_n_trips=("indexed_unit_volume", "mean"),
            average_n_trips=("n_trips", "mean"),
            n_units=("unit_id", "nunique"),
        )
        .reset_index()
    )
    diagnostic.insert(1, "month_label", diagnostic["month"].map(MONTH_LABELS))
    diagnostic.to_csv(PRETREND_OUTPUT, index=False)

    model = smf.ols(
        "log_n_trips ~ month_index * charged_share_2024_geo", data=pre
    ).fit(cov_type="cluster", cov_kwds={"groups": pre["unit_id"]})
    term = "month_index:charged_share_2024_geo"
    coef = float(model.params[term])
    se = float(model.bse[term])
    ci_lower, ci_upper = [float(v) for v in model.conf_int().loc[term]]
    return {
        "model_name": "pretrend_2024_no_june",
        "term": term,
        "coefficient": coef,
        "standard_error": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_rows": int(model.nobs),
        "n_units": int(pre["unit_id"].nunique()),
        "output_rows": int(len(diagnostic)),
    }


def build_placebo_panel() -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("SET threads TO 1")

    paths = required_hvfhv_paths((2023, 2024))
    con.execute(
        f"""
        CREATE OR REPLACE VIEW trips AS
        SELECT year, month, PULocationID, DOLocationID
        FROM read_parquet({parquet_list_sql(paths)})
        WHERE year IN (2023, 2024) AND month IN {tuple(MONTHS)}
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW zone_lookup AS
        SELECT LocationID, Borough, Zone AS zone_name, service_zone
        FROM read_csv_auto('{sql_path(ZONE_LOOKUP_PATH)}')
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE exposure_2023 AS
        WITH base AS (
            SELECT
                PULocationID,
                DOLocationID,
                (PULocationID IN {CRZ_SQL} OR DOLocationID IN {CRZ_SQL}) AS geography_exposed
            FROM trips
            WHERE year = 2023
        ),
        pickup AS (
            SELECT
                PULocationID AS zone,
                'pickup' AS direction,
                AVG(geography_exposed::INT)::DOUBLE AS charged_share_2023_geo
            FROM base
            GROUP BY PULocationID
        ),
        dropoff AS (
            SELECT
                DOLocationID AS zone,
                'dropoff' AS direction,
                AVG(geography_exposed::INT)::DOUBLE AS charged_share_2023_geo
            FROM base
            GROUP BY DOLocationID
        )
        SELECT * FROM pickup
        UNION ALL
        SELECT * FROM dropoff
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE placebo_panel AS
        WITH pickup AS (
            SELECT
                PULocationID AS zone,
                'pickup' AS direction,
                year,
                month,
                COUNT(*) AS n_trips
            FROM trips
            GROUP BY PULocationID, year, month
        ),
        dropoff AS (
            SELECT
                DOLocationID AS zone,
                'dropoff' AS direction,
                year,
                month,
                COUNT(*) AS n_trips
            FROM trips
            GROUP BY DOLocationID, year, month
        ),
        panel AS (
            SELECT * FROM pickup
            UNION ALL
            SELECT * FROM dropoff
        )
        SELECT
            p.zone,
            p.direction,
            p.year,
            p.month,
            p.n_trips,
            LN(p.n_trips) AS log_n_trips,
            CASE WHEN p.year = 2024 THEN 1 ELSE 0 END AS placebo_post,
            z.Borough,
            COALESCE(z.zone_name, 'Zone ' || CAST(p.zone AS VARCHAR)) AS zone_name,
            z.service_zone,
            (p.zone IN {CRZ_SQL}) AS crz_zone,
            e.charged_share_2023_geo,
            CAST(p.zone AS VARCHAR) || '_' || p.direction AS unit_id
        FROM panel p
        LEFT JOIN zone_lookup z ON p.zone = z.LocationID
        LEFT JOIN exposure_2023 e
            ON p.zone = e.zone AND p.direction = e.direction
        ORDER BY p.zone, p.direction, p.year, p.month
        """
    )
    con.execute(
        f"""
        COPY (
            SELECT * FROM placebo_panel
        ) TO '{sql_path(PLACEBO_PANEL_OUTPUT)}' (HEADER, DELIMITER ',')
        """
    )
    panel = con.execute("SELECT * FROM placebo_panel").fetchdf()
    con.close()
    return panel


def interpretation_flag(coef: float, ci_lower: float, ci_upper: float) -> str:
    reference_abs = abs(MODEL2_REFERENCE_COEF)
    coef_abs = abs(coef)
    ci_includes_zero = ci_lower <= 0 <= ci_upper
    if coef < 0 and coef_abs >= 0.75 * reference_abs:
        return "weakens_causal_interpretation"
    if coef_abs <= 0.50 * reference_abs or ci_includes_zero:
        return "supportive_diagnostic"
    return "mixed_diagnostic"


def fit_placebo_models(panel: pd.DataFrame) -> pd.DataFrame:
    model_specs = [
        (
            "placebo_simple",
            "log_n_trips ~ placebo_post * charged_share_2023_geo",
            panel,
        ),
        (
            "placebo_unit_fe",
            "log_n_trips ~ placebo_post * charged_share_2023_geo + C(unit_id) + C(month)",
            panel,
        ),
        (
            "placebo_unit_fe_exclude_n_trips_lt_30",
            "log_n_trips ~ placebo_post * charged_share_2023_geo + C(unit_id) + C(month)",
            panel[panel["n_trips"] >= 30].copy(),
        ),
    ]

    rows = []
    term = "placebo_post:charged_share_2023_geo"
    for model_name, formula, data in model_specs:
        data = data.dropna(subset=["log_n_trips", "placebo_post", "charged_share_2023_geo", "unit_id", "month"]).copy()
        model = smf.ols(formula, data=data).fit(cov_type="cluster", cov_kwds={"groups": data["unit_id"]})
        coef = float(model.params[term])
        se = float(model.bse[term])
        ci_lower, ci_upper = [float(v) for v in model.conf_int().loc[term]]
        rows.append(
            {
                "model_name": model_name,
                "coefficient": coef,
                "standard_error": se,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "n_rows": int(model.nobs),
                "interpretation_flag": interpretation_flag(coef, ci_lower, ci_upper),
            }
        )

    results = pd.DataFrame(rows)
    results.to_csv(PLACEBO_RESULTS_OUTPUT, index=False)
    return results


def write_notes(
    pretrend: dict[str, float | int | str],
    placebo_panel: pd.DataFrame,
    placebo_results: pd.DataFrame,
) -> None:
    missing_months = []
    expected = {(year, month) for year in (2023, 2024) for month in MONTHS}
    observed = set(zip(placebo_panel["year"], placebo_panel["month"]))
    for year, month in sorted(expected - observed):
        missing_months.append(f"{year}-{month:02d}")

    primary_placebo = placebo_results[
        placebo_results["model_name"].eq("placebo_unit_fe")
    ].iloc[0]
    if primary_placebo["interpretation_flag"] == "weakens_causal_interpretation":
        diagnostic_takeaway = (
            "The no-June placebo coefficient is negative and similar in magnitude "
            "to the existing Model 2 reference estimate, so this diagnostic weakens "
            "a causal interpretation."
        )
    elif primary_placebo["interpretation_flag"] == "supportive_diagnostic":
        diagnostic_takeaway = (
            "The no-June placebo coefficient is near zero, imprecise, or much weaker "
            "than the existing Model 2 reference estimate, so this diagnostic is supportive."
        )
    else:
        diagnostic_takeaway = (
            "The no-June placebo coefficient is not as large as the existing Model 2 "
            "reference estimate, but it is not close enough to zero to be cleanly supportive."
        )

    text = f"""# HVFHV No-June Pretrend And Placebo Diagnostics

Diagnostic only. These checks exclude June and do not prove or disprove parallel trends.

## Inputs

- Standardized HVFHV parquet files for Feb-May 2023 and Feb-May 2024
- Existing `hvfhv_monthly_panel.csv` for the 2024-only pretrend exposure
- CRZ zone list reused from `scripts/yellow_ds_pipeline.py`
- `data/taxi_zone_lookup.csv`

## 2024 Pretrend Diagnostic

Formula: `log_n_trips ~ month_index * charged_share_2024_geo`

- coefficient on `month_index:charged_share_2024_geo`: {pretrend['coefficient']:.6f}
- standard error: {pretrend['standard_error']:.6f}
- 95 percent CI: [{pretrend['ci_lower']:.6f}, {pretrend['ci_upper']:.6f}]
- rows: {pretrend['n_rows']}
- units: {pretrend['n_units']}

The pretrend output is a diagnostic visualization table, not proof of parallel trends.

## 2023-vs-2024 Placebo

Main exposure: `charged_share_2023_geo`, computed only from 2023 geography.

Reference for interpretation only: existing HVFHV Model 2 FE-style coefficient approximately {MODEL2_REFERENCE_COEF:.4f}. Model 2 is not rerun here.

Primary placebo result, `placebo_unit_fe`:

- coefficient on `placebo_post:charged_share_2023_geo`: {primary_placebo['coefficient']:.6f}
- standard error: {primary_placebo['standard_error']:.6f}
- 95 percent CI: [{primary_placebo['ci_lower']:.6f}, {primary_placebo['ci_upper']:.6f}]
- rows: {int(primary_placebo['n_rows'])}
- interpretation flag: {primary_placebo['interpretation_flag']}

{diagnostic_takeaway} This is diagnostic evidence, not proof.

## Coverage

- Missing expected months: {', '.join(missing_months) if missing_months else 'none'}
- Placebo panel rows: {len(placebo_panel)}
- Placebo panel units: {placebo_panel['unit_id'].nunique()}
- Missing placebo exposure rows: {int(placebo_panel['charged_share_2023_geo'].isna().sum())}
- Placebo rows with `n_trips < 30`: {int((placebo_panel['n_trips'] < 30).sum())}

## Outputs

- `data/processed/disruption_score/hvfhv_pretrend_2024_diagnostic.csv`
- `data/processed/disruption_score/hvfhv_placebo_2023_2024_panel.csv`
- `data/processed/disruption_score/hvfhv_placebo_2023_2024_results.csv`
"""
    NOTES_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    require_inputs()
    pretrend = write_pretrend_2024()
    placebo_panel = build_placebo_panel()
    placebo_results = fit_placebo_models(placebo_panel)
    write_notes(pretrend, placebo_panel, placebo_results)

    print("HVFHV no-June diagnostics complete.")
    print(f"Pretrend rows: {pretrend['output_rows']}")
    print(f"Placebo panel rows: {len(placebo_panel)}")
    print(f"Placebo results rows: {len(placebo_results)}")
    print("Primary placebo result:")
    primary = placebo_results[placebo_results["model_name"].eq("placebo_unit_fe")].iloc[0]
    print(
        f"  coefficient={primary['coefficient']:.6f}, "
        f"se={primary['standard_error']:.6f}, "
        f"ci=[{primary['ci_lower']:.6f}, {primary['ci_upper']:.6f}], "
        f"flag={primary['interpretation_flag']}"
    )


if __name__ == "__main__":
    main()
