# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import csv

csv_path = 'data/csv/'

class NabPipeline(object):

    def __init__(self):
        self.csvwriter = csv.writer(open('{}NAB-data.csv'.format(csv_path),'wb'))
        self.csvwriter.writerow([
            'Client ID', 'Transaction Reference','Date / Time','Type','Source','Channel',
            'Processed By','Recurring','Amount','Currency','Card Type','Account Number','Expiry Date','Cardholder Name'
        ])

    def process_item(self, item, spider):

        self.csvwriter.writerow([
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
