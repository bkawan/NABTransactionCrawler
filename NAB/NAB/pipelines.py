# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from NAB.sheets import Sheets
from NAB import settings
import time
csv_path = 'data/csv/'

class NabPipeline(object):

    def __init__(self):

        self.sheet = Sheets(
                            settings.SHEETS_PARAMETERS['spreadsheetId'],
                            settings.SHEETS_PARAMETERS['client_secret_file'],
                            settings.SHEETS_PARAMETERS['application_name'],
                            settings.SHEETS_PARAMETERS['sheet_name'],
                            )
        # last_date = '08-04-2016 13:58:20'



    def close_spider(self,spider):
        self.sheet.sort_sheet()


    def process_item(self, item, spider):

        #item['transaction_time']= 03-08-2016 16:47:40.000


        self.sheet.append_row([
            item['client_id'],
            item['transaction_reference'],
            item['transaction_time'],
            item['type'],
            item['source'],
            item['channel'],
            item['trading_name'],
            item['recurring'],
            item['amount'],
            item['currency'],
            item['card_type'],
            item['credit_card_number'],
            item['expiry_date'],
            item['payer_name']

                ])
        return item


