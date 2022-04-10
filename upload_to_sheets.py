from googleapiclient.discovery import build
import os
from google.oauth2 import service_account

SPREADSHEET_ID = "1Tlm0Wa0H-zfjs1Q0YPc2hJUaidA9maDgsK8E_quzGGM"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def create_unique_sheet(service, sheet_name: str, *, depth: int = 0) -> str:
    batch_update_values_request_body = {
        "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
    }
    request = service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body=batch_update_values_request_body
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
        spreadsheetId=SPREADSHEET_ID,
        range=spreadsheet_range,
        body={"values": receipt.formatted_sheet},
        valueInputOption="USER_ENTERED",
    ).execute()
