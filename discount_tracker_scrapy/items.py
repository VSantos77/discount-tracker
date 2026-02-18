# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader import ItemLoader
import datetime
from itemloaders.processors import TakeFirst, MapCompose, Identity
from re import search

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
    merchant_category_name = scrapy.Field()

class GaliciaDiscountLoader(ItemLoader):
    @staticmethod
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
    
    @staticmethod
    def format_payment_methods(value):
        """
        Format payment methods as a dict of card and card_type.
            
        :param value: input dict
        """

        return {
            'card': value.get('tarjeta', ''),
            'card_type': value.get('tipoTarjeta', '')
        }

    @staticmethod
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

class BBVADiscountLoader(ItemLoader):
    @staticmethod
    def normalize_valid_days(value):        
        if isinstance(value, str):
            value_list = value.split(',')

            if len(value_list) == 7:
                return [[index for index, is_active in enumerate(value_list) if is_active == '1']]
        return [list(range(0,7))]
    
    @staticmethod
    def get_payment_method(value):
        if isinstance(value, str):

            return {
                'card': 'all',
                'card_type': 'credito'
            }            
    
    @staticmethod
    def parse_discount_rate(value):
        if len(value) > 0:
            match = search('(\d+(?:[.,]\d+)?)\s*%', value)
            if match:
                return float(match.group(1)) / 100
        
        return 0

    @staticmethod
    def parse_merchant_name(value):
        if isinstance(value, str):
            match = search('^(.+?)(?=\s+\d+\s*(?:%|cuotas))', value)
            if match:
                return match.group(1).strip()
        return None

    default_output_processor = TakeFirst()
    default_input_processor = Identity()

    discount_valid_days_list_in = MapCompose(normalize_valid_days)
    discount_valid_online_in = MapCompose(lambda x: x > 0)
    discount_valid_instore_in = MapCompose(lambda x: x > 0)

    discount_rate_in = MapCompose(parse_discount_rate)

    merchant_name_in = MapCompose(parse_merchant_name)
    discount_payment_method_in = MapCompose(get_payment_method)
    discount_payment_method_out = Identity()