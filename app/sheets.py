import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = "1UqkyamJVr9tyrNk_WI55UwustHoaIjESGbFPYwFHtXI"  # Your actual spreadsheet ID
# Set your Google Sheet ID here (this will work for all tabs in the same file)
SPREADSHEET_ID = "1UqkyamJVr9tyrNk_WI55UwustHoaIjESGbFPYwFHtXI"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_service():
    # Get the service account JSON credentials from an ENV variable
    json_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not json_creds:
        raise Exception("Missing GOOGLE_APPLICATION_CREDENTIALS_JSON env variable")
    creds_info = json.loads(json_creds)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service
    return build("sheets", "v4", credentials=creds)

def read_all(sheet_name):
    service = get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A1:Z1000"
    ).execute()
    values = result.get("values", [])
    if not values:
        return []
    headers = values[0]
    # Fill missing cells with "" so all rows have the same length as headers
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in values[1:]]

def append_row(sheet_name, row_dict):
    # Ensure headers exist (by reading current data)
    rows = read_all(sheet_name)
    headers = rows[0].keys() if rows else row_dict.keys()
    headers = list(rows[0].keys()) if rows else list(row_dict.keys())
    # Always preserve the order of headers for consistency
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
        if str(row.get(column_name, "")).strip() == str(value).strip():
            return row
    return None

def update_row_by_column(sheet_name, column_name, value, update_dict):
    """
    Updates the first row in the sheet where column_name == value, with the values in update_dict.
    """
    service = get_service()
    # Read all data to find the row index
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A1:Z1000"
    ).execute()
    values = result.get("values", [])
    if not values:
        return False
    headers = values[0]
    for idx, row in enumerate(values[1:], start=2):  # start=2 because of 1-based index and header row
    for idx, row in enumerate(values[1:], start=2):  # 1-based index, 1 for header
        row_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
        if str(row_dict.get(column_name, "")).strip() == str(value).strip():
            # Update each specified column
            updates = []
            for k, v in update_dict.items():
                if k in headers:
                    col_idx = headers.index(k)
                    # Google Sheets API needs A1 notation, so we build the cell range
                    cell_range = f"{sheet_name}!{chr(65 + col_idx)}{idx}"
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
