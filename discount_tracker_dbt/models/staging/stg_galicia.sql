with source as (

    select
        raw_payload,
        scraped_at_dt
    from {{ source('staging', 'raw_discounts') }}
    where spider = 'galicia'

)

select
    json_value(raw_payload, '$.source_id') as source_id,
    'Banco Galicia' as issuer_name,

    -- Category promotions use categoria.descripcion; brand promotions use marca.nombre
    case
        when json_value(raw_payload, '$.tipoPromocion') = 'Categoria'
            then json_value(raw_payload, '$.categoria.descripcion')
        else json_value(raw_payload, '$.marca.nombre')
    end as merchant_name,

    case
        when json_value(raw_payload, '$.tipoPromocion') = 'Categoria'
            then json_value(raw_payload, '$.categoria.descripcion')
        else json_value(raw_payload, '$.marca.categoria.descripcion')
    end as merchant_category_name,

    parse_date('%d/%m/%Y', json_value(raw_payload, '$.fechaDesde'))
        as discount_start_date,
    parse_date('%d/%m/%Y', json_value(raw_payload, '$.fechaHasta'))
        as discount_end_date,

    -- porcentajeAhorro is a plain number (e.g. 20), normalise to 0..1
    case
        when nullif(
                trim(json_value(raw_payload, '$.porcentajeAhorro')), ''
            ) is not null
            then round(
                    safe_cast(
                        nullif(
                            trim(json_value(raw_payload, '$.porcentajeAhorro')),
                            ''
                        ) as numeric
                    )
                    / 100,
                    4
                )
    end as discount_rate,

    cast(null as string) as discount_name,
    json_value(raw_payload, '$.descripcionAdicional') as discount_description,
    json_value(raw_payload, '$.legales') as discount_terms_and_conditions,
    {#  Creates shareable url based on source id, tipoPromocion and merchant name / category name #}
    concat(
        'https://galicia.ar/personas/buscador-de-promociones?path=/promocion/',
        json_value(raw_payload, '$.source_id'), '|',
        if(
            json_value(raw_payload, '$.tipoPromocion') = 'Categoria',
            concat(
                json_value(raw_payload, '$.categoria.descripcion'),
                '|categoria|'
            ),
            concat(json_value(raw_payload, '$.marca.nombre'), '|marca|')
        )
    ) as discount_url,

    safe_cast(
        nullif(trim(json_value(raw_payload, '$.topeReintegro')), '') as numeric
    ) as discount_max_discount_amount,
    coalesce(
        safe_cast(
        nullif(trim(json_value(raw_payload, '$.minimoCompra')), '') as numeric
        ),
        0
    ) as discount_min_purchase_amount,
    
    {# If null -> 0 #}
    coalesce(
        safe_cast(
        nullif(
            trim(json_value(raw_payload, '$.cuotaSinInteresHasta')), ''
        ) as int64
        ),
        0 
    ) as discount_no_interest_installment_qty,

    {#  
        diasAplicacion: semicolon-separated day abbreviations e.g. "Lu;Ma;Mi"
        Convert to a 0-based integer array 
    #}
    array(
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
        from unnest(
                split(
                    coalesce(json_value(raw_payload, '$.diasAplicacion'), ''),
                    ';'
                )
            ) as day
        where day in ('Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do')
    ) as discount_valid_days_list,

    safe_cast(json_value(raw_payload, '$.tiendaOnline') as bool)
        as discount_valid_online,
    (
        safe_cast(json_value(raw_payload, '$.tiendaFisica') as bool)
        {# Fallback to searching for 'comercios adheridos' in discount description #}
        or regexp_contains(json_value(raw_payload,'$.leyendaCompra'), '(?i)comercios adheridos')  
    ) as discount_valid_instore,

    raw_payload as discount_metadata,
    scraped_at_dt

from source
