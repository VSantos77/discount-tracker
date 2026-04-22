import math

import scrapy


class SantanderSpider(scrapy.Spider):
    name = "santander"
    allowed_domains = ["www.santander.com.ar"]
    handle_httpstatus_all = True

    custom_settings = {
        # Santander endpoints can be slow/intermittent from containers.
        # Keep this spider independent from global timeout defaults.
        # robots.txt is still respected, but timeout/retry are kept short.
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_TIMEOUT": 20,
        "RETRY_TIMES": 2,
    }

    PAGE_SIZE = 12
    LIST_URL = "https://www.santander.com.ar/bff-benefits/brands?page={page}&limit={limit}"
    DETAIL_URL = "https://www.santander.com.ar/bff-benefits/brands/{brand_id}"

    def __init__(self, page_limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.page_limit = int(page_limit) if page_limit else None
        except ValueError as exc:
            raise ValueError("page_limit must be an integer") from exc

    async def start(self):
        self.logger.info("Starting Santander crawl from %s", self.LIST_URL.format(page=1, limit=self.PAGE_SIZE))
        yield scrapy.Request(
            url=self.LIST_URL.format(page=1, limit=self.PAGE_SIZE),
            callback=self.parse_brands,
            errback=self.errback_request,
            meta={"page": 1},
        )

    def parse_brands(self, response):
        self.logger.info("List response page=%s status=%s", response.meta.get("page", 1), response.status)

        if response.status != 200:
            self.logger.error("Santander list request failed. status=%s url=%s", response.status, response.url)
            return

        payload = response.json()
        items = payload.get("items", [])
        current_page = response.meta.get("page", 1)

        total_items = payload.get("totalItems")
        if current_page == 1 and total_items is not None:
            self.crawler.stats.set_value("custom/total_items_reported", total_items)
            self.logger.info("SANTANDER: totalItems reported by API: %s", total_items)

        for item in items:
            brand_id = item.get("id")
            if brand_id is None:
                continue

            yield scrapy.Request(
                url=self.DETAIL_URL.format(brand_id=brand_id),
                headers=self.custom_headers,
                callback=self.parse_brand_detail,
                errback=self.errback_request,
                meta={"brand_id": brand_id},
            )

        if not items:
            return

        if self.page_limit and current_page >= self.page_limit:
            self.logger.info("Reached page limit: %s", self.page_limit)
            return

        total_pages = None
        if total_items is not None:
            total_pages = max(1, math.ceil(total_items / self.PAGE_SIZE))

        if total_pages is not None and current_page >= total_pages:
            return

        next_page = current_page + 1
        yield scrapy.Request(
            url=self.LIST_URL.format(page=next_page, limit=self.PAGE_SIZE),
            headers=self.custom_headers,
            callback=self.parse_brands,
            errback=self.errback_request,
            meta={"page": next_page},
        )

    def parse_brand_detail(self, response):
        if response.status != 200:
            self.logger.warning(
                "Skipping detail id=%s due to status=%s",
                response.meta.get("brand_id"),
                response.status,
            )
            return

        # Keep payload raw and let dbt own all parsing/normalization logic.
        yield response.json()

    def errback_request(self, failure):
        request = failure.request
        self.logger.error("Request failed url=%s err=%s", request.url, failure.value)
