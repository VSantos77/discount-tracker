{{
  config(
    materialized='incremental',
    unique_key='payment_method_id'
  )
}}

with source as (
    select
        *
    from {{ ref('int_joined_discounts') }}
),

unpacked as (
    select distinct
        JSON_VALUE(discount_payment_method, '$.card')      as card_name,
        JSON_VALUE(discount_payment_method, '$.card_type') as card_type
    from source
),

final as (
select
    {{ dbt_utils.generate_surrogate_key(['card_name', 'card_type']) }} as payment_method_id,
    card_name,
    card_type
from unpacked
)

select
    payment_method_id,
    card_name,
    card_type
from final

{% if is_incremental() %}
    where payment_method_id not in (select payment_method_id from {{ this }})
{% endif %}