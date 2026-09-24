"""CLI interface for MOEPP air quality pipeline."""

import argparse
import sys
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .config import (
    ALL_REGION_IDS,
    ALL_STATION_IDS,
    ALLOWED_AGGREGATIONS,
    ALLOWED_PARAMETERS,
    DATE_FORMAT,
    DEFAULT_AGGREGATION,
    configure_logging,
    get_log_level,
    get_logger,
    get_output_db,
)
from .pipeline import run_ducklake_pipeline, run_pipeline
from .validation import parse_datetime

load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')


def parse_date_arg(date_str: str) -> str:
    """Parse date string for argparse — raises ArgumentTypeError on invalid format."""
    try:
        dt = parse_datetime(date_str)
        return dt.strftime(DATE_FORMAT)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='MOEPP Air Quality Data Pipeline - Fetch air quality measurements from MOEPP API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    default_to_date = (datetime.now() - timedelta(days=1)).strftime(DATE_FORMAT)

    parser.add_argument(
        '--from-date',
        type=parse_date_arg,
        default=None,
        help='Start date (YYYY-MM-DD). Default: managed by dlt incremental cursor'
    )
    parser.add_argument(
        '--to-date',
        type=parse_date_arg,
        default=default_to_date,
        help=f'End date (YYYY-MM-DD). Default: {default_to_date}',
    )

    parser.add_argument(
        '--regions',
        nargs='+',
        choices=ALL_REGION_IDS,
        metavar='ID',
        help='Region IDs to fetch (1, 2, or 3). If not specified, all regions are fetched.',
    )
    parser.add_argument(
        '--stations',
        nargs='+',
        choices=ALL_STATION_IDS,
        metavar='ID',
        help='Station IDs to fetch (e.g., 31 48 44). If not specified, all stations are fetched.',
    )
    parser.add_argument(
        '--parameters',
        nargs='+',
        choices=ALLOWED_PARAMETERS,
        metavar='PARAM',
        help=f'Parameters to fetch. Allowed: {", ".join(ALLOWED_PARAMETERS)}',
    )
    parser.add_argument(
        '--aggregation',
        choices=ALLOWED_AGGREGATIONS,
        default=DEFAULT_AGGREGATION,
        help='Aggregation level: 1=hourly, 8=8-hour, 24=daily. Default: 1 (hourly)',
    )

    default_db = get_output_db()
    parser.add_argument(
        '--output-db',
        type=str,
        default=default_db,
        help=f'Output DuckDB file path (duckdb destination only). Default: {default_db}',
    )
    parser.add_argument(
        '--destination',
        choices=['duckdb', 'ducklake'],
        default='duckdb',
        help='Destination: duckdb writes to a local DuckDB file, '
        'ducklake writes through DuckLake to Cloudflare R2. Default: duckdb',
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=get_log_level(),
        help='Logging level. Default: INFO',
    )
    parser.add_argument('--version', action='version', version='%(prog)s 0.1.0')

    return parser


def main(args: Sequence[str] | None = None):
    """Main entry point for CLI.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    configure_logging(parsed_args.log_level)
    logger = get_logger(__name__)

    from_date = parsed_args.from_date
    logger.info(f'Date range: {from_date or "incremental"} to {parsed_args.to_date}')

    logger.info('Starting MOEPP Air Quality Pipeline')

    common = {
        'from_date': from_date,
        'to_date': parsed_args.to_date,
        'region_ids': parsed_args.regions,
        'station_ids': parsed_args.stations,
        'parameters': parsed_args.parameters,
        'aggregation': parsed_args.aggregation,
    }
    try:
        if parsed_args.destination == 'ducklake':
            raw_args = list(args) if args is not None else sys.argv[1:]
            if any(a == '--output-db' or a.startswith('--output-db=') for a in raw_args):
                logger.warning('--output-db is ignored for the ducklake destination')
            logger.info('Using DuckLake destination (Cloudflare R2)')
            run_ducklake_pipeline(**common)
        else:
            output_db = str(Path(parsed_args.output_db).resolve())
            logger.info(f'Output database path: {output_db}')
            run_pipeline(**common, output_db=output_db)
        logger.info('Pipeline completed successfully!')
        return 0
    except Exception:
        logger.exception('Pipeline failed')
        return 1


if __name__ == '__main__':
    sys.exit(main())
