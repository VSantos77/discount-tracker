CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.raw_discounts (
    id SERIAL PRIMARY KEY,
    spider_name TEXT NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL,
    raw_payload JSONB NOT NULL,
    loaded_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);