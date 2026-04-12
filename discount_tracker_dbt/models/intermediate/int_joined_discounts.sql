/*
  int_joined_discounts.sql
  -----------------
  Union of all per-issuer staging models.
  Surrogate key is generated here so downstream marts reference a single model.

  To add a new issuer: create stg_<issuer>.sql and add a UNION ALL branch below.
*/

with

bbva    as (select * from {{ ref('stg_bbva') }}),
galicia as (select * from {{ ref('stg_galicia') }}),

combined as (
    select * from bbva
    union all
    select * from galicia
)

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
    discount_rate,
    discount_name,
    discount_description,
    discount_terms_and_conditions,
    discount_url,
    discount_max_discount_amount,
    discount_min_purchase_amount,
    discount_no_interest_installment_qty,
    discount_valid_days_list,
    discount_valid_online,
    discount_valid_instore,
    discount_payment_method,
    discount_metadata,
    scraped_at
from combined

