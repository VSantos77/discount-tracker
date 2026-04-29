# Start everything from scratch
start:
	docker compose up --build -d

# Start Infrastructure
up:
	docker compose up -d

# Stop everything	
down:
	docker compose down

# ── Individual pipeline steps ─────────────────────────────────────────────────

# Step 1: Run Scrapy spiders, write JSON files to data/
run-spiders:
	docker exec -it discount_orchestrator python orchestrate.py --spiders=$(SPIDERS)

# Step 2: Batch-load JSON files from data/ into raw_discounts table
run-load:
	docker exec -it discount_orchestrator python orchestrate.py --step=load

# Step 3: Run dbt deps + dbt build
run-dbt:
	docker exec -it discount_orchestrator python orchestrate.py --dbt-target=prod

# ── Full pipeline ──────────────────────────────────────────────────────────────

# Run all three steps in sequence (production)
run-pipeline:
	docker exec -it discount_orchestrator python orchestrate.py --dbt-target=prod

# Run all three steps with a limited item count (quick local test)
run-pipeline-test:
	docker exec -it discount_orchestrator python orchestrate.py --itemcount=5 --dbt-target=prod

# ── Prefect ────────────────────────────────────────────────────────────────────

# Trigger a manual pipeline run via the Prefect API (flow must be registered / container running)
prefect-run:
	docker exec -it discount_orchestrator uv run --group orchestrator prefect deployment run 'discount-tracker-pipeline/discount-tracker-pipeline'

# Open a shell in the orchestrator container (useful for ad-hoc prefect CLI commands)
prefect-shell:
	docker exec -it discount_orchestrator bash


test-dbt-image:
	docker run --rm -v $(GOOGLE_APPLICATION_CREDENTIALS):/app/key.json -e GCP_PROJECT_ID -e GOOGLE_APPLICATION_CREDENTIALS=/app/key.json vsantos77/discount-tracker-dbt:v1.1 build --select stg_galicia --target=prod

test-scrapy-image:
	docker run --rm -v $(GOOGLE_APPLICATION_CREDENTIALS):/app/key.json -e GCS_BUCKET -e GCP_PROJECT_ID -e GOOGLE_APPLICATION_CREDENTIALS=/app/key.json -e STORAGE_BACKEND=gcs vsantos77/discount-tracker-scrapy:v1.1 crawl galicia -s CLOSESPIDER_ITEMCOUNT=1