with source as (
    select * from {{ ref('int_business_deduped_discounts')}} 
),

distinct_issuers as (
    select distinct issuer_name from source where issuer_name is not null
)

SELECT 
    {{ dbt_utils.generate_surrogate_key(["issuer_name"]) }} AS id,  -- Generates a unique string/hash
    issuer_name AS name
FROM distinct_issuers