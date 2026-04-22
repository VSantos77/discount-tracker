with source as (

    select
        raw_payload,
        scraped_at_dt
    from {{ source('staging', 'raw_discounts') }}
    where spider = 'bbva'

),

deduped as (

    select
        raw_payload,
        scraped_at_dt,
        row_number() over (
            partition by JSON_VALUE(raw_payload, '$.source_id')
            order by scraped_at_dt desc
        ) as rn
    from source

)

select
    JSON_VALUE(raw_payload, '$.source_id')                          as source_id,
    'Banco BBVA'                                                     as issuer_name,

    -- Merchant name: strip trailing discount/installment annotation from cabecera
    -- e.g. "Starbucks 20% de descuento" -> "Starbucks"
    TRIM(REGEXP_REPLACE(
        JSON_VALUE(raw_payload, '$.cabecera'),
        r'(?i)\s+\d+(?:[.,]\d+)?\s*(?:%|cuotas).*$',
        ''
    ))                                                               as merchant_name,

    JSON_VALUE(raw_payload, '$.category_name')                      as merchant_category_name,

    -- Dates stored as YYYY-MM-DD
    PARSE_DATE('%Y-%m-%d', JSON_VALUE(raw_payload, '$.discount_start_date'))  as discount_start_date,
    PARSE_DATE('%Y-%m-%d', JSON_VALUE(raw_payload, '$.discount_end_date'))    as discount_end_date,

    -- Discount rate: extract first number followed by % from cabecera, fall back to subcabecera
    case
        when REGEXP_CONTAINS(JSON_VALUE(raw_payload, '$.cabecera'), r'\d+(?:[.,]\d+)?\s*%')
        then ROUND(
            SAFE_CAST(
                REGEXP_REPLACE(
                    REGEXP_EXTRACT(JSON_VALUE(raw_payload, '$.cabecera'), r'(\d+(?:[.,]\d+)?)\s*%'),
                    r',', '.'
                ) AS FLOAT64
            ) / 100,
            4
        )
        when REGEXP_CONTAINS(JSON_VALUE(raw_payload, '$.subcabecera'), r'\d+(?:[.,]\d+)?\s*%')
        then ROUND(
            SAFE_CAST(
                REGEXP_REPLACE(
                    REGEXP_EXTRACT(JSON_VALUE(raw_payload, '$.subcabecera'), r'(\d+(?:[.,]\d+)?)\s*%'),
                    r',', '.'
                ) AS FLOAT64
            ) / 100,
            4
        )
        else null
    end                                                              as discount_rate,

    JSON_VALUE(raw_payload, '$.cabecera')                           as discount_name,
    JSON_VALUE(raw_payload, '$.subcabecera')                        as discount_description,
    JSON_VALUE(raw_payload, '$.basesCondiciones')                   as discount_terms_and_conditions,
    CAST(NULL AS STRING)                                             as discount_url,

    -- Max discount amount from first beneficio entry
    case
        when ARRAY_LENGTH(JSON_QUERY_ARRAY(raw_payload, '$.beneficios')) > 0
        then SAFE_CAST(NULLIF(TRIM(JSON_VALUE(raw_payload, '$.beneficios[0].tope')), '') AS FLOAT64)
        else null
    end                                                              as discount_max_discount_amount,

    -- Min purchase amount: extract from basesCondiciones
    -- Patterns: "superiores a $50.000" (. as thousands sep) or "mayores a $35000" (no sep)
    -- Removes dots used as thousands separators (RE2 does not support lookaheads)
    case
        when REGEXP_CONTAINS(JSON_VALUE(raw_payload, '$.basesCondiciones'), r'(?i)(?:superiores?|mayores?)\s+a\s+\$\s*[\d.,]+')
        then SAFE_CAST(
                REGEXP_REPLACE(
                    REGEXP_EXTRACT(
                        JSON_VALUE(raw_payload, '$.basesCondiciones'),
                        r'(?i)(?:superiores?|mayores?)\s+a\s+\$\s*([\d.,]+)'
                    ),
                    r'\.', ''
                ) AS FLOAT64
             )
        else null
    end                                                              as discount_min_purchase_amount,

    case
        when ARRAY_LENGTH(JSON_QUERY_ARRAY(raw_payload, '$.beneficios')) > 0
        then SAFE_CAST(JSON_VALUE(raw_payload, '$.beneficios[0].cuota') AS INT64)
        else null
    end                                                              as discount_no_interest_installment_qty,

    -- Valid days: diasPromo is a 7-element comma-separated string of 0/1 flags (Mon-Sun)
    -- Convert to a JSON array string of 0-based weekday integers where flag = '1'
    -- If diasPromo is null, treat as valid all days (0-6)
    case
        when JSON_VALUE(raw_payload, '$.diasPromo') is null
        then '[0,1,2,3,4,5,6]'
        else (
            select CONCAT('[', IFNULL(STRING_AGG(CAST(offset AS STRING), ',' ORDER BY offset), ''), ']')
            from UNNEST(SPLIT(JSON_VALUE(raw_payload, '$.diasPromo'), ',')) AS flag WITH OFFSET AS offset
            where flag = '1'
        )
    end                                                              as discount_valid_days_list,

    -- canalesVenta arrays: non-empty means valid for that channel
    ARRAY_LENGTH(JSON_QUERY_ARRAY(raw_payload, '$.canalesVenta.web')) > 0        as discount_valid_online,
    ARRAY_LENGTH(JSON_QUERY_ARRAY(raw_payload, '$.canalesVenta.sucursales')) > 0 as discount_valid_instore,

    -- BBVA always credit; grupoTarjeta does not expose card-level detail
    PARSE_JSON('{"card": "all", "card_type": "credito"}')           as discount_payment_method,

    raw_payload                                                      as discount_metadata,
    scraped_at_dt

from deduped
where rn = 1
