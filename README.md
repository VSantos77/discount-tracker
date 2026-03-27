# 💸 Discount Tracker

A smart discount aggregation tool that tracks and presents available discounts across different financial institutions in Argentina. Browse, filter, and discover the best deals for your subscriptions in one centralized dashboard.

---

## 👥 For Casual Users

### What is Discount Tracker?

Discount Tracker is a web application that helps you find and track discounts offered by major banks and financial institutions for popular subscription services and online purchases.

**Key Features:**

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

The easiest way to get started is to follow the [Local Setup Guide](development/local.md). You'll have the app running in minutes with Docker.

**Quick Start:**
```bash
docker compose up -d --build
# Visit http://localhost:8501 to explore discounts
```

For cloud deployment, check the [Cloud Deployment Guide](development/cloud.md).

---

## 🛠️ For Technical Users

### Architecture Overview

Discount Tracker follows a modern ETL (Extract, Transform, Load) + Presentation pattern:

```
┌─────────────────────────────────────────────────────┐
│ EXTRACTION (Scrapy Spiders)                         │
│ - Crawl BBVA, Galicia bank websites                │
│ - Extract discount data, terms, conditions         │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ LOAD (PostgreSQL)                                   │
│ - Raw staging tables from spider output            │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ TRANSFORM (dbt)                                     │
│ - Dimensional modeling (dims + facts)              │
│ - Data validation & quality tests                  │
│ - Business logic & aggregations                    │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ PRESENTATION (Streamlit)                            │
│ - Dashboard: Summary analytics & charts            │
│ - Explorer: Filterable discount cards              │
│ - Pagination: 20 items per page                    │
└─────────────────────────────────────────────────────┘
```

### System Components

#### 1. **Data Extraction** (`discount_tracker_scrapy/`)
- Scrapy-based spiders for each bank (`bbva.py`, `galicia.py`)
- Custom pipelines for data normalization
- Middleware for handling rate-limiting and retries
- Configurable crawling (item count limits for testing, full runs for production)

**Output**: Raw discount items with merchant, discount %, cuotas, validity, terms

#### 2. **Data Loading** (PostgreSQL + `orchestrate.py`)
- PostgreSQL 16 database (containerized)
- Staging tables populated directly from Scrapy output
- Run statistics tracked for monitoring crawler health
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
- **Profiles**: Separate `dev_docker` target for containerized runs

**Command:**
```bash
make run-dbt-build  # Execute full dbt build with tests
```

#### 4. **Data Presentation** (`discount_tracker_streamlit/`)
- Streamlit web app running on port 8501
- Two-page layout:
  - **Dashboard**: Plotly bar charts (discounts by issuer, by category)
  - **Explorer**: Filterable, paginated discount card grid
- Features:
  - Sidebar filters (search, issuer, category, valid days)
  - Real-time filtering with pandas
  - Session state management for pagination
  - Green accent theme (#00A36C) matching financial industry standards
  - Responsive grid layout with day-validity visualization

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
| **Visualization** | Plotly | 6.6.0+ |

### Data Flow Lifecycle

1. **Crawl Phase** (~15 min):
   ```bash
   make run-orchestrator    # Full crawl (all items)
   make run-orchestrator-test  # Quick test run (5 items)
   ```
   - Spiders fetch merchant pages from bank websites
   - Items validated and deduplicated by pipelines
   - Results stored in PostgreSQL `staging_discounts` table
   - Crawl metadata saved to `scrapy_run_stats` table

2. **Transform Phase** (~2 min):
   ```bash
   make run-dbt-build
   ```
   - `stg_discounts`: Sanitize discount data, parse dates, normalize fields
   - `dim_merchants`: Build merchant dimension with deduplication
   - `dim_issuers`: Bank/issuer dimension (BBVA, Galicia, etc.)
   - `fct_discounts`: Fact table with foreign keys to dimensions
   - `streamlit_data`: Flat denormalized view for UI query optimization

3. **Serve Phase** (Real-time):
   - Streamlit loads data from `streamlit_data` view every 10 min
   - Filters applied in-memory with pandas
   - Charts rendered with Plotly
   - Interactive dashboard updated on filter interaction

### Environment Configuration

Create a `.env` file in project root (see `.env` template):

```bash
# Database
DB_HOST=db              # Docker service name (or IP for cloud)
DB_NAME=discount_db
DB_USER=discount_user
DB_PASSWORD=your_secure_password
POSTGRES_DB_PORT=5432

# pgAdmin (Database UI)
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin_password
```

### Docker Services

Run all services with:
```bash
docker compose up -d --build
```

**Services** (defined in `docker-compose.yml`):
- **db**: PostgreSQL database
- **pgadmin**: pgAdmin web interface (http://localhost:8080)
- **streamlit**: Streamlit web app (http://localhost:8501)
- **orchestrator**: Scrapy + dbt runner (triggered via `make run-orchestrator`)

### Useful Commands

```bash
# Infrastructure
make up                        # Start all services
make down                      # Stop all services

# Data Pipeline
make run-orchestrator          # Execute Scrapy crawl + dbt build
make run-orchestrator-test     # Quick test run (5 items)
make run-dbt-build            # Execute dbt only

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
└── Makefile                     # Task automation
```

### Setup & Deployment

- **Local Development**: [development/local.md](development/local.md)
- **Cloud (GCP)**: [development/cloud.md](development/cloud.md)

### Contributing

When modifying the data pipeline:
1. Update Scrapy spiders in `discount_tracker_scrapy/spiders/`
2. Add dbt tests in `discount_tracker_dbt/tests/`
3. Run `make run-orchestrator-test` to validate
4. Test Streamlit UI changes locally before pushing

---

**Created with Python, Scrapy, dbt, and Streamlit** 🚀
