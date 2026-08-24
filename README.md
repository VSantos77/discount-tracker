# 💸 Discount Tracker | Catalogo de Descuentos

Discount Tracker ("Catalogo de Descuentos") is a platform that helps track discounts for different banks and other issuing entities in Argentina, implementing a full ELT cloud data pipeline. It scrapes live discount data from various sources, standardizes and validates it using dbt, and serves the curated result in a [Streamlit Dashboard](https://catalogo-de-descuentos.streamlit.app/).

[app-demo.webm](https://github.com/user-attachments/assets/05bc775f-d1ac-4913-a4f1-083811ed85be)

> NOTE: The UI is in Spanish because the target audience is in Argentina. Browser translation usually works well if you want to inspect it in another language.

## Overview

<img width="801" height="446" alt="Discount Tracker - Architecture overview drawio" src="https://github.com/user-attachments/assets/94e0d6ef-a6e4-4609-89ad-30d392b0f54d" />

## How the system works

1. Scrapy spiders collect promotions from issuer websites.
2. The scraper writes raw JSONL files to a GCS bucket.
3. BigQuery exposes the raw landing zone as an external table.
4. dbt transforms the raw data into staging, intermediate, and analytics models.
5. Streamlit reads only the curated BigQuery models and renders the user-facing dashboard.
6. Terraform provisions the cloud resources, service accounts, datasets, Cloud Workflows, Cloud Scheduler, and Cloud Run jobs that tie the pipeline together.

## Main components

### Scraping

The scraper lives in [discount_tracker_scrapy](discount_tracker_scrapy). It contains the Scrapy project, spiders, pipelines, and runtime settings for collecting issuer promotions and sending raw output to object storage. One spider per active entity is implemented.

The active scraper configuration is centered in [discount_tracker_scrapy/settings.py](discount_tracker_scrapy/settings.py). It expects `GCP_PROJECT_ID`, `GCS_BUCKET`, and `STORAGE_BACKEND` at runtime.

### Transformation

The dbt project lives in [discount_tracker_dbt](discount_tracker_dbt). It defines the warehouse model layers and the tests that enforce data quality.

Models are organized in a medallion-style layering:

- **[sources](discount_tracker_dbt/models/staging/sources.yml)** — the `raw_discounts` BigQuery external table over the GCS bucket, hive-partitioned by spider name and scrape date. One row per scraped record, holding the raw JSON payload.
- **[staging](discount_tracker_dbt/models/staging/)** — one model per entity, parsing and normalizing fields out of the raw payload.
- **[intermediate](discount_tracker_dbt/models/intermediate/)** — consolidates discounts across sources, applying filtering, renaming, and deduplication (source- and business-level).
- **[analytics/core](discount_tracker_dbt/models/analytics/core/)** — the curated data layer, served via `fct_discounts`.
- **[analytics/streamlit](discount_tracker_dbt/models/analytics/streamlit/)** — presentation layer consumed by the Streamlit app.


### Presentation

The dashboard lives in [discount_tracker_streamlit/app.py](discount_tracker_streamlit/app.py).

It connects to BigQuery using a service account from `st.secrets`, then loads curated SQL queries from [discount_tracker_streamlit/utils/queries](discount_tracker_streamlit/utils/queries) and renders:

- a discounts guided search page
- a discount issuer status view with scrape freshness and counts

The Streamlit app keeps its own runtime dependencies in [discount_tracker_streamlit/requirements.txt](discount_tracker_streamlit/requirements.txt) for easier hosting on Streamlit Cloud.

### Infrastructure

Terraform lives in [terraform](terraform). It provisions the bucket, BigQuery datasets, Cloud Run jobs, service accounts, and the workflow that orchestrates the pipeline in GCP.

Orchestration is handled by a Cloud Workflow that runs the scraper and dbt jobs, with Cloud Scheduler used to trigger that workflow on a schedule.

This is where the deployment boundary is enforced:

- scraper jobs only need storage and job permissions
- dbt jobs need BigQuery access and read access to the raw landing zone
- the workflow service account only needs permission to trigger and observe jobs

### CI/CD

Two GitHub Actions pipelines ([.github/workflows/](.github/workflows/)) test and deploy the scrapy and dbt components independently on every push to `main`: run the relevant tests (real spider crawls for scrapy, `dbt build --target ci` against a dev dataset for dbt), then on a successful push to `main` build and push a Docker image and roll it out to the corresponding Cloud Run job. See [ARCHITECTURE.md §10](ARCHITECTURE.md#10-cicd) for the full pipeline breakdown.

## Key design decisions

- One repository, multiple runtimes. The repo keeps the scraper, warehouse logic, and dashboard together so the data flow stays visible, but each runtime has a clear boundary.
- Raw files land in object storage (GCS) and are exposed to BigQuery via external table. This provides flexibility in case the parsing logic changes and allows the scraper to focus exclusively on extraction.
- Hive partitioning on the raw external table keeps reads focused on the scraped date partitions that matter, instead of forcing every query to scan the full landing zone.
- dbt implements a medallion-style structure: raw data is parsed on the bronze (staging) layer, consolidated and validated step by step on silver (intermediate), and published as gold (analytics/core, analytics/streamlit) models for the dashboard. There's no separate dimensional layer — the fact table carries issuer and merchant category as plain columns rather than joining out to dimension tables, since the data volume doesn't justify the extra indirection.
- dbt tests are applied throughout the pipeline, layer by layer: source tests validate incoming payload structure; staging tests validate parsing output and core business rules; intermediate tests confirm deduplication and category-resolution logic hold; analytics tests confirm the fact table and its streamlit-facing views stay consistent with each other.
- Streamlit reads curated data only. The app is intentionally presentation-only, so it stays lightweight and easier to run locally or deploy separately.
- Terraform owns the cloud shape. Infrastructure, IAM, datasets, and Cloud Run jobs are declared as code so the environment can be recreated consistently.
- Scrapy and dbt runners each install only the required dependencies, keeping docker image size as low as possible.
- CI/CD deploys are gated on tests passing and only run on a direct push to `main` — pull requests run tests but never deploy.

## Setup

The repo is Python 3.12+ and uses `uv` at the root.

For cloud deployment, see [docs/cloud-setup.md](docs/cloud-setup.md).

## Environment variables

The current architecture uses a small set of runtime variables:

- `GCP_PROJECT_ID` for the scraper, dbt profile, and cloud resources
- `GCP_REGION` for dbt and Terraform
- `GCS_BUCKET` for the scraper output bucket
- `STORAGE_BACKEND` to choose the scraper storage target

Terraform also expects the corresponding inputs:

- `TF_VAR_gcp_project_id`
- `TF_VAR_gcp_region`
- `TF_VAR_owner_email`
- `TF_VAR_notification_email`

The Streamlit app uses `st.secrets` for its BigQuery service account instead of environment-based auth.

## Repository layout

```text
discount-tracker/
├── discount_tracker_scrapy/      # Scrapy project, spiders, pipelines, runtime settings
├── discount_tracker_dbt/         # dbt project, packages, models, tests
├── discount_tracker_streamlit/   # Streamlit dashboard app and app-local assets
├── terraform/                    # GCP infrastructure as code
├── .github/workflows/            # CI/CD pipelines (test + deploy, scrapy and dbt)
├── tests/                        # pytest suite (scrapy spider output validation)
├── docs/                         # supplementary guides (cloud setup, ...)
├── scripts/                      # operational scripts (e.g. Cloud Workflow integration test suite)
├── resources/                    # static assets referenced from docs (e.g. this README)
├── Dockerfile                    # container build for the non-UI runtime paths
├── pyproject.toml                # root project metadata and shared dependency groups
├── uv.lock                       # locked Python dependencies
├── scrapy.cfg                    # Scrapy entrypoint configuration
├── ARCHITECTURE.md               # technical deep-dive: internals, GCP resources, IAM, CI/CD
└── README.md                     # project overview and setup guide
```

## Technology stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+
| Scraping | Scrapy |
| Warehouse | BigQuery |
| Storage | Google Cloud Storage |
| Transformation | dbt |
| Dashboard | Streamlit |
| IaC | Terraform |
| Runtime orchestration | Google Cloud Scheduler + Workflows + Run Jobs |
