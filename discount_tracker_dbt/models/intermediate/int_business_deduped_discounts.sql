with discounts as (
    select * from {{ ref('int_business_dedup_audit')}}
)

select
    *
from discounts
where rn = 1