{#- Fails when the share of non-null values of column_name, per group, is below min_share.
    With time_column, rows after the group's latest non-null value are ignored: hours whose value
    has not been published yet are not "missing" (the live job reads only recent files, where the
    unpublished tail is a large share; over the full archive it is negligible). -#}
{% test min_coverage(model, column_name, group_by, min_share, time_column=none) %}
with scoped as (
    select *
    {%- if time_column %},
        max(case when {{ column_name }} is not null then {{ time_column }} end)
            over (partition by {{ group_by }}) as _last_published
    {%- endif %}
    from {{ model }}
)
select {{ group_by }}, avg(case when {{ column_name }} is null then 0 else 1 end) as share
from scoped
{%- if time_column %}
where {{ time_column }} <= _last_published
{%- endif %}
group by {{ group_by }}
having avg(case when {{ column_name }} is null then 0 else 1 end) < {{ min_share }}
{% endtest %}
