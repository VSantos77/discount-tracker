with source as (

    select
        raw_payload,
        scraped_at_dt
    from {{ source('staging', 'raw_discounts') }}
    where spider = 'naranjax'
),

{# Filter out malformed before parsing records #}
valid_structure as (
    select *
    from source
    where
        json_type(json_query(raw_payload, '$.id'))                   is not null
        and json_type(json_query(raw_payload, '$.commerceName'))     is not null
        and json_type(json_query(raw_payload, '$.benefitName'))      is not null
        and json_type(json_query(raw_payload, '$.days'))             is not null
        and json_type(json_query(raw_payload, '$.benefit'))          is not null
        and json_type(json_query(raw_payload, '$.promotionDetails')) is not null
        and json_type(json_query(raw_payload, '$.days.weekdaysApplied')) is not null
        and json_type(json_query(raw_payload, '$.paymentMethods')) is not null

)


select
    json_value(raw_payload, '$.id') as source_id,
    'Naranja X' as issuer_name,

    json_value(raw_payload, '$.commerceName') as merchant_name,
    json_value(raw_payload, '$.category.name') as merchant_category_name,

    -- Date format from API is DD/MM/YYYY
    parse_date('%d/%m/%Y', json_value(raw_payload, '$.days.dateFrom'))
        as discount_start_date,
    parse_date('%d/%m/%Y', json_value(raw_payload, '$.days.dateTo'))
        as discount_end_date,

    {# If discountPercentage is null -> discount_rate = 0 #}
    coalesce(
        round(
            safe_cast(
                json_value(
                    raw_payload, '$.benefit.discountPercentage'
                ) as float64
            )
            / 100,
            4
        ),
        0
    ) as discount_rate,

    json_value(raw_payload, '$.benefitName') as discount_name,
    json_value(raw_payload, '$.subtitle') as discount_description,
    json_value(raw_payload, '$.legal') as discount_terms_and_conditions,
    json_value(raw_payload, '$.discount_url') as discount_url,

    {# If null then no max discount amount -> 0 #}
    coalesce(
        safe_cast(
            nullif(json_value(raw_payload, '$.promotionDetails.refundLimit'), '')
            as float64
        ),
        0 
    ) as discount_max_discount_amount,

    {# If null then no min purchase amount -> 0 #}
    coalesce(
        safe_cast(
            nullif(json_value(raw_payload, '$.promotionDetails.forPurchasesOver'),'')
        as float64),
        0
    ) as discount_min_purchase_amount,

    {# 
        Installment count: extract N from "N cuotas cero/sin interés" in benefitName
        If NULL -> 0 
    #}
    coalesce(
        case
            {# Custom rule for Plan Z discounts, that allow up to 3 installments with no interest #}
            when regexp_contains(
                json_value(raw_payload, '$.benefitName'),
                '(?i)plan z'
            ) then 3
            when regexp_contains(
                    json_value(raw_payload, '$.benefitName'),
                    r'(\d+)\s+cuotas?\s+(?:cero|sin)\s+inter'
                )
                then safe_cast(
                        regexp_extract(
                            json_value(raw_payload, '$.benefitName'),
                            r'(\d+)\s+cuotas?\s+(?:cero|sin)\s+inter'
                        )
                        as int64
                    )
        end,
        0
    ) as discount_no_interest_installment_qty,

    {# weekdaysApplied uses 1=Mon..7=Sun; convert to 0-based (0=Mon..6=Sun) #}
    array(
        select safe_cast(json_value(d, '$') as int64) - 1
        from unnest(json_query_array(raw_payload, '$.days.weekdaysApplied'))
                as d
    ) as discount_valid_days_list,

    coalesce(
        safe_cast(
            json_value(raw_payload, '$.promotionDetails.appliesOnline') as bool
        ),
        false
    ) as discount_valid_online,

    coalesce(
        safe_cast(
            json_value(raw_payload, '$.promotionDetails.appliesInStore') as bool
        ),
        false
    ) or (
        ARRAY_LENGTH(JSON_QUERY_ARRAY(raw_payload, '$.commerces')) > 0
    ) as discount_valid_instore,

    array(
    select json_value(m, '$')
    from unnest(
            {# Coalescing to avoid error from unnest on null value #}
            coalesce(
                json_query_array(raw_payload, '$.paymentMethods'),
                []
            )
        ) as m
    ) as discount_payment_methods_list,

    raw_payload as discount_metadata,
    scraped_at_dt

from valid_structure
