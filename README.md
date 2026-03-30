# 💸 Discount Tracker

Discount Tracker is a centralized dashboard that automatically tracks and organizes bank promotions in Argentina. It helps people quickly decide where to buy and how to pay to maximize savings.

> **Data Engineering Zoomcamp 2026 reviewers**: there is a dedicated section for you below: **For Data Engineering Zoomcamp 2026 Reviewers**.

<img width="1278" height="532" alt="image" src="https://github.com/user-attachments/assets/d789435b-7179-4fea-aab7-ca621c90fc8d" />

<img width="1280" height="581" alt="image2" src="https://github.com/user-attachments/assets/48958d99-f6fa-4d83-95f8-4ffef623ff6e" />

---

## Presentation

### What this project is

Discount Tracker is a web app that collects bank promotions from issuer websites, processes that data, and shows it in a clean interface so users can discover the best discounts in seconds.

### What problem it solves

Bank discounts are fragmented across multiple apps and websites, often with different formats and changing terms. This project solves that by centralizing promotions in one place, standardizing the data, and making it searchable and filterable.

### What you can do with it

- Browse all available discounts in one dashboard
- Filter discounts by issuer, category, and valid weekdays
- Search discounts by merchant name
- Compare discount percentages and installments
- Check where each discount is valid (online, in-store, or both)
- Read terms and conditions without leaving the app

### Notes for non-Spanish speakers

The app UI is in Spanish because it targets users in Argentina. Browser translation works well if needed.

### Quick start

Full setup guides:

- Local: [setup_guides/local.md](setup_guides/local.md)
- Cloud: [setup_guides/cloud.md](setup_guides/cloud.md)
- Terraform details: [terraform/README.md](terraform/README.md)

Fast local run:

```bash
make start                        # Builds and starts the necessary docker containers
make run-orchestrator-test        # Do a quick run of the batch ingestion script

# Go to http://localhost:8501 to visit the streamlit app!
```

---


## For Technical Users

### Architecture overview

The project follows an ETL + Presentation flow:

```text
Scrapy ingestion -> PostgreSQL staging/load -> dbt transformations -> Streamlit dashboard
```

Detailed flow:

```
┌─────────────────────────────────────────────────────┐
│ EXTRACTION (Scrapy spiders)                         │
│ - Crawl issuer websites                              │
│ - Extract discounts, terms, and validity info        │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ LOAD (PostgreSQL)                                   │
│ - Persist raw/staging records                       │
│ - Track run statistics                              │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ TRANSFORM (dbt)                                     │
│ - Clean and normalize source data                   │
│ - Build dimensions and fact tables                  │
│ - Run data quality tests                            │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ PRESENTATION (Streamlit + Plotly)                  │
│ - Dashboard analytics                               │
│ - Explorer with filters and pagination              │
└─────────────────────────────────────────────────────┘
```

### Main components

1. **Data extraction** ([discount_tracker_scrapy](discount_tracker_scrapy))
   - Spiders per issuer: [discount_tracker_scrapy/spiders/bbva.py](discount_tracker_scrapy/spiders/bbva.py), [discount_tracker_scrapy/spiders/galicia.py](discount_tracker_scrapy/spiders/galicia.py)
   - Pipelines for normalization and persistence

2. **Load and orchestration** ([orchestrate.py](orchestrate.py), [run_spiders.py](run_spiders.py))
   - Containerized PostgreSQL 16 backend
   - Orchestrated pipeline execution from Make targets
   - Schema bootstrapping in [init-db/init.sql](init-db/init.sql)

3. **Transformations** ([discount_tracker_dbt](discount_tracker_dbt))
   - Staging model: [discount_tracker_dbt/models/staging/stg_discounts.sql](discount_tracker_dbt/models/staging/stg_discounts.sql)
   - Dimensions: [discount_tracker_dbt/models/marts/dim_issuers.sql](discount_tracker_dbt/models/marts/dim_issuers.sql), [discount_tracker_dbt/models/marts/dim_merchants.sql](discount_tracker_dbt/models/marts/dim_merchants.sql), [discount_tracker_dbt/models/marts/dim_payment_methods.sql](discount_tracker_dbt/models/marts/dim_payment_methods.sql)
   - Fact: [discount_tracker_dbt/models/marts/fct_discounts.sql](discount_tracker_dbt/models/marts/fct_discounts.sql)
   - Streamlit mart: [discount_tracker_dbt/models/marts/streamlit/streamlit_data.sql](discount_tracker_dbt/models/marts/streamlit/streamlit_data.sql)

4. **Presentation app** ([discount_tracker_streamlit/app.py](discount_tracker_streamlit/app.py))
   - Dashboard page with issuer/category charts
   - Explorer page with filters, cards, terms popovers, and pagination

### Technology stack

| Layer | Technology | Version |
|-------|------------|---------|
| Language | Python | 3.12+ |
| Web app | Streamlit | 1.55.0+ |
| Visualization | Plotly | 6.6.0+ |
| Ingestion | Scrapy | 2.14.1+ |
| Transformation | dbt-core | 1.11.6+ |
| Database | PostgreSQL | 16 (Alpine) |
| Container runtime | Docker Compose | Latest |
| IaC | Terraform | 1.8+ |
| Cloud | Google Cloud Platform (Compute Engine) | Latest |

