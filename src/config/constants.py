"""Constants for MOEPP API configuration."""

# Available measurement parameters
ALLOWED_PARAMETERS = ['PM10', 'SO2', 'PM25', 'O3', 'NO2', 'CO']

# Available aggregation values
# '1' = hourly, '8' = 8-hour, '24' = daily
ALLOWED_AGGREGATIONS = ['1', '8', '24']

# Minimum date for API (ISO format)
MIN_DATE = '2007-01-01'

# Default values
DEFAULT_AGGREGATION = '1'  # hourly


# API limits
MAX_DATE_RANGE_DAYS = 30  # Maximum 1 month

# Date and time format for API and storage
DATE_FORMAT = '%Y-%m-%d'
