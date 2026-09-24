"""dlt pipeline configuration for MOEPP air quality data."""

from datetime import datetime, timedelta
from pathlib import Path

import boto3
import dlt
from botocore.exceptions import ClientError
from dlt.common.configuration.specs import AwsCredentials
from dlt.common.storages.configuration import FilesystemConfigurationWithLocalFiles
from dlt.destinations.impl.ducklake.configuration import DuckLakeCredentials

from .config import (
    DATE_FORMAT,
    DEFAULT_DUCKLAKE_METADATA_PATH,
    DEFAULT_PRIMARY_KEY,
    DEFAULT_TABLE_NAME,
    DUCKLAKE_CATALOG_NAME,
    DUCKLAKE_CATALOG_R2_KEY,
    DUCKLAKE_DATA_R2_PREFIX,
    MIN_DATE,
    get_logger,
    get_output_db,
    require_r2_writer_config,
)
from .source import measurements_resource
from .validation import validate_all

logger = get_logger(__name__)


def _validate_inputs(
    from_date: str | None,
    to_date: str,
    region_ids: list[str] | None,
    station_ids: list[str] | None,
    parameters: list[str] | None,
    aggregation: str,
) -> None:
    logger.info('Validating input parameters...')
    validate_all(
        from_date=from_date or MIN_DATE,
        to_date=to_date,
        region_ids=region_ids,
        station_ids=station_ids,
        parameters=parameters,
        aggregation=aggregation,
    )
    logger.info('Validation passed')


def _make_incremental(from_date: str | None) -> dlt.sources.incremental:
    if from_date is not None:
        initial_value = datetime.strptime(from_date, DATE_FORMAT) - timedelta(days=1)
    else:
        initial_value = datetime.strptime(MIN_DATE, DATE_FORMAT)
    return dlt.sources.incremental('date', initial_value=initial_value)


def _build_resource(
    to_date: str,
    from_date: str | None,
    region_ids: list[str] | None,
    station_ids: list[str] | None,
    parameters: list[str] | None,
    aggregation: str,
    incremental: dlt.sources.incremental,
):
    return measurements_resource(
        to_date=to_date,
        from_date=from_date,
        region_ids=region_ids,
        station_ids=station_ids,
        parameters=parameters,
        aggregation=aggregation,
        incremental=incremental,
    )


def _r2_client(key_id: str, secret: str, account_id: str):
    """Create an S3-compatible client for Cloudflare R2."""

    return boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name='auto',
    )


def download_catalog(client, bucket: str, dest: str) -> bool:
    """Download the DuckLake catalog file from R2.

    Args:
        client: S3-compatible client for R2.
        bucket: R2 bucket name.
        dest: Local path to write the catalog file to.

    Returns:
        True if an existing catalog was downloaded, False on first run
        (no catalog on R2 yet — a new DuckLake will be created on attach).
    """
    try:
        response = client.get_object(Bucket=bucket, Key=DUCKLAKE_CATALOG_R2_KEY)
        with open(dest, 'wb') as f:
            f.writelines(response['Body'].iter_chunks(chunk_size=8 * 1024 * 1024))
        logger.info(f'Downloaded catalog from s3://{bucket}/{DUCKLAKE_CATALOG_R2_KEY}')
        return True
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') in ('404', 'NoSuchKey', 'NoSuchBucket'):
            logger.info('No catalog on R2 yet — a new DuckLake will be created')
            return False
        raise


def upload_catalog(client, bucket: str, src: str) -> None:
    """Upload the DuckLake catalog file to R2 (call only on success)."""
    with open(src, 'rb') as f:
        client.put_object(Bucket=bucket, Key=DUCKLAKE_CATALOG_R2_KEY, Body=f.read())
    logger.info(f'Uploaded catalog to s3://{bucket}/{DUCKLAKE_CATALOG_R2_KEY}')


