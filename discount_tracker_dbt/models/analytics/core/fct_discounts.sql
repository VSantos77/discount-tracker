with discounts as (
    select
        *
    from {{ ref('int_business_deduped_discounts') }}
),

issuers as (
    select
        *
    from {{ ref('dim_issuers') }}
),

merchants as (
    select
        *
    from {{ ref('dim_merchants') }}
)

select
    d.discount_business_id AS id,
    i.id AS issuer_id,
    m.id AS merchant_id,
    d.discount_start_date AS start_date,
    d.discount_end_date AS end_date,
    d.discount_is_active AS is_active,
    d.discount_rate AS rate,
    d.discount_no_interest_installment_qty AS no_interest_installment_qty,
    d.discount_name AS name,
    d.discount_description AS description,
    d.discount_url AS url,
    d.discount_terms_and_conditions AS terms_and_conditions,
    d.discount_max_discount_amount AS max_discount_amount,
    d.discount_min_purchase_amount AS min_purchase_amount,
    d.discount_valid_days_list AS valid_days_list,
    d.discount_valid_online AS valid_online,
    d.discount_valid_instore AS valid_instore,
    d.discount_metadata AS metadata,
    d.last_updated_at_date
from discounts d
left join issuers i 
    on d.issuer_name = i.name
left join merchants m 
    on d.merchant_name = m.name 
    and d.merchant_category_name = m.category_name_original