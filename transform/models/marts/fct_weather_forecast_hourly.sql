-- BA-level forecast weather keyed by the hour-ending instant it describes. The value at the
-- instant T was predicted 48 h before T, so it becomes available at T - 48 h + publication delay;
-- gridcast.features encodes that as available_at and the leakage test checks it.
select
    ba_code,
    valid_time_utc as hour_ending_utc,
    n_cities,
    temperature_c,
    temperature_unweighted_c,
    temperature_spread_c,
    dew_point_c,
    relative_humidity_pct,
    cloud_cover_pct,
    wind_speed_kmh,
    shortwave_radiation_wm2
from {{ ref('int_weather__ba_hourly') }}
