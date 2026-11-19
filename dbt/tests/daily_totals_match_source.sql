{% set recent_delays = source('ttc_raw', 'subway_delays_recent') %}
{% set recent_codes = source('ttc_raw', 'delay_codes_recent') %}

-- A dbt data test passes when its query returns zero rows.
WITH source_delays AS (
    SELECT delay_minutes
    FROM {{ source('ttc_raw', 'subway_delays') }}
    {% if recent_feed_available(recent_delays, recent_codes) %}
    UNION ALL
    SELECT delay_minutes
    FROM {{ recent_delays }}
    {% endif %}
),
source_totals AS (
    SELECT
        COUNT(*) AS logged_reports,
        COUNT(*) FILTER (WHERE delay_minutes > 0) AS reported_delays,
        SUM(delay_minutes) AS total_delay_minutes
    FROM source_delays
),
daily_totals AS (
    SELECT
        SUM(logged_reports) AS logged_reports,
        SUM(reported_delays) AS reported_delays,
        SUM(total_delay_minutes) AS total_delay_minutes
    FROM {{ ref('daily_delay_totals') }}
)
SELECT source_totals.*
FROM source_totals
CROSS JOIN daily_totals
WHERE source_totals.logged_reports = 0
   OR source_totals.logged_reports IS DISTINCT FROM daily_totals.logged_reports
   OR source_totals.reported_delays IS DISTINCT FROM daily_totals.reported_delays
   OR source_totals.total_delay_minutes IS DISTINCT FROM daily_totals.total_delay_minutes
