with source as (
        select * from {{ source('staging', 'stg_discounts') }}
  ),
  renamed as (
      select
        {{ dbt_utils.generate_surrogate_key([
          'issuer_name',
          'merchant_name',
          'discount_start_date',
          'discount_end_date',
          'discount_rate',
          'discount_no_interest_installment_qty'
        ]) }} AS discount_id,  -- Generates a unique text/hash based on multiple columns
        cast({{ adapter.quote("issuer_name") }} AS text) AS issuer_name,
        cast({{ adapter.quote("merchant_name") }} as text) as merchant_name,
        cast({{ adapter.quote("discount_start_date") }} as date) as discount_start_date,
        cast({{ adapter.quote("discount_end_date") }} as date) as discount_end_date,
        cast({{ adapter.quote("discount_payment_method") }} as jsonb) as discount_payment_method,
        round(cast({{ adapter.quote("discount_rate") }} as numeric),4) as discount_rate,
        cast({{ adapter.quote("discount_no_interest_installment_qty") }} as integer) as discount_no_interest_installment_qty,
        cast({{ adapter.quote("discount_name") }} as text) as discount_name,
        cast({{ adapter.quote("discount_description") }} as text) as discount_description,
        cast({{ adapter.quote("discount_url") }} as text) as discount_url,
        cast({{ adapter.quote("discount_terms_and_conditions") }} as text) as discount_terms_and_conditions,
        cast({{ adapter.quote("discount_max_discount_amount") }} as integer) as discount_max_discount_amount,
        cast({{ adapter.quote("discount_min_purchase_amount") }} as integer) as discount_min_purchase_amount,
        cast({{ adapter.quote("discount_valid_days_list") }} as jsonb) as discount_valid_days_list,
        cast({{ adapter.quote("discount_valid_online") }} as boolean) as discount_valid_online,
        cast({{ adapter.quote("discount_valid_instore") }} as boolean) as discount_valid_instore,
        cast({{ adapter.quote("discount_metadata") }} as jsonb) as discount_metadata,
        cast({{ adapter.quote("scraped_at") }} as timestamp) as scraped_at

      from source
  )
  select * from renamed
    