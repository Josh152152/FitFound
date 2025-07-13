import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Set your Google Sheet ID here (this will work for all tabs in the same file)
SPREADSHEET_ID = "1UqkyamJVr9tyrNk_WI55UwustHoaIjESGbFPYwFHtXI"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_service():
    """
    Get the Google Sheets API service using service account credentials.
    """
    json_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not json_creds:
        raise Exception("Missing GOOGLE_APPLICATION_CREDENTIALS_JSON env variable")
    creds_info = json.loads(json_creds)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def read_all(sheet_name):
    """
    Reads all rows of data from the given sheet tab name and returns them as a list of dictionaries.
    The first row is treated as the header, and each row's values are matched to the header keys.
    """
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
    """
    Appends a new row to the specified sheet.
    The row dictionary keys should match the column headers.
    """
    # Ensure headers exist (by reading current data)
    rows = read_all(sheet_name)
    headers = list(rows[0].keys()) if rows else list(row_dict.keys())
    # Always preserve the order of headers for consistency
    row = [row_dict.get(header, "") for header in headers]
    service = get_service()
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_name}!A1",  # Specify where the row should be appended
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()

def find_row_by_column(sheet_name, column_name, value):
    """
    Searches for a row in the given sheet where the column_name matches the provided value.
    Returns the row if found, otherwise returns None.
    """
    rows = read_all(sheet_name)
    for row in rows:
        if str(row.get(column_name, "")).strip() == str(value).strip():
            return row
    return None

def update_row_by_column(sheet_name, column_name, value, update_dict):
    """
    Updates the first row in the sheet where column_name == value, with the values in update_dict.
    """
    service = get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A1:Z1000"
    ).execute()
    values = result.get("values", [])
    if not values:
        return False
    headers = values[0]
    for idx, row in enumerate(values[1:], start=2):  # 1-based index, 1 for header
        row_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
        if str(row_dict.get(column_name, "")).strip() == str(value).strip():
            updates = []
            for k, v in update_dict.items():
                if k in headers:
                    col_idx = headers.index(k)
                    # Handle columns beyond Z (AA, AB, etc.)
                    def col_letter(n):
                        result = ""
                        while n >= 0:
                            result = chr(n % 26 + 65) + result
                            n = n // 26 - 1
                        return result
                    cell_range = f"{sheet_name}!{col_letter(col_idx)}{idx}"
                    updates.append({
                        "range": cell_range,
                        "values": [[v]]
                    })
            if updates:
                body = {"valueInputOption": "USER_ENTERED", "data": updates}
                service.spreadsheets().values().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body=body
                ).execute()
            return True
    return False
