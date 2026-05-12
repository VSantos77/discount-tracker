{{ 
    config(
        materialized='table'
    )
}}

with discounts as (
    select
        i.issuer_name,
        d.scraped_at_dt
    from {{ ref('fct_discounts') }} d
    join {{ ref('dim_issuers') }} i on d.issuer_id = i.issuer_id
)

select
    issuer_name,
    max(scraped_at_dt) as last_scraped_at,
    count(*) as discount_count
from discounts
where issuer_name is not null
group by issuer_name
having count(*) > 0
order by issuer_name
