{{
    config(
        severity = 'warn'
    )
}}

SELECT
    discount_id,
    source_id,
    issuer_name
FROM {{ ref('int_normalized_discounts') }}
WHERE 
    discount_rate = 0
    AND discount_no_interest_installment_qty = 0