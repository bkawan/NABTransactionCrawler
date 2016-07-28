# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class NabItem(scrapy.Item):
    # define the fields for your item here like:


    client_id = scrapy.Field()
    trading_name = scrapy.Field()

    payer_name = scrapy.Field()

    transaction_reference = scrapy.Field()
    transaction_time = scrapy.Field()
    source = scrapy.Field()
    type = scrapy.Field()
    channel = scrapy.Field()
    recurring = scrapy.Field()
    amount = scrapy.Field()
    currency = scrapy.Field()

    card_type = scrapy.Field()
    credit_card_number = scrapy.Field()
    expiry_date = scrapy.Field()



