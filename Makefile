# Start everything from scratch
start:
	docker compose up --build -d

# Start Infrastructure
up:
	docker compose up -d

# Stop everything	
down:
	docker compose down

# Run orchestrator (Scrapy + DBT)
run-orchestrator-prod:
	docker exec -it discount_orchestrator python orchestrate.py --dbt-target=prod

# Test run orchestrator (short Scrapy crawl + DBT using dev target)
run-orchestrator-test:
	docker exec -it discount_orchestrator python orchestrate.py --itemcount=5 --dbt-target=prod