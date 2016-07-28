# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response
import datetime
import sys
import codecs
import locale
import re
from NAB.items import NabItem
from NAB.sheets import Sheets
from NAB import settings


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

        sheet = Sheets(
            settings.SHEETS_PARAMETERS['spreadsheetId'],
            settings.SHEETS_PARAMETERS['client_secret_file'],
            settings.SHEETS_PARAMETERS['application_name'],
            settings.SHEETS_PARAMETERS['sheet_name'],
        )
        self.last_date = sheet.get_last_date()
        date_time_group = re.search(r'(\d\d-\d\d-\d\d\d\d)+(.*?)+(\d\d:\d\d)', self.last_date)

        self.date = date_time_group.group(1)
        self.hours_minutes = date_time_group.group(3)
        self.temp_date = None

    def parse(self, response):

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

        delta = datetime.timedelta(days=180)
        fromdate = self.date.replace("-","/")
        fromtime = self.hours_minutes

        temp_fromdate = datetime.datetime.strptime(fromdate, "%d/%m/%Y")
        temp_todate = temp_fromdate + delta
        self.temp_date = temp_todate + datetime.timedelta(days=1)

        todate = temp_todate.strftime("%d/%m/%Y")

        yield scrapy.FormRequest.from_response(
                response,
                formdata={
                    'fromdate': fromdate,
                    'fromtime': fromtime,
                    'todate': todate,
                    'totime': fromtime,
                    'resptype': "",
                    'submit': 'Search',
                },
                callback=self.search_results,
            )

    def search_results(self, response):
        # inspect_response(response, self)

        empty_search_results = response.xpath("//tr[@class='empty']/td[contains(text(),'Your search did not return any results')]/text()").extract()
        table_elements = response.xpath("//table[@id='pageddatatable']")
        table_row_selector = table_elements.xpath(".//tbody/tr")

        for row in table_row_selector:
            try:
                account_number = row.xpath(".//td/text()").extract()[2]
            except IndexError:
                account_number = ""
            try:
                amount = row.xpath(".//td/text()").extract()[3]
            except IndexError:
                amount = ""

            link = row.xpath(".//a[@class='hyperlink']/@href").extract_first()
            pay_type = row.xpath(".//td[@class='txntype']/text()").extract_first()
            tender_type = row.xpath(".//td/img/@alt").extract_first()
            transaction_ref_link = response.urljoin(link)
            request = scrapy.Request(transaction_ref_link, callback=self.transaction_details, dont_filter=True)

            request.meta['type'] = pay_type
            request.meta['card_type'] = tender_type
            request.meta['account_number'] = account_number
            request.meta['amount'] = amount

            yield request

        # Extract  Pagination  link
        next_pagi = response.xpath("//a[contains(text(),'Next')]/@href").extract_first()

        if next_pagi:
            next_link = response.urljoin(next_pagi)
            yield scrapy.Request(next_link,callback=self.search_results, dont_filter=True)

        # search again with new date input
        elif not empty_search_results:
            self.date = self.temp_date.strftime("%d/%m/%Y")
            print("*************************")
            print("Date", self.date)
            yield scrapy.Request(response.urljoin("txnSearch.nab"), self.search_transaction, dont_filter=True)
        else:
            print ("No Search Result Found:", empty_search_results)

    def transaction_details(self, response):
        # inspect_response(response,self)

        tables_selector = response.xpath("//table[@id='formtable']")
        client_details_table = tables_selector[0]
        payer_details_table = tables_selector[1]
        transaction_details_table = tables_selector[2]
        tender_details_tabe = tables_selector[3]

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




        item = NabItem()

        item['client_id'] = self.get_index(client_details,0)
        item['trading_name'] = self.get_index(client_details,1)
        item['payer_name'] = self.get_index(payer_details,0)

        item['transaction_reference'] = self.get_index(transaction_details,0)
        item['transaction_time'] = self.get_index(transaction_details,1)
        item['type'] = response.meta['type']

        type_source = self.get_index(transaction_details, 2)
        source = None

        if type_source:
            if "/" in type_source:
                type_source = type_source.split("/")
                source = self.get_index(type_source,1)
                if "api" in source.lower():
                    source = source.lower().strip('api')
                    source = source.upper()
        item['source'] = source

        item['channel'] = self.get_index(transaction_details,3)
        recurring = self.get_index(transaction_details,4)
        if recurring == "No":
            recurring = "N"
        item['recurring'] = recurring

        amount = re.search(r'[.0-9]+',response.meta['amount']).group()
        if ".00" in amount:
            amount = amount.replace(".00","")

        item['amount'] = amount
        item['currency'] = re.search(r'[a-zA-Z]+',response.meta['amount']).group()

        item['card_type'] = response.meta['card_type']
        item['credit_card_number'] = response.meta['account_number']
        item['expiry_date'] = self.get_index(tender_details,2)


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
            except AttributeError:
                value = value
        except IndexError:
            value = ""
        return value
