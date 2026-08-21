{% macro json_keys_not_null(column_name, keys, joiner="and") %}
    {% for key in keys %}
        json_type(json_query({{ column_name }}, '$.{{ key }}')) is not null
        {% if not loop.last %} {{ joiner }} {% endif %}
    {% endfor %}
{% endmacro %}