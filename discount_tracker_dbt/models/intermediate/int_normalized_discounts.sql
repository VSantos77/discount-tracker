with

source as (select * from {{ ref('int_business_deduped_discounts') }}),

category_override as (select * from {{ ref('merchant_category_override') }}),

category_mapping as (select * from {{ ref('merchant_category_mapping') }})

select
    s.*,
    coalesce(
        co.normalized_category,
        cm.clean_category,
        'Sin categorizar'
    ) as merchant_category_clean
from source as s
left join category_override as co
    on lower(s.merchant_name) = lower(co.merchant_name)
left join category_mapping as cm
    on lower(s.merchant_category_name) = lower(cm.raw_category)
