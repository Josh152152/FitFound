import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = "1UqkyamJVr9tyrNk_WI55UwustHoaIjESGbFPYwFHtXI"  # Replace this with your actual spreadsheet ID
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_service():
    json_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not json_creds:
        raise Exception("Missing GOOGLE_APPLICATION_CREDENTIALS_JSON env variable")

    creds_info = json.loads(json_creds)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service

def read_all(sheet_name):
    service = get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A1:Z1000"
    ).execute()
    values = result.get("values", [])
    if not values:
        return []
    headers = values[0]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in values[1:]]

def append_row(sheet_name, row_dict):
    rows = read_all(sheet_name)
    headers = rows[0].keys() if rows else row_dict.keys()
    row = [row_dict.get(header, "") for header in headers]
    service = get_service()
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_name,
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()

def find_row_by_column(sheet_name, column_name, value):
    rows = read_all(sheet_name)
    for row in rows:
        if row.get(column_name) == value:
            return row
    return None
