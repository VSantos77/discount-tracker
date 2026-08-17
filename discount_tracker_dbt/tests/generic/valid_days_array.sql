{#
    Test if valid_days_list field is properly normalized
    (Array with values in range 0-6)
#}
{% test valid_days_array(model, column_name) %}
select
    {{ column_name }}
from {{ model }},
unnest({{ column_name }}) as day_value
where day_value not between 0 and 6
{% endtest %}