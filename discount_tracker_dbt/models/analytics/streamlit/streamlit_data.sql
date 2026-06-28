with discounts as (
    select
        *
    from {{ ref('fct_discounts') }}
),

merchants as (
    select
        *
    from {{ ref('dim_merchants') }}
),

issuers as (
    select
        *
    from {{ ref('dim_issuers') }}
)

select
        d.id AS discount_id,
        i.name AS issuer_name,
        m.name AS merchant_name,
        m.category_name_normalized AS merchant_category_name,
        d.start_date AS discount_start_date,
        d.end_date AS discount_end_date,
        d.rate AS discount_rate,
        d.no_interest_installment_qty AS discount_no_interest_installment_qty,
        d.name AS discount_name,
        d.description AS discount_description,
        d.url AS discount_url,
        d.terms_and_conditions AS discount_terms_and_conditions,
        d.max_discount_amount AS discount_max_discount_amount,
        d.min_purchase_amount AS discount_min_purchase_amount,
        d.valid_days_list AS discount_valid_days_list,
        d.valid_online AS discount_valid_online,
        d.valid_instore AS discount_valid_instore,
        d.metadata AS discount_metadata,
        d.last_updated_at_date
from
    discounts d
join merchants m on d.merchant_id = m.id
join issuers i on d.issuer_id = i.id