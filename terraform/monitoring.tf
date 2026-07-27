locals {
  scrapy_log_filter = join("\n", [
    "resource.type=\"cloud_run_job\"",
    "resource.labels.job_name=\"discount-tracker-scrapy-job\"",
    "logName=\"projects/${var.gcp_project_id}/logs/run.googleapis.com%2Fstderr\"",
    "textPayload=~\"WORKFLOW_STATS\"",
  ])

  spider_label_extractor = "REGEXP_EXTRACT(textPayload, \"spider[^a-z]+([a-z]+)\")"

  exponential_buckets = {
    num_finite_buckets = 64
    growth_factor      = 2
    scale              = 1
  }
}

resource "google_logging_metric" "scrapy_items_scraped" {
  name        = "scrapy/items_scraped"
  description = "Items scraped per spider run"
  filter      = local.scrapy_log_filter

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    display_name = "Scrapy Items Scraped"
    labels {
      key        = "spider"
      value_type = "STRING"
    }
  }

  value_extractor  = "REGEXP_EXTRACT(textPayload, \"item_scraped_count[^0-9]+([0-9]+)\")"
  label_extractors = { spider = local.spider_label_extractor }
  bucket_options {
    exponential_buckets {
      num_finite_buckets = local.exponential_buckets.num_finite_buckets
      growth_factor      = local.exponential_buckets.growth_factor
      scale              = local.exponential_buckets.scale
    }
  }
}

resource "google_logging_metric" "scrapy_elapsed_seconds" {
  name        = "scrapy/elapsed_seconds"
  description = "Spider run duration in seconds"
  filter      = local.scrapy_log_filter

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    display_name = "Scrapy Elapsed Seconds"
    labels {
      key        = "spider"
      value_type = "STRING"
    }
  }

  value_extractor  = "REGEXP_EXTRACT(textPayload, \"elapsed_time_seconds[^0-9]+([0-9.]+)\")"
  label_extractors = { spider = local.spider_label_extractor }
  bucket_options {
    exponential_buckets {
      num_finite_buckets = local.exponential_buckets.num_finite_buckets
      growth_factor      = local.exponential_buckets.growth_factor
      scale              = local.exponential_buckets.scale
    }
  }
}

resource "google_logging_metric" "scrapy_responses_per_minute" {
  name        = "scrapy/responses_per_minute"
  description = "HTTP responses per minute per spider run"
  filter      = local.scrapy_log_filter

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    display_name = "Scrapy Responses Per Minute"
    labels {
      key        = "spider"
      value_type = "STRING"
    }
  }

  value_extractor  = "REGEXP_EXTRACT(textPayload, \"responses_per_minute[^0-9]+([0-9.]+)\")"
  label_extractors = { spider = local.spider_label_extractor }
  bucket_options {
    exponential_buckets {
      num_finite_buckets = local.exponential_buckets.num_finite_buckets
      growth_factor      = local.exponential_buckets.growth_factor
      scale              = local.exponential_buckets.scale
    }
  }
}

resource "google_logging_metric" "scrapy_items_per_minute" {
  name        = "scrapy/items_per_minute"
  description = "Items scraped per minute per spider run"
  filter      = local.scrapy_log_filter

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    display_name = "Scrapy Items Per Minute"
    labels {
      key        = "spider"
      value_type = "STRING"
    }
  }

  value_extractor  = "REGEXP_EXTRACT(textPayload, \"items_per_minute[^0-9]+([0-9.]+)\")"
  label_extractors = { spider = local.spider_label_extractor }
  bucket_options {
    exponential_buckets {
      num_finite_buckets = local.exponential_buckets.num_finite_buckets
      growth_factor      = local.exponential_buckets.growth_factor
      scale              = local.exponential_buckets.scale
    }
  }
}

resource "google_logging_metric" "scrapy_403_responses" {
  name        = "scrapy/403_responses"
  description = "403 responses per spider run — key signal for blocking/anti-scraping"
  filter      = local.scrapy_log_filter

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    display_name = "Scrapy 403 Responses"
    labels {
      key        = "spider"
      value_type = "STRING"
    }
  }

  value_extractor  = "REGEXP_EXTRACT(textPayload, \"response_status_count/403[^0-9]+([0-9]+)\")"
  label_extractors = { spider = local.spider_label_extractor }
  bucket_options {
    exponential_buckets {
      num_finite_buckets = local.exponential_buckets.num_finite_buckets
      growth_factor      = local.exponential_buckets.growth_factor
      scale              = local.exponential_buckets.scale
    }
  }
}
