with source as (

    select
        raw_payload,
        scraped_at_dt
    from {{ source('staging', 'raw_discounts') }}
    where spider = 'galicia'

)

select
    JSON_VALUE(raw_payload, '$.source_id')                                      as source_id,
    'Banco Galicia'                                                             as issuer_name,

    -- Category promotions use categoria.descripcion; brand promotions use marca.nombre
    case
        when JSON_VALUE(raw_payload, '$.tipoPromocion') = 'Categoria'
        then JSON_VALUE(raw_payload, '$.categoria.descripcion')
        else JSON_VALUE(raw_payload, '$.marca.nombre')
    end                                                                         as merchant_name,

    case
        when JSON_VALUE(raw_payload, '$.tipoPromocion') = 'Categoria'
        then JSON_VALUE(raw_payload, '$.categoria.descripcion')
        else JSON_VALUE(raw_payload, '$.marca.categoria.descripcion')
    end                                                                         as merchant_category_name,

    PARSE_DATE('%d/%m/%Y', JSON_VALUE(raw_payload, '$.fechaDesde'))             as discount_start_date,
    PARSE_DATE('%d/%m/%Y', JSON_VALUE(raw_payload, '$.fechaHasta'))             as discount_end_date,

    -- porcentajeAhorro is a plain number (e.g. 20), normalise to 0..1
    case
        when NULLIF(TRIM(JSON_VALUE(raw_payload, '$.porcentajeAhorro')), '') is not null
        then ROUND(
            SAFE_CAST(NULLIF(TRIM(JSON_VALUE(raw_payload, '$.porcentajeAhorro')), '') AS NUMERIC) / 100,
            4
        )
        else null
    end                                                                         as discount_rate,

    CAST(NULL AS STRING)                                                        as discount_name,
    JSON_VALUE(raw_payload, '$.descripcionAdicional')                           as discount_description,
    JSON_VALUE(raw_payload, '$.legales')                                        as discount_terms_and_conditions,
    CAST(NULL AS STRING)                                                        as discount_url,

    SAFE_CAST(NULLIF(TRIM(JSON_VALUE(raw_payload, '$.topeReintegro')), '') AS NUMERIC)      as discount_max_discount_amount,
    CAST(NULL AS FLOAT64)                                                       as discount_min_purchase_amount,
    SAFE_CAST(NULLIF(TRIM(JSON_VALUE(raw_payload, '$.cuotaSinInteresHasta')), '') AS INT64) as discount_no_interest_installment_qty,

    -- diasAplicacion: semicolon-separated day abbreviations e.g. "Lu;Ma;Mi"
    -- Convert to a JSON array of 0-based weekday integers
    TO_JSON_STRING(
        ARRAY(
            select
                case day
                    when 'Lu' then 0
                    when 'Ma' then 1
                    when 'Mi' then 2
                    when 'Ju' then 3
                    when 'Vi' then 4
                    when 'Sa' then 5
                    when 'Do' then 6
                end
            from UNNEST(SPLIT(COALESCE(JSON_VALUE(raw_payload, '$.diasAplicacion'), ''), ';')) as day
            where day in ('Lu','Ma','Mi','Ju','Vi','Sa','Do')
        )
    )                                                                           as discount_valid_days_list,

    SAFE_CAST(JSON_VALUE(raw_payload, '$.tiendaOnline') AS BOOL)                as discount_valid_online,
    SAFE_CAST(JSON_VALUE(raw_payload, '$.tiendaFisica') AS BOOL)                as discount_valid_instore,

    raw_payload                                                                 as discount_metadata,
    scraped_at_dt

from source
