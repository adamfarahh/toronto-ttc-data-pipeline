{% macro recent_feed_available(delays, codes) %}
    {% if not execute %}
        {{ return(false) }}
    {% endif %}

    {% set delays_exist = load_relation(delays) is not none %}
    {% set codes_exist = load_relation(codes) is not none %}
    {% if delays_exist != codes_exist %}
        {{ exceptions.raise_compiler_error('The recent TTC feed is incomplete. Run refresh_recent.py to restore both tables.') }}
    {% endif %}

    {{ return(delays_exist) }}
{% endmacro %}
