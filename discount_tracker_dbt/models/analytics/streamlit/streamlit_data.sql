with discounts as (
    select
        *
    from {{ ref('fct_discounts') }}
)

select
        id AS discount_id,
        issuer_name,
        merchant_name,
        merchant_category_name,
        start_date AS discount_start_date,
        end_date AS discount_end_date,
        (start_date <= CURRENT_DATE AND end_date > CURRENT_DATE) AS discount_is_active,
        rate AS discount_rate,
        no_interest_installment_qty AS discount_no_interest_installment_qty,
        name AS discount_name,
        description AS discount_description,
        url AS discount_url,
        terms_and_conditions AS discount_terms_and_conditions,
        max_discount_amount AS discount_max_discount_amount,
        min_purchase_amount AS discount_min_purchase_amount,
        valid_days_list AS discount_valid_days_list,
        valid_online AS discount_valid_online,
        valid_instore AS discount_valid_instore,
        metadata AS discount_metadata,
        last_updated_at_date
from
    discounts