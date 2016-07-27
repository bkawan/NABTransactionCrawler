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
    acquire_details = scrapy.Field()

    payer_name = scrapy.Field()
    payer_email = scrapy.Field()

    transaction_reference = scrapy.Field()
    transaction_time = scrapy.Field()
    # type_source = scrapy.Field()
    type = scrapy.Field()
    channel = scrapy.Field()
    recurring = scrapy.Field()
    amount = scrapy.Field()

    card_type = scrapy.Field()
    credit_card_number = scrapy.Field()
    expiry_date = scrapy.Field()

    code = scrapy.Field()
    response_message = scrapy.Field()
    approved = scrapy.Field()
    bank_transaction_id = scrapy.Field()
    authorization_code = scrapy.Field()
    settlement_Date = scrapy.Field()
       

