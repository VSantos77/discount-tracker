{{ config(
    materialized='incremental',
    unique_key='mapping_id'
) }}

with source as (
    select
        *
    from {{ ref('int_joined_discounts') }}
),

mapped as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'discount_id',
            'payment_method_id'
        ]) }} as mapping_id,
        discount_id,
        dm.payment_method_id
    from source s
    join {{ ref('dim_payment_methods')}} dm
        on dm.card_name = s.discount_payment_method ->> 'card'
        and dm.card_type = s.discount_payment_method ->> 'card_type'
)

select
    *
from mapped

{% if is_incremental() %}
where mapping_id not in (
    select mapping_id
    from {{ this }}
)
{% endif %}