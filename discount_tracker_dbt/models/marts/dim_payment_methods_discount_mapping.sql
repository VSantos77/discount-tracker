{{ config(
    materialized='incremental',
    unique_key='mapping_id'
) }}

with source as (
    select
        *
    from {{ ref('stg_discounts') }}
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
    cross join lateral jsonb_to_recordset(s.discount_payment_method) as pm(card TEXT, card_type TEXT)
    join {{ ref('dim_payment_methods')}} dm
        on dm.card_name = pm.card
        and dm.card_type = pm.card_type
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