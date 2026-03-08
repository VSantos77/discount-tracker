{{
  config(
    materialized='incremental',
    unique_key='merchant_id'
  )
}}

with source as (
    select * from {{ ref('stg_discounts')}} 
),

distinct_merchants as (
    select distinct 
        merchant_name,
        merchant_category_name 
    from 
        source 
    where 
        merchant_name is not null
),

final as (
    SELECT 
        {{ dbt.hash("merchant_name") }} AS merchant_id,
        merchant_name,
        merchant_category_name
    FROM distinct_merchants
)

SELECT * FROM final

{% if is_incremental() %}
    WHERE merchant_id NOT IN (SELECT merchant_id FROM {{ this }})
{% endif %}