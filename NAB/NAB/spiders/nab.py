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
import time

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
        """ Get last date from the sheet"""
        self.last_date = sheet.get_last_date()


        """ To fill the login form  """
        date_time_group = re.search(r'(\d\d-\d\d-\d\d\d\d)+(.*?)+(\d\d:\d\d)', self.last_date)
        self.date = date_time_group.group(1)
        self.hours_minutes = date_time_group.group(3)

        """ Temporary Date to Search Again """
        self.temp_date = None

        print("****************************")
        print ('Sheet Last Date', self.last_date)
        print ('Date', self.date)
        print ('Hours Minutes ', self.hours_minutes)

        print ('Temp Date', self.temp_date)
        print("****************************")

        try:
            self.last_date = re.sub('\.(0+)', "", self.last_date)
            self.last_date_epoch = int((time.mktime(time.strptime(self.last_date, '%d-%m-%Y %H:%M:%S')))) - time.timezone
        except ValueError:
            try:
                self.last_date_epoch = int((time.mktime(time.strptime(self.last_date, '%d-%m-%Y %H:%M:%S')))) - time.timezone
            except ValueError:
                pass

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
            link = response.xpath("//ul[@class='level1']/li/a/@href")
            if link:
                link = link[2].extract()
            else:

                link = ""
            baseurl = "https://transact.nab.com.au/nabtransact/"
            link = "{}/{}".format(baseurl, link)
            yield scrapy.Request(link, self.search_transaction)

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
            print("New Date To Search: ", self.date)
            yield scrapy.Request(response.urljoin("txnSearch.nab"), self.search_transaction, dont_filter=True)
        else:
            print ("No Search Result Found:", empty_search_results)

    def transaction_details(self, response):
        # inspect_response(response,self)

        tables_selector = response.xpath("//table[@id='formtable']")

        try:
            client_details_table = tables_selector[0]
        except IndexError:
            client_details_table = False
            print("******************************************")
            self.logger.error(" No Selector Client Details div elements")
            print("******************************************")


        try:
            payer_details_table = tables_selector[1]
        except IndexError:
            payer_details_table=False
            print("******************************************")
            self.logger.error(" No  Selector Payer Details div elements ")
            print("******************************************")


        try:
            transaction_details_table = tables_selector[2]
        except IndexError:
            transaction_details_table =False
            print("******************************************")
            self.logger.error(" No  Selector for Transaction detail div  element")
            print("******************************************")


        try:
            tender_details_tabe = tables_selector[3]
        except:
            tender_details_tabe = False
            print("******************************************")
            self.logger.error(" No Selector for Tender Details div elements ")
            print("******************************************")



        """****************************************************************"""

        if client_details_table:
            client_details_selector = client_details_table.xpath(".//td[@class='value']")
            client_details = []
            for client_detail in client_details_selector:
                detail = client_detail.xpath("text()").extract_first()
                client_details.append(self.strip(detail))
        else:
            client_details = []

        """****************************************************************"""

        if payer_details_table:
            payer_details_selector = payer_details_table.xpath(".//td[@class='value']")
            payer_details = []
            for payer_detail in payer_details_selector:
                detail = payer_detail.xpath("text()").extract_first()
                payer_details.append(self.strip(detail))
        else:
            payer_details = []


        """****************************************************************"""

        if transaction_details_table:
            transaction_details_selector = transaction_details_table.xpath(".//td[@class='value']")
            transaction_details = []
            for transaction_detail in transaction_details_selector:
                detail = transaction_detail.xpath("text()").extract_first()
                transaction_details.append(self.strip(detail))
            transaction_payment_type = transaction_details_table.xpath(".//td[@class='typepay']/text()").extract_first()

            transaction_details.insert(2, self.strip(transaction_payment_type))
        else:
            transaction_details = []
        """****************************************************************"""

        if tender_details_tabe:
            tender_details_selector = tender_details_tabe.xpath(".//td[@class='value']")
            tender_details = []
            for tender_detail in tender_details_selector:

                if tender_detail.xpath("img/@alt"):
                    tender_details.append(self.strip(tender_detail.xpath("img/@alt").extract_first()))
                else:
                    detail = tender_detail.xpath("text()").extract_first()
                    tender_details.append(self.strip(detail))
        else:
            tender_details = []

        """ Convert Transaction time to epoch To comapre with last date from the sheet """
        transaction_time = self.get_index(transaction_details, 1)
        transaction_time_epoch = 0
        try:
            transaction_time = re.sub('\.(0+)', "", transaction_time)
            transaction_time_epoch = int((time.mktime(time.strptime(transaction_time, '%d-%m-%Y %H:%M:%S')))) - time.timezone
        except ValueError:
            try:
                transaction_time_epoch = int((time.mktime(time.strptime(transaction_time, '%d-%m-%Y %H:%M:%S')))) - time.timezone
            except ValueError:
                pass


        print("**********************************")
        """" Checking whether conversion time vs original time same """

        print("Transaction Time Epoch:",transaction_time_epoch)
        human_transaction_time = time.strftime("%m-%d-%Y %H:%M:%S", time.gmtime(transaction_time_epoch))
        print("Comapare Transaction Time Human Readable ",human_transaction_time,self.get_index(transaction_details, 1) )
        print("Last Date from the Sheet Epoch: ", self.last_date_epoch)
        human_last_date = time.strftime("%m-%d-%Y %H:%M:%S", time.gmtime(self.last_date_epoch))
        print("Comapare Last sheet Date Human Readable ",  human_last_date, self.last_date)

        print("**********************************")

        if transaction_time_epoch > self.last_date_epoch:
            # human_transaction_time = time.strftime("%m-%d-%Y %H:%M:%S", time.gmtime(transaction_time_epoch))

            item = NabItem()

            item['client_id'] = self.get_index(client_details,0)
            item['trading_name'] = self.get_index(client_details,1)
            item['payer_name'] = self.get_index(payer_details,0)

            item['transaction_reference'] = self.get_index(transaction_details,0)

            # item['transaction_time'] = self.get_index(transaction_details, 1)
            item['transaction_time'] = human_transaction_time

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
            else:
                recurring = self.get_index(transaction_details,4)

            item['recurring'] = recurring

            amount_group = re.search(r'[.0-9]+',response.meta['amount'])
            if amount_group:
                amount = amount_group.group()
                if ".00" in amount:
                    amount = amount.replace(".00","")
            else:
                amount = response.meta['amount']

            item['amount'] = amount
            currency_group = re.search(r'[a-zA-Z]+',response.meta['amount'])
            if currency_group:
                item['currency'] = currency_group.group()
            else:
                item['currency'] = amount

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
