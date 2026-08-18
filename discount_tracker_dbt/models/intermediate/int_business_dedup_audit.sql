with discounts as (
    select * from {{ ref('int_source_deduped_discounts') }}
),

discounts_prepared as (
    select
        *,
        {# Convert to string representations to pass to generate surrogate key func #}
        array_to_string(
            array(
                select cast(x as string)
                from unnest(discount_valid_days_list) as x
                order by x
            ),
            ','
        ) as discount_valid_days_list_str,
        array_to_string(
            array(
                select to_json_string(x)
                from unnest(discount_payment_methods_list) as x
                order by to_json_string(x)
            ),
            ','
        ) as discount_payment_methods_list_str
    from discounts
),

discounts_with_surrogate_key as (
    select
        {# 
            Some entitites can send the same discount with different source ids.
            Generate content hash used for deduplication based on discount content.

        #}
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
            'discount_valid_instore',
            'discount_payment_methods_list_str'
        ])}} AS discount_content_hash,
        * except(discount_valid_days_list_str, discount_payment_methods_list_str)
    from discounts_prepared
),

discounts_with_rank as (
    select
        *,
        row_number() over(
            partition by discount_content_hash
            order by last_updated_at_date desc, discount_id asc
        ) as rn
    from discounts_with_surrogate_key
)

select * from discounts_with_rank