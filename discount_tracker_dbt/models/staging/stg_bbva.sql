with source as (

    select
        raw_payload,
        scraped_at_dt
    from {{ source('staging', 'raw_discounts') }}
    where spider = 'bbva'

)

select
    json_value(raw_payload, '$.source_id') as source_id,
    'Banco BBVA' as issuer_name,

    -- Merchant name: strip trailing discount/installment/benefit annotations from cabecera
    -- e.g. "Starbucks 20% de descuento" -> "Starbucks"
    -- e.g. "Pasion Beneficio exclusivo MODO" -> "Pasion"
    trim(regexp_replace(
        json_value(raw_payload, '$.cabecera'),
        r'(?i)\s+(?:\d+(?:[.,]\d+)?\s*(?:%|cuotas)|Beneficio|descuento|exclusivo).*$',
        ''
    )) as merchant_name,

    json_value(raw_payload, '$.category_name') as merchant_category_name,

    -- Dates stored as YYYY-MM-DD
    parse_date('%Y-%m-%d', json_value(raw_payload, '$.discount_start_date'))
        as discount_start_date,
    parse_date('%Y-%m-%d', json_value(raw_payload, '$.discount_end_date'))
        as discount_end_date,

    {# 
        Discount rate: extract first number followed by % from cabecera, fall back to subcabecera
        If null: discount rate = 0 
    #}
    coalesce(
        case
            when regexp_contains(
                    json_value(raw_payload, '$.cabecera'), r'\d+(?:[.,]\d+)?\s*%'
                )
                then round(
                        safe_cast(
                            regexp_replace(
                                regexp_extract(
                                    json_value(raw_payload, '$.cabecera'),
                                    r'(\d+(?:[.,]\d+)?)\s*%'
                                ),
                                r',', '.'
                            ) as float64
                        ) / 100,
                        4
                    )
            when regexp_contains(
                    json_value(raw_payload, '$.subcabecera'), r'\d+(?:[.,]\d+)?\s*%'
                )
                then round(
                        safe_cast(
                            regexp_replace(
                                regexp_extract(
                                    json_value(raw_payload, '$.subcabecera'),
                                    r'(\d+(?:[.,]\d+)?)\s*%'
                                ),
                                r',', '.'
                            ) as float64
                        ) / 100,
                        4
                    )
            -- Fallback: extract from terms and conditions, e.g. "20% de reintegro", "30% de descuento"
            when regexp_contains(
                    json_value(raw_payload, '$.basesCondiciones'),
                    r'(?i)\d+(?:[.,]\d+)?\s*%\s*de\s*(?:reintegro|descuento)'
                )
                then round(
                        safe_cast(
                            regexp_replace(
                                regexp_extract(
                                    json_value(raw_payload, '$.basesCondiciones'),
                                    r'(?i)(\d+(?:[.,]\d+)?)\s*%\s*de\s*(?:reintegro|descuento)'
                                ),
                                r',', '.'
                            ) as float64
                        ) / 100,
                        4
                    )
            -- Fallback: first % match in beneficios[0].requisitos, e.g. "30% Jueves en pases"
            -- CAST to STRING required because JSON_QUERY returns JSON type; requisitos is an array so JSON_VALUE would return null
            when regexp_contains(
                    to_json_string(
                        json_query(raw_payload, '$.beneficios[0].requisitos')
                    ),
                    r'\d+(?:[.,]\d+)?\s*%'
                )
                then round(
                        safe_cast(
                            regexp_replace(
                                regexp_extract(
                                    to_json_string(
                                        json_query(
                                            raw_payload,
                                            '$.beneficios[0].requisitos'
                                        )
                                    ),
                                    r'(\d+(?:[.,]\d+)?)\s*%'
                                ),
                                r',', '.'
                            ) as float64
                        ) / 100,
                        4
                    )
        end,
        0
    ) as discount_rate,

    json_value(raw_payload, '$.cabecera') as discount_name,
    json_value(raw_payload, '$.subcabecera') as discount_description,
    json_value(raw_payload, '$.basesCondiciones')
        as discount_terms_and_conditions,
    concat(
        'https://www.bbva.com.ar/beneficios/beneficio.html?id=',
        json_value(raw_payload, '$.source_id')
    ) as discount_url,

    {# Null means 0 max discount amount #}
    coalesce(
        case
        when array_length(json_query_array(raw_payload, '$.beneficios')) > 0
            then safe_cast(
                    nullif(
                        trim(json_value(raw_payload, '$.beneficios[0].tope')),
                        ''
                    ) as float64
                )
        end,
        0 
    ) as discount_max_discount_amount,

    -- Min purchase amount: extract from basesCondiciones
    -- Patterns: "superiores a $50.000" (. as thousands sep) or "mayores a $35000" (no sep)
    -- Removes dots used as thousands separators (RE2 does not support lookaheads)
    coalesce(
        case
        when regexp_contains(
                json_value(raw_payload, '$.basesCondiciones'),
                r'(?i)(?:superiores?|mayores?)\s+a\s+\$\s*[\d.,]+'
            )
            then safe_cast(
                    regexp_replace(
                        regexp_extract(
                            json_value(raw_payload, '$.basesCondiciones'),
                            r'(?i)(?:superiores?|mayores?)\s+a\s+\$\s*([\d.,]+)'
                        ),
                        r'\.', ''
                    ) as float64
                )
        end,
        0
    ) as discount_min_purchase_amount,

    {# greatest to handle odd cases where installment qty is -1 #}
    greatest(
        case
        when array_length(json_query_array(raw_payload, '$.beneficios')) > 0
            then safe_cast(
                    json_value(raw_payload, '$.beneficios[0].cuota') as int64
                )
        end,
        0
    ) as discount_no_interest_installment_qty,

    -- Valid days: diasPromo is a 7-element comma-separated string of 0/1 flags (Mon-Sun)
    -- Convert to a 0-based integer array where flag = '1'
    -- If diasPromo is null, treat as valid all days (0-6)
    case
        when json_value(raw_payload, '$.diasPromo') is null
            then [0, 1, 2, 3, 4, 5, 6]
        else array(
                select cast(offset as int64)
                from unnest(
                        split(json_value(raw_payload, '$.diasPromo'), ',')
                    ) as flag with offset as offset
                where flag = '1'
            )
    end as discount_valid_days_list,

    {# 
        If discount is via MODO, then it is only valid instore. 
        Otherwise, check canalesVenta array length. 
    #}
    if(
        coalesce(safe_cast(json_value(raw_payload, '$.esModo') as bool),false),
        false,
        array_length(json_query_array(raw_payload, '$.canalesVenta.web')) > 0 
    ) as discount_valid_online,

    if(
        coalesce(safe_cast(json_value(raw_payload, '$.esModo') as bool),false),
        true,
        array_length(json_query_array(raw_payload, '$.canalesVenta.sucursales')) > 0
    ) as discount_valid_instore,

    {#
        grupoTarjeta always contains a non-null, non-empty scalar value. 
        In the event that happens, return empty array so tests fail.
    #}
    case
        when json_value(raw_payload, '$.grupoTarjeta') is not null
            and json_value(raw_payload, '$.grupoTarjeta') != ''
            {# parsed value is a scalar. Converting to singled value array for consistency #}
            then [json_value(raw_payload, '$.grupoTarjeta')]
        else []
    end as discount_payment_methods_list,

    raw_payload as discount_metadata,
    scraped_at_dt

from source
