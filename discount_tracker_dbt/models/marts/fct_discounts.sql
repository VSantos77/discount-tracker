{{ config(
    materialized='incremental',
    unique_key='discount_id'
)}}

with discounts as (
    select
        *
    from {{ ref('stg_discounts') }}
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
    d.discount_id,
    i.issuer_id,
    m.merchant_id,
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
from discounts d
join issuers i on d.issuer_name = i.issuer_name
join merchants m on d.merchant_name = m.merchant_name

{% if is_incremental() %}
    where d.discount_id not in (select discount_id from {{ this }})
{% endif %}