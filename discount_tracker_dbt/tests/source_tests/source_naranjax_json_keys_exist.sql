{{ assert_payload_has_keys(
    relation=source('staging','raw_discounts'),
    column_name='raw_payload',
    expected_keys=['$.id','$.commerceName','$.benefitName','$.days','$.benefit','$.promotionDetails','$.days.weekdaysApplied'],
    where_clause="spider = 'naranjax'"
) }}