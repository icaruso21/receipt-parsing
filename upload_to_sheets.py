from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import os
from google.auth.transport.requests import Request
from google.oauth2 import service_account

spreadsheet_id = "1Tlm0Wa0H-zfjs1Q0YPc2hJUaidA9maDgsK8E_quzGGM"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
oauth_token_path = "../Downloads/client_secret_339936403154-d4igrfc42tefqoi6usscasv1t9jj2fjr.apps.googleusercontent.com.json"
creds = None


def create_unique_sheet(service, sheet_name: str, *, depth: int = 0) -> str:
    batch_update_values_request_body = {
        "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
    }
    request = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=batch_update_values_request_body
    )
    try:
        request.execute()
        print(f"Sheet name ({sheet_name}) created.")
    except:
        print(f"Sheet name ({sheet_name}) already present")
        return create_unique_sheet(service, f"{sheet_name}{depth}", depth=depth + 1)
    return sheet_name


def add_reciept_to_sheet(sheet_name: str, receipt: "Receipt"):
    service = build(
        "sheets",
        "v4",
        credentials=service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES
        ),
    )

    unique_sheet_name = create_unique_sheet(service, sheet_name)

    spreadsheet_range = f"{unique_sheet_name}"

    # Call the Sheets API
    sheet = service.spreadsheets()

    sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range=spreadsheet_range,
        body={"values": receipt.formatted_sheet},
        valueInputOption="USER_ENTERED",
    ).execute()
