output "bucket_name" {
  value       = google_storage_bucket.data_lake.name
  description = "The name of the GCS bucket for Scrapy uploads"
}

output "bigquery_dataset" {
  value       = google_bigquery_dataset.dataset_raw_source.dataset_id
  description = "The BigQuery dataset ID for dbt"
}