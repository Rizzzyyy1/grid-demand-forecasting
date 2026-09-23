{% test equal_to_column(model, column_name, other) %}
select *
from {{ model }}
where {{ column_name }} is distinct from {{ other }}
{% endtest %}
