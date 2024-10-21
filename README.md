# pdfdb

Build a sqlite or CSV file from the text and OCR-ed images in a PDF.

This tool is designed to extract, organize and index the textual data in PDF file.

While reviewing public court documents, I found it was difficult (if not impossible) to search to text in scanned documents, and those with many images. I designed this to extract that data, and store it in a way that made it easy to query.

For now, that means CSV or a SQLite DB.

This is very much a **Work In Progress**.

Current design builds an large table of page number, line number and text. These values are derived from constructing an image for each fully rendered page, applying OCR to the constructed page.

This mostly works, but there are still a few bugs fully detecting line numbers. Future plans include fixing line numbering, dumping to sqlite DB file, better REDACTION handling and dumping
HOCR output.

Once the bugs are fixed and valid datasets are written to the DB, a single-page-app dataset browser will be introduced with:
- full text search
- SQL support
- sortable table display

## Usage

Assuming you have `python3` installed,
```
pdfdb.py [pdf-file-name]
```

This will generate to stdout CSV container the extracted text, with the columns:
```
page, line, text
```

To capture (using the include sample legal document):
```
pdfdb.py docs/chutkan-order-government-appendix-vol-i.pdf > docs/chutkan-appendix.csv
```

Given the size of a document, this might take a few minutes to run.
