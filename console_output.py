import sys
import time
import math
from time import sleep
import textwrap as tw

###FORMATTING###
BOX_PADDING = 1
WRAP_WIDTH = 45
LINE_WIDTH = 70

###CONSTUCTION ELEMENTS###
ROOF = "═"
FLOOR = "═"
WALL = "║"
SPACE = " "
NEW_LINE = "\n"
TL_CORNER = "╔"
TR_CORNER = "╗"
BL_CORNER = "╚"
BR_CORNER = "╝"


def message(text):
    for char in text:
        sleep(0.001)
        sys.stdout.write(char)
    sys.stdout.write("\n")


def print_text_by_line(text):
    rows = text.split("\n")
    for row in rows:
        sleep(0.001)
        print(row)
    print("\n")


def top_line(length):
    return TL_CORNER + ROOF * (length + (BOX_PADDING * 4)) + TR_CORNER


def bottom_line(length):
    return BL_CORNER + FLOOR * (length + (BOX_PADDING * 4)) + BR_CORNER


def spacer(length):
    return SPACE * length


def box_message(text, title):
    rows = text.split("\n")
    width = len(max(rows, key=len))
    height = len(rows)
    h_padding = BOX_PADDING * 2
    v_padding = BOX_PADDING
    top_padding = BOX_PADDING - 1

    bm = ""
    bm += top_line(width)

    title_line = ""
    title_line += NEW_LINE
    title_line += WALL
    title_line += spacer(int(math.trunc((width - len(title))/2 + h_padding)))
    title_line += title.upper()
    title_line += spacer(int(round((width - len(title))/2 + h_padding, 0)))
    title_line += WALL

    bm += title_line

    top_spacer = ""
    top_spacer += NEW_LINE
    top_spacer += WALL
    top_spacer += spacer(h_padding)
    top_spacer += spacer(width)
    top_spacer += spacer(h_padding)
    top_spacer += WALL

    bm += top_spacer * (top_padding)

    for row in rows:
        tail_spacing = width - len(row)
        bm += "\n" + WALL + (" " * BOX_PADDING * 2) + row + \
            (" " * tail_spacing) + (" " * BOX_PADDING * 2) + WALL
    bm += ("\n" + WALL + (" " * (width + (BOX_PADDING * 4))) + WALL) * BOX_PADDING
    bm += "\n" + bottom_line(width)
    print_text_by_line(bm)


def draw_line(length):
    return "-" * length


def padded_list(content, title):
    wrapper = tw.TextWrapper(width=WRAP_WIDTH)
    print(title.upper())
    draw_line(LINE_WIDTH)
    for row in content:
        lines = wrapper.wrap(row[0])
        length = len(lines[len(lines) - 1])
        for i in range(0, len(lines)):
            if i == (len(lines) - 1):
                padding_length = LINE_WIDTH - len(lines[i]) - len(row[1])
                padding = "." * padding_length
                print(lines[i].capitalize() + padding + row[1])
            else:
                print(lines[i].capitalize())


def status(status_message):
    print("STATUS: " + status_message)


def error(error_message):
    print("ERROR: " + error_message)
