SELECT
    issuer_name,
    last_scraped_at,
    discount_count
FROM `{project_id}.prod_dbt_analytics.issuer_metadata`
ORDER BY issuer_name