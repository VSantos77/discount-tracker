with

source            as (select * from {{ ref('int_source_deduped_discounts') }}),
category_override as (select * from {{ ref('merchant_category_override') }}),
category_mapping  as (select * from {{ ref('merchant_category_mapping') }})

select
    s.discount_id,
    s.source_id,
    s.issuer_name,
    s.merchant_name,
    s.merchant_category_name,
    -- Resolved category: merchant-level override wins, then category mapping, then fallback
    COALESCE(
        co.normalized_category,
        cm.clean_category,
        'Sin categorizar'
    )                                                               as merchant_category_clean,
    s.discount_start_date,
    s.discount_end_date,
    GREATEST(COALESCE(s.discount_rate, 0), 0)                       as discount_rate,
    s.discount_name,
    s.discount_description,
    s.discount_terms_and_conditions,
    s.discount_url,
    COALESCE(s.discount_max_discount_amount, 0)                     as discount_max_discount_amount,
    COALESCE(s.discount_min_purchase_amount, 0)                     as discount_min_purchase_amount,
    GREATEST(COALESCE(s.discount_no_interest_installment_qty, 0), 0) as discount_no_interest_installment_qty,
    s.discount_valid_days_list,
    s.discount_valid_online,
    s.discount_valid_instore,
    s.discount_metadata,
    s.scraped_at_dt                                                 as last_updated_at_date
from source s
left join category_override co
    on LOWER(s.merchant_name) = LOWER(co.merchant_name)
left join category_mapping cm
    on LOWER(s.merchant_category_name) = LOWER(cm.raw_category)
