"""REST API source for MOEPP air quality data."""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import dlt
from dlt.sources.helpers import requests

from .config import (
    ALLOWED_PARAMETERS,
    BASE_URL,
    DEFAULT_AGGREGATION,
    DEFAULT_PRIMARY_KEY,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    get_logger,
)
from .pagination import chunk_date_range

logger = get_logger(__name__)


def parse_local_timestamp(date_str: str) -> datetime:
    """Parse a local datetime string into a naive datetime.

    Args:
        date_str: Date/time string in YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS format

    Returns:
        Naive datetime (wall-clock time as given by the API)
    """
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f'Unable to parse datetime: {date_str}')


API_FIELD_TO_COLUMN = {
    'date': 'date',
    'stationName': 'station_name_mk',
    'stationNameEN': 'station_name_en',
    'cO_Value': 'co',
    'nO2_Value': 'no2',
    'o3_Value': 'o3',
    'pM25_Value': 'pm25',
    'pM10_Value': 'pm10',
    'sO2_Value': 'so2',
}

COLUMNS = {
    'date': {'data_type': 'timestamp', 'timezone': False},
    'station_name_mk': {'data_type': 'text'},
    'station_name_en': {'data_type': 'text'},
    'co': {'data_type': 'double'},
    'no2': {'data_type': 'double'},
    'o3': {'data_type': 'double'},
    'pm25': {'data_type': 'double'},
    'pm10': {'data_type': 'double'},
    'so2': {'data_type': 'double'},
}

_MEASUREMENT_COLUMNS = frozenset(col.lower() for col in ALLOWED_PARAMETERS)



@dlt.resource(
    name='measurements',
    write_disposition='merge',
    primary_key=DEFAULT_PRIMARY_KEY,
    columns=COLUMNS,
)
def measurements_resource(
    to_date: str,
    from_date: str | None = None,
    region_ids: list[str] | None = None,
    station_ids: list[str] | None = None,
    parameters: list[str] | None = None,
    aggregation: str = DEFAULT_AGGREGATION,
    request_delay: float = DEFAULT_REQUEST_DELAY,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    incremental: dlt.sources.incremental,
) -> Iterator[dict[str, Any]]:
    """dlt resource for MOEPP air quality measurements.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        region_ids: Optional list of region IDs
        station_ids: Optional list of station IDs
        parameters: Optional list of parameters (PM10, SO2, etc.)
        aggregation: Aggregation level ('1', '8', '24')
        request_delay: Seconds to wait between API requests
        timeout: Request timeout in seconds
        incremental: dlt incremental cursor for stateful fetching

    Yields:
        Measurement records as dictionaries
    """
    yield from fetch_measurements(
        from_date=from_date,
        to_date=to_date,
        region_ids=region_ids,
        station_ids=station_ids,
        parameters=parameters,
        aggregation=aggregation,
        request_delay=request_delay,
        timeout=timeout,
        incremental=incremental,
    )


def build_payload(
    from_date: str,
    to_date: str,
    region_ids: list[str] | None = None,
    station_ids: list[str] | None = None,
    parameters: list[str] | None = None,
    aggregation: str = DEFAULT_AGGREGATION,
) -> dict[str, Any]:
    """Build the POST request payload for the MOEPP API.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        region_ids: Optional list of region IDs
        station_ids: Optional list of station IDs
        parameters: Optional list of parameters
        aggregation: Aggregation level

    Returns:
        Dictionary representing the JSON payload
    """
    # API requires all these fields to be present, even if empty
    return {
        'FromDate': from_date,
        'ToDate': to_date,
        'Aggregation': aggregation,
        'RegionIds': region_ids or [],
        'StationIds': station_ids or [],
        'Parameters': parameters or [],
    }


