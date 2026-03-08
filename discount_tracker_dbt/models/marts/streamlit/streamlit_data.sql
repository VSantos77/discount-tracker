{{ 
    config(
        materialized='table',
    )
}}

with discounts as (
    select
        *
    from {{ ref('fct_discounts') }}
),

merchants as (
    select
        *
    from {{ ref('dim_merchants') }}
),

issuers as (
    select
        *
    from {{ ref('dim_issuers') }}
)

select
        d.discount_id,
        i.issuer_name,
        m.merchant_name,
        m.merchant_category_name,
        d.discount_start_date,
        d.discount_end_date,
        d.discount_rate,
        d.discount_no_interest_installment_qty,
        d.discount_name,
        d.discount_description,
        d.discount_url,
        d.discount_terms_and_conditions,
        d.discount_max_discount_amount,
        d.discount_min_purchase_amount,
        d.discount_valid_days_list,
        d.discount_valid_online,
        d.discount_valid_instore,
        d.discount_metadata,
        d.scraped_at
from
    discounts d
join merchants m on d.merchant_id = m.merchant_id
join issuers i on d.issuer_id = i.issuer_id