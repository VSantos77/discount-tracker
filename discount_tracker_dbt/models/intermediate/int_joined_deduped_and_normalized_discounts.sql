with

bbva              as (select * from {{ ref('stg_bbva') }}),
galicia           as (select * from {{ ref('stg_galicia') }}),
naranjax          as (select * from {{ ref('stg_naranjax') }}),

unioned as (
    select * from bbva
    union all
    select * from galicia
    union all
    select * from naranjax
),

combined as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'source_id',
            'issuer_name'
        ]) }}                               as discount_id,
        issuer_name,
        merchant_name,
        merchant_category_name,
        discount_start_date,
        discount_end_date,
        GREATEST(COALESCE(discount_rate,0),0) AS discount_rate,
        discount_name,
        discount_description,
        discount_terms_and_conditions,
        discount_url,
        COALESCE(discount_max_discount_amount,0) AS discount_max_discount_amount,
        COALESCE(discount_min_purchase_amount,0) AS discount_min_purchase_amount,
        GREATEST(COALESCE(discount_no_interest_installment_qty,0),0) AS discount_no_interest_installment_qty,
        discount_valid_days_list,
        discount_valid_online,
        discount_valid_instore,
        discount_metadata,
        scraped_at_dt AS last_updated_at_date
    from unioned
),

deduped as (
    {# 
        Dedup based on discount_id, since the same discount can 
        be scraped multiple times.
    #}
    select
        *
    from combined
    qualify row_number() over (
        partition by discount_id 
        order by last_updated_at_date desc
    ) = 1
)

select
    *
from deduped
