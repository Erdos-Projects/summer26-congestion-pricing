# Data Setup

Large TLC trip-level Parquet files are not stored in git. The repository includes the smaller
processed tables, samples, QC outputs, and taxi-zone geometry needed to inspect the analysis.

## Standardized data: recommended setup

The complete standardized-data package is available on
[Google Drive](https://drive.google.com/file/d/1lceqcvCE38_g8thraWwVSv_J1t-7Vatp/view?usp=sharing)
(approximately 7.3 GB).

It contains 30 monthly Parquet files:

- Yellow Taxi and HVFHV;
- February-June 2023, 2024, and 2025;
- 2024-2025 for the main analysis;
- 2023 for the no-fee placebo comparisons.

Download the ZIP and extract it outside the repository first. The archive also contains its own
`README.md`, `DATA_MANIFEST.csv`, and `SHA256SUMS.txt`, so extracting it directly over the repository
could overwrite the project README.

From the extracted package directory, verify the files:

```bash
shasum -a 256 -c SHA256SUMS.txt
```

Then copy only the standardized-trip directory into the repository:

```bash
mkdir -p data/processed
cp -R data/processed/00_standardized_trips /path/to/summer26-congestion-pricing/data/processed/
```

The final repository layout should be:

```text
data/processed/00_standardized_trips/
  yellow/
    2023/02.parquet ... 06.parquet
    2024/02.parquet ... 06.parquet
    2025/02.parquet ... 06.parquet
  hvfhv/
    2023/02.parquet ... 06.parquet
    2024/02.parquet ... 06.parquet
    2025/02.parquet ... 06.parquet
```

## Build from raw TLC files

The original monthly records can be downloaded from the
[NYC TLC Trip Record Data page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
Raw files are public source data and are not redistributed in this repository.

Place Yellow and HVFHV files under `data/raw/{year}/{Month}/`, using names such as:

```text
data/raw/2024/Feb/yellow_tripdata_2024-02.parquet
data/raw/2024/Feb/fhvhv_tripdata_2024-02.parquet
```

Then run:

```bash
python scripts/standardize_trips.py
python scripts/validate_standardized_trips.py
```

Building all three years from raw files is substantially slower than using the standardized-data
package. See [`../docs/data_structure_and_schema.md`](../docs/data_structure_and_schema.md) for the
schema and cleaning rules.

## What is tracked in git

The following smaller artifacts remain in the repository:

- `data/processed/disruption_score/`: burden metrics, exposure checks, monthly panels, and placebo panels;
- `data/processed/modeling/`: model-ready feature tables;
- `data/processed/samples/`: representative and diagnostic samples;
- `data/processed/qc/`: standardization and validation reports;
- `data/geo/taxi_zones/`: TLC taxi-zone geometry.

The main notebooks read standardized Parquet files from
`data/processed/00_standardized_trips/{service}/{year}/{month}.parquet`.
