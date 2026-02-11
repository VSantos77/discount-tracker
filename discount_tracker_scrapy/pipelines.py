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
        
        # 1. Get the list of all fields defined in your items.py dynamically
        # This ensures no field is omitted, even if it's NULL/missing
        all_defined_fields = item.fields.keys()
        
        # 2. Create a dict with every field; missing ones default to None
        clean_data = {field: adapter.get(field) for field in all_defined_fields}

        # 3. Serialize your JSON fields (now safe because keys are guaranteed)
        for json_field in ['discount_valid_days_list', 'discount_metadata', 'discount_payment_method']:
            if clean_data.get(json_field) is not None:
                clean_data[json_field] = json.dumps(clean_data[json_field])

        try:
            self.cursor.execute(self.sql_query, clean_data)
            self.connection.commit()
        except Exception as e:
            spider.logger.error(f"Postgres Error: {e}")
            self.connection.rollback()
                
        return item

    def close_spider(self, spider):
        if self.cursor: self.cursor.close()
        if self.connection: self.connection.close()