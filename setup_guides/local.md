# Local Development Guide (Clean Setup on a New Computer)

This guide explains how to run the project locally from scratch on a different computer.

## 1. Prerequisites

Install these tools first:

1. Docker Desktop (with Docker Compose v2)
2. Git
3. GNU Make (optional, only if you want to use `make` shortcuts)

Quick checks:

```bash
docker --version
docker compose version
git --version
make --version
```

## 2. Clone the Repository

```bash
git clone <YOUR_REPO_URL>
cd discount-tracker
```

## 3. Create Local Environment File

Copy the template and fill values:

```bash
cp .env-example .env
```

Use this as a working local example:

```dotenv
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=discount_tracker
DB_HOST=db
POSTGRES_DB_PORT=5432

PGADMIN_EMAIL=admin@local.dev
PGADMIN_PASSWORD=admin123
```

Notes:

1. `DB_HOST=db` is the Docker Compose service name for Postgres.
2. `POSTGRES_DB_PORT=5432` is used by the app to connect to Postgres.
3. If your local Postgres already uses 5432 and conflicts, stop it or adjust port mappings in `docker-compose.yml`.

## 4. Build and Start Services

Option A: with Make

```bash
make up
```

Option B: plain Docker Compose

```bash
docker compose up -d --build
```

This starts:

1. Postgres (`discount_db`)
2. pgAdmin (`discount_pgadmin`)
3. Streamlit app (`discount_streamlit`)
4. Orchestrator container (`discount_orchestrator`)

## 5. Verify Services Are Running

```bash
docker ps
```

You should see all 4 containers up.

## 6. Run Data Ingestion + Transformations

Run full orchestrator pipeline:

```bash
make run-orchestrator
```

Short test run (limited Scrapy crawl):

```bash
make run-orchestrator-test
```

Run dbt only:

```bash
make run-dbt-build
```

## 7. Open Local Apps

1. Streamlit: http://localhost:8501
2. pgAdmin: http://localhost:8080

For pgAdmin login use values from `.env`:

1. `PGADMIN_EMAIL`
2. `PGADMIN_PASSWORD`

## 8. Useful Logs and Debug Commands

```bash
docker compose logs -f streamlit
docker compose logs -f orchestrator
docker compose logs -f db
```

Run an interactive shell in orchestrator container:

```bash
docker exec -it discount_orchestrator bash
```

## 9. Stop or Reset

Stop everything:

```bash
make down
# or
docker compose down
```

Full reset (removes containers, network, and DB volume data):

```bash
docker compose down -v
```

Use reset only if you want a fresh empty database.

## 10. Common Issues

### Port already in use

Symptom:

1. `docker compose up` fails on port bindings (5432, 8080, or 8501).

Fix:

1. Stop the conflicting local service.
2. Or change port mapping in `docker-compose.yml`.

### Missing environment variables

Symptom:

1. App or dbt fails to connect to DB.

Fix:

1. Verify `.env` exists in repo root.
2. Ensure `DB_HOST`, `POSTGRES_DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` are set.

### Streamlit opens but no data appears

Fix:

1. Run `make run-orchestrator`.
2. Refresh Streamlit page.

## 11. Recommended First-Run Flow

```bash
cp .env-example .env
docker compose up -d --build
make run-orchestrator-test
```

Then open Streamlit at http://localhost:8501.
