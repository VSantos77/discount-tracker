# Start Infrastructure
up:
	docker-compose up -d

# Stop everything
down:
	docker-compose down

# Run the Galicia Spider
crawl-galicia:
	docker-compose run --rm orchestrator uv run scrapy crawl galicia $(SCRAPER_ARGS)
# Run the Normalization Script
normalize:
	docker-compose run --rm orchestrator uv run python -m utils.scripts.normalize_staging_data

# The "Full Meal": Run crawl then normalize
pipeline: crawl-galicia normalize

