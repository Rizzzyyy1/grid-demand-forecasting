-- One row per (BA, hour) per source file, for the configured BAs only. Types parsed, nothing
-- cleaned. A malformed timestamp or number fails the build here with DuckDB's parse error.
with src as (
    select *
    from read_csv(
        '{{ var("raw_dir") }}/eia/EIA930_BALANCE_*.csv',
        all_varchar = true,
        union_by_name = true,
        filename = true,
        header = true
    )
)

select
    "Balancing Authority" as ba_code,
    {{ eia_utc('"UTC Time at End of Hour"') }} as hour_ending_utc,
    cast(strptime("Data Date", '%m/%d/%Y') as date) as eia_local_date,
    cast("Hour Number" as integer) as eia_hour_number,
    {{ eia_mw('"Demand (MW)"') }} as demand_reported_mw,
    {{ eia_mw('"Demand (MW) (Adjusted)"') }} as demand_adjusted_mw,
    {{ eia_mw('"Demand Forecast (MW)"') }} as operator_forecast_mw,
    {{ eia_mw('"Net Generation (MW)"') }} as net_generation_mw,
    regexp_extract(filename, '[^/]+$') as source_file
from src
where "Balancing Authority" in (select ba_code from {{ ref('regions') }})
