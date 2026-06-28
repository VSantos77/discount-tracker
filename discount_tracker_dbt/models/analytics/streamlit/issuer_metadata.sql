with discounts as (
    select
        i.name AS issuer_name,
        d.last_updated_at_date
    from {{ ref('fct_discounts') }} d
    join {{ ref('dim_issuers') }} i on d.issuer_id = i.id
)

select
    issuer_name,
    max(last_updated_at_date) as last_scraped_at,
    count(*) as discount_count
from discounts
where issuer_name is not null
group by issuer_name
having count(*) > 0
order by issuer_name
