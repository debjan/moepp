-- @materialize: true
-- Monthly summary statistics by station
-- Supports year-over-year comparisons and seasonal analysis
-- {{ if dev }} WHERE date >= '2007-01-01' {{ end }}

SELECT
  DATE_TRUNC('month', date) as month,
  EXTRACT(YEAR FROM date) as year,
  EXTRACT(MONTH FROM date) as month_num,
  station_name_en,
  -- Monthly averages
  AVG(pm10) as avg_pm10,
  AVG(pm25) as avg_pm25,
  AVG(no2) as avg_no2,
  AVG(so2) as avg_so2,
  AVG(co) as avg_co,
  AVG(o3) as avg_o3,
  -- Standard deviations for variability analysis
  STDDEV(pm10) as stddev_pm10,
  STDDEV(pm25) as stddev_pm25,
  STDDEV(no2) as stddev_no2,
  STDDEV(so2) as stddev_so2,
  STDDEV(co) as stddev_co,
  STDDEV(o3) as stddev_o3,
  -- Maximum values
  MAX(pm10) as max_pm10,
  MAX(pm25) as max_pm25,
  MAX(no2) as max_no2,
  MAX(so2) as max_so2,
  MAX(co) as max_co,
  MAX(o3) as max_o3,
  -- Minimum values
  MIN(pm10) as min_pm10,
  MIN(pm25) as min_pm25,
  MIN(no2) as min_no2,
  MIN(so2) as min_so2,
  MIN(co) as min_co,
  MIN(o3) as min_o3,
  -- Data completeness
  COUNT(*) as total_records,
  COUNT(pm10) as pm10_records,
  -- Percentage of complete data
  ROUND(COUNT(pm10) * 100.0 / COUNT(*), 2) as pm10_completeness_pct
FROM {{ ref "air_quality" }}
GROUP BY
  DATE_TRUNC('month', date),
  EXTRACT(YEAR FROM date),
  EXTRACT(MONTH FROM date),
  station_name_en
ORDER BY month DESC, station_name_en
