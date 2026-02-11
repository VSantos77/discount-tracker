INSERT INTO dim_merchants (name)
    SELECT DISTINCT merchant_name 
    FROM stg_discounts
    ON CONFLICT (name) DO NOTHING;