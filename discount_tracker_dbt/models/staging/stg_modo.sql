with source as (

    select
        raw_payload,
        scraped_at
    from {{ source('staging', 'raw_discounts') }}
    where spider_name = 'modo'

),

deduped as (

    select
        raw_payload,
        scraped_at,
        row_number() over (
            partition by coalesce(
                nullif(trim(raw_payload->>'source_id'), ''),
                nullif(trim(raw_payload->>'promo_id'), ''),
                nullif(trim(raw_payload->>'id'), '')
            )
            order by scraped_at desc
        ) as rn
    from source

)

select
    coalesce(
        nullif(trim(raw_payload->>'source_id'), ''),
        nullif(trim(raw_payload->>'promo_id'), ''),
        nullif(trim(raw_payload->>'id'), '')
    )                                                           as source_id,

    -- Issuer: row[5].text holds the bank name (or "Bancos adheridos" for multi-bank)
    trim(raw_payload->'content'->'row'->5->>'text')             as issuer_name,

    -- Merchant: 'where' field, same as row[0].text
    trim(raw_payload->>'where')                                 as merchant_name,

    coalesce(
        nullif(trim(raw_payload->>'merchant_category_name'), ''),
        case coalesce(nullif(trim(raw_payload->>'merchant_category_id'), '')::integer, nullif(raw_payload->'categories_whitelist'->'categories'->0->>'map_category', '')::integer, 0)
            when 1 then 'Supermercados'
            when 2 then 'Gastronomia'
            when 3 then 'Indumentaria'
            when 4 then 'Farmacias, Perfumerias y Peluquerias'
            when 5 then 'Combustibles'
            when 6 then 'Deportes'
            when 7 then 'Hogar'
            when 8 then 'Automoviles'
            when 10 then 'Electro y Tecnologia'
            when 11 then 'Ferreteria y Pinturerias'
            when 12 then 'Mascotas'
            when 13 then 'Jugueterias y Librerias'
            when 14 then 'Entretenimiento'
            else 'Otros'
        end
    )                                                           as merchant_category_name,

    -- Dates are ISO timestamps; cast to date
    (raw_payload->>'start_date')::date                          as discount_start_date,
    (raw_payload->>'stop_date')::date                           as discount_end_date,

    -- Discount rate: extract first number followed by % from row[1].text
    -- e.g. "20% de reintegro" -> 0.2000
    case
        when raw_payload->'content'->'row'->1->>'text' ~ '\d+(?:[.,]\d+)?\s*%'
        then round(
            cast(
                regexp_replace(
                    (regexp_match(
                        raw_payload->'content'->'row'->1->>'text',
                        '(\d+(?:[.,]\d+)?)\s*%'
                    ))[1],
                    ',', '.', 'g'
                ) as numeric
            ) / 100,
            4
        )
        else null
    end                                                         as discount_rate,

    raw_payload->>'title'                                       as discount_name,

    -- row[1].text is the human-readable benefit description
    raw_payload->'content'->'row'->1->>'text'                   as discount_description,
    null::text                                                  as discount_terms_and_conditions,

    -- Canonical promo URL
    'https://www.modo.com.ar/promos/' || (raw_payload->>'slug')::text   as discount_url,

    -- Cap amount: row[4].text; 0 means no cap
    case
        when nullif(trim(raw_payload->'content'->'row'->4->>'text'), '')::numeric > 0
        then nullif(trim(raw_payload->'content'->'row'->4->>'text'), '')::numeric
        else null
    end                                                         as discount_max_discount_amount,

    null::numeric                                               as discount_min_purchase_amount,

    -- Installment qty: extract from row[1].text e.g. "9 cuotas sin interés" -> 9
    case
        when raw_payload->'content'->'row'->1->>'text' ~* '\d+\s+cuotas'
        then (regexp_match(
            raw_payload->'content'->'row'->1->>'text',
            '(\d+)\s+cuotas'
        ))[1]::integer
        else null
    end                                                         as discount_no_interest_installment_qty,

    -- Valid days: days_of_week is a string of single-char codes L M X J V S D (Mon-Sun)
    -- Convert to 0-based integer array [0..6]
    (
        select jsonb_agg(day_num order by day_num)
        from (values
            ('L', 0), ('M', 1), ('X', 2), ('J', 3), ('V', 4), ('S', 5), ('D', 6)
        ) as t(letter, day_num)
        where raw_payload->>'days_of_week' like '%' || letter || '%'
    )                                                           as discount_valid_days_list,

    -- payment_flow: comma-separated flags "instore", "online", "instore_nfc"
    raw_payload->>'payment_flow' like '%online%'                as discount_valid_online,
    raw_payload->>'payment_flow' like '%instore%'               as discount_valid_instore,

    -- Payment method: bank name from row[5]; no card-level detail in listing payload
    jsonb_build_object(
        'bank',      trim(raw_payload->'content'->'row'->5->>'text'),
        'card',      null,
        'card_type', null
    )                                                           as discount_payment_method,

    raw_payload                                                 as discount_metadata,
    scraped_at

from deduped
where rn = 1
