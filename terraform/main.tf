# Resources have been split into component files:
#   storage.tf   — GCS bucket, BigQuery datasets, raw_discounts external table
#   jobs.tf      — Scrapy and dbt service accounts, IAM, Cloud Run jobs
#   workflow.tf  — Workflows SA, IAM, workflow definition, Cloud Scheduler
#   monitoring.tf — Log-based metrics for scrapy stats
