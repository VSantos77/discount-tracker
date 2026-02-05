CREATE TABLE IF NOT EXISTS discounts (
    id SERIAL PRIMARY KEY,
    
    -- Required Fields
    issuer_name TEXT NOT NULL,
    merchant_name TEXT NOT NULL,
    discount_start_date DATE,
    discount_end_date DATE,
    discount_payment_method TEXT,
    discount_rate DECIMAL(5,4),

    -- Optional Fields
    discount_no_interest_installment_qty INTEGER,
    discount_name TEXT,
    discount_description TEXT,
    discount_url TEXT UNIQUE,
    discount_terms_and_conditions TEXT,
    discount_max_discount_amount DECIMAL(12, 2), -- More precise for money
    discount_min_purchase_amount DECIMAL(12, 2),
    discount_valid_days_list JSONB,              -- Better than a string for lists
    discount_valid_online BOOLEAN,
    discount_valid_instore BOOLEAN,
    discount_metadata JSONB,                     -- For any extra unstructured data
    
    -- Audit fields
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);