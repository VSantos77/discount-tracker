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
        when 'lunes'                 then '[0]'::jsonb
        when 'martes'                then '[1]'::jsonb
        when 'miércoles'             then '[2]'::jsonb
        when 'miercoles'             then '[2]'::jsonb
        when 'jueves'                then '[3]'::jsonb
        when 'viernes'               then '[4]'::jsonb
        when 'sábado'                then '[5]'::jsonb
        when 'sabado'                then '[5]'::jsonb
        when 'sábados'               then '[5]'::jsonb
        when 'sabados'               then '[5]'::jsonb
        when 'domingo'               then '[6]'::jsonb
        when 'lunes y martes'        then '[0,1]'::jsonb
        when 'martes y miércoles'    then '[1,2]'::jsonb
        when 'martes y miercoles'    then '[1,2]'::jsonb
        when 'miércoles y jueves'    then '[2,3]'::jsonb
        when 'miercoles y jueves'    then '[2,3]'::jsonb
        when 'sábados y domingos'    then '[5,6]'::jsonb
        when 'sabados y domingos'    then '[5,6]'::jsonb
        when 'fines de semana'       then '[5,6]'::jsonb
        when 'de lunes a jueves'     then '[0,1,2,3]'::jsonb
        when 'lunes a viernes'       then '[0,1,2,3,4]'::jsonb
        when 'lunes a sábado'        then '[0,1,2,3,4,5]'::jsonb
        when 'lunes a sabado'        then '[0,1,2,3,4,5]'::jsonb
        when 'todos los días'        then '[0,1,2,3,4,5,6]'::jsonb
        when 'todos los dias'        then '[0,1,2,3,4,5,6]'::jsonb
        else null
    end                                                                     as discount_valid_days_list,
    false                                                                   as discount_valid_online,
    true                                                                    as discount_valid_instore,
    jsonb_build_object(
        'card',      'Cuenta DNI',
        'card_type', 'digital_wallet'
    )                                                                       as discount_payment_method,
    raw_payload                                                             as discount_metadata,
    scraped_at
from deduped
where rn = 1
