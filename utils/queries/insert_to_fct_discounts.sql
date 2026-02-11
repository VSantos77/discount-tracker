INSERT INTO fct_discounts (
    id,
    issuer_id,
    merchant_id,
    start_date,
    end_date,
    name,
    description,
    url,
    terms_and_conditions,
    rate,
    no_interest_installment_qty,
    max_discount_amount,
    min_purchase_amount,
    payment_method,
    valid_days_list,
    metadata,
    valid_online,
    valid_instore,
    scraped_at_ts
)
SELECT
    md5(concat(i.id::text, m.id::text, s.discount_start_date::text, s.discount_end_date::text, s.discount_rate::text))::uuid,
    i.id,
    m.id,
    s.discount_start_date,
    s.discount_end_date,
    s.discount_name,
    s.discount_description,
    s.discount_url,
    s.discount_terms_and_conditions,
    s.discount_rate,
    s.discount_no_interest_installment_qty,
    s.discount_max_discount_amount,
    s.discount_min_purchase_amount,
    s.discount_payment_method::jsonb,
    s.discount_valid_days_list::jsonb,
    s.discount_metadata::jsonb,
    s.discount_valid_online,
    s.discount_valid_instore,
    s.scraped_at
FROM stg_discounts s
JOIN dim_issuers i ON s.issuer_name = i.name
JOIN dim_merchants m ON s.merchant_name = m.name
ON CONFLICT DO NOTHING;