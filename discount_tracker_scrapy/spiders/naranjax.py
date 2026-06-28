import json
import math
import scrapy
from scrapy.exceptions import CloseSpider


class NaranjaXSpider(scrapy.Spider):
    name = "naranjax"
    allowed_domains = ["bkn-promotions.naranjax.com"]

    _catalog_url = "https://bkn-promotions.naranjax.com/bff-promotions-web/api/binder/filter"
    _detail_url = "https://bkn-promotions.naranjax.com/bff-promotions-web/api/binder/{commerce}/detail/{plan}"
    _page_size = 10

    # The BFF validates that requests look like same-site browser fetches.
    # These headers mirror what Chrome sends for an XHR from naranjax.com.
    _base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.naranjax.com",
        "Referer": "https://www.naranjax.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    def __init__(self, page_limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.page_limit = int(page_limit) if page_limit else None
        except ValueError:
            raise ValueError("page_limit must be an integer")

    def _catalog_post(self, page):
        body = {
            "filters": {
                "geoposition": {
                    "latitude": "-34.61315",
                    "longitude": "-58.37723",
                    "zoom": "30km",
                }
            },
            "pageOptions": {"page": page, "size": self._page_size},
        }
        return scrapy.Request(
            url=self._catalog_url,
            method="POST",
            headers=self._base_headers,
            body=json.dumps(body),
            callback=self.parse_catalog,
            meta={"page": page},
        )

    def _detail_post(self, catalog_item):
        url = self._detail_url.format(
            commerce=catalog_item["url"],
            plan=catalog_item["urlDetail"],
        )
        return scrapy.Request(
            url=url,
            method="POST",
            headers=self._base_headers,
            body=json.dumps({
                "payload": {
                    "latitude": -34.61315,
                    "longitude": -58.37723,
                    "province": "Buenos Aires",
                    "locality": "",
                }
            }),
            callback=self.parse_detail,
            meta={"catalog": catalog_item},
        )

    def start_requests(self):
        yield self._catalog_post(page=1)

    handle_httpstatus_list = [400, 403, 422, 429, 500]
    custom_settings = {"ROBOTSTXT_OBEY": False}

    def parse_catalog(self, response):
        if response.status != 200:
            self.logger.error(
                f"Catalog request failed — status {response.status}, body: {response.text[:500]}"
            )
            raise CloseSpider(reason=f"Unexpected status {response.status} on page {response.meta['page']}")

        data = response.json()

        for item in data["data"]:
            if item.get("urlDetail"):
                # Single-plan item: fetch detail for exact numeric fields and legal text
                yield self._detail_post(item)
            else:
                # Multi-plan item: plans are unnested in the staging layer from catalog data
                yield item
                self.crawler.stats.inc_value("custom/items_scraped/naranjax")

        # On page 1, read the total and fan out all remaining pages concurrently
        if response.meta["page"] == 1:
            info = data["info"]
            total_pages = math.ceil(info["total"] / info["itemsByPage"])
            limit = min(total_pages, self.page_limit) if self.page_limit else total_pages
            for page in range(2, limit + 1):
                yield self._catalog_post(page=page)

    def parse_detail(self, response):
        catalog = response.meta["catalog"]
        if response.status != 200:
            self.logger.warning(
                f"Detail fetch failed ({response.status}) for "
                f"{catalog['url']}/{catalog['urlDetail']}, falling back to catalog data"
            )
            yield catalog
        else:
            detail = response.json()
            # Drop the list of individual store locations — it can be very large
            # and isn't useful for the discount data model
            detail.pop("commerces", None)
            yield {**catalog, "detail": detail}
        self.crawler.stats.inc_value("custom/items_scraped/naranjax")
