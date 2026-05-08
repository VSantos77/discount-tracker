SELECT DISTINCT 
    discount_id,
    issuer_name,
    d.merchant_category_name
FROM {{ ref('int_joined_discounts') }} as d
LEFT JOIN {{ ref('merchant_category_mapping') }} as m
    ON TRIM(LOWER(d.merchant_category_name)) = TRIM(LOWER(m.raw_category))
WHERE m.raw_category IS NULL