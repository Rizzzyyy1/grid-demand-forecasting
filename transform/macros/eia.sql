{#- Parse an EIA-930 "MM/DD/YYYY H:MM:SS AM" UTC string into a TIMESTAMPTZ. -#}
{% macro eia_utc(column) -%}
    (strptime({{ column }}, '%m/%d/%Y %I:%M:%S %p') at time zone 'UTC')
{%- endmacro %}

{#- Cast an EIA numeric string to DOUBLE; blanks become NULL, anything else unparsable fails. -#}
{% macro eia_mw(column) -%}
    cast(nullif(trim({{ column }}), '') as double)
{%- endmacro %}
