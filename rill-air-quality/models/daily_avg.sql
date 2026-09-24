-- @materialize: true
-- Daily averages by station
-- Reduces 3.6M hourly records to ~150k daily records for faster dashboard performance
-- {{ if dev }} WHERE date >= '2007-01-01' {{ end }}

SELECT
  date::DATE as day,
  station_name_en,
  -- Region mapping based on station geography
  CASE
    WHEN station_name_en IN ('CENTAR', 'GAZI BABA', 'LISICE', 'RECTORATE', 'MILADINOVCI', 'KARPOSH', 'MOBILE GP') THEN 'Region 1 - Skopje'
    WHEN station_name_en IN ('BITOLA 1', 'BITOLA 2', 'GOSTIVAR', 'KICHEVO', 'LAZAROPOLE', 'OHRID', 'PRILEP', 'TETOVO') THEN 'Region 2 - West/Southwest'
    WHEN station_name_en IN ('BEROVO', 'VELES 2', 'KAVADARCI', 'KOCHANI', 'KUMANOVO', 'GEVGELIJA', 'STRUMICA') THEN 'Region 3 - East/Southeast'
    ELSE 'Unknown'
  END as region,
  -- PM10 statistics
  AVG(pm10) as avg_pm10,
  MIN(pm10) as min_pm10,
  MAX(pm10) as max_pm10,
  -- PM2.5 statistics
  AVG(pm25) as avg_pm25,
  MIN(pm25) as min_pm25,
  MAX(pm25) as max_pm25,
  -- NO2 statistics
  AVG(no2) as avg_no2,
  MIN(no2) as min_no2,
  MAX(no2) as max_no2,
  -- SO2 statistics
  AVG(so2) as avg_so2,
  MIN(so2) as min_so2,
  MAX(so2) as max_so2,
  -- CO statistics
  AVG(co) as avg_co,
  MIN(co) as min_co,
  MAX(co) as max_co,
  -- O3 statistics
  AVG(o3) as avg_o3,
  MIN(o3) as min_o3,
  MAX(o3) as max_o3,
  -- Data completeness metrics
  COUNT(*) as record_count,
  COUNT(pm10) as pm10_count,
  COUNT(pm25) as pm25_count,
  COUNT(no2) as no2_count,
  COUNT(so2) as so2_count,
  COUNT(co) as co_count,
  COUNT(o3) as o3_count,
  -- Flag incomplete days (<20 hours of data)
  CASE WHEN COUNT(*) < 20 THEN true ELSE false END as incomplete_data
FROM {{ ref "air_quality" }}
GROUP BY date::DATE, station_name_en,
  CASE
    WHEN station_name_en IN ('CENTAR', 'GAZI BABA', 'LISICE', 'RECTORATE', 'MILADINOVCI', 'KARPOSH', 'MOBILE GP') THEN 'Region 1 - Skopje'
    WHEN station_name_en IN ('BITOLA 1', 'BITOLA 2', 'GOSTIVAR', 'KICHEVO', 'LAZAROPOLE', 'OHRID', 'PRILEP', 'TETOVO') THEN 'Region 2 - West/Southwest'
    WHEN station_name_en IN ('BEROVO', 'VELES 2', 'KAVADARCI', 'KOCHANI', 'KUMANOVO', 'GEVGELIJA', 'STRUMICA') THEN 'Region 3 - East/Southeast'
    ELSE 'Unknown'
  END
ORDER BY day DESC, station_name_en
