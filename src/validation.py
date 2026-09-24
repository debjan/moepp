"""Validation utilities for MOEPP air quality pipeline."""

from datetime import datetime

from .config import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_PARAMETERS,
    DATE_FORMAT,
    MIN_DATE,
    REGION_STATIONS,
)


class ValidationError(Exception):
    """Raised when input validation fails."""


def validation_error(field: str, message: str) -> ValidationError:
    """Factory for creating consistent validation error messages.

    Args:
        field: Field name that failed validation
        message: Specific error message

    Returns:
        ValidationError with formatted message
    """
    return ValidationError(f'[{field}] {message}')


def parse_datetime(date_str: str) -> datetime:
    """Parse date string to datetime object."""

    return datetime.strptime(date_str, DATE_FORMAT)


def validate_region_station_combination(
    region_ids: list[str] | None,
    station_ids: list[str] | None
) -> None:
    """Validate that station IDs are compatible with selected region IDs.

    Args:
        region_ids: List of region IDs (e.g., ['1', '2'])
        station_ids: List of station IDs (e.g., ['31', '48'])

    Raises:
        ValidationError: If any station is not in the selected regions
    """
    if not region_ids or not station_ids:
        return

    valid_stations = set()
    for region_id in region_ids:
        if region_id not in REGION_STATIONS:
            raise validation_error('region_id', f'Invalid region ID: {region_id}')
        valid_stations.update(REGION_STATIONS[region_id])

    for station_id in station_ids:
        if station_id not in valid_stations:
            station_region = next(
                (region for region, stations in REGION_STATIONS.items() if station_id in stations),
                None,
            )
            if station_region:
                raise validation_error(
                    'station_id',
                    f'Station {station_id} is in region {station_region}, '
                    f'but region {station_region} is not in selected regions {region_ids}'
                )
            else:
                raise validation_error('station_id', f'Invalid station ID: {station_id}')


def validate_parameters(parameters: list[str] | None) -> None:
    """Validate that all parameters are in the allowed list.

    Args:
        parameters: List of parameter names (e.g., ['PM10', 'NO2'])

    Raises:
        ValidationError: If any parameter is not allowed
    """
    if not parameters:
        return

    for param in parameters:
        if param not in ALLOWED_PARAMETERS:
            raise validation_error(
                'parameter',
                f'Invalid parameter: {param}. '
                f'Allowed parameters: {", ".join(ALLOWED_PARAMETERS)}'
            )


def validate_aggregation(aggregation: str) -> None:
    """Validate that aggregation value is allowed.

    Args:
        aggregation: Aggregation value ('1', '8', or '24')

    Raises:
        ValidationError: If aggregation value is not allowed
    """
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise validation_error(
            'aggregation',
            f'Invalid aggregation: {aggregation}. '
            f"Allowed values: {', '.join(ALLOWED_AGGREGATIONS)}"
        )


def _parse_date_or_raise(field: str, value: str) -> datetime:
    try:
        return parse_datetime(value)
    except ValueError as e:
        raise validation_error(field, f'Invalid format. Use YYYY-MM-DD. Error: {e}') from e


def validate_date_range(from_date: str, to_date: str) -> None:
    """Validate date range format and constraints.

    Args:
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)

    Raises:
        ValidationError: If dates are invalid or out of range
    """
    # Parse dates to datetime objects for validation
    start_dt = _parse_date_or_raise('from_date', from_date)
    end_dt = _parse_date_or_raise('to_date', to_date)

    min_date = datetime.strptime(MIN_DATE, DATE_FORMAT)
    if start_dt < min_date:
        raise validation_error('from_date', f'Date {from_date} is before minimum allowed date {MIN_DATE}')

    max_date = datetime.now()
    if start_dt > max_date:
        raise validation_error(
            'from_date',
            f'Date {from_date} is in the future. Maximum allowed is today ({max_date.strftime(DATE_FORMAT)}).'
        )
    if end_dt > max_date:
        raise validation_error(
            'to_date',
            f'Date {to_date} is in the future. Maximum allowed is today ({max_date.strftime(DATE_FORMAT)}).'
        )

    if start_dt > end_dt:
        raise validation_error('from_date', f'Date {from_date} is after to date {to_date}')


def validate_all(
    from_date: str,
    to_date: str,
    region_ids: list[str] | None = None,
    station_ids: list[str] | None = None,
    parameters: list[str] | None = None,
    aggregation: str = '1',
) -> None:
    """Run all validations.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        region_ids: Optional list of region IDs
        station_ids: Optional list of station IDs
        parameters: Optional list of parameters
        aggregation: Aggregation value

    Raises:
        ValidationError: If any validation fails
    """
    validate_date_range(from_date, to_date)
    validate_region_station_combination(region_ids, station_ids)
    validate_parameters(parameters)
    validate_aggregation(aggregation)
