-- One row per calendar date. Everything here is known years in advance (no leakage risk).
with spine as (
    select cast(range as date) as calendar_date
    from range(date '2018-01-01', date '2029-01-01', interval 1 day)
)

select
    s.calendar_date,
    extract(year from s.calendar_date) as year,
    extract(month from s.calendar_date) as month,
    extract(isodow from s.calendar_date) as iso_weekday,
    extract(doy from s.calendar_date) as day_of_year,
    h.holiday_name,
    h.holiday_date is not null as is_holiday,
    case
        when h.holiday_date is not null then 'holiday'
        when extract(isodow from s.calendar_date) >= 6 then 'weekend'
        else 'weekday'
    end as day_type,
    case
        when extract(month from s.calendar_date) in (12, 1, 2) then 'winter'
        when extract(month from s.calendar_date) in (3, 4, 5) then 'spring'
        when extract(month from s.calendar_date) in (6, 7, 8) then 'summer'
        else 'autumn'
    end as season
from spine as s
left join {{ ref('us_holidays') }} as h on s.calendar_date = h.holiday_date
