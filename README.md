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
```
usage: pdfdb.py [-h] [-t TYPE] [--pages PAGES] filename

Parse PDF data into CSV, SQLite or PNG files

positional arguments:
  filename

options:
  -h, --help       show this help message and exit
  -t, --type TYPE  Type to output: [csv], db or png
  --pages PAGES    Range of pages to process, e.g 1-11,13,37-
```

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

## Work Log

### Oct 21, 2024

Satisfied with CSV production, I notice that a lot of pages aren't registering line numbers correctly, and the line numbers are treated as a seperate column. Exploring the details of the OCR results seems a good way to start looking into that. The next steps are:
- generate HOCR from the page images
- store page no + result and a clear format in a sqlite table
- use std tools to explore

Added CLI args for page ranges (very helpful for testing), and specifying the output type. The output file is generated in the same location as the input file, with a new file extension, as specified by `--type`.