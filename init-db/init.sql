CREATE TABLE IF NOT EXISTS stg_discounts (
    id SERIAL PRIMARY KEY,
    
    -- Required Fields
    issuer_name TEXT NOT NULL,
    merchant_name TEXT NOT NULL,
    discount_start_date DATE NOT NULL,
    discount_end_date DATE NOT NULL,
    discount_payment_method JSONB NOT NULL,
    discount_rate DECIMAL(5,4) NOT NULL,

    -- Optional Fields
    discount_no_interest_installment_qty INTEGER,
    discount_name TEXT,
    discount_description TEXT,
    discount_url TEXT,
    discount_terms_and_conditions TEXT,
    discount_max_discount_amount DECIMAL(12, 2),
    discount_min_purchase_amount DECIMAL(12, 2),
    discount_valid_days_list JSONB,
    discount_valid_online BOOLEAN,
    discount_valid_instore BOOLEAN,
    discount_metadata JSONB,
    
    -- Audit fields
    scraped_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS dim_issuers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_merchants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_payment_methods_raw (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    CONSTRAINT unique_payment_method UNIQUE (name, type)
);

CREATE TABLE IF NOT EXISTS map_discount_payment_methods (
    ID SERIAL PRIMARY KEY,
    discount_id UUID NOT NULL,
    payment_method_id INTEGER NOT NULL,
    CONSTRAINT unique_discount_payment_combination UNIQUE (discount_id, payment_method_id)
)

CREATE TABLE IF NOT EXISTS fct_discounts (
    -- IDS
    id UUID PRIMARY KEY,
    issuer_id INTEGER NOT NULL REFERENCES dim_issuers(id),
    merchant_id INTEGER NOT NULL REFERENCES dim_merchants(id),
    
    -- Date
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    -- Timestamps
    scraped_at_ts TIMESTAMPTZ DEFAULT NOW(),
    
    -- Text
    name TEXT,
    description TEXT,
    url TEXT,
    terms_and_conditions TEXT,

    -- Numeric
    rate DECIMAL(5,4) NOT NULL,
    no_interest_installment_qty INTEGER,
    max_discount_amount DECIMAL(12, 2),
    min_purchase_amount DECIMAL(12, 2),
    
    -- JSON
    valid_days_list JSONB,
    metadata JSONB,
    
    -- Boolean
    valid_online BOOLEAN,
    valid_instore BOOLEAN
)