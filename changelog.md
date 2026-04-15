# Changelog

## 2026-04-14

### Added
- New Santander Scrapy spider (`santander`) with paginated brand discovery and per-brand detail requests.
- New dbt staging model for Santander: `stg_santander.sql`.
- New dbt staging model for Modo: `stg_modo.sql`.
- Spider activation config file: `utils/spider_config.yaml`.

### Changed
- `int_joined_discounts.sql` now includes Santander records in the union pipeline.
- `int_joined_discounts.sql` now applies defensive normalization:
	- `discount_rate` forced to non-negative via `GREATEST(COALESCE(...), 0)`.
	- Numeric amount fields coalesced to zero where missing.
	- Installment quantity forced to non-negative.
- `fct_discounts.sql` joins to dimensions changed from `INNER JOIN` to `LEFT JOIN` to avoid dropping fact rows when dimensions are missing.
- Scrapy runtime settings tuned:
	- `DOWNLOAD_DELAY` increased.
	- AutoThrottle enabled.
- Orchestration updated to support active-spider filtering from YAML config and validate requested spider names.

### Fixed
- Staging numeric cast hardening for BBVA and Galicia models to avoid failures on empty strings.
- Modo staging parsing moved fully into dbt, including source id fallback and category mapping.

### Notes
- `changelog.md` is currently listed in `.gitignore`.
