"""Settings and configuration for MOEPP air quality pipeline."""

import os

BASE_URL = 'https://air.moepp.gov.mk/api/data/measurements-filtered'

DEFAULT_OUTPUT_DB = 'moepp.duckdb'
DEFAULT_TABLE_NAME = 'measurements'
DEFAULT_PRIMARY_KEY = ('date', 'station_name_mk', 'station_name_en')

DEFAULT_REQUEST_DELAY = 1.0
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0

DEFAULT_LOG_LEVEL = 'INFO'

DUCKLAKE_CATALOG_NAME = 'moepp_ducklake'
DUCKLAKE_CATALOG_R2_KEY = 'ducklake/metadata.ducklake'
DUCKLAKE_DATA_R2_PREFIX = 'ducklake/data/'
DEFAULT_DUCKLAKE_METADATA_PATH = 'metadata.ducklake'


def get_output_db() -> str:
    """Get output database path from environment or default."""
    return os.environ.get('MOEPP_OUTPUT_DB', DEFAULT_OUTPUT_DB)


def get_r2_public_base_url() -> str | None:
    """Get public base URL of the R2 bucket (e.g. https://pub-xxx.r2.dev)."""
    return os.environ.get('MOEPP_R2_PUBLIC_BASE_URL')


def require_r2_writer_config() -> tuple[str, str, str, str]:
    """Get R2 writer credentials from environment.

    Returns:
        Tuple of (key_id, secret, account_id, bucket).

    Raises:
        RuntimeError: If any required variable is missing.
    """
    missing = [
        name
        for name in (
            'MOEPP_R2_KEY_ID',
            'MOEPP_R2_SECRET',
            'MOEPP_R2_ACCOUNT_ID',
            'MOEPP_R2_BUCKET',
        )
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(
            'Missing R2 writer configuration: '
            + ', '.join(missing)
            + '. Set them as GitHub Actions secrets.'
        )
    return (
        os.environ['MOEPP_R2_KEY_ID'],
        os.environ['MOEPP_R2_SECRET'],
        os.environ['MOEPP_R2_ACCOUNT_ID'],
        os.environ['MOEPP_R2_BUCKET'],
    )


def catalog_public_url(public_base_url: str) -> str:
    """Get the public HTTPS URL of the DuckLake catalog file on R2."""
    return public_base_url.rstrip('/') + '/' + DUCKLAKE_CATALOG_R2_KEY


def get_log_level() -> str:
    """Get log level from environment or default."""
    log_level = os.environ.get('MOEPP_LOG_LEVEL', DEFAULT_LOG_LEVEL)
    return (
        log_level
        if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        else DEFAULT_LOG_LEVEL
    )
