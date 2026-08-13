{{
    config(
        materialized='incremental',
        unique_key='id',
        incremental_strategy='merge'
    )
}}


with discounts as (
    select *
    from {{ ref('int_business_deduped_discounts') }}
    {% if is_incremental() %}
        where last_updated_at_date
            > (select max(last_updated_at_date) from {{ this }})

        {# Used for testing incremental logic #}
    {% elif var('cutoff_date', none) is not none %}
        where last_updated_at_date <= '{{ var("cutoff_date") }}'
    {% endif %}
)

select
    discount_id as id,
    issuer_name,
    merchant_name,
    merchant_category_name,
    merchant_category_clean,
    discount_start_date as start_date,
    discount_end_date as end_date,
    discount_rate as rate,
    discount_no_interest_installment_qty as no_interest_installment_qty,
    discount_name as name,
    discount_description as description,
    discount_url as url,
    discount_terms_and_conditions as terms_and_conditions,
    discount_max_discount_amount as max_discount_amount,
    discount_min_purchase_amount as min_purchase_amount,
    discount_valid_days_list as valid_days_list,
    discount_valid_online as valid_online,
    discount_valid_instore as valid_instore,
    discount_metadata as metadata,
    last_updated_at_date
from discounts
