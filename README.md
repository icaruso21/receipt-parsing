# receipt-parsing

A python project that parses receipts using google vision and uploads the interpreted information to google sheets.

## Installation

1. Install packages using `requirements.txt`
2. Create a google cloud service account with both the sheets api and google vision api enabled
3. Save a service account key (json) and record the path on the environment variable `GOOGLE_APPLICATION_CREDENTIALS`
4. Install just (casey/just on github)

## Usage

run `just parse-receipts` to parse all pdf receipts currently present in `scanned_pdfs` and upload the information to the specified sheet.

- Multiple page pdfs are supported (one receipt is expected per page).

## To specify a sheet

1.  share that sheet with the configured service account
2.  update the variable `SPREADSHEET_ID` in `./upload_to_sheets.py` to the id of this sheet
