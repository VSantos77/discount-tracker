INSERT INTO discounts (
    issuer_name, merchant_name, discount_start_date, discount_end_date,
    discount_payment_method, discount_rate, discount_no_interest_installment_qty,
    discount_name, discount_description, discount_url, discount_terms_and_conditions,
    discount_max_discount_amount, discount_min_purchase_amount, 
    discount_valid_days_list, discount_valid_online, discount_valid_instore, 
    discount_metadata
) VALUES (
    %(issuer_name)s, %(merchant_name)s, %(discount_start_date)s, %(discount_end_date)s,
    %(discount_payment_method)s, %(discount_rate)s, %(discount_no_interest_installment_qty)s,
    %(discount_name)s, %(discount_description)s, %(discount_url)s, %(discount_terms_and_conditions)s,
    %(discount_max_discount_amount)s, %(discount_min_purchase_amount)s, 
    %(discount_valid_days_list)s, %(discount_valid_online)s, %(discount_valid_instore)s, 
    %(discount_metadata)s
)
ON CONFLICT (discount_url) DO UPDATE SET
    discount_end_date = EXCLUDED.discount_end_date,
    scraped_at = CURRENT_TIMESTAMP;