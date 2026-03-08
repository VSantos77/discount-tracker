# Start Infrastructure
up:
	docker-compose up -d

# Stop everything
down:
	docker-compose down

# Run Spider
crawl:
	docker-compose run --rm orchestrator uv run run_spiders.py $(SCRAPER_ARGS)
	
# Test crawl with single page and dry run (no DB writes)
test-crawl:
	docker-compose run --rm orchestrator uv run run_spiders.py --page_limit=1 --dry_run=1
# Run the Normalization Script
normalize-python:
	docker-compose run --rm orchestrator uv run python -m utils.scripts.normalize_staging_data
# Run dbt
normalize-dbt:
	docker-compose run --rm orchestrator uv run dbt build --project-dir discount_tracker_dbt --profiles-dir discount_tracker_dbt

# The "Full Meal": Run crawl then normalize
pipeline: crawl normalize-dbt

