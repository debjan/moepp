-- @materialize: true
-- Air Quality Index (AQI) categorization based on WHO/EU standards
-- Calculates AQI categories for PM10 and PM2.5, determines dominant pollutant
-- {{ if dev }} WHERE date >= '2007-01-01' {{ end }}

WITH categorized AS (
  SELECT
    date,
    station_name_en,
    pm10,
    pm25,
    no2,
    so2,
    co,
    o3,
    -- PM10 categorization (WHO/EU standards)
    -- Good: ≤ 20 μg/m³
    -- Fair: 21-50 μg/m³
    -- Moderate: 51-100 μg/m³
    -- Poor: 101-200 μg/m³
    -- Very Poor: > 200 μg/m³
    CASE
      WHEN pm10 IS NULL THEN NULL
      WHEN pm10 <= 20 THEN 'Good'
      WHEN pm10 <= 50 THEN 'Fair'
      WHEN pm10 <= 100 THEN 'Moderate'
      WHEN pm10 <= 200 THEN 'Poor'
      ELSE 'Very Poor'
    END as pm10_category,
    -- PM2.5 categorization (WHO/EU standards)
    -- Good: ≤ 10 μg/m³
    -- Fair: 11-25 μg/m³
    -- Moderate: 26-50 μg/m³
    -- Poor: 51-100 μg/m³
    -- Very Poor: > 100 μg/m³
    CASE
      WHEN pm25 IS NULL THEN NULL
      WHEN pm25 <= 10 THEN 'Good'
      WHEN pm25 <= 25 THEN 'Fair'
      WHEN pm25 <= 50 THEN 'Moderate'
      WHEN pm25 <= 100 THEN 'Poor'
      ELSE 'Very Poor'
    END as pm25_category,
    -- Category priority for determining overall AQI (lower = better)
    CASE
      WHEN pm10 IS NULL THEN NULL
      WHEN pm10 <= 20 THEN 1
      WHEN pm10 <= 50 THEN 2
      WHEN pm10 <= 100 THEN 3
      WHEN pm10 <= 200 THEN 4
      ELSE 5
    END as pm10_priority,
    CASE
      WHEN pm25 IS NULL THEN NULL
      WHEN pm25 <= 10 THEN 1
      WHEN pm25 <= 25 THEN 2
      WHEN pm25 <= 50 THEN 3
      WHEN pm25 <= 100 THEN 4
      ELSE 5
    END as pm25_priority
  FROM {{ ref "air_quality" }}
)
SELECT
  date,
  station_name_en,
  pm10,
  pm25,
  no2,
  so2,
  co,
  o3,
  pm10_category,
  pm25_category,
  -- Overall AQI category (worst of available pollutants - dominant pollutant approach)
  CASE
    WHEN pm10_priority IS NULL AND pm25_priority IS NULL THEN NULL
    WHEN COALESCE(pm10_priority, 0) >= COALESCE(pm25_priority, 0) AND pm10_priority IS NOT NULL THEN pm10_category
    WHEN COALESCE(pm25_priority, 0) > COALESCE(pm10_priority, 0) AND pm25_priority IS NOT NULL THEN pm25_category
    WHEN pm10_priority IS NOT NULL THEN pm10_category
    ELSE pm25_category
  END as overall_aqi_category,
  -- Dominant pollutant (the one determining the overall AQI)
  CASE
    WHEN pm10_priority IS NULL AND pm25_priority IS NULL THEN NULL
    WHEN COALESCE(pm10_priority, 0) >= COALESCE(pm25_priority, 0) AND pm10_priority IS NOT NULL THEN 'PM10'
    WHEN COALESCE(pm25_priority, 0) > COALESCE(pm10_priority, 0) AND pm25_priority IS NOT NULL THEN 'PM2.5'
    WHEN pm10_priority IS NOT NULL THEN 'PM10'
    ELSE 'PM2.5'
  END as dominant_pollutant,
  -- AQI priority value (numeric for sorting/filtering)
  GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) as aqi_priority,
  -- Health advisory based on overall category
  CASE
    WHEN pm10_priority IS NULL AND pm25_priority IS NULL THEN 'No data available'
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 1 THEN 'Air quality is satisfactory'
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 2 THEN 'Acceptable air quality'
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 3 THEN 'Sensitive groups should limit outdoor activity'
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 4 THEN 'Health effects possible for everyone'
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 5 THEN 'Avoid outdoor activities'
    ELSE 'Unknown'
  END as health_advisory,
  -- Color coding for dashboards (aligned with gruvbox theme)
  -- Using theme colors for consistency: Good (green) -> Poor (red) gradient
  CASE
    WHEN pm10_priority IS NULL AND pm25_priority IS NULL THEN '#6b7280'  -- gray-500 (no data)
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 1 THEN '#10b981'  -- emerald-500 (Good)
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 2 THEN '#22c55e'  -- green-500 (Fair)
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 3 THEN '#eab308'  -- yellow-500 (Moderate)
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 4 THEN '#f97316'  -- orange-500 (Poor)
    WHEN GREATEST(COALESCE(pm10_priority, 0), COALESCE(pm25_priority, 0)) = 5 THEN '#dc2626'  -- red-600 (Very Poor)
    ELSE '#6b7280'  -- gray-500 (fallback)
  END as aqi_color
FROM categorized
ORDER BY date DESC, station_name_en
