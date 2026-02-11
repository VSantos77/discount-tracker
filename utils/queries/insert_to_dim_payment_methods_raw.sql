INSERT INTO dim_payment_methods_raw (name, type)
SELECT DISTINCT
    INITCAP(pm->>'card'),
    LOWER((pm->>'card_type'))
FROM stg_discounts s
CROSS JOIN jsonb_array_elements(s.discount_payment_method) AS pm
ON CONFLICT (name, type) DO NOTHING;