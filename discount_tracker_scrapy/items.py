# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader import ItemLoader
import datetime
from itemloaders.processors import TakeFirst, MapCompose, Identity

class DiscountItem(scrapy.Item):

    # Required
    issuer_name = scrapy.Field() 
    merchant_name = scrapy.Field()
    discount_start_date = scrapy.Field()
    discount_end_date = scrapy.Field()
    discount_payment_method = scrapy.Field()
    discount_rate = scrapy.Field()

    # Optional
    discount_no_interest_installment_qty = scrapy.Field()
    discount_name = scrapy.Field()
    discount_description = scrapy.Field()
    discount_url = scrapy.Field()
    discount_terms_and_conditions = scrapy.Field()
    discount_max_discount_amount = scrapy.Field()
    discount_min_purchase_amount = scrapy.Field()
    discount_valid_days_list = scrapy.Field()
    discount_valid_online = scrapy.Field()
    discount_valid_instore = scrapy.Field()
    discount_metadata = scrapy.Field()

def format_date(value):
    """
    Format date from 'dd/mm/yyyy' to 'yyyy-mm-dd'
    
    :param value: input value
    """
    try:
        dt = datetime.datetime.strptime(value, '%d/%m/%Y')
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return value
    
def format_payment_methods(value):
    """
    Format payment methods as a dict of card and card_type.
        
    :param value: input dict
    """

    return {
        'card': value.get('tarjeta', ''),
        'card_type': value.get('tipoTarjeta', '')
    }

def parse_valid_dates(value):
    """
    Format valid dates string into list of weekday integers
        
    :param value: input string
    """
     
    day_map = {
        'Lu': 0, 'Ma': 1, 'Mi': 2, 'Ju': 3, 
        'Vi': 4, 'Sa': 5, 'Do': 6
    }

    return [day_map.get(day, -1) for day in value.split(';') if day in day_map]

class GaliciaDiscountLoader(ItemLoader):
    default_output_processor = TakeFirst()

    discount_start_date_in = MapCompose(format_date)
    discount_end_date_in = MapCompose(format_date)

    discount_payment_method_in = MapCompose(format_payment_methods)
    discount_payment_method_out = Identity()

    discount_valid_days_list_in = MapCompose(parse_valid_dates)
    discount_valid_days_list_out = Identity()

    discount_rate_in = MapCompose(lambda x: float(x) if x is not None else None)
    discount_max_discount_amount_in = MapCompose(lambda x: float(x) if x is not None else None)
    discount_min_purchase_amount_in = MapCompose(lambda x: float(x) if x is not None else None)
    discount_no_interest_installment_qty_in = MapCompose(lambda x: int(x) if x is not None else None)

    discount_valid_online_in = MapCompose(lambda x: bool(x) if x is not None else None)