def _run_core(
    pipeline: dlt.Pipeline,
    destination: str,
    to_date: str,
    from_date: str | None = None,
    region_ids: list[str] | None = None,
    station_ids: list[str] | None = None,
    parameters: list[str] | None = None,
    aggregation: str = '1',
    table_name: str = DEFAULT_TABLE_NAME,
) -> None:
    """Build the resource and run a configured pipeline."""
    resource = _build_resource(
        to_date, from_date, region_ids, station_ids, parameters, aggregation,
        _make_incremental(from_date),
    )

    logger.info(f'Starting {destination} pipeline')
    logger.info(
        f'Using merge strategy with primary key for deduplication: {DEFAULT_PRIMARY_KEY}'
    )

    info = pipeline.run(
        resource,
        table_name=table_name,
        loader_file_format='parquet'
    )

    logger.info('Pipeline completed successfully')
    logger.info(f'Load info: {info}')


def run_pipeline(
    to_date: str,
    from_date: str | None = None,
    region_ids: list[str] | None = None,
    station_ids: list[str] | None = None,
    parameters: list[str] | None = None,
    aggregation: str = '1',
    output_db: str | None = None,
    table_name: str = DEFAULT_TABLE_NAME,
) -> None:
    """Run the MOEPP air quality data pipeline.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        region_ids: Optional list of region IDs
        station_ids: Optional list of station IDs
        parameters: Optional list of parameters (PM10, SO2, etc.)
        aggregation: Aggregation level ("1", "8", "24")
        output_db: Output DuckDB file path (optional, uses env or default)
        table_name: Name of the table to create (default: "measurements")
    """
    _validate_inputs(from_date, to_date, region_ids, station_ids, parameters, aggregation)

    db_path = output_db or get_output_db()
    logger.info(f'Output database: {db_path}')

    pipeline = dlt.pipeline(
        pipeline_name='moepp_duckdb',
        destination=dlt.destinations.duckdb(db_path),
        dataset_name='main',
    )

    _run_core(
        pipeline,
        'DuckDB',
        to_date,
        from_date,
        region_ids,
        station_ids,
        parameters,
        aggregation,
        table_name,
    )


def run_ducklake_pipeline(
    to_date: str,
    from_date: str | None = None,
    region_ids: list[str] | None = None,
    station_ids: list[str] | None = None,
    parameters: list[str] | None = None,
    aggregation: str = '1',
    metadata_path: str = DEFAULT_DUCKLAKE_METADATA_PATH,
    table_name: str = DEFAULT_TABLE_NAME,
) -> None:
    """Run the MOEPP pipeline writing through DuckLake to Cloudflare R2.

    Downloads the DuckLake catalog file from R2, attaches it locally,
    runs the dlt load, and uploads the catalog back only on success —
    a failed run leaves the published catalog untouched.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        region_ids: Optional list of region IDs
        station_ids: Optional list of station IDs
        parameters: Optional list of parameters (PM10, SO2, etc.)
        aggregation: Aggregation level ("1", "8", "24")
        metadata_path: Local path for the DuckLake catalog file
        table_name: Name of the table to create (default: "measurements")
    """
    _validate_inputs(from_date, to_date, region_ids, station_ids, parameters, aggregation)

    key_id, secret, account_id, bucket = require_r2_writer_config()
    client = _r2_client(key_id, secret, account_id)

    local_catalog = Path(metadata_path).resolve()
    download_catalog(client, bucket, str(local_catalog))

    # Native dlt ducklake destination: DuckDB-file catalog (downloaded from
    # R2 above) + Parquet data on R2 via S3-compatible storage config.
    storage = FilesystemConfigurationWithLocalFiles(
        bucket_url=f's3://{bucket}/{DUCKLAKE_DATA_R2_PREFIX}',
        credentials=AwsCredentials(
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            region_name='auto',
        ),
    )
    credentials = DuckLakeCredentials(
        DUCKLAKE_CATALOG_NAME,
        catalog=f'duckdb:///{local_catalog.as_posix()}',
        storage=storage,
    )
    logger.info(f'DuckLake catalog: {local_catalog}')

    pipeline = dlt.pipeline(
        pipeline_name='moepp_ducklake',
        destination=dlt.destinations.ducklake(credentials=credentials),
        dataset_name='main',
    )

    _run_core(
        pipeline,
        'DuckLake',
        to_date,
        from_date,
        region_ids,
        station_ids,
        parameters,
        aggregation,
        table_name,
    )

    upload_catalog(client, bucket, str(local_catalog))
