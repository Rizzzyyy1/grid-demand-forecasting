-- De-duplicated, cleaned hourly demand and operator forecast per BA.
--
-- Rules (each one's affected-row count is reported by dq_cleaning_log):
--   R1 duplicate (ba, hour) across files -> keep the row from the newest file
--   R2 reported demand <= 0              -> treated as missing
--   R3 reported demand outside [low, high] x the BA's centred 7-day median -> outlier, missing
--   R4 operator forecast <= 0 or outside the same band -> missing (not scored)
-- `demand_mw` (the scoring target) is the reported value where it passes R2-R3, else NULL.
-- `demand_filled_mw` (for lag features only) falls back to EIA's adjusted/imputed series.
with ranked as (
    select
        *,
        row_number() over (
            partition by ba_code, hour_ending_utc order by source_file desc
        ) as file_rank
    from {{ ref('stg_eia__balance') }}
),

deduped as (
    select * exclude (file_rank) from ranked where file_rank = 1
),

with_median as (
    select
        *,
        median(demand_reported_mw) filter (where demand_reported_mw > 0) over (
            partition by ba_code
            order by hour_ending_utc
            range between interval 84 hours preceding and interval 84 hours following
        ) as demand_median_7d_mw
    from deduped
),

flagged as (
    select
        *,
        demand_reported_mw is null as is_missing,
        demand_reported_mw <= 0 as is_nonpositive,
        demand_reported_mw > 0 and (
            demand_reported_mw < {{ var('outlier_low_ratio') }} * demand_median_7d_mw
            or demand_reported_mw > {{ var('outlier_high_ratio') }} * demand_median_7d_mw
        ) as is_outlier,
        operator_forecast_mw is not null and (
            operator_forecast_mw <= 0
            or operator_forecast_mw < {{ var('outlier_low_ratio') }} * demand_median_7d_mw
            or operator_forecast_mw > {{ var('outlier_high_ratio') }} * demand_median_7d_mw
        ) as is_forecast_invalid
    from with_median
)

select
    ba_code,
    hour_ending_utc,
    eia_local_date,
    eia_hour_number,
    demand_reported_mw,
    demand_adjusted_mw,
    demand_median_7d_mw,
    coalesce(is_missing, false) as is_missing,
    coalesce(is_nonpositive, false) as is_nonpositive,
    coalesce(is_outlier, false) as is_outlier,
    coalesce(is_forecast_invalid, false) as is_forecast_invalid,
    case
        when not coalesce(is_nonpositive, false) and not coalesce(is_outlier, false)
            then demand_reported_mw
    end as demand_mw,
    case
        when demand_reported_mw > 0 and not coalesce(is_outlier, false) then demand_reported_mw
        when demand_adjusted_mw > 0
            and demand_adjusted_mw
                between {{ var('outlier_low_ratio') }} * demand_median_7d_mw
                and {{ var('outlier_high_ratio') }} * demand_median_7d_mw
            then demand_adjusted_mw
    end as demand_filled_mw,
    case when not coalesce(is_forecast_invalid, false) then operator_forecast_mw end
        as operator_forecast_mw,
    source_file
from flagged
