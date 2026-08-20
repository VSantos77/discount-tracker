
{{ assert_payload_has_keys(
    relation=source('staging','raw_discounts'),
    column_name='raw_payload',
    expected_keys= var('galicia'),
    where_clause="spider = 'galicia'"
) }}

