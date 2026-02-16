import scrapy
from discount_tracker_scrapy.items import DiscountItem, BBVADiscountLoader

class BBVASpider(scrapy.Spider):
    name = "bbva"
    allowed_domains = ["go.bbva.com.ar", "bbva.com.ar"]
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'CONCURRENT_REQUESTS': 5, # Be gentle with bank APIs to avoid IP bans
        'DOWNLOAD_DELAY': 1,      # 1 second between requests
    }

    def __init__(self, page_limit=None, *args, **kwargs):
        super(BBVASpider, self).__init__(*args, **kwargs)
        # Convert the string arg to an int, or None if not provided
        try:
            self.page_limit = int(page_limit) if page_limit else None
        except ValueError:
            raise(ValueError("page_limit must be an integer"))

    # Starting with Page 1 of the catalog
    base_catalog_url = "https://go.bbva.com.ar/willgo/fgo/API/v3/communications?&pager={}"
    detail_api_url = "https://go.bbva.com.ar/willgo/fgo/API/v3/communication/{}"
    discount_url = 'https://www.bbva.com.ar/beneficios/beneficio?id={}'

    def start_requests(self):
        # Start the crawl at page 1
        yield scrapy.Request(url=self.base_catalog_url.format(1), callback=self.parse_catalog, meta={'page': 1})

    def parse_catalog(self, response):

        discounts = response.json()['data']
        
        if not discounts:
            self.logger.info("No more discounts found. Stopping.")
            return

        for discount in discounts:
            discount_data = {}
            discount_data['discount_id'] = discount.get('id')
            discount_data['discount_start_date'] = discount.get('fechaDesde')
            discount_data['discount_end_date'] = discount.get('fechaHasta')
            discount_data['subcabecera'] = discount.get('subcabecera')

            if discount_data['discount_id']:
                # Dispatch a request for the specific details of this discount
                yield scrapy.Request(
                    url=self.detail_api_url.format(discount_data['discount_id']),
                    callback=self.parse_details,
                    meta = discount_data
                )

        current_page = response.meta['page']

        if self.page_limit and current_page >= self.page_limit:
            self.logger.info(f"Reached page limit: {self.page_limit}")
            return
        else:
            next_page = current_page + 1
            yield scrapy.Request(
                url=self.base_catalog_url.format(next_page),
                callback=self.parse_catalog,
                meta={'page': next_page}
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

        yield loader.load_item()