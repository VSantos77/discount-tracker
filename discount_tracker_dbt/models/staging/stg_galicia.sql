with source as (

    select
        raw_payload,
        scraped_at
    from {{ source('staging', 'raw_discounts') }}
    where spider_name = 'galicia'

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
    'Banco Galicia'                                             as issuer_name,

    -- Category promotions use categoria.descripcion; brand promotions use marca.nombre
    case
        when raw_payload->>'tipoPromocion' = 'Categoria'
        then raw_payload->'categoria'->>'descripcion'
        else raw_payload->'marca'->>'nombre'
    end                                                         as merchant_name,

    case
        when raw_payload->>'tipoPromocion' = 'Categoria'
        then raw_payload->'categoria'->>'descripcion'
        else raw_payload->'marca'->'categoria'->>'descripcion'
    end                                                         as merchant_category_name,

    to_date(raw_payload->>'fechaDesde', 'DD/MM/YYYY')           as discount_start_date,
    to_date(raw_payload->>'fechaHasta', 'DD/MM/YYYY')           as discount_end_date,

    -- porcentajeAhorro is a plain number (e.g. 20), normalise to 0..1
    case
        when nullif(trim(raw_payload->>'porcentajeAhorro'), '') is not null
        then round(nullif(trim(raw_payload->>'porcentajeAhorro'), '')::numeric / 100, 4)
        else null
    end                                                         as discount_rate,

    null::text                                                  as discount_name,
    raw_payload->>'descripcionAdicional'                        as discount_description,
    raw_payload->>'legales'                                     as discount_terms_and_conditions,
    null::text                                                  as discount_url,

    nullif(trim(raw_payload->>'topeReintegro'), '')::numeric    as discount_max_discount_amount,
    null::numeric                                               as discount_min_purchase_amount,
    nullif(trim(raw_payload->>'cuotaSinInteresHasta'), '')::integer as discount_no_interest_installment_qty,

    -- diasAplicacion: semicolon-separated day abbreviations e.g. "Lu;Ma;Mi"
    -- Convert to a JSONB array of 0-based weekday integers
    (
        select jsonb_agg(
            case day
                when 'Lu' then 0
                when 'Ma' then 1
                when 'Mi' then 2
                when 'Ju' then 3
                when 'Vi' then 4
                when 'Sa' then 5
                when 'Do' then 6
            end
        )
        from unnest(string_to_array(raw_payload->>'diasAplicacion', ';')) as day
        where day in ('Lu','Ma','Mi','Ju','Vi','Sa','Do')
    )                                                           as discount_valid_days_list,

    (raw_payload->>'tiendaOnline')::boolean                     as discount_valid_online,
    (raw_payload->>'tiendaFisica')::boolean                     as discount_valid_instore,

    jsonb_build_object(
        'card',      raw_payload->'mediosDePago'->>'tarjeta',
        'card_type', raw_payload->'mediosDePago'->>'tipoTarjeta'
    )                                                           as discount_payment_method,

    raw_payload                                                 as discount_metadata,
    scraped_at

from deduped
where rn = 1
