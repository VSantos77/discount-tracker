{% macro assert_payload_has_keys(relation, column_name, expected_keys, where_clause="1=1") %}

select {{ column_name }}
from {{ relation }}
where {{ column_name }} is not null
and {{ where_clause }}
  and (
    {% for key in expected_keys %}
        {# Checks if key is missing or extracts as NULL #}
        json_type(json_query({{column_name}}, '{{ key }}')) is null
        {% if not loop.last %} or {% endif %}
    {% endfor %}
  )

{% endmacro %}