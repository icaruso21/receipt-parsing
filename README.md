# receipt-parsing

Receipt parser using google vision and spacy that uploads results to google sheets.

## Installation

1. Install packages using `requirements.txt`
2. Create a google cloud service account with both the sheets api and google vision api enabled
3. Save a service account key (json) and record the path on the environment variable `GOOGLE_APPLICATION_CREDENTIALS`
4. Install [just](https://github.com/casey/just) 
5. run `just create-directories`


## Usage

run `just parse-receipts` to parse all pdf receipts currently present in `scanned_pdfs` and upload the information to the specified sheet.

- Multiple page pdfs are supported (one receipt is expected per page).

## To specify a sheet

1.  share that sheet with the configured service account
2.  set the variable `SPREADSHEET_ID` in `./upload_to_sheets.py` to the id of this sheet

## Credits
Thanks to [@lutzkuen](https://github.com/lutzkuen/receipt-parser) for providing inspiration that was foundational to this project.
