# 💸 Discount Tracker

A centralized dashboard that automatically tracks and organizes bank promotions in Argentina. Browse, filter, and discover the smartest way to pay, ensuring you never miss a chance to save at checkout.

<img width="1278" height="532" alt="image" src="https://github.com/user-attachments/assets/d789435b-7179-4fea-aab7-ca621c90fc8d" />

<img width="1280" height="581" alt="image2" src="https://github.com/user-attachments/assets/48958d99-f6fa-4d83-95f8-4ffef623ff6e" />

---

## 👥 For Casual Users

### What is Discount Tracker?

Discount Tracker is a web application that helps you find and track discounts offered by major banks and financial institutions (a.k.a issuers)* for popular subscription services and online purchases.

\*For now, only BBVA Bank and Galicia Bank, but more to come soon!

### Why Discount Tracker?

I built this because I was tired of feeling like I was missing out.

Between bank promos, club memberships, and digital wallets, figuring out where to shop and how to pay has become a part-time job. This dashboard brings it all together. No more digging through five different banking apps—just the best deals, right when you need them.

### Key Features:

**IMPORTANT NOTICE**: tool UI is in Spanish (since it's meant to be used in Argentina). If you don't speak spanish, I suggest using Google's built in web translation service: I tried it and works pretty well!

- 📱 **Browse Discounts**: Explore all available discounts in an easy-to-use interface
- 🔍 **Smart Filtering**: Filter by:
  - Bank/Issuer (BBVA, Galicia, etc.)
  - Discount Category (streaming, food, travel, etc.)
  - Days of the week the discount is valid
  - Search by merchant name
- 📊 **Dashboard**: See at-a-glance insights with charts showing discount distribution by issuer and category
- 💰 **Detailed Info**: Each discount card shows:
  - Discount percentage
  - Number of payments (cuotas/installments)
  - Valid days of the week
  - Where it can be used (online, in-store, or both)
  - Relevant terms and conditions

### Getting Started

The easiest way to get started is to follow the [Local Setup Guide](setup_guides/local.md). You'll have the app running in minutes with Docker.

**Quick Start:**
```bash
make start

make run-orchestrator-test # within project folder

# Visit http://localhost:8501 to explore discounts
```

For cloud deployment on GCP, follow the [Cloud Deployment Guide](setup_guides/cloud.md) and Terraform setup in [terraform/README.md](terraform/README.md).

---

## 🛠️ For Technical Users

### Architecture Overview

Discount Tracker follows a modern ETL (Extract, Transform, Load) + Presentation pattern:

```
┌─────────────────────────────────────────────────────┐
│ EXTRACTION (Scrapy Spiders)                         │
│ - Crawl issuers websites                            │
│ - Extract discount data, terms, conditions          │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ LOAD (PostgreSQL)                                   │
│ - Raw staging tables from spider output             │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ TRANSFORM (dbt)                                     │
│ - Dimensional modeling (dims + facts)               │
│ - Data validation & quality tests                   │
│ - Business logic & aggregations                     │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ PRESENTATION (Streamlit)                            │
│ - Dashboard: Summary analytics & charts             │
│ - Explorer: Filterable discount cards               │
└─────────────────────────────────────────────────────┘
```

### System Components

#### 1. **Data Extraction** (`discount_tracker_scrapy/`)
- Scrapy-based spiders for each issuer (`bbva.py`, `galicia.py`)
- Custom pipelines for data normalization and load to postgresDB.
- Configurable crawling (item count limits for testing, full runs for production)

**Output**: Raw discount items with merchant, discount %, cuotas, validity, terms

#### 2. **Data Loading** (PostgreSQL + `orchestrate.py`)
- PostgreSQL 16 database (containerized)
- Staging tables populated directly from Scrapy output
- Run statistics tracked for monitoring crawler health loaded to DB.
- Schema managed via `init-db/init.sql`

**Database Service**: `discount_db` (port 5432)
**Admin Interface**: pgAdmin (port 8080) for manual inspection

#### 3. **Data Transformation** (`discount_tracker_dbt/`)
- dbt project with staging and marts layers
- Modeling:
  - **Staging** (`stg_discounts.sql`): Clean, normalize raw data
  - **Dimensions** (`dim_*.sql`): Issuers, merchants, payment methods
  - **Facts** (`fct_discounts.sql`): Granular discount records
  - **Marts** (Streamlit layer): Aggregated `streamlit_data.sql` for UI queries
- **Testing**: dbt tests for data quality, uniqueness, referential integrity

#### 4. **Data Presentation** (`discount_tracker_streamlit/`)
- Streamlit web app running on port 8501
- Two-page layout:
  - **Dashboard**: Plotly bar charts (discounts by issuer, by category)
  - **Explorer**: Filterable, paginated discount card grid
- Features:
  - Sidebar filters (search, issuer, category, valid days)
  - Real-time filtering with pandas
  - Session state management for pagination

**Data Query**: Raw SQL via `utils/queries/streamlit_data.sql` (cached 10-min TTL)


### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Language** | Python | 3.12+ |
| **Web Framework** | Streamlit | 1.55.0+ |
| **Data Pipeline** | dbt-core | 1.11.6+ |
| **Web Scraping** | Scrapy | 2.14.1+ |
| **Database** | PostgreSQL | 16 (Alpine) |
| **Package Manager** | uv | Latest |
| **Container Orchestration** | Docker Compose | Latest |
| **Infrastructure as Code** | Terraform | 1.8+ |
| **Cloud Platform** | Google Cloud Platform (Compute Engine) | Latest |
| **Visualization** | Plotly | 6.6.0+ |

### Environment Configuration

Create a `.env` file in project root (see `.env` template):

```bash
# Database
DB_HOST=discount_db              # Docker service name (or IP for cloud)
DB_NAME=discounts_db
DB_USER=discount_user
DB_PASSWORD=your_secure_password
POSTGRES_DB_PORT=5432

# pgAdmin (Database UI)
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin_password

# dbt (required by orchestrator)
DBT_PROFILES_DIR=discount_tracker_dbt
DBT_PROJECT_DIR=discount_tracker_dbt

# removes uv warnings when working across different platforms
UV_LINK_MODE=copy
```

### Docker Services

Start all services from scratch:
```bash
make start
```

**Services** (defined in `docker-compose.yml`):
- **db**: PostgreSQL database
- **pgadmin**: pgAdmin web interface (http://localhost:8080)
- **streamlit**: Streamlit web app (http://localhost:8501)
- **orchestrator**: Scrapy + dbt runner (triggered via `make run-orchestrator`)

### Useful Commands

```bash
# Infrastructure
make start                     # Build and starts all containers
make up                        # Start all services
make down                      # Stop all services

# Data Pipeline
make run-orchestrator          # Execute Scrapy crawl + dbt build
make run-orchestrator-test     # Quick test run (5 items)

# Debugging
docker logs discount_streamlit  # View app logs
docker exec -it discount_orchestrator /bin/bash  # Shell into orchestrator
```

### Project Structure

```
discount-tracker/
├── discount_tracker_scrapy/      # Scrapy spiders & pipelines
│   ├── spiders/
│   │   ├── bbva.py              # BBVA bank scraper
│   │   └── galicia.py           # Galicia bank scraper
│   ├── pipelines.py             # Data normalization
│   └── settings.py              # Scrapy config
├── discount_tracker_dbt/         # dbt transformations
│   ├── models/
│   │   ├── staging/             # Raw data cleanup
│   │   └── marts/               # Analytics tables
│   ├── tests/                   # Data quality tests
│   └── profiles.yml             # dbt database config
├── discount_tracker_streamlit/   # Streamlit web app
│   ├── app.py                   # Main dashboard & explorer
│   └── .streamlit/config.toml   # Streamlit config
├── utils/                        # Shared utilities
│   ├── functions.py             # DB connection helpers
│   ├── configs.py               # Config loader
│   └── queries/                 # SQL files for data loading
├── orchestrate.py               # ETL orchestration script
├── run_spiders.py               # Scrapy runner
├── docker-compose.yml           # Service definitions
├── Dockerfile                   # Multi-stage build
├── terraform/                   # GCP infrastructure provisioning (Terraform)
│   ├── main.tf                  # VM + metadata startup script
│   ├── firewall.tf              # Streamlit, pgAdmin, Postgres, SSH rules
│   ├── cloud-init.sh            # VM bootstrap: Docker, uv, make, app startup
│   └── README.md                # Terraform usage guide
├── setup_guides/                # Local and cloud setup guides
│   ├── local.md
│   └── cloud.md
└── Makefile                     # Task automation
```

### Setup & Deployment

- **Local Development**: [setup_guides/local.md](setup_guides/local.md)
- **Cloud (GCP + Terraform)**: [setup_guides/cloud.md](setup_guides/cloud.md)
- **Terraform Reference**: [terraform/README.md](terraform/README.md)
