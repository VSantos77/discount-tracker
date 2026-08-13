{{
    config(
        materialized='incremental',
        unique_key='id',
        incremental_strategy='merge'
    )
}}


with discounts as (
    select
        *
    from {{ ref('int_business_deduped_discounts') }}
    {% if is_incremental() %}
    where last_updated_at_date > (select max(last_updated_at_date) from {{ this }})
    
    {# Used for testing incremental logic #}
    {% elif var('cutoff_date', none) is not none %}
    where last_updated_at_date <= '{{ var("cutoff_date") }}'
    {% endif %}
)

select
    discount_id AS id,
    issuer_name,
    merchant_name,
    merchant_category_name,
    merchant_category_clean,
    discount_start_date AS start_date,
    discount_end_date AS end_date,
    discount_rate AS rate,
    discount_no_interest_installment_qty AS no_interest_installment_qty,
    discount_name AS name,
    discount_description AS description,
    discount_url AS url,
    discount_terms_and_conditions AS terms_and_conditions,
    discount_max_discount_amount AS max_discount_amount,
    discount_min_purchase_amount AS min_purchase_amount,
    discount_valid_days_list AS valid_days_list,
    discount_valid_online AS valid_online,
    discount_valid_instore AS valid_instore,
    discount_metadata AS metadata,
    last_updated_at_date
from discounts