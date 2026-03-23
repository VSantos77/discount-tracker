import scrapy
import json
from discount_tracker_scrapy.items import DiscountItem, GaliciaDiscountLoader

class GaliciaSpider(scrapy.Spider):
    name = "galicia"
    allowed_domains = ["loyalty.bff.bancogalicia.com.ar"]

    def __init__(self, page_limit=None, *args, **kwargs):
        super(GaliciaSpider, self).__init__(*args, **kwargs)
        # Convert the string arg to an int, or None if not provided
        try:
            self.page_limit = int(page_limit) if page_limit else None
        except ValueError:
            raise(ValueError("page_limit must be an integer"))

    # Starting with Page 1 of the catalog
    base_catalog_url = "https://loyalty.bff.bancogalicia.com.ar/api/portal/personalizacion/v1/promociones/catalogo?page={}&pageSize=15"
    detail_api_url = "https://loyalty.bff.bancogalicia.com.ar/api/portal/catalogo/v1/promociones/idPromocion/{}"

    def start_requests(self):
        # Start the crawl at page 1
        yield scrapy.Request(url=self.base_catalog_url.format(1), callback=self.parse_catalog, meta={'page': 1})

    def parse_catalog(self, response):

        data = response.json()['data']
        
        discounts = data.get('list', [])
        
        if not discounts:
            self.logger.info("No more discounts found. Stopping.")
            return

        for discount in discounts:
            discount_id = discount.get('id')
            if discount_id:
                # Dispatch a request for the specific details of this discount
                yield scrapy.Request(
                    url=self.detail_api_url.format(discount_id),
                    callback=self.parse_details,
                    meta={'discount_id' : discount_id}
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
        
        loader = GaliciaDiscountLoader(item=DiscountItem(), response=response)

        loader.add_value('issuer_name', "Banco Galicia")
        
        # Handle discounts for entire categories (e.g all electronics shops)
        if data.get('tipoPromocion') == 'Categoria':
            merchant_name = data.get('categoria', {}).get('descripcion')
            category_name = merchant_name
        else:
            merchant_name = data.get('marca').get('nombre', None)
            category_name = data.get('marca', {}).get('categoria', {}).get('descripcion')
        
        loader.add_value('merchant_name', merchant_name)
        loader.add_value('merchant_category_name', category_name)
        loader.add_value('discount_name', None)
        loader.add_value('discount_description', data.get('descripcionAdicional', None))
        loader.add_value('discount_url', None)
        loader.add_value('discount_start_date', data.get('fechaDesde', None))
        loader.add_value('discount_end_date', data.get('fechaHasta', None))
        loader.add_value('discount_terms_and_conditions', data.get('legales', None))
        loader.add_value('discount_rate', data.get('porcentajeAhorro', None))
        loader.add_value('discount_max_discount_amount', data.get('topeReintegro', None))
        loader.add_value('discount_min_purchase_amount', None)
        loader.add_value('discount_no_interest_installment_qty', data.get('cuotaSinInteresHasta', None))
        loader.add_value('discount_valid_days_list', data.get('diasAplicacion', None))
        loader.add_value('discount_valid_online', data.get('tiendaOnline', None))
        loader.add_value('discount_valid_instore', data.get('tiendaFisica', None))
        loader.add_value('discount_metadata', data)
        loader.add_value('discount_payment_method', data.get('mediosDePago', {}))

        yield loader.load_item()