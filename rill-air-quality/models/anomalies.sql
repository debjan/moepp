-- @materialize: true
-- Anomaly Detection Model
-- Identifies air quality measurements exceeding 2 standard deviations from the mean
-- Supports drill-down analysis for investigating unusual spikes or drops
-- {{ if dev }} WHERE date >= '2007-01-01' {{ end }}

WITH daily_stats AS (
  -- Calculate daily statistics for anomaly baseline
  SELECT
    date::DATE as day,
    station_name_en,
    AVG(pm10) as daily_avg_pm10,
    AVG(pm25) as daily_avg_pm25,
    AVG(no2) as daily_avg_no2,
    AVG(so2) as daily_avg_so2,
    AVG(co) as daily_avg_co,
    AVG(o3) as daily_avg_o3,
    STDDEV(pm10) as daily_stddev_pm10,
    STDDEV(pm25) as daily_stddev_pm25,
    COUNT(*) as hourly_records
  FROM {{ ref "air_quality" }}
  GROUP BY date::DATE, station_name_en
),
monthly_baseline AS (
  -- Calculate monthly baseline for comparison (30-day rolling window concept)
  SELECT
    station_name_en,
    EXTRACT(YEAR FROM day) as year,
    EXTRACT(MONTH FROM day) as month,
    AVG(daily_avg_pm10) as monthly_avg_pm10,
    STDDEV(daily_avg_pm10) as monthly_stddev_pm10,
    AVG(daily_avg_pm25) as monthly_avg_pm25,
    STDDEV(daily_avg_pm25) as monthly_stddev_pm25,
    AVG(daily_avg_no2) as monthly_avg_no2,
    STDDEV(daily_avg_no2) as monthly_stddev_no2,
    AVG(daily_avg_so2) as monthly_avg_so2,
    STDDEV(daily_avg_so2) as monthly_stddev_so2,
    AVG(daily_avg_co) as monthly_avg_co,
    STDDEV(daily_avg_co) as monthly_stddev_co,
    AVG(daily_avg_o3) as monthly_avg_o3,
    STDDEV(daily_avg_o3) as monthly_stddev_o3
  FROM daily_stats
  GROUP BY station_name_en, EXTRACT(YEAR FROM day), EXTRACT(MONTH FROM day)
),
anomalies_flagged AS (
  SELECT
    ds.day,
    ds.station_name_en,
    ds.hourly_records,
    -- PM10 anomaly detection (>2 std dev from monthly mean)
    ds.daily_avg_pm10,
    mb.monthly_avg_pm10,
    mb.monthly_stddev_pm10,
    CASE
      WHEN mb.monthly_stddev_pm10 > 0 
        AND ABS(ds.daily_avg_pm10 - mb.monthly_avg_pm10) > 2 * mb.monthly_stddev_pm10
      THEN true
      ELSE false
    END as pm10_anomaly,
    CASE
      WHEN mb.monthly_stddev_pm10 > 0
      THEN (ds.daily_avg_pm10 - mb.monthly_avg_pm10) / mb.monthly_stddev_pm10
      ELSE 0
    END as pm10_zscore,
    -- PM2.5 anomaly detection
    ds.daily_avg_pm25,
    mb.monthly_avg_pm25,
    mb.monthly_stddev_pm25,
    CASE
      WHEN mb.monthly_stddev_pm25 > 0 
        AND ABS(ds.daily_avg_pm25 - mb.monthly_avg_pm25) > 2 * mb.monthly_stddev_pm25
      THEN true
      ELSE false
    END as pm25_anomaly,
    CASE
      WHEN mb.monthly_stddev_pm25 > 0
      THEN (ds.daily_avg_pm25 - mb.monthly_avg_pm25) / mb.monthly_stddev_pm25
      ELSE 0
    END as pm25_zscore,
    -- NO2 anomaly detection
    ds.daily_avg_no2,
    mb.monthly_avg_no2,
    mb.monthly_stddev_no2,
    CASE
      WHEN mb.monthly_stddev_no2 > 0 
        AND ABS(ds.daily_avg_no2 - mb.monthly_avg_no2) > 2 * mb.monthly_stddev_no2
      THEN true
      ELSE false
    END as no2_anomaly,
    CASE
      WHEN mb.monthly_stddev_no2 > 0
      THEN (ds.daily_avg_no2 - mb.monthly_avg_no2) / mb.monthly_stddev_no2
      ELSE 0
    END as no2_zscore,
    -- SO2 anomaly detection
    ds.daily_avg_so2,
    mb.monthly_avg_so2,
    mb.monthly_stddev_so2,
    CASE
      WHEN mb.monthly_stddev_so2 > 0 
        AND ABS(ds.daily_avg_so2 - mb.monthly_avg_so2) > 2 * mb.monthly_stddev_so2
      THEN true
      ELSE false
    END as so2_anomaly,
    CASE
      WHEN mb.monthly_stddev_so2 > 0
      THEN (ds.daily_avg_so2 - mb.monthly_avg_so2) / mb.monthly_stddev_so2
      ELSE 0
    END as so2_zscore,
    -- CO anomaly detection
    ds.daily_avg_co,
    mb.monthly_avg_co,
    mb.monthly_stddev_co,
    CASE
      WHEN mb.monthly_stddev_co > 0 
        AND ABS(ds.daily_avg_co - mb.monthly_avg_co) > 2 * mb.monthly_stddev_co
      THEN true
      ELSE false
    END as co_anomaly,
    CASE
      WHEN mb.monthly_stddev_co > 0
      THEN (ds.daily_avg_co - mb.monthly_avg_co) / mb.monthly_stddev_co
      ELSE 0
    END as co_zscore,
    -- O3 anomaly detection
    ds.daily_avg_o3,
    mb.monthly_avg_o3,
    mb.monthly_stddev_o3,
    CASE
      WHEN mb.monthly_stddev_o3 > 0 
        AND ABS(ds.daily_avg_o3 - mb.monthly_avg_o3) > 2 * mb.monthly_stddev_o3
      THEN true
      ELSE false
    END as o3_anomaly,
    CASE
      WHEN mb.monthly_stddev_o3 > 0
      THEN (ds.daily_avg_o3 - mb.monthly_avg_o3) / mb.monthly_stddev_o3
      ELSE 0
    END as o3_zscore,
    mb.year,
    mb.month
  FROM daily_stats ds
  JOIN monthly_baseline mb
    ON ds.station_name_en = mb.station_name_en
    AND EXTRACT(YEAR FROM ds.day) = mb.year
    AND EXTRACT(MONTH FROM ds.day) = mb.month
)
SELECT
  day,
  station_name_en,
  year,
  month,
  hourly_records,
  -- PM10 anomaly details
  daily_avg_pm10,
  monthly_avg_pm10,
  monthly_stddev_pm10,
  pm10_anomaly,
  pm10_zscore,
  -- PM2.5 anomaly details
  daily_avg_pm25,
  monthly_avg_pm25,
  monthly_stddev_pm25,
  pm25_anomaly,
  pm25_zscore,
  -- NO2 anomaly details
  daily_avg_no2,
  monthly_avg_no2,
  monthly_stddev_no2,
  no2_anomaly,
  no2_zscore,
  -- SO2 anomaly details
  daily_avg_so2,
  monthly_avg_so2,
  monthly_stddev_so2,
  so2_anomaly,
  so2_zscore,
  -- CO anomaly details
  daily_avg_co,
  monthly_avg_co,
  monthly_stddev_co,
  co_anomaly,
  co_zscore,
  -- O3 anomaly details
  daily_avg_o3,
  monthly_avg_o3,
  monthly_stddev_o3,
  o3_anomaly,
  o3_zscore,
  -- Overall anomaly flag (any pollutant anomalous)
  CASE
    WHEN pm10_anomaly OR pm25_anomaly OR no2_anomaly OR so2_anomaly OR co_anomaly OR o3_anomaly
    THEN true
    ELSE false
  END as has_anomaly,
  -- Count of anomalous pollutants per day
  (CASE WHEN pm10_anomaly THEN 1 ELSE 0 END +
   CASE WHEN pm25_anomaly THEN 1 ELSE 0 END +
   CASE WHEN no2_anomaly THEN 1 ELSE 0 END +
   CASE WHEN so2_anomaly THEN 1 ELSE 0 END +
   CASE WHEN co_anomaly THEN 1 ELSE 0 END +
   CASE WHEN o3_anomaly THEN 1 ELSE 0 END) as anomaly_count,
  -- Primary anomalous pollutant (highest z-score)
  CASE
    WHEN ABS(pm10_zscore) >= ABS(pm25_zscore) 
     AND ABS(pm10_zscore) >= ABS(no2_zscore)
     AND ABS(pm10_zscore) >= ABS(so2_zscore)
     AND ABS(pm10_zscore) >= ABS(co_zscore)
     AND ABS(pm10_zscore) >= ABS(o3_zscore)
     AND pm10_anomaly
    THEN 'PM10'
    WHEN ABS(pm25_zscore) >= ABS(no2_zscore)
     AND ABS(pm25_zscore) >= ABS(so2_zscore)
     AND ABS(pm25_zscore) >= ABS(co_zscore)
     AND ABS(pm25_zscore) >= ABS(o3_zscore)
     AND pm25_anomaly
    THEN 'PM2.5'
    WHEN ABS(no2_zscore) >= ABS(so2_zscore)
     AND ABS(no2_zscore) >= ABS(co_zscore)
     AND ABS(no2_zscore) >= ABS(o3_zscore)
     AND no2_anomaly
    THEN 'NO2'
    WHEN ABS(so2_zscore) >= ABS(co_zscore)
     AND ABS(so2_zscore) >= ABS(o3_zscore)
     AND so2_anomaly
    THEN 'SO2'
    WHEN ABS(co_zscore) >= ABS(o3_zscore)
     AND co_anomaly
    THEN 'CO'
    WHEN o3_anomaly
    THEN 'O3'
    ELSE NULL
  END as primary_anomalous_pollutant,
  -- Max z-score across all pollutants
  GREATEST(ABS(pm10_zscore), ABS(pm25_zscore), ABS(no2_zscore), 
           ABS(so2_zscore), ABS(co_zscore), ABS(o3_zscore)) as max_zscore,
  -- Anomaly severity classification
  CASE
    WHEN GREATEST(ABS(pm10_zscore), ABS(pm25_zscore), ABS(no2_zscore), 
                  ABS(so2_zscore), ABS(co_zscore), ABS(o3_zscore)) > 3 THEN 'High'
    WHEN GREATEST(ABS(pm10_zscore), ABS(pm25_zscore), ABS(no2_zscore), 
                  ABS(so2_zscore), ABS(co_zscore), ABS(o3_zscore)) > 2 THEN 'Moderate'
    ELSE 'Normal'
  END as anomaly_severity
FROM anomalies_flagged
ORDER BY day DESC, station_name_en