def request_api(
    url: str,
    payload: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
    chunk_info: str = '',
    max_retries: int = MAX_RETRIES,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
) -> dict[str, Any]:
    """Make a POST request to the API with exponential backoff retry.

    Args:
        url: API endpoint URL
        payload: JSON payload for the request
        timeout: Request timeout in seconds
        chunk_info: Optional description of chunk being fetched (for logging)
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff between retries

    Returns:
        Parsed JSON response as dictionary
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
            if status_code is not None and 400 <= status_code < 500 and status_code != 429:
                logger.error(f'API request failed {chunk_info} with status {status_code}, not retrying')
                logger.exception('API request error')
                raise
            if attempt >= max_retries:
                logger.error(f'API request failed {chunk_info} after {max_retries + 1} attempts')
                logger.exception('API request error')
                raise
            delay = backoff_factor ** attempt
            if status_code == 429:
                retry_after = (getattr(getattr(exc, 'response', None), 'headers', None) or {}).get('Retry-After')
                try:
                    if retry_after is not None:
                        delay = max(delay, float(retry_after))
                except (TypeError, ValueError):
                    pass
            logger.warning(
                f'API request failed {chunk_info} (attempt {attempt + 1}/{max_retries + 1}). '
                f'Retrying in {delay:.1f}s...'
            )
            time.sleep(delay)

    raise RuntimeError(f'API request failed {chunk_info}: retry loop exhausted')


def fetch_measurements(
    to_date: str,
    from_date: str | None = None,
    region_ids: list[str] | None = None,
    station_ids: list[str] | None = None,
    parameters: list[str] | None = None,
    aggregation: str = DEFAULT_AGGREGATION,
    request_delay: float = DEFAULT_REQUEST_DELAY,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    incremental: dlt.sources.incremental,
) -> Iterator[dict[str, Any]]:
    """Fetch measurements from MOEPP API with automatic date chunking.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        region_ids: Optional list of region IDs
        station_ids: Optional list of station IDs
        parameters: Optional list of parameters
        aggregation: Aggregation level
        request_delay: Seconds to wait between requests
        timeout: Request timeout in seconds
        incremental: dlt incremental cursor for stateful fetching

    Yields:
        Normalized measurement records
    """
    if from_date is not None:
        actual_from_date = from_date
        logger.info(f'Using explicit from_date: {actual_from_date}')
    else:
        actual_from_date = incremental.last_value.strftime('%Y-%m-%d')  # ty:ignore[unresolved-attribute]
        logger.info(f'Incremental last_value found: {incremental.last_value}. Fetching from {actual_from_date}')

    # Split date range into chunks
    date_chunks = list(chunk_date_range(actual_from_date, to_date))
    logger.info(f'Fetching data for {len(date_chunks)} date chunk(s)')

    for i, (chunk_from, chunk_to) in enumerate(date_chunks):
        logger.info(f'Fetching chunk {i + 1}/{len(date_chunks)}: {chunk_from} to {chunk_to}')

        # Build payload for this chunk
        payload = build_payload(
            from_date=chunk_from,
            to_date=chunk_to,
            region_ids=region_ids,
            station_ids=station_ids,
            parameters=parameters,
            aggregation=aggregation,
        )

        chunk_info = f'for {chunk_from} to {chunk_to}'
        data = request_api(BASE_URL, payload, timeout, chunk_info)

        if not isinstance(data, list):
            logger.warning(f'Unexpected response format for {chunk_from} to {chunk_to}')
            continue

        logger.info(f'Received {len(data)} records for chunk {i + 1}')

        # Yield normalized records
        for record in data:
            if not isinstance(record, dict):
                logger.warning(f'Skipping malformed record of type {type(record).__name__}: {record!r}')
                continue
            normalized = normalize_record(record)
            if normalized is not None:
                yield normalized

        # Rate limiting - wait before next request (except for last chunk)
        if i < len(date_chunks) - 1:
            time.sleep(request_delay)


def normalize_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize an API record to standardized format.

    Converts:
    - Column names to snake_case
    - NULL strings to None
    - Station names from IDs
    - Date strings to naive local datetime

    Args:
        record: Raw API record

    Returns:
        Normalized record, or None if the record should be skipped
    """
    if not isinstance(record, dict):
        logger.warning(f'Skipping malformed record of type {type(record).__name__}: {record!r}')
        return None

    normalized: dict[str, Any] = {}

    for api_name, value in record.items():
        if (norm_name := API_FIELD_TO_COLUMN.get(api_name)) is None:
            logger.warning(f"Unknown API field '{api_name}', skipping")
            continue

        if value == 'NULL':
            normalized[norm_name] = None
        elif norm_name == 'date' and isinstance(value, str):
            try:
                normalized[norm_name] = parse_local_timestamp(value)
            except ValueError:
                logger.warning(f'Skipping record with unparseable date: {value!r}')
                return None
        else:
            normalized[norm_name] = value

    if not isinstance(normalized.get('date'), datetime):
        logger.warning(f'Skipping record with missing date: {record!r}')
        return None

    if all(normalized.get(col) is None for col in _MEASUREMENT_COLUMNS):
        return None

    return normalized
