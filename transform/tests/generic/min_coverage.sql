{#- Fails when the share of non-null values of column_name, per group, is below min_share. -#}
{% test min_coverage(model, column_name, group_by, min_share) %}
select {{ group_by }}, avg(case when {{ column_name }} is null then 0 else 1 end) as share
from {{ model }}
group by {{ group_by }}
having avg(case when {{ column_name }} is null then 0 else 1 end) < {{ min_share }}
{% endtest %}
