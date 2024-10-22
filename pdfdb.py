#!/usr/bin/env python3
"""pdfdb"""

#pylint: disable=too-many-arguments
#pylint: disable=R0917


import re
import io
import sqlite3
import argparse
import logging

from PIL import Image
from pypdf import PdfReader, PageObject

import pytesseract

log = logging.getLogger(__name__)

def multi_image_page(page:PageObject) -> Image:
    """stitch together a multi-image page"""
    #cols = 2
    #rows = math.ceil(len(page.images) / cols)

    # first pass: page size!
    images = [None] * len(page.images)
    for img in page.images:
        match = re.match(r'^Im(\d+)', img.name)
        i = int(match.group(1))
        images[i] = img.image

    # pattern is LLlRRrLLlRRr and stop when you run out
    #            012345678901
    # half-page
    col_w = images[0].size[0]
    page_w = images[0].size[0] + images[3].size[0]
    page_h = (images[0].size[1] + images[1].size[1] + images[2].size[1]) * 2 # hacky
    mode = page.images[0].image.mode

    im = Image.new(mode, (page_w, page_h))

    next_paste = (0,0)
    col_start = 0
    col = 0
    for i, image in enumerate(images):
        im.paste(image, box=next_paste)

        if image.size[1] < 10:
            # break
            if col == 0:
                # new column
                col = 1
                next_paste = (col_w, col_start)
            else:
                # 1st col, 2nd half of page
                col = 0
                col_start = next_paste[1] + image.size[1]
                next_paste = (0, col_start)
        else:
            # update y with height of image
            next_paste = (next_paste[0], next_paste[1] + image.size[1])

    return im


def append_csv(filename, page_num, page_image):
    """append page to a csv file"""
    #csv_file = f"{pathlib.Path(filename).stem}.csv"
    csv_file = filename.replace(".pdf", ".csv", 1)

    with open(csv_file, "a", encoding="utf-8") as text_out:
        data = pytesseract.image_to_string(page_image)

        # iterate text, remove line numbers
        text = io.StringIO(data)
        line = text.readline()
        while line:
            line = line.strip()
            line = line.replace("|", "I") # fix those vertical bars!
            line = line.replace('"','""') # esc quotes in text, for CSV
            line_no = "?"

            match = re.match(r'^(\d+)', line)
            if match:
                # strip leading line numers from text
                line_no = int(match.group(0)) # for later
                line = line[match.end():].strip()
            elif line == "SEALED": # hacky, but cleans up a lot
                line = ""

            if len(line) > 0:
                #file.write(f"{page.page_number},{line_no},\"{line}\"\n")
                text_out.write(f"{page_num},{line_no},\"{line}\"\n")

            # next line
            line = text.readline()


class Token:
    """A dataclass to capture details of text recognized by OCR"""
    text: str
    conf: float
    page: int
    x: int
    y: int
    w: int
    h: int

    def __init__(self, text: str, conf: float, page: int, x: int, y: int, w: int, h: int) -> None:
        self.text = text
        self.conf = conf
        self.page = page
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __str__(self) -> str:
        return self.text

    def tuple(self):
        """returns a tuple representing the values for DB insertion"""
        return(self.page, self.x, self.y, self.w, self.h, self.conf, self.text)


def page_to_tokens(page_num: int, page_image: Image):
    """Scan an image for text, with the bounding boxes and confidence"""
    tokens = []
    d = pytesseract.image_to_data(page_image, output_type=pytesseract.Output.DICT)
    n_boxes = len(d['level'])
    for i in range(n_boxes):
        if d['conf'][i] > 0:
            token = Token(
               text=d['text'][i],
               conf=d['conf'][i],
               page=page_num,
               x=d['left'][i],
               y=d['top'][i],
               w=d['width'][i],
               h=d['height'][i])
            tokens.append(token)

    return tokens


def init_db(db: sqlite3.Cursor) -> None:
    """init db tables"""
    # create tokens table
    db.execute("CREATE TABLE IF NOT EXISTS tokens(page, x, y, w, h, conf, text)")


