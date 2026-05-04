/*
  int_joined_discounts.sql
  -----------------
  Union of all per-issuer staging models.
  Surrogate key is generated here so downstream marts reference a single model.

  To add a new issuer: create stg_<issuer>.sql and add a UNION ALL branch below.
*/

with

bbva              as (select * from {{ ref('stg_bbva') }}),
galicia           as (select * from {{ ref('stg_galicia') }}),

unioned as (
    select * from bbva
    union all
    select * from galicia
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
        discount_payment_method,
        discount_metadata,
        scraped_at_dt
    from unioned
),

deduped as (
    select
        *
    from combined
    qualify row_number() over (
        partition by discount_id 
        order by scraped_at_dt desc
    ) = 1
)

select
    *
from deduped
