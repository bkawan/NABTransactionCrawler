# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response
import datetime
from datetime import timedelta
from datetime import date
import sys
import codecs
import locale

from NAB.items import NabItem



class NabSpider(scrapy.Spider):
    name = "nab"
    allowed_domains = ["nab.com.au"]
    start_urls = (
        'https://transact.nab.com.au/nabtransact/',
    )


    def __init__(self):
        sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
        reload(sys)
        sys.setdefaultencoding('utf-8')
        self.today = date.today()


    def parse(self, response):
        # client_id = ''
        # username = ''
        # password = ''
        try:
            login_file = open('login_details.txt')

            client_id = None

            username = None
            password = None
            for detail in login_file:
                if detail.lower().startswith('username'):
                    username = detail.split(":")[1].strip()
                if detail.lower().startswith('password'):
                    password = detail.split(":")[1].strip()
                if detail.lower().startswith('client id'):
                    client_id = detail.split(":")[1].strip()

            return scrapy.FormRequest.from_response(
                response,
                formdata={'j_subaccount': client_id, 'j_username': username, 'j_password': password},
                callback=self.after_login,
            )
        except (OSError, IOError) as e:
            self.logger.error(e)


    def after_login(self, response):
        if "Login Failed" in response.body:
            self.logger.error("Login failed!! Please check user name and password in login_details.txt file")
            return

        else:


            print("*******************")

            link = response.xpath("//ul[@class='level1']/li/a/@href")
            link = link[2].extract()
            baseurl = "https://transact.nab.com.au/nabtransact/"
            link = "{}/{}".format(baseurl, link)

            yield scrapy.Request(link, self.search_transaction)

            print("*******************")

    def search_transaction(self, response):

        todate = self.today

        delta = datetime.timedelta(days=180)
        fromdate = todate - delta
        todate = todate.strftime("%d/%m/%Y")
        fromdate = fromdate.strftime("%d/%m/%Y")

        print("**********************")
        print("from Date: " , fromdate)
        print(" To Date: " , todate)

        print("****************")


        yield scrapy.FormRequest.from_response(
                response,
                formdata={
                    'fromdate': fromdate,
                    'fromtime': "00:00",
                    'todate': todate,
                    'totime': "23:59",
                    'resptype': "",
                    'submit': 'Search',
                },
                callback=self.search_results,
            )

    def search_results(self, response):

        print("****** Search Results *********")
        #
        # inspect_response(response, self)


        empty_search_results = response.xpath("//tr[@class='empty']/td[contains(text(),'Your search did not return any results')]/text()").extract()

        table_elements = response.xpath("//table[@id='pageddatatable']")
        table_row_selector = table_elements.xpath(".//tbody/tr")

        for row in table_row_selector:
            account_number = row.xpath(".//td/text()").extract()[2]
            amount = row.xpath(".//td/text()").extract()[3]
            link = row.xpath(".//a[@class='hyperlink']/@href").extract_first()
            pay_type = row.xpath(".//td[@class='txntype']/text()").extract_first()
            tender_type = row.xpath(".//td/img/@alt").extract_first()
            transaction_ref_link = response.urljoin(link)
            request = scrapy.Request(transaction_ref_link, callback=self.transaction_details)

            request.meta['type'] = pay_type
            request.meta['card_type'] = tender_type
            request.meta['account_number'] = account_number
            request.meta['amount'] = amount

            yield request

        next_pagi = response.xpath("//a[contains(text(),'Next')]/@href").extract_first()
        if next_pagi:
            next_link = response.urljoin(next_pagi)
            yield scrapy.Request(next_link,callback=self.search_results,dont_filter=True)
        elif not empty_search_results:
            todate = self.today - timedelta(days=179)
            self.today = todate
            print("*************************")
            print("Date", self.today)
            yield scrapy.Request(response.urljoin("txnSearch.nab"), self.search_transaction, dont_filter=True)
        else:
            print ("No Search Result Found:",empty_search_results)

    def transaction_details(self, response):
        # inspect_response(response,self)

        tables_selector = response.xpath("//table[@id='formtable']")
        client_details_table = tables_selector[0]
        payer_details_table = tables_selector[1]
        transaction_details_table = tables_selector[2]
        tender_details_tabe = tables_selector[3]
        financial_response_details_table = tables_selector[4]

        """****************************************************************"""

        client_details_selector = client_details_table.xpath(".//td[@class='value']")
        client_details = []
        for client_detail in client_details_selector:
            detail = client_detail.xpath("text()").extract_first()
            client_details.append(self.strip(detail))

        """****************************************************************"""

        payer_details_selector = payer_details_table.xpath(".//td[@class='value']")
        payer_details = []
        for payer_detail in payer_details_selector:
            detail = payer_detail.xpath("text()").extract_first()
            payer_details.append(self.strip(detail))

        """****************************************************************"""

        transaction_details_selector = transaction_details_table.xpath(".//td[@class='value']")
        transaction_details = []
        for transaction_detail in transaction_details_selector:
            detail = transaction_detail.xpath("text()").extract_first()
            transaction_details.append(self.strip(detail))
        transaction_payment_type = transaction_details_table.xpath(".//td[@class='typepay']/text()").extract_first()

        transaction_details.insert(2, self.strip(transaction_payment_type))
        """****************************************************************"""

        tender_details_selector = tender_details_tabe.xpath(".//td[@class='value']")
        tender_details = []
        for tender_detail in tender_details_selector:

            if tender_detail.xpath("img/@alt"):
                tender_details.append(self.strip(tender_detail.xpath("img/@alt").extract_first()))
            else:
                detail = tender_detail.xpath("text()").extract_first()
                tender_details.append(self.strip(detail))

        """****************************************************************"""
        financial_response_details_selector = financial_response_details_table.xpath(".//td[@class='value']")
        financial_response_details = []
        for financial_detail in financial_response_details_selector:
            detail = financial_detail.xpath("text()").extract_first()
            financial_response_details.append(self.strip(detail))
        """****************************************************************"""


        item = NabItem()
        item['client_id'] = self.get_index(client_details,0)
        item['trading_name'] = self.get_index(client_details,1)
        item['acquire_details'] = self.get_index(client_details,2)
        item['payer_name'] = self.get_index(payer_details,0)
        item['payer_email'] = self.get_index(payer_details,1)

        item['transaction_reference'] = self.get_index(transaction_details,0)
        item['transaction_time'] = self.get_index(transaction_details,1)
        # item['type_source'] = transaction_details[2]
        item['type'] = response.meta['type']

        item['channel'] = self.get_index(transaction_details,3)
        item['recurring'] = self.get_index(transaction_details,4)
        item['amount'] = response.meta['amount']

        item ['card_type'] = response.meta['card_type']
        item['credit_card_number'] = response.meta['account_number']
        item['expiry_date'] = self.get_index(tender_details,2)

        item['code'] = self.get_index(financial_response_details,0)
        item['response_message'] = self.get_index(financial_response_details,1)
        item['approved'] = self.get_index(financial_response_details,2)
        item['bank_transaction_id'] = self.get_index(financial_response_details,3)
        item['authorization_code'] = self.get_index(financial_response_details,4)
        item['settlement_Date'] = self.get_index(financial_response_details,5)

        yield item

    def strip(self, string):

        value = string
        if string:
            value = string.strip()

        return value

    def get_index(self, item_list, index):
        try:
            value = item_list[index]
            try:
                value = value.strip()
            except:
                value = value
        except:
            value = ""

        return value
