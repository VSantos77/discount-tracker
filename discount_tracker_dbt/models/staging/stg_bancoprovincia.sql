with source as (
    select raw_payload, scraped_at
    from {{ source('staging', 'raw_discounts') }}
    where spider_name = 'bancoprovincia'
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
    'Banco Provincia'                                                       as issuer_name,
    -- strip leading "En " prefix from merchant_text (e.g. "En Authogar y Santa Ola")
    nullif(trim(regexp_replace(raw_payload->>'merchant_text', '^En\s+', '', 'i')), '')  as merchant_name,
    -- category derived from the URL slug (best available category signal)
    nullif(trim(raw_payload->>'category_slug'), '')                         as merchant_category_name,
    -- date range: attempt to extract DD/MM/YYYY or "D de month de YYYY" patterns
    -- start date
    case
        when raw_payload->>'date_text' ~ '\d{1,2}/\d{1,2}/\d{4}'
        then to_date(
            (regexp_match(raw_payload->>'date_text', '(\d{1,2}/\d{1,2}/\d{4})'))[1],
            'DD/MM/YYYY'
        )
        when raw_payload->>'date_text' ~* '\d{1,2}\s+de\s+\w+\s+de\s+\d{4}'
        then to_date(
            (regexp_match(raw_payload->>'date_text', '(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', 'i'))[1],
            'DD "de" Month "de" YYYY'
        )
        else null
    end                                                                     as discount_start_date,
    -- end date: second date in range, or same as start for single dates
    case
        when array_length(
            regexp_matches(raw_payload->>'date_text', '\d{1,2}/\d{1,2}/\d{4}', 'g')::text[],
            1
        ) >= 2
        then to_date(
            (regexp_matches(raw_payload->>'date_text', '\d{1,2}/\d{1,2}/\d{4}', 'g'))[1][1],
            'DD/MM/YYYY'
        )
        when array_length(
            regexp_matches(raw_payload->>'date_text', '\d{1,2}\s+de\s+\w+\s+de\s+\d{4}', 'gi')::text[],
            1
        ) >= 2
        then to_date(
            (regexp_matches(raw_payload->>'date_text', '\d{1,2}\s+de\s+\w+\s+de\s+\d{4}', 'gi'))[1][1],
            'DD "de" Month "de" YYYY'
        )
        else null
    end                                                                     as discount_end_date,
    case
        when (raw_payload->>'discount_rate') is not null
        then round((raw_payload->>'discount_rate')::numeric / 100, 4)
        else null
    end                                                                     as discount_rate,
    null::text                                                              as discount_name,
    raw_payload->>'description'                                             as discount_description,
    raw_payload->>'legal_text'                                              as discount_terms_and_conditions,
    raw_payload->>'discount_url'                                            as discount_url,
    -- max discount: extract first "Pesos N" or "$N" amount from description (tope de reintegro)
    case
        when raw_payload->>'description' ~* 'tope.*?(?:pesos|[\$\$])\s*[\d.,]+'
        then replace(
            (regexp_match(
                raw_payload->>'description',
                '(?:pesos|[\$\$])\s*([\d.]+(?:,\d+)?)',
                'i'
            ))[1],
            '.', ''
        )::numeric
        else null
    end                                                                     as discount_max_discount_amount,
    null::numeric                                                           as discount_min_purchase_amount,
    (raw_payload->>'installments')::integer                                 as discount_no_interest_installment_qty,
    -- date_text → valid days; null for unrecognised patterns
    case lower(trim(raw_payload->>'date_text'))
        when 'todos los días'              then '[0,1,2,3,4,5,6]'::jsonb
        when 'todos los dias'              then '[0,1,2,3,4,5,6]'::jsonb
        when 'lunes a viernes'             then '[0,1,2,3,4]'::jsonb
        when 'fines de semana'             then '[5,6]'::jsonb
        else
            -- single named day anywhere in the text
            case
                when lower(raw_payload->>'date_text') like '%lunes%'     and
                     lower(raw_payload->>'date_text') not like '%martes%' and
                     lower(raw_payload->>'date_text') not like '%viernes%'
                then '[0]'::jsonb
                when lower(raw_payload->>'date_text') like '%martes%'    and
                     lower(raw_payload->>'date_text') not like '%miércoles%' and
                     lower(raw_payload->>'date_text') not like '%miercoles%'
                then '[1]'::jsonb
                when (lower(raw_payload->>'date_text') like '%miércoles%' or
                      lower(raw_payload->>'date_text') like '%miercoles%') and
                     lower(raw_payload->>'date_text') not like '%jueves%'
                then '[2]'::jsonb
                when lower(raw_payload->>'date_text') like '%jueves%'    and
                     lower(raw_payload->>'date_text') not like '%viernes%'
                then '[3]'::jsonb
                when lower(raw_payload->>'date_text') like '%viernes%'   and
                     lower(raw_payload->>'date_text') not like '%sábado%' and
                     lower(raw_payload->>'date_text') not like '%sabado%'
                then '[4]'::jsonb
                when (lower(raw_payload->>'date_text') like '%sábado%' or
                      lower(raw_payload->>'date_text') like '%sabado%')  and
                     lower(raw_payload->>'date_text') not like '%domingo%'
                then '[5]'::jsonb
                when lower(raw_payload->>'date_text') like '%domingo%'   and
                     lower(raw_payload->>'date_text') not like '%sábado%' and
                     lower(raw_payload->>'date_text') not like '%sabado%'
                then '[6]'::jsonb
                -- date range (not a day name) → null, let downstream filter
                else null
            end
    end                                                                     as discount_valid_days_list,
    false                                                                   as discount_valid_online,
    true                                                                    as discount_valid_instore,
    raw_payload                                                             as discount_metadata,
    scraped_at
from deduped
where rn = 1
