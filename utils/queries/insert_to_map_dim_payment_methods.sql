INSERT INTO map_discount_payment_methods (discount_id, payment_method_id)
SELECT 
    md5(concat(i.id::text, m.id::text, s.discount_start_date::text, s.discount_end_date::text, s.discount_rate::text))::uuid as d_id,
    dm.id
FROM stg_discounts s
-- Explode the JSON list into a virtual table 'pm'
CROSS JOIN LATERAL jsonb_to_recordset(s.discount_payment_method) 
    AS pm(card TEXT, card_type TEXT)
JOIN dim_issuers i ON s.issuer_name = i.name
JOIN dim_merchants m ON s.merchant_name = m.name
JOIN dim_payment_methods_raw dm 
    ON dm.name = INITCAP(pm.card) 
    AND dm.type = LOWER(pm.card_type)
ON CONFLICT (discount_id, payment_method_id) DO NOTHING;