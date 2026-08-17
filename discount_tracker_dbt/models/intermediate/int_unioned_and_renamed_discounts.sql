with

bbva as (select * from {{ ref('stg_bbva') }}),

galicia as (select * from {{ ref('stg_galicia') }}),

naranjax as (select * from {{ ref('stg_naranjax') }}),

unioned as (
    select * from bbva
    union all
    select * from galicia
    union all
    select * from naranjax
),

renamed as (
select
    * except(scraped_at_dt),
    scraped_at_dt as last_updated_at_date
from unioned
),

filtered as (
    select * from renamed
    where 
        {# Explicitly filter out discounts that are not rate or no-interest-installment based #}
        (discount_rate != 0 or discount_no_interest_installment_qty != 0)
        {# Filter out discounts that cannot be determined if valid online and/or instore #}
        and (discount_valid_instore or discount_valid_online)
)

select * from filtered