with source as (

    select
        raw_payload,
        scraped_at_dt
    from {{ source('staging', 'raw_discounts') }}
    where spider = 'naranjax'

),

-- Each catalog item may carry multiple plans (multi-plan merchants, urlDetail=null)
-- or a single plan (merchants where urlDetail was set and the detail endpoint was
-- fetched). Cross-joining unnests them uniformly; the nested $.detail object is only
-- populated for single-plan items and enriches the numeric fields when present.
unnested as (

    select
        raw_payload,
        scraped_at_dt,
        plan,
        plan_offset
    from source
    cross join UNNEST(JSON_QUERY_ARRAY(raw_payload, '$.plans')) as plan WITH OFFSET as plan_offset

)

select
    -- Composite key: catalog UUID + plan index keeps each plan row unique across runs
    CONCAT(JSON_VALUE(raw_payload, '$.id'), '_', CAST(plan_offset AS STRING))    as source_id,
    'Naranja X'                                                                   as issuer_name,

    JSON_VALUE(raw_payload, '$.commerceName')                                     as merchant_name,
    JSON_VALUE(raw_payload, '$.category.name')                                    as merchant_category_name,

    -- Date format from API is DD/MM/YYYY
    PARSE_DATE('%d/%m/%Y', JSON_VALUE(plan, '$.days.dateFrom'))                   as discount_start_date,
    PARSE_DATE('%d/%m/%Y', JSON_VALUE(plan, '$.days.dateTo'))                     as discount_end_date,

    -- Exact integer from detail endpoint when available;
    -- otherwise extract first "N%" pattern from title (e.g. "Hasta 25% off" → 0.25)
    COALESCE(
        CASE
            WHEN JSON_VALUE(raw_payload, '$.detail.benefit.discountPercentage') IS NOT NULL
            THEN ROUND(
                SAFE_CAST(JSON_VALUE(raw_payload, '$.detail.benefit.discountPercentage') AS FLOAT64) / 100,
                4
            )
        END,
        CASE
            WHEN REGEXP_CONTAINS(JSON_VALUE(raw_payload, '$.title'), r'\d+(?:[.,]\d+)?\s*%')
            THEN ROUND(
                SAFE_CAST(
                    REGEXP_EXTRACT(JSON_VALUE(raw_payload, '$.title'), r'(\d+(?:[.,]\d+)?)\s*%')
                    AS FLOAT64
                ) / 100,
                4
            )
        END
    )                                                                              as discount_rate,

    JSON_VALUE(raw_payload, '$.title')                                             as discount_name,
    JSON_VALUE(raw_payload, '$.subtitle')                                          as discount_description,
    -- Legal text is only available from the detail endpoint (single-plan items)
    JSON_VALUE(raw_payload, '$.detail.legal')                                      as discount_terms_and_conditions,
    JSON_VALUE(raw_payload, '$.fullUrl')                                            as discount_url,

    -- refundLimit from detail endpoint is already a numeric string (e.g. "8000");
    -- fallback: parse peso amount from the refund tag (e.g. "$ 8.000" → 8000)
    COALESCE(
        SAFE_CAST(JSON_VALUE(raw_payload, '$.detail.promotionDetails.refundLimit') AS FLOAT64),
        (
            select SAFE_CAST(
                REGEXP_REPLACE(
                    REGEXP_EXTRACT(JSON_VALUE(tag, '$.description'), r'\$\s*([\d.]+)'),
                    r'\.', ''
                ) AS FLOAT64
            )
            from UNNEST(JSON_QUERY_ARRAY(raw_payload, '$.tags')) as tag
            where JSON_VALUE(tag, '$.type') = 'refund'
              and REGEXP_CONTAINS(JSON_VALUE(tag, '$.description'), r'\$')
            limit 1
        )
    )                                                                              as discount_max_discount_amount,

    -- forPurchasesOver is only present in the detail endpoint
    SAFE_CAST(
        NULLIF(JSON_VALUE(raw_payload, '$.detail.promotionDetails.forPurchasesOver'), '')
        AS FLOAT64
    )                                                                              as discount_min_purchase_amount,

    -- Installment count: extract N from "N cuotas cero/sin interés" in title
    case
        when REGEXP_CONTAINS(JSON_VALUE(raw_payload, '$.title'), r'(\d+)\s+cuotas?\s+(?:cero|sin)\s+inter')
        then SAFE_CAST(
            REGEXP_EXTRACT(JSON_VALUE(raw_payload, '$.title'), r'(\d+)\s+cuotas?\s+(?:cero|sin)\s+inter')
            AS INT64
        )
        else null
    end                                                                            as discount_no_interest_installment_qty,

    -- weekdaysApplied uses 1=Mon..7=Sun; convert to 0-based (0=Mon..6=Sun)
    ARRAY(
        select SAFE_CAST(JSON_VALUE(d, '$') AS INT64) - 1
        from UNNEST(JSON_QUERY_ARRAY(plan, '$.days.weekdaysApplied')) as d
    )                                                                              as discount_valid_days_list,

    -- Detail endpoint has explicit separate booleans for online and in-store;
    -- catalog plan only has appliesOnline (null → default false / treat as instore)
    COALESCE(
        SAFE_CAST(JSON_VALUE(raw_payload, '$.detail.promotionDetails.appliesOnline') AS BOOL),
        SAFE_CAST(JSON_VALUE(plan, '$.promotionDetails.appliesOnline') AS BOOL),
        false
    )                                                                              as discount_valid_online,

    COALESCE(
        SAFE_CAST(JSON_VALUE(raw_payload, '$.detail.promotionDetails.appliesInStore') AS BOOL),
        NOT COALESCE(SAFE_CAST(JSON_VALUE(plan, '$.promotionDetails.appliesOnline') AS BOOL), false)
    )                                                                              as discount_valid_instore,

    raw_payload                                                                    as discount_metadata,
    scraped_at_dt

from unnested
