with source as (

    select
        raw_payload,
        scraped_at
    from {{ source('staging', 'raw_discounts') }}
    where spider_name = 'santander'

),

normalized as (

    select
        case
            when raw_payload ? 'item' and jsonb_typeof(raw_payload->'item') = 'object'
            then raw_payload->'item'
            when raw_payload ? 'data' and jsonb_typeof(raw_payload->'data') = 'object'
            then raw_payload->'data'
            else raw_payload
        end                                                     as payload,
        raw_payload,
        scraped_at
    from source

),

deduped as (

    select
        payload,
        raw_payload,
        scraped_at,
        row_number() over (
            partition by coalesce(
                nullif(trim(payload->>'source_id'), ''),
                nullif(trim(payload->>'id'), ''),
                nullif(trim(payload->>'code'), '')
            )
            order by scraped_at desc
        ) as rn
    from normalized

)

select
    coalesce(
        nullif(trim(payload->>'source_id'), ''),
        nullif(trim(payload->>'id'), ''),
        nullif(trim(payload->>'code'), '')
    )                                                           as source_id,

    'Banco Santander'                                           as issuer_name,

    coalesce(
        nullif(trim(payload->>'name'), ''),
        nullif(trim(payload->'brand'->>'name'), ''),
        nullif(trim(payload->>'title'), '')
    )                                                           as merchant_name,

    coalesce(
        nullif(trim(payload->'category'->>'name'), ''),
        nullif(trim(payload->'category'->>'description'), ''),
        nullif(trim(payload->'rubro'->>'name'), ''),
        nullif(trim(payload->'brandType'->>'description'), '')
    )                                                           as merchant_category_name,

    case
        when coalesce(payload->>'startDate', payload->>'validFrom', payload->>'fromDate', payload->>'vigenciaDesde') ~ '^\d{4}-\d{2}-\d{2}'
        then to_date(left(coalesce(payload->>'startDate', payload->>'validFrom', payload->>'fromDate', payload->>'vigenciaDesde'), 10), 'YYYY-MM-DD')
        when coalesce(payload->>'startDate', payload->>'validFrom', payload->>'fromDate', payload->>'vigenciaDesde') ~ '^\d{2}/\d{2}/\d{4}$'
        then to_date(coalesce(payload->>'startDate', payload->>'validFrom', payload->>'fromDate', payload->>'vigenciaDesde'), 'DD/MM/YYYY')
        else null
    end                                                         as discount_start_date,

    case
        when coalesce(payload->>'endDate', payload->>'validTo', payload->>'toDate', payload->>'vigenciaHasta') ~ '^\d{4}-\d{2}-\d{2}'
        then to_date(left(coalesce(payload->>'endDate', payload->>'validTo', payload->>'toDate', payload->>'vigenciaHasta'), 10), 'YYYY-MM-DD')
        when coalesce(payload->>'endDate', payload->>'validTo', payload->>'toDate', payload->>'vigenciaHasta') ~ '^\d{2}/\d{2}/\d{4}$'
        then to_date(coalesce(payload->>'endDate', payload->>'validTo', payload->>'toDate', payload->>'vigenciaHasta'), 'DD/MM/YYYY')
        else null
    end                                                         as discount_end_date,

    case
        when coalesce(payload->>'benefitDescription', payload->>'description', payload->>'title', '') ~ '\d+(?:[.,]\d+)?\s*%'
        then round(
            regexp_replace(
                (regexp_match(
                    coalesce(payload->>'benefitDescription', payload->>'description', payload->>'title', ''),
                    '(\d+(?:[.,]\d+)?)\s*%'
                ))[1],
                ',', '.', 'g'
            )::numeric / 100,
            4
        )
        else null
    end                                                         as discount_rate,

    nullif(trim(payload->>'title'), '')                        as discount_name,

    coalesce(
        nullif(trim(payload->>'benefitDescription'), ''),
        nullif(trim(payload->>'description'), '')
    )                                                           as discount_description,

    coalesce(
        nullif(trim(payload->>'termsAndConditions'), ''),
        nullif(trim(payload->>'legal'), ''),
        nullif(trim(payload->>'legals'), '')
    )                                                           as discount_terms_and_conditions,

    coalesce(
        nullif(trim(payload->>'url'), ''),
        nullif(trim(payload->>'link'), ''),
        nullif(trim(payload->>'webUrl'), '')
    )                                                           as discount_url,

    coalesce(
        nullif(trim(payload->>'maxDiscountAmount'), ''),
        nullif(trim(payload->>'maxAmount'), ''),
        nullif(trim(payload->>'capAmount'), '')
    )::numeric                                                  as discount_max_discount_amount,

    coalesce(
        nullif(trim(payload->>'minPurchaseAmount'), ''),
        nullif(trim(payload->>'minAmount'), '')
    )::numeric                                                  as discount_min_purchase_amount,

    case
        when coalesce(payload->>'benefitDescription', payload->>'description', payload->>'title', '') ~* '(\d+)\s*cuotas'
        then (regexp_match(
            coalesce(payload->>'benefitDescription', payload->>'description', payload->>'title', ''),
            '(\d+)\s*cuotas',
            'i'
        ))[1]::integer
        else null
    end                                                         as discount_no_interest_installment_qty,

    null::jsonb                                                 as discount_valid_days_list,

    case
        when lower(coalesce(payload->>'online', payload->>'isOnline', '')) in ('true', 't', '1', 'si', 'yes')
        then true
        when lower(coalesce(payload->>'online', payload->>'isOnline', '')) in ('false', 'f', '0', 'no')
        then false
        else (
            lower(coalesce(payload->>'channel', payload->>'channels', payload->>'channelType', '')) like '%online%'
            or lower(coalesce(payload->>'channel', payload->>'channels', payload->>'channelType', '')) like '%web%'
        )
    end                                                         as discount_valid_online,

    case
        when lower(coalesce(payload->>'instore', payload->>'isInStore', '')) in ('true', 't', '1', 'si', 'yes')
        then true
        when lower(coalesce(payload->>'instore', payload->>'isInStore', '')) in ('false', 'f', '0', 'no')
        then false
        else (
            lower(coalesce(payload->>'channel', payload->>'channels', payload->>'channelType', '')) like '%instore%'
            or lower(coalesce(payload->>'channel', payload->>'channels', payload->>'channelType', '')) like '%presencial%'
            or lower(coalesce(payload->>'channel', payload->>'channels', payload->>'channelType', '')) like '%sucursal%'
        )
    end                                                         as discount_valid_instore,

    raw_payload                                                 as discount_metadata,
    scraped_at

from deduped
where rn = 1
