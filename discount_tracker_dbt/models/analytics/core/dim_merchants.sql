with source as (
    select * from {{ ref('int_business_deduped_discounts')}} 
),

distinct_merchants as (
    select distinct 
        {{ dbt_utils.generate_surrogate_key(["merchant_name", "merchant_category_name"]) }} AS merchant_id,
        merchant_name,
        merchant_category_name
    from 
        source 
    where 
        merchant_name is not null
),

parsed_categories as (
    SELECT 
        merchant_id AS id,
        merchant_name AS name,
        merchant_category_name AS category_name_original,
        COALESCE(mcm.clean_category, 'Sin categorizar') AS category_name_normalized
    FROM distinct_merchants AS m
    LEFT JOIN {{ ref('merchant_category_mapping')}} AS mcm
    {# to lower case for ease of matching #}
    ON LOWER(m.merchant_category_name) = LOWER(mcm.raw_category) 
)

SELECT * FROM parsed_categories