-- tests/source_bbva_json_keys_exist.sql
{{ assert_payload_has_keys(
    relation=source('staging','raw_discounts'),
    column_name='raw_payload',
    expected_keys=['$.source_id', '$.cabecera', '$.canalesVenta', '$.beneficios', '$.diasPromo', '$.basesCondiciones', '$.subcabecera'],
    where_clause="spider = 'bbva'"
) }}