### Environment variables

Create a `.env` file in the project root:

```bash
# Database
DB_HOST=discount_db
DB_NAME=discounts_db
DB_USER=discount_user
DB_PASSWORD=your_secure_password
POSTGRES_DB_PORT=5432

# pgAdmin
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin_password

# dbt
DBT_PROFILES_DIR=discount_tracker_dbt
DBT_PROJECT_DIR=discount_tracker_dbt

# uv compatibility
UV_LINK_MODE=copy
```

### Common commands

```bash
# Infra lifecycle
make start
make up
make down

# Data pipeline
make run-orchestrator
make run-orchestrator-test

# Debugging
docker logs discount_streamlit
docker exec -it discount_orchestrator /bin/bash
```

### Project structure

```text
discount-tracker/
├── discount_tracker_scrapy/      # Scrapy spiders and pipelines
├── discount_tracker_dbt/         # dbt project: staging, marts, tests
├── discount_tracker_streamlit/   # Streamlit UI
├── utils/                        # shared helpers and SQL queries
├── init-db/                      # DB initialization SQL
├── setup_guides/                 # local and cloud setup docs
├── terraform/                    # GCP infrastructure as code
├── orchestrate.py                # batch orchestration
├── run_spiders.py                # spider execution entrypoint
├── docker-compose.yml            # service composition
├── Dockerfile                    # app image build
└── Makefile                      # developer and pipeline commands
```

### Setup and deployment docs

- Local setup: [setup_guides/local.md](setup_guides/local.md)
- Cloud deployment: [setup_guides/cloud.md](setup_guides/cloud.md)
- Terraform reference: [terraform/README.md](terraform/README.md)


---

## For Data Engineering Zoomcamp 2026 Reviewers

This section maps the implementation to the project evaluation criteria, along with suggested scores based on self-assesment.

### 1) Problem description

- **Criterion target**: clearly describe the problem and solution
- **How this project addresses it**: the project centralizes scattered bank promotions, normalizes raw issuer data, and exposes discount intelligence through a user-facing dashboard
- **Self-assessment**: **4/4**

### 2) Cloud

- **Criterion target**: cloud development plus IaC for full score
- **How this project addresses it**:
  - Runs on Google Cloud Platform (Compute Engine)
  - Infrastructure is provisioned with Terraform in [terraform](terraform)
  - Includes startup automation in [terraform/cloud-init.sh](terraform/cloud-init.sh)
- **Self-assessment**: **4/4**

### 3) Data ingestion (Batch / Workflow orchestration)

- **Chosen ingestion mode**: **Batch**
- **How this project addresses it**:
  - Scrapy spiders ingest discount data from issuer websites
  - `orchestrate.py` executes the pipeline steps (crawl, load, transform)
  - Make targets provide reproducible pipeline runs (`make run-orchestrator`, `make run-orchestrator-test`)
- **Self-assessment under strict rubric wording**: **2/4** (pipeline is orchestrated end-to-end, but it does not currently include a separate cloud data lake upload stage)

### 4) Data warehouse

- **Criterion target**: DWH tables, and partitioning/clustering for full score
- **How this project addresses it**:
  - Uses PostgreSQL as analytical serving store
  - Builds dimensional/fact model with dbt (`dim_*`, `fct_discounts`, Streamlit mart)
- **Self-assessment**: **2/4** (warehouse modeling is implemented; explicit partition/cluster optimization strategy is not currently part of the design)

### 5) Transformations (dbt / Spark / similar)

- **Criterion target**: dbt/Spark-based transformations for full score
- **How this project addresses it**:
  - Transformations are implemented with dbt in [discount_tracker_dbt](discount_tracker_dbt)
  - Includes staging, dimensions, facts, tests, and a presentation mart
- **Self-assessment**: **4/4**

### 6) Dashboard

- **Criterion target**: at least 2 tiles for full score
- **How this project addresses it**:
  - Streamlit dashboard includes two core visual tiles/charts:
    - Discounts by issuer
    - Discounts by category
- **Self-assessment**: **4/4**

### 7) Reproducibility

- **Criterion target**: clear, complete instructions that work
- **How this project addresses it**:
  - Step-by-step setup docs for local and cloud environments
  - Docker Compose + Makefile targets for consistent runs
  - Terraform configuration and variables for reproducible cloud provisioning
- **Self-assessment**: **4/4**

### 8) Going the extra mile (Optional)

- **Tests**: **Partially included**. The project includes dbt data quality tests (for example `not_null` and `unique` tests in marts models), but it does not yet include an automated Python unit/integration test suite for the scraping and app layers.
- **Use make**: **Included**. The project uses a Makefile for common workflows such as startup, teardown, and orchestrator runs.
- **CI/CD pipeline**: **Not included yet**. There is currently no repository CI/CD workflow configured.

---