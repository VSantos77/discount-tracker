with source as (

    select
        raw_payload,
        scraped_at_dt
    from {{ source('staging', 'raw_discounts') }}
    where spider = 'naranjax'

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

    -- Exact integer from detail endpoint when available;
    -- otherwise extract first "N%" pattern from title (e.g. "Hasta 25% off" → 0.25)
    coalesce(
        case
            when json_value(
                    raw_payload, '$.benefit.discountPercentage'
                ) is not null
                then round(
                        safe_cast(
                            json_value(
                                raw_payload, '$.benefit.discountPercentage'
                            ) as float64
                        )
                        / 100,
                        4
                    )
        end,
        case
            when regexp_contains(
                    json_value(raw_payload, '$.benefitName'),
                    r'\d+(?:[.,]\d+)?\s*%'
                )
                then round(
                        safe_cast(
                            regexp_extract(
                                json_value(raw_payload, '$.benefitName'),
                                r'(\d+(?:[.,]\d+)?)\s*%'
                            )
                            as float64
                        ) / 100,
                        4
                    )
        end
    ) as discount_rate,

    json_value(raw_payload, '$.benefitName') as discount_name,
    json_value(raw_payload, '$.subtitle') as discount_description,
    json_value(raw_payload, '$.legal') as discount_terms_and_conditions,
    json_value(raw_payload, '$.discount_url') as discount_url,

    safe_cast(
        nullif(json_value(raw_payload, '$.promotionDetails.refundLimit'), '')
        as float64
    ) as discount_max_discount_amount,

    safe_cast(
        nullif(
            json_value(raw_payload, '$.promotionDetails.forPurchasesOver'), ''
        )
        as float64
    ) as discount_min_purchase_amount,

    -- Installment count: extract N from "N cuotas cero/sin interés" in benefitName
    case
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
    end as discount_no_interest_installment_qty,

    -- weekdaysApplied uses 1=Mon..7=Sun; convert to 0-based (0=Mon..6=Sun)
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
    ) as discount_valid_instore,

    raw_payload as discount_metadata,
    scraped_at_dt

from source
