-- The hourly fact table every model trains and scores on. local_date / hour_number are
-- recomputed from each BA's clock (same convention as gridcast.core.time) and tested against
-- the values EIA publishes.
with d as (
    select c.*, r.timezone
    from {{ ref('int_eia__demand_cleaned') }} as c
    join {{ ref('regions') }} as r using (ba_code)
),

localised as (
    select
        *,
        cast(timezone(timezone, hour_ending_utc - interval 1 hour) as date) as local_date
    from d
)

select
    ba_code,
    hour_ending_utc,
    local_date,
    cast(
        epoch(hour_ending_utc - timezone(timezone, cast(local_date as timestamp))) / 3600
        as integer
    ) as hour_number,
    eia_local_date,
    eia_hour_number,
    demand_mw,
    demand_filled_mw,
    operator_forecast_mw,
    is_missing,
    is_nonpositive,
    is_outlier,
    is_forecast_invalid
from localised
