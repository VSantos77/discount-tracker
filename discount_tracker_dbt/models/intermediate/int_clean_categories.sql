with discounts as (
    select * from {{ ref('int_joined_discounts')}}
),

categories as (
    select * from {{ ref('merchant_category_mapping') }}
),

cleaned_categories as (
    select
        * except(merchant_category_name),
        coalesce(
            c.clean_category,
            d.merchant_category_name
        ) as merchant_category_name
    from discounts as d
    left join categories as c
        on TRIM(LOWER(d.merchant_category_name)) = TRIM(LOWER(c.raw_category))
)

select * from cleaned_categories