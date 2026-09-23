-- How many rows each cleaning rule touched, per BA (a check that passes says how much it checked).
with staged as (
    select ba_code, count(*) as n_staged from {{ ref('stg_eia__balance') }} group by 1
),

cleaned as (
    select
        ba_code,
        count(*) as n_rows,
        count(*) filter (where is_missing) as r0_missing_reported,
        count(*) filter (where is_nonpositive) as r2_nonpositive,
        count(*) filter (where is_outlier) as r3_outlier,
        count(*) filter (where is_forecast_invalid) as r4_forecast_invalid,
        count(*) filter (where demand_mw is null) as target_null,
        count(*) filter (where demand_filled_mw is null) as filled_null,
        count(*) filter (where operator_forecast_mw is null) as operator_forecast_null
    from {{ ref('int_eia__demand_cleaned') }}
    group by 1
)

select
    cleaned.ba_code,
    staged.n_staged,
    staged.n_staged - cleaned.n_rows as r1_duplicates_removed,
    cleaned.* exclude (ba_code)
from cleaned join staged using (ba_code)
order by ba_code
