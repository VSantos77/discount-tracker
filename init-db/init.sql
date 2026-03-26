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
    merchant_category_name TEXT,
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

CREATE TABLE IF NOT EXISTS spider_crawl_stats (
    id SERIAL PRIMARY KEY,
    spider_name TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    finish_time TIMESTAMPTZ NOT NULL,
    item_count INTEGER NOT NULL,
    reason TEXT,
    runtime_seconds DECIMAL(10, 2) NOT NULL
);