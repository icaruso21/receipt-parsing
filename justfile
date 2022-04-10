create-directories:
  mkdir scanned_pdfs && mkdir parsed_image_jsons && mkdir images

parse-receipts:
  python3 ./parse_receipts.py && python3 ./coords_to_csv.py
