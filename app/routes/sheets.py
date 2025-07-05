import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SHEET_ID = 'your_sheet_id'

def get_service():
    creds = Credentials.from_service_account_file('path_to_your_credentials.json', scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def get_data(sheet_name):
    service = get_service()
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=sheet_name).execute()
    return result.get('values', [])
