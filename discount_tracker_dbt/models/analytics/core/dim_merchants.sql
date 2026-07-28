with source as (
    select * from {{ ref('int_business_deduped_discounts')}}
),

distinct_merchants as (
    select distinct
        {{ dbt_utils.generate_surrogate_key(["merchant_name", "merchant_category_clean"]) }} AS merchant_id,
        merchant_name,
        merchant_category_clean
    from source
    where merchant_name is not null
)

SELECT
    merchant_id             AS id,
    merchant_name           AS name,
    merchant_category_clean AS category_name
FROM distinct_merchants
