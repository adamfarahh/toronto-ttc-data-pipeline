SELECT
    station,
    COUNT(*) AS reported_delays
FROM {{ ref('subway_delay_reports') }}
WHERE is_reported_delay
  AND station LIKE '% STATION'
GROUP BY station
