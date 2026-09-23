{#- Every complete local day has 23, 24 or 25 hours (DST). The first and last day of the data
    may be partial and are excluded. -#}
{% test hours_per_local_day(model, ba_column, day_column) %}
with days as (
    select {{ ba_column }} as ba, {{ day_column }} as d, count(*) as hours
    from {{ model }}
    group by 1, 2
),
bounds as (select ba, min(d) as first_day, max(d) as last_day from days group by 1)
select days.*
from days join bounds using (ba)
where d > first_day and d < last_day and hours not in (23, 24, 25)
{% endtest %}
