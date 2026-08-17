with source as (
    select * from {{ ref('int_unioned_and_renamed_discounts') }}
),

with_id as (
    select
        {{ dbt_utils.generate_surrogate_key(['source_id', 'issuer_name']) }} as discount_id,
        *
    from source
)

select *
from with_id
qualify row_number() over (
    partition by discount_id
    order by last_updated_at_date desc
) = 1
