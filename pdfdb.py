#!/usr/bin/env python3

import re
import io
import math
import sys

from PIL import Image
from pypdf import PdfReader, PageObject

import pytesseract


def multi_image_page(page:PageObject) -> Image:
    cols = 2
    rows = math.ceil(len(page.images) / cols)

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

    #print(f"creating image mode: {mode}, {page_w} x {page_h}")
    im = Image.new(mode, (page_w, page_h))

    next = (0,0)
    col_start = 0
    col = 0
    for i, image in enumerate(images):
        #print(f"pasting {i} {image} to {next}")
        im.paste(image, box=next)

        if image.size[1] < 10:
            # break
            if col == 0:
                # new column
                col = 1
                next = (col_w, col_start)
            else:
                # 1st col, 2nd half of page
                col = 0
                col_start = next[1] + image.size[1]
                next = (0, col_start)
        else:
            next = (next[0], next[1] + image.size[1]) # update y with height of image

    return im


def dump_csv(filename:str) -> None:
    text_out = sys.stdout

    reader = PdfReader(filename)

    #print(f"#pages: {len(reader.pages)}")
    #print(f"metadata={reader.metadata}")

    # csv header
    text_out.write("\"page\",\"line\",\"text\"\n")

    for page in reader.pages:
        #print(f"{page.page_number} [{len(page.images)}]")
        #text = strip_crlf(page.extract_text())

        page_image = None

        # This needs to be woven backtogether in to one full page for OCR
        # assume everything is the same as the first image
        if len(page.images) == 0:
            pass
        elif len(page.images) == 1:
            page_image = page.images[0].image
        else:
            page_image = multi_image_page(page)

        if page_image:
            data = pytesseract.image_to_string(page_image)

            # iterate text, remove line numbers
            text = io.StringIO(data)
            line = text.readline()
            while line:
                line = line.strip()
                line = line.replace("|", "I") # fix those vertical bars!
                line = line.replace('"','""') # esc quotes in text, for CSV
                line_no = "?" # FIXME: if a line-no is missing, enumerate based on existing

                match = re.match(r'^(\d+)', line)
                if match:
                    # strip leading line numers from text
                    line_no = int(match.group(0)) # for later
                    line = line[match.end():].strip()
                elif line == "SEALED": # hacky, but cleans up a lot
                    line = ""

                if len(line) > 0:
                    #file.write(f"{page.page_number},{line_no},\"{line}\"\n")
                    text_out.write(f"{page.page_number},{line_no},\"{line}\"\n")

                # next line
                line = text.readline()


def main() -> None:
    filename = sys.argv.pop()
    dump_csv(filename)


if __name__ == '__main__':
    main()
