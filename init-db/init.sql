CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.raw_discounts (
    id SERIAL PRIMARY KEY,
    spider_name TEXT NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL,
    raw_payload JSONB NOT NULL,
    loaded_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS raw.spider_crawl_stats (
    id SERIAL PRIMARY KEY,
    spider_name TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    finish_time TIMESTAMPTZ NOT NULL,
    item_count INTEGER NOT NULL,
    reason TEXT,
    runtime_seconds DECIMAL(10, 2) NOT NULL
);