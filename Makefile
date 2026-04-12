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
	docker exec -it discount_orchestrator python orchestrate.py --step=spiders

# Step 2: Batch-load JSON files from data/ into raw_discounts table
run-load:
	docker exec -it discount_orchestrator python orchestrate.py --step=load

# Step 3: Run dbt deps + dbt build
run-dbt:
	docker exec -it discount_orchestrator python orchestrate.py --step=dbt --dbt-target=prod

# ── Full pipeline ──────────────────────────────────────────────────────────────

# Run all three steps in sequence (production)
run-pipeline:
	docker exec -it discount_orchestrator python orchestrate.py --dbt-target=prod

# Run all three steps with a limited item count (quick local test)
run-pipeline-test:
	docker exec -it discount_orchestrator python orchestrate.py --itemcount=5 --dbt-target=prod