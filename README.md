# MOEPP Air Quality Data Pipeline

A Python-based data pipeline using [dlt](https://dlthub.com/) to ingest air quality measurements from the Macedonian Environmental Protection Program (MOEPP) API into [DuckLake](https://ducklake.select/) on Cloudflare R2 for analytics. Local DuckDB remains available as a fallback destination.

## Overview

This pipeline fetches air quality measurements (PM10, SO2, PM25, O3, NO2, CO) from monitoring stations (2.6M+ hourly rows, 2007→present) and stores them as Parquet on Cloudflare R2 with a DuckLake catalog. Rill dashboards read the public bucket with zero setup.

## Features

- Automated ingestion from MOEPP REST API
- Automatic date range pagination (handles API 1-month limit)
- Client-side validation of regions, stations, and parameters
- DuckLake destination (native `dlt.destinations.ducklake`) with merge/upsert deduplication
- Gap-tolerant incremental fetching (each run loads last-loaded-date → yesterday)
- Daily scheduled runs via GitHub Actions (single-writer concurrency group)
- Catalog-as-file lifecycle (download → load → upload-on-success; failed runs never publish)
- CLI interface for easy usage
- NULL value handling and type conversions

## Dashboards (Rill)

[Rill](https://docs.rilldata.com/) reads from DuckLake on Cloudflare R2 (public bucket, no credentials, no local files).

```bash
git clone https://github.com/debjan/moepp
cd rill-air-quality
rill start .
```

Dashboards always read the latest published catalog. Python pipeline is not needed for the Rill dashboard.

## Installation (Python pipeline)

### Prerequisites

- Python 3.10+

### Setup

```bash
# Clone the repository
git clone https://github.com/debjan/moepp
cd moepp
uv sync
```

## Usage

### Command Line

```bash
# Fetch data for all stations (default: incremental, through yesterday)
uv run python run.py --destination ducklake

# Fetch specific date range
uv run python run.py --destination ducklake --from-date 2024-01-01 --to-date 2024-01-31

# Fetch specific regions
uv run python run.py --destination ducklake --regions 1 2

# Fetch specific stations
uv run python run.py --destination ducklake --stations 31 48 44

# Fetch specific parameters
uv run python run.py --destination ducklake --parameters PM10 PM25 NO2

# Change aggregation (1=hourly, 8=8-hour, 24=daily)
uv run python run.py --destination ducklake --aggregation 24

# Local DuckDB fallback (uses --output-db; ignored by ducklake)
uv run python run.py --destination duckdb --output-db /path/to/data.duckdb
```

### Python API

```python
from src.pipeline import run_ducklake_pipeline, run_pipeline

# DuckLake on R2 (incremental through yesterday)
run_ducklake_pipeline(to_date="2024-01-31")

# Run with custom date range
run_ducklake_pipeline(
    from_date="2024-01-01",
    to_date="2024-01-31",
)

# Run with custom parameters
run_ducklake_pipeline(
    from_date="2024-01-01",
    to_date="2024-01-31",
    region_ids=["1", "2"],
    station_ids=["31", "48"],
    parameters=["PM10", "PM25"],
    aggregation="1",
)

# Local DuckDB fallback
run_pipeline(
    from_date="2024-01-01",
    to_date="2024-01-31",
    output_db="moepp.duckdb",
)
```

## Project Structure

```text
moepp/
├── src/                    # Source code
│   ├── __init__.py
│   ├── source.py           # REST API source
│   ├── pipeline.py         # dlt pipelines (DuckDB + DuckLake)
│   ├── validation.py       # Input validation
│   ├── pagination.py       # Date range chunking
│   ├── main.py             # CLI entry point
│   └── config/             # Configuration files
│       ├── __init__.py
│       ├── mappings.py     # Region/station mappings
│       ├── logger.py       # Logger
│       ├── constants.py    # API constants
│       └── settings.py     # Settings (incl. R2/DuckLake helpers)
├── rill-air-quality/       # Rill dashboards (models, dashboards)
├── .github/workflows/      # Daily DuckLake ingest (moepp-ducklake.yml)
├── pyproject.toml          # Package configuration
└── README.md               # This file
```

## Storage Backend

### DuckLake on Cloudflare R2 (primary)

Parquet data files plus a DuckDB-file catalog (`ducklake/metadata.ducklake`), both in the public-read `moepp-ducklake` bucket. The GitHub Actions workflow (`moepp-ducklake.yml`, daily 02:00 UTC, `concurrency: moepp-pipeline`) is the sole writer: it downloads the catalog, loads `last-loaded-date → yesterday`, and uploads the catalog back only on success. Missed days self-heal on the next run; merge on `(date, station_name_mk, station_name_en)` dedupes overlaps.

- **Table**: `moepp_ducklake.main.measurements`
- **Primary keys**: `date`, `station_name_mk`, `station_name_en`
- **Writer secrets** (GitHub Actions only): `MOEPP_R2_KEY_ID`, `MOEPP_R2_SECRET`, `MOEPP_R2_ACCOUNT_ID`, `MOEPP_R2_BUCKET`

```bash
# DuckLake storage
uv run python run.py --destination ducklake
```

### DuckDB (fallback)

Local file-based storage with automatic merge/upsert deduplication.

- **Primary keys**: `date`, `station_name_mk`, `station_name_en`
- **Automatic incremental**: Tracks last record date
- **Configuration**: Set `MOEPP_OUTPUT_DB` environment variable or use `--output-db`

```bash
uv run python run.py --destination duckdb
```

## Environment Variables

| Variable                                                                          | Needed by                                   | Purpose                                          |
| --------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------ |
| `MOEPP_R2_KEY_ID` / `MOEPP_R2_SECRET` / `MOEPP_R2_ACCOUNT_ID` / `MOEPP_R2_BUCKET` | Writer (GitHub Actions secrets)             | R2 read/write for catalog + data                 |
| `MOEPP_R2_PUBLIC_BASE_URL`                                                        | Local catalog workflows (`sync_catalog.py`) | Public bucket URL, e.g. `https://pub-xxx.r2.dev` |
| `MOEPP_OUTPUT_DB`                                                                 | Local DuckDB runs                           | Output file path (default: `moepp.duckdb`)       |
| `MOEPP_LOG_LEVEL`                                                                 | All runs                                    | Logging level (default: `INFO`)                  |

## License

MIT License
