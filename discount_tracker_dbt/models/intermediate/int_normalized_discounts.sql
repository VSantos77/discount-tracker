with

source as (select * from {{ ref('int_business_deduped_discounts') }}),

category_override as (select * from {{ ref('merchant_category_override') }}),

category_mapping as (select * from {{ ref('merchant_category_mapping') }})

select
    s.* except(
        merchant_category_name,
        merchant_name
    ),
    coalesce(
        co.normalized_category,
        cm.parsed_merchant_category_name,
        'Sin categorizar'
    ) as merchant_category_clean,
    initcap(s.merchant_name) as merchant_name
from source as s
left join category_override as co
    on lower(s.merchant_name) = lower(co.merchant_name)
left join category_mapping as cm
    on lower(cm.issuer) = lower(s.issuer_name)
    and lower(s.merchant_category_name) = lower(cm.raw_merchant_category_name)
