# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

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
        

