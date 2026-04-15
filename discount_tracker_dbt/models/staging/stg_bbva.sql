with source as (

    select
        raw_payload,
        scraped_at
    from {{ source('staging', 'raw_discounts') }}
    where spider_name = 'bbva'

),

deduped as (

    select
        raw_payload,
        scraped_at,
        row_number() over (
            partition by raw_payload->>'source_id'
            order by scraped_at desc
        ) as rn
    from source

)

select
    raw_payload->>'source_id'                                   as source_id,
    'Banco BBVA'                                                as issuer_name,

    -- Merchant name: strip trailing discount/installment annotation from cabecera
    -- e.g. "Starbucks 20% de descuento" -> "Starbucks"
    trim(regexp_replace(
        raw_payload->>'cabecera',
        '\s+\d+(?:[.,]\d+)?\s*(?:%|cuotas).*$',
        '',
        'i'
    ))                                                          as merchant_name,

    raw_payload->>'category_name'                               as merchant_category_name,

    -- Dates stored as DD/MM/YYYY in catalog_start_date / catalog_end_date
    to_date(raw_payload->>'discount_start_date', 'YYYY-MM-DD')   as discount_start_date,
    to_date(raw_payload->>'discount_end_date',   'YYYY-MM-DD')   as discount_end_date,

    -- Discount rate: extract first number followed by % from cabecera, fall back to subcabecera
    case
        when raw_payload->>'cabecera' ~ '\d+(?:[.,]\d+)?\s*%'
        then round(
            cast(
                regexp_replace(
                    (regexp_match(raw_payload->>'cabecera', '(\d+(?:[.,]\d+)?)\s*%'))[1],
                    ',', '.', 'g'
                ) as numeric
            ) / 100,
            4
        )
        when raw_payload->>'subcabecera' ~ '\d+(?:[.,]\d+)?\s*%'
        then round(
            cast(
                regexp_replace(
                    (regexp_match(raw_payload->>'subcabecera', '(\d+(?:[.,]\d+)?)\s*%'))[1],
                    ',', '.', 'g'
                ) as numeric
            ) / 100,
            4
        )
        else null
    end                                                         as discount_rate,

    raw_payload->>'cabecera'                                    as discount_name,
    raw_payload->>'subcabecera'                                 as discount_description,
    raw_payload->>'basesCondiciones'                            as discount_terms_and_conditions,
    null::text                                                  as discount_url,

    -- Max discount amount and installments from first beneficio entry
    case
        when jsonb_array_length(raw_payload->'beneficios') > 0
        then nullif(trim(raw_payload->'beneficios'->0->>'tope'), '')::numeric
        else null
    end                                                         as discount_max_discount_amount,

    -- Min purchase amount: extract from basesCondiciones
    -- Patterns: "superiores a $50.000" (. as thousands sep) or "mayores a $35000" (no sep)
    -- Strips . only when used as thousands separator (digit groups of 3)
    case
        when raw_payload->>'basesCondiciones' ~* '(?:superiores?|mayores?)\s+a\s+\$\s*[\d.,]+'
        then regexp_replace(
                (regexp_match(
                    raw_payload->>'basesCondiciones',
                    '(?:superiores?|mayores?)\s+a\s+\$\s*([\d.,]+)',
                    'i'
                ))[1],
                '\.(?=\d{3}(?:[.,]|$))', '', 'g'
             )::numeric
        else null
    end                                                         as discount_min_purchase_amount,

    case
        when jsonb_array_length(raw_payload->'beneficios') > 0
        then (raw_payload->'beneficios'->0->>'cuota')::integer
        else null
    end                                                         as discount_no_interest_installment_qty,

    -- Valid days: diasPromo is a 7-element comma-separated string of 0/1 flags (Mon-Sun)
    -- Convert to a JSONB array of 0-based weekday integers where flag = '1'
    -- If diasPromo is null, treat as valid all days (0-6)
    case
        when raw_payload->>'diasPromo' is null
        then '[0,1,2,3,4,5,6]'::jsonb
        else (
            select jsonb_agg(idx - 1)
            from regexp_split_to_table(raw_payload->>'diasPromo', ',') with ordinality as t(flag, idx)
            where flag = '1'
        )
    end                                                         as discount_valid_days_list,

    -- canalesVenta arrays: non-empty means valid for that channel
    jsonb_array_length(raw_payload->'canalesVenta'->'web') > 0          as discount_valid_online,
    jsonb_array_length(raw_payload->'canalesVenta'->'sucursales') > 0   as discount_valid_instore,

    -- BBVA always credit; grupoTarjeta does not expose card-level detail
    jsonb_build_object('card', 'all', 'card_type', 'credito')   as discount_payment_method,

    raw_payload                                                 as discount_metadata,
    scraped_at

from deduped
where rn = 1
