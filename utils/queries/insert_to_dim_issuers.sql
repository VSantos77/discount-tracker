INSERT INTO dim_issuers (name)
    SELECT DISTINCT issuer_name 
    FROM stg_discounts
    ON CONFLICT (name) DO NOTHING;