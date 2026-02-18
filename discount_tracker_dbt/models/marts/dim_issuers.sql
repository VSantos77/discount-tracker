{{
  config(
    materialized='incremental',
    unique_key='issuer_id'
  )
}}

with source as (
    select * from {{ ref('stg_discounts')}} 
),

distinct_issuers as (
    select distinct issuer_name from source where issuer_name is not null
)

SELECT 
    {{ dbt.hash("issuer_name") }} AS issuer_id,  -- Generates a unique string/hash
    issuer_name
FROM distinct_issuers

{% if is_incremental() %}
    WHERE issuer_name NOT IN (SELECT name FROM {{ this }})
{% endif %}