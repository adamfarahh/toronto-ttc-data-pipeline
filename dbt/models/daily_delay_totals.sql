SELECT
    service_date,
    COUNT(*) AS logged_reports,
    COUNT(*) FILTER (WHERE is_reported_delay) AS reported_delays,
    SUM(delay_minutes) AS total_delay_minutes
FROM {{ ref('subway_delay_reports') }}
GROUP BY service_date
