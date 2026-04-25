# Changelog

## 2026-04-25

### Added
- New Scrapy spider `cuentadni` for Banco Provincia Cuenta DNI benefits (JSON API).
- New Scrapy spider `bancoprovincia` for main Banco Provincia benefits page (HTML scraping).
- New dbt staging model `stg_cuentadni.sql` with `.NET` epoch date parsing and `titulo_fecha` → weekday mapping.
- New dbt staging model `stg_bancoprovincia.sql`.
- `int_joined_discounts.sql` updated to union both new Banco Provincia staging models.
- `utils/spider_config.yaml` updated with `cuentadni` and `bancoprovincia` entries (active).
- `RawPayloadWrapperPipeline` in `pipelines.py`: wraps each scraped item as `{"raw_payload": <item>}` before FEED export so GCS JSONL files have a consistent single-column schema for BigQuery.
- `google-cloud-storage` and `neon-api` added to `pyproject.toml` dependencies.
- BigQuery external table `raw_discounts` defined in Terraform (`google_bigquery_table.raw_discounts`) with explicit JSON schema, hive partitioning on `{spider:STRING}/{scraped_at_dt:DATE}`, and `autodetect = false`.
- `dbt-bigquery` added as a dependency; `profiles.yml` updated with a BigQuery target (`discount-tracker-bq`).
- `stg_galicia.sql` rewritten for BigQuery SQL dialect (`JSON_VALUE`, `PARSE_DATE`, `SAFE_CAST`, `SPLIT`, `JSON_OBJECT`, etc.).
- `sources.yml` updated to reflect BigQuery external table columns (`spider`, `scraped_at_dt`, `raw_payload`).

### Changed
- `settings.py`: GCS feed URI now includes a date folder (`landing/{spider}/{YYYY-MM-DD}/{timestamp}.jsonl`) for BigQuery hive partition alignment. DB credential variables removed (no longer needed by Scrapy).
- `ITEM_PIPELINES` enabled in `settings.py` with `RawPayloadWrapperPipeline` at priority 100.
- `orchestrate.py`: pipeline simplified to `run-spiders` → `run-dbt`; `task_load_raw_json` task and its import removed.
- `profiles.yml`: migrated from `dbt-postgres` to `dbt-bigquery`; profile renamed to `discount-tracker-bq`.

### Removed
- `load_raw_json.py` deleted — Scrapy writes directly to GCS; BigQuery reads via external tables.
- `utils/configs.py` deleted — only existed to provide `DB_SETTINGS` for the load script.
- `init-db/` directory deleted — Docker Postgres init script no longer relevant.
- `psycopg2-binary` removed from `pyproject.toml`.

---

## 2026-04-17

### Changed
- `task_run_dbt` now runs `dbt build` via `ShellOperation` from `prefect-shell`, streaming stdout line-by-line to Prefect's logger instead of using `PrefectDbtRunner`.

### Removed
- Removed `prefect-dbt` dependency; replaced with `prefect-shell`.

---

## 2026-04-16

### Added
- Prefect orchestration: `orchestrate.py` rewritten using `@flow` and `@task` decorators; pipeline serve mode enabled (`--serve` flag).
- `prefect-server` service added to `docker-compose.yml` with a dedicated `prefect_data` volume.
- Orchestrator container now starts in Prefect serve mode (`python orchestrate.py --serve`).
- `PREFECT_API_URL` environment variable wired into the orchestrator container.
- Makefile targets `prefect-run` and `prefect-shell` added for triggering deployments and opening a container shell.
- Prefect table artifact in `task_run_spiders` to surface per-spider scraped item counts, runtimes, and finish reasons in the Prefect UI.

### Changed
- `load_raw_json.py`: extracted `load_raw_json_data()` as a callable function (raises on failure) so it can be invoked directly from `orchestrate.py`; `main()` is now a thin CLI wrapper.
- `docker-compose.yml`: `DBT_PROFILES_DIR` and `DBT_PROJECT_DIR` hardcoded to container paths instead of relying on host env vars.
- Makefile: updated `run-spiders` and `run-dbt` targets to match new `orchestrate.py` argument interface.

---

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
