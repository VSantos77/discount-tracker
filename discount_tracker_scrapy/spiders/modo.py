import scrapy


class ModoSpider(scrapy.Spider):
    name = "modo"
    allowed_domains = ["www.modo.com.ar"]

    # All slots visible on the /promos hub page, filtered to actively running promos.
    # Page size is set to total_results on the first response to fetch everything in one pass;
    # if that fails we fall back to standard pagination with BATCH_SIZE per request.
    BATCH_SIZE = 100

    API_BASE = (
        "https://www.modo.com.ar/promos/api/rewards/slots"
        "?slots=web-modo-hub-carrousel_principal"
        "%2Cweb-modo-hub-destacadas"
        "%2Cweb-modo-hub-supermercados"
        "%2Cweb-modo-hub-exclusivas-online"
        "%2Cweb-modo-hub-promos-financiacion"
        "%2Cweb-modo-hub-mas-promos"
        "&banks=&fcalcstatus=running&fdoweeks=&fflow="
        "&categories=&source=web_modo&origin=web_modo"
        "&search_text=&search_ia=false"
    )

    def __init__(self, itemcount=None, page_limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.itemcount = int(itemcount) if itemcount else None
        except ValueError:
            raise ValueError("itemcount must be an integer")
        try:
            self.page_limit = int(page_limit) if page_limit else None
        except ValueError:
            raise ValueError("page_limit must be an integer")

    def start_requests(self):
        if self.itemcount:
            # Fetch exactly itemcount records in one request — no metadata probe needed
            yield scrapy.Request(
                url=f"{self.API_BASE}&limit={self.itemcount}&page=1",
                callback=self.parse_page,
                meta={"page": 1, "total_pages": 1},
            )
        else:
            # Fetch page 1 with limit=1 to read total_results, then fetch all at once
            yield scrapy.Request(
                url=f"{self.API_BASE}&limit=1&page=1",
                callback=self.parse_first,
            )

    def parse_first(self, response):
        total = response.json().get("metadata", {}).get("pagination", {}).get("total_results", 0)
        self.logger.info(f"MODO: {total} active promotions found")

        if self.page_limit:
            # Test mode: paginate normally with BATCH_SIZE
            yield from self._request_page(1)
        else:
            # Fetch everything in a single request
            yield scrapy.Request(
                url=f"{self.API_BASE}&limit={total}&page=1",
                callback=self.parse_page,
                meta={"page": 1, "total_pages": 1},
            )

    def parse_page(self, response):
        body = response.json()
        cards = body.get("data", {}).get("cards", [])

        for card in cards:
            yield card

        pagination = body.get("metadata", {}).get("pagination", {})
        current_page = pagination.get("page", 1)
        total_pages = pagination.get("total_pages", 1)

        if self.page_limit and current_page >= self.page_limit:
            self.logger.info(f"Reached page limit: {self.page_limit}")
            return

        if current_page < total_pages:
            yield from self._request_page(current_page + 1)

    def _request_page(self, page):
        yield scrapy.Request(
            url=f"{self.API_BASE}&limit={self.BATCH_SIZE}&page={page}",
            callback=self.parse_page,
            meta={"page": page},
        )

