with source as (
        select * from {{ source('staging', 'stg_discounts') }}
  ),
  renamed as (
      select
        {{ adapter.quote("id") }},
        {{ adapter.quote("issuer_name") }},
        {{ adapter.quote("merchant_name") }},
        {{ adapter.quote("discount_start_date") }},
        {{ adapter.quote("discount_end_date") }},
        {{ adapter.quote("discount_payment_method") }},
        {{ adapter.quote("discount_rate") }},
        {{ adapter.quote("discount_no_interest_installment_qty") }},
        {{ adapter.quote("discount_name") }},
        {{ adapter.quote("discount_description") }},
        {{ adapter.quote("discount_url") }},
        {{ adapter.quote("discount_terms_and_conditions") }},
        {{ adapter.quote("discount_max_discount_amount") }},
        {{ adapter.quote("discount_min_purchase_amount") }},
        {{ adapter.quote("discount_valid_days_list") }},
        {{ adapter.quote("discount_valid_online") }},
        {{ adapter.quote("discount_valid_instore") }},
        {{ adapter.quote("discount_metadata") }},
        {{ adapter.quote("scraped_at") }}

      from source
  )
  select * from renamed
    