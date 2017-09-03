#!/usr/bin/env python2

from __future__ import print_function
import httplib2
import os
import csv

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

class Sheets():

    def __init__(self, spreadsheetId, client_secret_file, application_name, sheet_name):
        self.flags = None

        self.SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
        self.CLIENT_SECRET_FILE = client_secret_file
        self.APPLICATION_NAME = application_name

        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        discoveryUrl = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
        self.service = discovery.build('sheets', 'v4', http=http,
                                  discoveryServiceUrl=discoveryUrl)

        self.spreadsheetId = spreadsheetId

        result = self.service.spreadsheets().get(spreadsheetId=self.spreadsheetId).execute()

        sheet = [ (sheet['properties']['sheetId'], sheet['properties']['title']) for sheet in result['sheets'] if sheet['properties']['title'] == sheet_name ]

        if not sheet:
            raise ValueError('No such sheet in this spreadsheet')

        self.sheet_name = sheet_name
        self.sheet_id = sheet[0][0]

        self.last_row = self.get_row(last=True)

    def get_credentials(self):
        """Gets valid user credentials from storage.
        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.
        Returns:
            Credentials, the obtained credential.
        """

        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'sheets.googleapis.com-python-quickstart.json')

        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES)
            flow.user_agent = self.APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else: # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials

    def get_last_date(self, row_no = False):
        rangeName = self.sheet_name + '!'
        rangeName += 'C1:C'

        result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheetId, range=rangeName,
                majorDimension='COLUMNS').execute()
        values = result.get('values',[])

        last_date = values[0][-1]

        if row_no:
            return len(values[0])
        else:
            return last_date

    def get_row(self, row_no = None, last = False):
        if not row_no and not last:
            raise ValueError('Invalid usage')

        if last:
            row_no = self.get_last_date(row_no = True)

        rangeName = self.sheet_name + '!'
        rangeName += 'A{0}:V{0}'.format(row_no)

        result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheetId, range=rangeName,
                majorDimension='ROWS').execute()

        values = result.get('values',[])

        row = values[0]

        return row

    def append_row(self, row):
        if not type(row) is list:
            raise Exception('row is not a list')

        row_count = self.get_last_date(row_no=True) + 1

        new_row = row[0:14] # A-N
        new_row.append('=right(B{0},7)'.format(row_count)) #O
        new_row.append( self.last_row[15] ) #P
        new_row.append('=J{0}'.format(row_count)) #Q
        new_row.append('=if(J{0}="JPY",I{0}*100,I{0})'.format(row_count)) #R
        new_row.append( self.last_row[18] ) #S
        new_row.append('=R{0}-S{0}'.format(row_count)) #T
        new_row.append( self.last_row[20] ) #U
        new_row.append( self.last_row[21] ) #V

        rangeName = self.sheet_name + '!'
        rangeName += 'A{0}:V{0}'.format(row_count)

        body = {
            'range' : rangeName,
            'values' : [new_row],
            'majorDimension' : 'ROWS'
        }

        result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheetId, range=rangeName,
                valueInputOption='USER_ENTERED', body=body).execute()
        return result

    def sort_sheet(self):

        sort_column_index = 2 # sort using 3rd column

        body = {
            'requests': [
                {
                    'sortRange': {
                        'range': {
                            'sheetId': self.sheet_id,
                            'startRowIndex': 1,
                            'startColumnIndex': 0
                        },
                        'sortSpecs': [
                            {
                                'dimensionIndex': sort_column_index,
                                'sortOrder': 'ASCENDING'
                            }
                        ]
                    }
                }
            ]
        }

        result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheetId, body=body).execute()

        return result

if __name__=='__main__':
    sheet = Sheets(spreadsheetId = '1mKAsY92nA3I6PhTkNd9aLIY8_SZMXERr2wg5WTYMk34',
            client_secret_file = 'client_secret.json',
            application_name = 'FinancialData',
            sheet_name = 'V46')

    print()