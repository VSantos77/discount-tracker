with discounts as (
    select *
    from {{ ref('fct_discounts') }}
)

select
    id as discount_id,
    issuer_name,
    merchant_name,
    merchant_category_name,
    start_date as discount_start_date,
    end_date as discount_end_date,
    (start_date <= current_date and end_date > current_date)
        as discount_is_active,
    rate as discount_rate,
    no_interest_installment_qty as discount_no_interest_installment_qty,
    name as discount_name,
    description as discount_description,
    url as discount_url,
    terms_and_conditions as discount_terms_and_conditions,
    max_discount_amount as discount_max_discount_amount,
    min_purchase_amount as discount_min_purchase_amount,
    valid_days_list as discount_valid_days_list,
    valid_online as discount_valid_online,
    valid_instore as discount_valid_instore,
    payment_methods_list as discount_payment_methods_list,
    last_updated_at_date
from
    discounts
