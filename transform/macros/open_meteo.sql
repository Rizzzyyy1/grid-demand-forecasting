{#- Staging for one Open-Meteo product. Every raw file is (ba, city, month); arrays are unnested
    in parallel (DuckDB zips same-length unnests). Columns are declared so that all-null arrays in
    early files (only temperature was archived before 2024-01-20) do not change inferred types. -#}
{% macro stg_open_meteo(kind, suffix) -%}
{%- set variables = ['temperature_2m', 'dew_point_2m', 'relative_humidity_2m', 'cloud_cover',
                     'wind_speed_10m', 'shortwave_radiation'] -%}
with files as (
    select filename, hourly
    from read_json(
        '{{ var("raw_dir") }}/weather/{{ kind }}/*/*/*.json',
        filename = true,
        columns = {
            hourly: 'STRUCT(time VARCHAR[]{% for v in variables %}, {{ v }}{{ suffix }} DOUBLE[]{% endfor %})'
        }
    )
),

unnested as (
    select
        regexp_extract(filename, '{{ kind }}/([A-Z]+)/', 1) as ba_code,
        regexp_extract(filename, '{{ kind }}/[A-Z]+/([a-z0-9-]+)/', 1) as city_slug,
        unnest(hourly.time) as valid_time_text
        {%- for v in variables %},
        unnest(hourly.{{ v }}{{ suffix }}) as {{ v }}
        {%- endfor %}
    from files
)

select
    ba_code,
    city_slug,
    strptime(valid_time_text, '%Y-%m-%dT%H:%M') at time zone 'UTC' as valid_time_utc,
    temperature_2m as temperature_c,
    dew_point_2m as dew_point_c,
    -- Percentages are clamped: the archive contains e.g. cloud_cover = 101 (seen 2025-03/05).
    least(greatest(relative_humidity_2m, 0), 100) as relative_humidity_pct,
    least(greatest(cloud_cover, 0), 100) as cloud_cover_pct,
    wind_speed_10m as wind_speed_kmh,
    shortwave_radiation as shortwave_radiation_wm2
from unnested
{%- endmacro %}
