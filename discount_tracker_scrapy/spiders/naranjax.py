import json
import math
import scrapy
from scrapy.exceptions import CloseSpider


class NaranjaXSpider(scrapy.Spider):
    name = "naranjax"
    allowed_domains = ["bkn-promotions.naranjax.com"]

    _base_url = 'https://bkn-promotions.naranjax.com/bff-promotions-web/api/binder'
    _catalog_url = f"{_base_url}/filter"
    _commerce_url = _base_url + "/{commerce}"
    _detail_url = _base_url + "/{commerce}/detail/{plan}"
    _page_size = 10

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

    def _detail_post(self, commerce, plan, discount_url):
        url = self._detail_url.format(
            commerce=commerce,
            plan=plan,
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
            meta={
                    'commerce' : commerce,
                    'plan' : plan,
                    'discount_url' : discount_url
                },
        )

    def _multi_plan_post(self, multi_plan_item):

        # Send request for multi plan commerces
        commerce = multi_plan_item.get('url')
        discount_url = multi_plan_item.get('fullUrl')

        url = self._commerce_url.format(
            commerce=commerce
        )

        return scrapy.Request(
            url=url,
            method='POST',
            headers=self._base_headers,
            body=json.dumps({
                "payload": {
                    "latitude": -34.61315,
                    "longitude": -58.37723,
                    "province": "Buenos Aires",
                    "locality": "",
                }
            }),
            callback=self.parse_multiplan,
            meta={
                'commerce' : commerce,
                'discount_url' : discount_url
            },
        )

    def start_requests(self):
        yield self._catalog_post(page=1)

    handle_httpstatus_list = [400, 403, 422, 429, 500]
    # custom_settings = {"ROBOTSTXT_OBEY": False}

    def parse_catalog(self, response):

        # If response fails, close spider and log error
        if response.status != 200:
            self.logger.error(
                f"Catalog request failed — status {response.status}, body: {response.text[:500]}"
            )
            raise CloseSpider(reason=f"Unexpected status {response.status} on page {response.meta['page']}")

        data = response.json()

        for item in data["data"]:
            if item.get("urlDetail"):
                # Single-plan item: send request for details
                yield self._detail_post(
                    item.get('url'), 
                    item.get('urlDetail'),
                    item.get('fullUrl')
                )
            else:
                # Multi-plan item: send request for plans specifics
                yield self._multi_plan_post(item)

        # On page 1, read the total and fan out all remaining pages concurrently
        if response.meta["page"] == 1:
            info = data["info"]
            total_pages = math.ceil(info["total"] / info["itemsByPage"])
            limit = min(total_pages, self.page_limit) if self.page_limit else total_pages
            for page in range(2, limit + 1):
                yield self._catalog_post(page=page)

    def parse_detail(self, response):
        commerce = response.meta['commerce']
        plan = response.meta['plan']

        if response.status != 200:
            self.logger.warning(
                f"Detail fetch failed ({response.status}) for "
                f"{commerce}/{plan}"
            )
        else:
            detail = response.json()
            # Drop the list of individual store locations — it can be very large
            # and isn't useful for the discount data model
            detail.pop("commerces", None)

            yield {
                    'id' : f'{commerce}_{plan}',
                    'discount_url' : response.meta['discount_url'],
                    **detail
            }
            self.crawler.stats.inc_value("custom/items_scraped/naranjax")

    def parse_multiplan(self, response):
        commerce = response.meta['commerce']
        discount_url_base = response.meta['discount_url']

        if response.status != 200:
            self.logger.warning(
                f"Multi plan fetch failed ({response.status}) for "
                f"{commerce}"
            )

        # Generate one details request for each plan within commerce
        else:
            plan_url_list = [item['url'] for item in response.json()['nearCurrent']]

            for plan in plan_url_list:
                discount_url = f'{discount_url_base}/{plan}'
                yield self._detail_post(commerce, plan, discount_url)