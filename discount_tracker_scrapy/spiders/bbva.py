import scrapy
from discount_tracker_scrapy.items import DiscountItem, BBVADiscountLoader
from scrapy.exceptions import CloseSpider

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

    # Starting with Page 1 of the catalog
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

        for category in categories_ls:

            category_id = category.get('idRubro')
            category_name = category.get('nombre')

            # Yield one request for each category, starting with page 1
            yield scrapy.Request(
                url=self.base_catalog_url.format(1, category_id),
                meta={'category_name': category_name, 'page': 1},
                callback=self.parse_catalog,
            )

    def parse_catalog(self, response):

        discounts = response.json()['data']
        
        if not discounts:
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
        else:
            next_page = current_page + 1
            yield scrapy.Request(
                url=self.base_catalog_url.format(next_page, response.meta['category_name']),
                callback=self.parse_catalog,
                meta={'page': next_page, 'category_name': response.meta['category_name']}
            )

    def parse_details(self, response):

        self.logger.info(f"Parsing details for discount ID: {response.meta['discount_id']}")

        data = response.json()['data']
        
        loader = BBVADiscountLoader(item=DiscountItem(), response=response)

        loader.add_value('issuer_name', "Banco BBVA")
        loader.add_value('merchant_name', data.get('cabecera'))
        loader.add_value('discount_name', data.get('cabecera'))
        loader.add_value('discount_description', response.meta['subcabecera'])
        loader.add_value('discount_url', self.discount_url.format(response.meta['discount_id']))
        loader.add_value('discount_start_date', response.meta['discount_start_date'])
        loader.add_value('discount_end_date', response.meta['discount_end_date'])
        loader.add_value('discount_terms_and_conditions', data.get('basesCondiciones'))
        loader.add_value('discount_rate', data.get('cabecera', ''))
        loader.add_value('discount_max_discount_amount', data.get('beneficios')[0].get('tope'))
        loader.add_value('discount_min_purchase_amount', None)
        loader.add_value('discount_no_interest_installment_qty', data.get('beneficios')[0].get('cuota'))
        loader.add_value('discount_valid_days_list', data.get('diasPromo'))
        loader.add_value('discount_valid_online', len(data.get('canalesVenta').get('web')))
        loader.add_value('discount_valid_instore', len(data.get('canalesVenta').get('sucursales')))
        loader.add_value('discount_metadata', data)
        loader.add_value('discount_payment_method', data.get('grupoTarjeta'))
        loader.add_value('merchant_category_name', response.meta['category_name'])

        yield loader.load_item()