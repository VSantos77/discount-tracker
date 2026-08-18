-- tests/generic/non_empty_array.sql
{% test non_empty_array(model, column_name) %}

select {{ column_name }}
from {{ model }}
where array_length({{ column_name }}) = 0

{% endtest %}