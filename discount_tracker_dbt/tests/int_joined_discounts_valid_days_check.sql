SELECT
    discount_id,
    issuer_name,
    source_id,
    day_num
FROM {{ ref('int_normalized_discounts') }},
UNNEST(discount_valid_days_list) AS day_num
-- Check if any number is outside the 0-6 range
WHERE day_num < 0 OR day_num > 6