with source as (
    select raw_payload, scraped_at
    from {{ source('staging', 'raw_discounts') }}
    where spider_name = 'cuentadni'
),
deduped as (
    select raw_payload, scraped_at,
        row_number() over (
            partition by raw_payload->>'source_id'
            order by scraped_at desc
        ) as rn
    from source
)
select
    raw_payload->>'source_id'                                               as source_id,
    'Cuenta DNI'                                                       as issuer_name,
    initcap(raw_payload->'Entity'->'Beneficio'->>'url')                     as merchant_name,
    raw_payload->'Entity'->'Rubros'->0->>'nombre'                           as merchant_category_name,
    -- /Date(ms)/ .NET epoch format → date
    to_timestamp(
        (regexp_match(
            raw_payload->'Entity'->'Beneficio'->>'fecha_desde',
            '/Date\((\d+)\)/'
        ))[1]::bigint / 1000
    )::date                                                                 as discount_start_date,
    to_timestamp(
        (regexp_match(
            raw_payload->'Entity'->'Beneficio'->>'fecha_hasta',
            '/Date\((\d+)\)/'
        ))[1]::bigint / 1000
    )::date                                                                 as discount_end_date,
    round(
        (raw_payload->'Entity'->'Beneficio'->>'porcentaje')::numeric / 100,
        4
    )                                                                       as discount_rate,
    raw_payload->'Entity'->'Beneficio'->>'titulo'                           as discount_name,
    coalesce(
        nullif(trim(raw_payload->'Entity'->'Beneficio'->>'subtitulo'), ''),
        nullif(trim(raw_payload->'Entity'->'Beneficio'->>'bajada'), '')
    )                                                                       as discount_description,
    raw_payload->'Entity'->'Beneficio'->>'legal'                            as discount_terms_and_conditions,
    nullif(trim(raw_payload->'Entity'->'Beneficio'->>'urlPagina'), '')      as discount_url,
    -- extract first $N.NNN amount from bajada (tope de reintegro)
    case
        when raw_payload->'Entity'->'Beneficio'->>'bajada' ~ '\$[\s]?[\d.,]+'
        then replace(
            (regexp_match(
                raw_payload->'Entity'->'Beneficio'->>'bajada',
                '\$[\s]?([\d.]+(?:,\d+)?)'
            ))[1],
            '.', ''
        )::numeric
        else null
    end                                                                     as discount_max_discount_amount,
    null::numeric                                                           as discount_min_purchase_amount,
    null::integer                                                           as discount_no_interest_installment_qty,
    -- titulo_fecha → day index array (0=Mon … 6=Sun); null for unrecognised patterns
    case lower(trim(raw_payload->'Entity'->'Beneficio'->>'titulo_fecha'))
        when 'lunes'                 then ARRAY[0]
        when 'martes'                then ARRAY[1]
        when 'miércoles'             then ARRAY[2]
        when 'miercoles'             then ARRAY[2]
        when 'jueves'                then ARRAY[3]
        when 'viernes'               then ARRAY[4]
        when 'sábado'                then ARRAY[5]
        when 'sabado'                then ARRAY[5]
        when 'sábados'               then ARRAY[5]
        when 'sabados'               then ARRAY[5]
        when 'domingo'               then ARRAY[6]
        when 'lunes y martes'        then ARRAY[0,1]
        when 'martes y miércoles'    then ARRAY[1,2]
        when 'martes y miercoles'    then ARRAY[1,2]
        when 'miércoles y jueves'    then ARRAY[2,3]
        when 'miercoles y jueves'    then ARRAY[2,3]
        when 'sábados y domingos'    then ARRAY[5,6]
        when 'sabados y domingos'    then ARRAY[5,6]
        when 'fines de semana'       then ARRAY[5,6]
        when 'de lunes a jueves'     then ARRAY[0,1,2,3]
        when 'lunes a viernes'       then ARRAY[0,1,2,3,4]
        when 'lunes a sábado'        then ARRAY[0,1,2,3,4,5]
        when 'lunes a sabado'        then ARRAY[0,1,2,3,4,5]
        when 'todos los días'        then ARRAY[0,1,2,3,4,5,6]
        when 'todos los dias'        then ARRAY[0,1,2,3,4,5,6]
        else null
    end                                                                     as discount_valid_days_list,
    false                                                                   as discount_valid_online,
    true                                                                    as discount_valid_instore,
    raw_payload                                                             as discount_metadata,
    scraped_at
from deduped
where rn = 1
