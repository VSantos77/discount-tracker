import os
import json
import psycopg2
from scrapy.exceptions import NotConfigured
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from utils.scripts.get_project_root_path import get_project_root_path

class CheckMandatoryFieldsPipeline:
    MANDATORY_FIELDS = [
            'issuer_name',
            'merchant_name',
            'discount_start_date',
            'discount_end_date',
            'discount_payment_method',
            'discount_rate',
            'discount_valid_days_list'
    ]
    
    def process_item(self, item, spider):

        adapter = ItemAdapter(item)
        
        # Check mandatory fields
        for field in self.MANDATORY_FIELDS:
            if adapter.get(field) is None or (isinstance(adapter.get(field),str) and len(adapter.get(field).strip())==0):
                raise DropItem(f'Mandatory field {field} is missing')
            
        return item

class SendToPostgresPipeline:
    def __init__(self, db_settings, sql_query):
        self.db_settings = db_settings
        self.sql_query = sql_query # Store the query string here
        self.connection = None
        self.cursor = None

    # Executes before the pipeline's __init__ method
    @classmethod
    def from_crawler(cls, crawler):
        # 1. Get DB settings
        db_settings = {
            'host': crawler.settings.get('DB_HOST'),
            'database': crawler.settings.get('DB_NAME'),
            'user': crawler.settings.get('DB_USER'),
            'password': crawler.settings.get('DB_PASSWORD'),
            'port': crawler.settings.get('DB_PORT'),
        }

        if not db_settings['database']:
            raise NotConfigured("Database settings not found in environment")

        # 2. Load the SQL file
        sql_path = get_project_root_path() / "utils" / "queries" / "insert_to_stg_discount.sql"

        with open(sql_path, 'r') as f:
            sql_query = f.read()

        return cls(db_settings, sql_query)
            

    def open_spider(self, spider):
        self.connection = psycopg2.connect(**self.db_settings)
        self.cursor = self.connection.cursor()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        if getattr(spider, 'dry_run', '').lower() in ('true', '1'):
            # Avoid sending to postgres but return item so next pipeline can handle
            return item

        for json_field in ['discount_valid_days_list', 'discount_metadata', 'discount_payment_method']:
            if adapter.get(json_field) is not None:
                adapter[json_field] = json.dumps(adapter[json_field])

        try:
            self.cursor.execute(self.sql_query, adapter.asdict())
            self.connection.commit()
        except Exception as e:
            spider.logger.error(f"Postgres Error: {e}")
            self.connection.rollback()
                
        return item

    def close_spider(self, spider):
        if self.cursor: self.cursor.close()
        if self.connection: self.connection.close()

class EnsureFullSchemaPipeline:
    """
    Ensures that every field defined in the Item exists in the output,
    setting missing fields to None.
    """
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # item.fields is a dict of all fields defined in your Item class
        for field_name in item.fields:
            if field_name not in adapter:
                # This ensures the key exists for the JSON Exporter and Postgres
                adapter[field_name] = None
                
        return item