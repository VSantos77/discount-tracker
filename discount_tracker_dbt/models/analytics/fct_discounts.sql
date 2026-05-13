{{ config(
    materialized='incremental',
    unique_key='discount_id',
    incremental_strategy='merge',
    merge_update_columns=[
        'issuer_id',
        'merchant_id',
        'discount_start_date',
        'discount_end_date',
        'discount_rate',
        'discount_no_interest_installment_qty',
        'discount_name',
        'discount_description',
        'discount_url',
        'discount_terms_and_conditions',
        'discount_max_discount_amount',
        'discount_min_purchase_amount',
        'discount_valid_days_list',
        'discount_valid_online',
        'discount_valid_instore',
        'discount_metadata',
        'scraped_at_dt'
    ]
)}}

with discounts_source as (
    select
        *
    from {{ ref('int_clean_categories') }}
),

discounts as (
    -- Deduplicate incoming batch to prevent inserting duplicates
    -- that don't exist in target yet
    select *
    from discounts_source
    qualify row_number() over (partition by discount_id order by scraped_at_dt desc) = 1
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
    d.scraped_at_dt
from discounts d
left join issuers i on d.issuer_name = i.issuer_name
left join merchants m on d.merchant_name = m.merchant_name 
    and d.merchant_category_name = m.merchant_category_name

{% if is_incremental() %}
    where d.scraped_at_dt > (select max(scraped_at_dt) from {{ this }})
{% endif %}