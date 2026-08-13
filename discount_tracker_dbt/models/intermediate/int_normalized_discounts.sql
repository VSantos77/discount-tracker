with

source as (select * from {{ ref('int_source_deduped_discounts') }}),

category_override as (select * from {{ ref('merchant_category_override') }}),

category_mapping as (select * from {{ ref('merchant_category_mapping') }})

select
    s.discount_id,
    s.source_id,
    s.issuer_name,
    s.merchant_name,
    s.merchant_category_name,
    -- Resolved category: merchant-level override wins, then category mapping, then fallback
    coalesce(
        co.normalized_category,
        cm.clean_category,
        'Sin categorizar'
    ) as merchant_category_clean,
    s.discount_start_date,
    s.discount_end_date,
    greatest(coalesce(s.discount_rate, 0), 0) as discount_rate,
    s.discount_name,
    s.discount_description,
    s.discount_terms_and_conditions,
    s.discount_url,
    coalesce(s.discount_max_discount_amount, 0) as discount_max_discount_amount,
    coalesce(s.discount_min_purchase_amount, 0) as discount_min_purchase_amount,
    greatest(coalesce(s.discount_no_interest_installment_qty, 0), 0)
        as discount_no_interest_installment_qty,
    s.discount_valid_days_list,
    s.discount_valid_online,
    s.discount_valid_instore,
    s.discount_metadata,
    s.scraped_at_dt as last_updated_at_date
from source as s
left join category_override as co
    on lower(s.merchant_name) = lower(co.merchant_name)
left join category_mapping as cm
    on lower(s.merchant_category_name) = lower(cm.raw_category)
