-- Check the import and see how many records report a positive delay.
SELECT COUNT(*) AS imported_rows,
       COUNT(*) FILTER (WHERE delay_minutes > 0) AS positive_delay_rows,
       MIN(service_date) AS first_date,
       MAX(service_date) AS last_date,
       SUM(delay_minutes) AS total_delay_minutes
FROM subway_delays;

-- Count positive-delay reports by the station labels recorded in the workbook.
SELECT station,
       COUNT(*) AS reported_delays
FROM subway_delays
WHERE delay_minutes > 0
  AND station LIKE '% STATION'
GROUP BY station
ORDER BY reported_delays DESC, station
LIMIT 10;

-- Add up the reported service delay minutes for each TTC cause code.
SELECT delays.delay_code,
       COALESCE(codes.description, 'Unmapped TTC code') AS cause,
       SUM(delays.delay_minutes) AS total_delay_minutes,
       COUNT(*) AS reported_delays
FROM subway_delays AS delays
LEFT JOIN delay_codes AS codes ON codes.delay_code = delays.delay_code
WHERE delays.delay_minutes > 0
GROUP BY delays.delay_code, codes.description
ORDER BY total_delay_minutes DESC, delays.delay_code
LIMIT 10;
