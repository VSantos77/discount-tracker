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
    select distinct merchant_name from source where merchant_name is not null
)

SELECT 
    {{ dbt.hash("merchant_name") }} AS merchant_id,  -- Generates a unique string/hash
    merchant_name
FROM distinct_merchants

{% if is_incremental() %}
    WHERE merchant_name NOT IN (SELECT merchant_name FROM {{ this }})
{% endif %}