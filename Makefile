# Start Infrastructure
up:
	docker-compose up -d

# Stop everything
down:
	docker-compose down

# Run orchestrator (Scrapy + DBT)
run-orchestrator:
	docker exec -it discount_orchestrator python orchestrate.py

# Test run orchestrator (short Scrapy crawl + DBT)
run-orchestrator-test:
	docker exec -it discount_orchestrator python orchestrate.py --itemcount 5

# Run dbt build
run-dbt-build:
	docker exec -it discount_orchestrator dbt build --target=dev_docker --profiles-dir=discount_tracker_dbt --project-dir=discount_tracker_dbt




	