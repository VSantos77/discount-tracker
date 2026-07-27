resource "google_storage_bucket" "data_lake" {
  name          = "${var.gcp_project_id}-discount-lake"
  location      = var.gcp_region
  force_destroy = true

  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_bigquery_dataset" "dataset_raw_source" {
  dataset_id    = "raw_source"
  friendly_name = "Raw Source Data"
  description   = "Warehouse for raw discount data from spiders (bronze layer)"
  location      = var.gcp_region
}

resource "google_bigquery_dataset" "dataset_prod_dbt_staged" {
  dataset_id    = "prod_dbt_staged"
  friendly_name = "Production DBT Staged Data"
  description   = "Warehouse for staging and intermediate tables (silver layer)"
  location      = var.gcp_region
}

resource "google_bigquery_dataset" "dataset_prod_dbt_analytics" {
  dataset_id    = "prod_dbt_analytics"
  friendly_name = "Production DBT Analytics Data"
  description   = "Warehouse for marts data (gold layer)"
  location      = var.gcp_region
}

resource "google_bigquery_dataset" "dataset_dev_dbt_staged" {
  dataset_id    = "dev_dbt_staged"
  friendly_name = "Development DBT Staged Data"
  description   = "Warehouse for staging and intermediate tables (silver layer)"
  location      = var.gcp_region
}

resource "google_bigquery_dataset" "dataset_dev_dbt_analytics" {
  dataset_id    = "dev_dbt_analytics"
  friendly_name = "Development DBT Analytics Data"
  description   = "Warehouse for marts data (gold layer)"
  location      = var.gcp_region
}

resource "google_bigquery_table" "raw_discounts" {
  dataset_id          = google_bigquery_dataset.dataset_raw_source.dataset_id
  table_id            = "raw_discounts"
  deletion_protection = false

  external_data_configuration {
    autodetect    = false
    source_format = "NEWLINE_DELIMITED_JSON"
    source_uris   = ["gs://${google_storage_bucket.data_lake.name}/landing/*"]

    hive_partitioning_options {
      mode                     = "AUTO"
      source_uri_prefix        = "gs://${google_storage_bucket.data_lake.name}/landing"
      require_partition_filter = true
    }
  }
}
