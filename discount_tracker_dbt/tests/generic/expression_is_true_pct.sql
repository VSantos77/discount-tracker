{% test expression_is_true_pct(model, expression) %}

{# 
    Use percentage of failing rows as failing calc.
    Fail calc only accepts integers -> Multiplying and rounding to basis points (1 bp = 0.01%)
    e.g 500 bp = 5% 
#}
{{ config(
    fail_calc = 'coalesce(round(10000 * safe_divide(failing_rows, total_rows)), 0)'
) }}

with validation as (

    select
        count(*) as total_rows,
        countif(not ({{ expression }})) as failing_rows
    from {{ model }}

)

select total_rows, failing_rows
from validation

{% endtest %}