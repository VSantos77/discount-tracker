with discounts as (
    select * from {{ ref('int_joined_deduped_and_normalized_discounts') }}
),

discounts_prepared as (
    select
        *,
        ARRAY_TO_STRING(ARRAY(SELECT CAST(x AS STRING) FROM UNNEST(discount_valid_days_list) AS x), ',') as discount_valid_days_list_str
    from discounts
),

discounts_with_surrogate_key as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'issuer_name',
            'merchant_name',
            'merchant_category_name',
            'discount_start_date',
            'discount_end_date',
            'discount_rate',
            'discount_max_discount_amount',
            'discount_min_purchase_amount',
            'discount_no_interest_installment_qty',
            'discount_valid_days_list_str',
            'discount_valid_online',
            'discount_valid_instore'
        ])}} AS discount_business_id,
        * except(discount_valid_days_list_str)
    from discounts_prepared
),

discounts_with_rank as (
    select
        *,
        row_number() over(
            partition by discount_business_id
            order by last_updated_at_date desc
        ) as rn
    from discounts_with_surrogate_key
)

select * from discounts_with_rank