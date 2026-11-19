SELECT
    delay_code,
    MIN(cause) AS cause,
    SUM(delay_minutes) AS total_delay_minutes,
    COUNT(*) AS reported_delays
FROM {{ ref('subway_delay_reports') }}
WHERE is_reported_delay
-- Match descriptions that differ only in capitalization. Keep revised descriptions separate.
GROUP BY delay_code, UPPER(cause)
