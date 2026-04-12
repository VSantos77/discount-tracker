import scrapy
from scrapy.exceptions import CloseSpider
import re

class BBVASpider(scrapy.Spider):
    name = "bbva"
    allowed_domains = ["go.bbva.com.ar", "bbva.com.ar"]

    def __init__(self, page_limit=None, *args, **kwargs):
        super(BBVASpider, self).__init__(*args, **kwargs)
        # Convert the string arg to an int, or None if not provided
        try:
            self.page_limit = int(page_limit) if page_limit else None
        except ValueError:
            raise(ValueError("page_limit must be an integer"))

    # Starting with Page 0 of the catalog
    base_catalog_url = "https://go.bbva.com.ar/willgo/fgo/API/v3/communications?&pager={}&rubros={}"
    detail_api_url = "https://go.bbva.com.ar/willgo/fgo/API/v3/communication/{}"
    discount_url = 'https://www.bbva.com.ar/beneficios/beneficio?id={}'
    category_url = 'https://go.bbva.com.ar/willgo/fgo/API/v3/rubros/filtro'

    def start_requests(self):
        # Get category list
        yield scrapy.Request(url=self.category_url, callback=self.parse_categories)

    def parse_categories(self, response):
        self.logger.info("Parsing categories")

        # If the response is not 200, stop the spider with an error
        if response.status != 200:
            raise CloseSpider(reason=f"Failed to fetch categories: HTTP {response.status}")
                    
        categories_ls = response.json()['rubros']

        self.logger.info('Categories to be parsed: {}'.format([cat.get('nombre') for cat in categories_ls]))

        for category in categories_ls:

            category_id = category.get('idRubro')
            category_name = category.get('nombre')

            # Yield one request for each category, starting with page 0
            yield scrapy.Request(
                url=self.base_catalog_url.format(0, category_id),
                meta={
                    'category_name': category_name,
                    'category_id' : category_id,
                    'page': 0
                },
                callback=self.parse_catalog,
            )

    def parse_catalog(self, response):
        
        # Get total page number
        if not response.meta.get('page_limit_api'):
            paginas_raw = response.json()['message']
            page_limit_api = re.search(r'paginas:\s*(\d+)', paginas_raw).group(1)

            if page_limit_api:
                page_limit_api = int(page_limit_api)
                self.logger.info(
                    f"API page limit for category '{response.meta['category_name']}': {page_limit_api}"
                )
            else:
                page_limit_api = 999 # No limit
        else:
            page_limit_api = response.meta['page_limit_api']

        discounts = response.json()['data']
        
        if not discounts or len(discounts) == 0:
            self.logger.info("No more discounts found. Stopping.")
            return
        
        # Parse some basic info
        for discount in discounts:
            discount_data = {}
            discount_data['discount_id'] = discount.get('id')
            discount_data['discount_start_date'] = discount.get('fechaDesde')
            discount_data['discount_end_date'] = discount.get('fechaHasta')
            discount_data['subcabecera'] = discount.get('subcabecera')
            discount_data['category_name'] = response.meta['category_name']

            if discount_data['discount_id']:
                # Dispatch a request for the specific details of this discount
                yield scrapy.Request(
                    url=self.detail_api_url.format(discount_data['discount_id']),
                    callback=self.parse_details,
                    meta = discount_data
                )

        current_page = response.meta['page']

        # Generate request for next page if we haven't reached the page limit
        if self.page_limit and current_page >= self.page_limit:
            self.logger.info(f"Reached page limit: {self.page_limit}")
            return
        # If no explicit limit defined, stop at API defined page limit
        elif not self.page_limit:
            if current_page >= page_limit_api:
                self.logger.info(
                    f"Reached API page limit for category: '{response.meta['category_name']}': {page_limit_api}"
                )
                return
        
        # Else, return request for next page
        next_page = current_page + 1
        yield scrapy.Request(
            url=self.base_catalog_url.format(next_page, response.meta['category_id']),
            callback=self.parse_catalog,
            meta={
                'category_name': response.meta['category_name'],
                'category_id': response.meta['category_id'],
                'page': next_page,
                'page_limit_api' : page_limit_api
            }
        )

    def parse_details(self, response):

        self.logger.info(f"Parsing details for discount ID: {response.meta['discount_id']}")

        data = response.json()['data']

        yield {
            # Catalog-level meta (raw strings from the catalog API response)
            'source_id': response.meta['discount_id'],
            'discount_start_date': response.meta['discount_start_date'],
            'discount_end_date': response.meta['discount_end_date'],
            'subcabecera': response.meta['subcabecera'],
            'category_name': response.meta['category_name'],
            # Full detail API response — untransformed
            **data,
        }

        # Keep track of discounts scraped per category
        self.crawler.stats.inc_value(f'custom/items_scraped/{response.meta["category_name"]}')