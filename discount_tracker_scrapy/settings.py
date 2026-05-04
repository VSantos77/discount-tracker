# Scrapy settings for discount_tracker_scrapy project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import datetime as _dt
import os

GCS_BUCKET = os.getenv('GCS_BUCKET', '')
_today = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d')
GCS_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '')
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'local')

BOT_NAME = "discount_tracker_scrapy"

SPIDER_MODULES = ["discount_tracker_scrapy.spiders"]
NEWSPIDER_MODULE = "discount_tracker_scrapy.spiders"

ADDONS = {}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Concurrency and throttling settings
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.5

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    "discount_tracker_scrapy.middlewares.DiscountTrackerScrapySpiderMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "discount_tracker_scrapy.middlewares.DiscountTrackerScrapyDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# No active item pipelines — export is handled by FEEDS below.
ITEM_PIPELINES = {
    "discount_tracker_scrapy.pipelines.RawPayloadWrapperPipeline": 100,
}

# Feed exports: one .jsonl file per spider per run.
# STORAGE_BACKEND=gcs  → writes to gs://<GCS_BUCKET>/landing/<spider>/<YYYY>/<MM>/<DD>/<timestamp>.jsonl
# STORAGE_BACKEND=local → writes to data/landing/<spider>/<timestamp>.jsonl (default)
_feed_uri = (
    f'gs://{GCS_BUCKET}/landing/spider=%(name)s/scraped_at_dt={_today}/%(time)s.jsonl'
    if STORAGE_BACKEND == 'gcs'
    else 'data/landing/%(name)s/%(time)s.jsonl'
)
FEEDS = {
    _feed_uri: {
        'format': 'jsonlines',
        'encoding': 'utf8',
        'store_empty': False,
        'overwrite': True,
    }
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"