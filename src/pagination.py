"""Date range pagination utilities for MOEPP API."""

from collections.abc import Generator
from datetime import timedelta

from .config import DATE_FORMAT, MAX_DATE_RANGE_DAYS
from .validation import parse_datetime


def chunk_date_range(
    from_date: str,
    to_date: str,
    max_days: int = MAX_DATE_RANGE_DAYS,
) -> Generator[tuple[str, str], None, None]:
    """Split a date range into chunks of at most max_days.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        max_days: Maximum days per chunk (default: 31)

    Yields:
        Tuples of (chunk_from, chunk_to) as date strings (YYYY-MM-DD)
    """
    start = parse_datetime(from_date)
    end = parse_datetime(to_date)
    chunk_delta = timedelta(days=max_days)

    while start <= end:
        chunk_end = min(start + chunk_delta, end)
        yield (
            start.strftime(DATE_FORMAT),
            chunk_end.strftime(DATE_FORMAT),
        )
        start = chunk_end + timedelta(days=1)
