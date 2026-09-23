-- BA-level hourly forecast weather: population-weighted and unweighted means over the BA's cities.
-- The weighted mean renormalises over the cities present in that hour; n_cities says how many.
{%- set cols = ['temperature_c', 'dew_point_c', 'relative_humidity_pct', 'cloud_cover_pct',
                'wind_speed_kmh', 'shortwave_radiation_wm2'] %}
with city as (
    select w.*, c.population
    from {{ ref('stg_open_meteo__forecast_d2') }} as w
    join {{ ref('cities') }} as c
        on w.ba_code = c.ba_code and w.city_slug = c.city_slug
)

select
    ba_code,
    valid_time_utc,
    count(temperature_c) as n_cities,
    {%- for col in cols %}
    sum({{ col }} * population) / nullif(sum(case when {{ col }} is not null then population end), 0)
        as {{ col }},
    {%- endfor %}
    avg(temperature_c) as temperature_unweighted_c,
    max(temperature_c) - min(temperature_c) as temperature_spread_c
from city
group by ba_code, valid_time_utc