def store_tokens(db: sqlite3.Cursor, tokens: list[Token]) -> None:
    """Store a collection of tokens in the db"""
    data = [token.tuple() for token in tokens]
    db.executemany("INSERT INTO tokens VALUES(?, ?, ?, ?, ?, ?, ?)", data)


class Range:
    """Range"""
    RANGE_REGEX = re.compile(r"((?P<start>\d*)-(?P<end>\d*)|(?P<page>\d+)),?")

    """A contigious range of numbers"""
    start: int
    end: int

    def __init__(self, start, end) -> None:
        self.start = start
        self.end = end

    def __str__(self) -> str:
        return f"{self.start}-{self.end}" if self.end > self.start else str(self.start)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{self.__dict__}"

    def in_range(self, val:int) -> bool:
        """returns true if a value is in the specificed range"""
        # in some cases, end == 0, indicating open-ended
        if self.end:
            return self.start <= val <= self.end
        return self.start <= val

    @classmethod
    def from_args(cls, arg_val: str) -> 'list[Range]':
        """Parse valid page ranges from the argument"""
        # pages=-2,4,8-54,70-
        ranges = []
        for match in cls.RANGE_REGEX.finditer(arg_val):
            group = match.groupdict()
            if 'page' in group and group['page']:
                page = int(group['page'])
                ranges.append(Range(page, page))
            else:
                # either start or end can be ''
                start = int(group['start']) if group['start'] else 1
                end = int(group['end']) if group['end'] else 0 # open-ended
                ranges.append(Range(start, end))
        return ranges


def write_db(db:sqlite3.Cursor, page_num: int, page_image:Image) -> None:
    """Write to the DB"""
    tokens = page_to_tokens(page_num, page_image)
    store_tokens(db, tokens)


def write_png(filename:str, page: int, page_image:Image):
    """Write a png file"""
    png_file = filename.replace(".pdf", f"-page{page}.png")
    print("filename:", png_file)
    page_image.save(png_file)


def in_page_range(page_num: int, pages: list[Range]) -> bool:
    """test if a specific page is in a complex range spec"""
    # special case: None and empty range list assume all pages in range
    if not pages:
        return True

    # check if current page is in range
    for page_range in pages:
        if page_range.in_range(page_num):
            return True

    # range specified, but not found in *any*
    return False


def process_page_images(page: PageObject) -> Image:
    """Check the available pages images to reconstruct a single page"""
    if not page.images:
        log.debug("no images on page %s, skipping", page.page_number+1)
        return None
    if len(page.images) == 1:
        return page.images[0].image
    return multi_image_page(page)


def process_doc(filename: str, output: str, pages_arg: list[Range] = None):
    """process a PDF doc"""
    reader = PdfReader(filename)

    db = None
    if output == "db":
        db_file = filename.replace(".pdf", ".db")
        conn = sqlite3.connect(db_file, autocommit=True)
        db = conn.cursor()
        init_db(db)

    for page in reader.pages:
        page_num = page.page_number + 1 # 0-based numbering
        # check if this page in the arg list
        if in_page_range(page_num, pages_arg):
            # print metadata, not stored anywhere
            print(page_num, page.extract_text())

            # The page needs to be woven backtogether in to one full page for OCR
            # assume everything is the same as the first image
            page_image = process_page_images(page)
            if not page_image:
                # empty page, nothing to do
                continue

            match output:
                case "csv":
                    append_csv(filename, page_num, page_image)
                case "db":
                    write_db(db, page_num, page_image)
                case "png":
                    write_png(filename, page_num, page_image)

    if db:
        db.close()


def main() -> None:
    """main"""
    # setup CLI arg parsing
    parser = argparse.ArgumentParser(
                        prog='pdfdb.py',
                        description='Parse PDF data into CSV, SQLite or PNG files')
    parser.add_argument('filename')
    parser.add_argument('-t', '--type',
                        default="csv",
                        type=str,
                        help="Type to output: [csv], db or png")
    parser.add_argument('--pages',
                        type=str,
                        help="Range of pages to process, e.g 1-11,13,37-")

    # parse the args
    args = parser.parse_args()
    page_ranges = None
    if args.pages:
        page_ranges = Range.from_args(args.pages)

    # process the doc
    process_doc(args.filename, args.type, page_ranges)


if __name__ == '__main__':
    main()
