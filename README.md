# receipt-parsing

A python project that parses receipts using google vision and uploads the interpreted information to google sheets.

## Usage

run `just parse-receipts` to parse and upload all pdf receipts currently present in `scanned_pdfs`.

- Multiple page pdfs are supported (one receipt is expected per page).

## To upload to a different sheet

1.  share that sheet with the configured service account
2.  update the variable `SPREADSHEET_ID` in `./upload_to_sheets.py` to the id of this sheet
