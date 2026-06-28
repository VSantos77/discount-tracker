with fct_discount_cnt AS (
    select
        COUNT(*) AS fc_cnt
    from {{ ref('fct_discounts')}}
),

issuer_metadata_cnt AS (
    select
        sum(discount_count) AS im_cnt
    from {{ ref('issuer_metadata')}}
)

select
    1
from fct_discount_cnt CROSS JOIN issuer_metadata_cnt
WHERE fc_cnt != im_cnt