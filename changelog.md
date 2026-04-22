# Changelog

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
