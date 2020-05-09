#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import shlex
import pyte
import ptyprocess
import threading
import time
import digitalio
import board
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7789 as st7789
from bdflib import reader
import json
import logging

#setup logging
logging.basicConfig(level=logging.INFO)

# open theme file
with open("theme.json", "r") as handle:
    logging.info("Loading theme")
    theme = json.load(handle)

# load miniwi
with open("miniwi-qrunicode.bdf", "rb") as handle:
    logging.info("Reading font")
    bdffont = reader.read_bdf(handle)


def getGlyph(number, font):
    """extract a glyph from the BDF font"""
    glyph = font[number]
    glyphPixels = glyph.iter_pixels()

    img = Image.new('1', (4, 9))
    pixels = img.load()
 
    for y, Y in enumerate(glyphPixels):
        for x, X in enumerate(Y):
            pixels[x, y] = X

    return img

# this holds all the glyphs as images
logging.info("Loading font")
glyphDict = {cp: getGlyph(cp, bdffont) for cp in bdffont.codepoints()}
logging.info("Font loaded")

# Configuration for CS and DC pins (these are FeatherWing defaults on M0/M4):
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# Create the ST7789 display:
disp = st7789.ST7789(spi, cs=cs_pin, dc=dc_pin, rst=reset_pin, baudrate=BAUDRATE,
                     width=240, height=240, y_offset=80)

width = disp.width
height = disp.height

rotation = 180


# Turn on the backlight
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# sleep between reads on the buffer
sleep = 0.1

# font attributes
fontwidth = 4
fontheight = 8

# calculate the rows and columns based on the font and display width
columns = int(width / fontwidth)
rows = int(height / fontheight)

# create the terminal emulator 
screen = pyte.Screen(columns, rows)
stream = pyte.ByteStream(screen)

# run a tmux and create/reattach to the "tty" session
argv = shlex.split("tmux -2 new-session -A -s tty")

# get 
buff = screen.buffer

# create the image for the display
image = Image.new("RGB", (width, height), "black")

# get a draw object to paste the font glyphs and stuff
draw = ImageDraw.Draw(image)

# create the old cursor
oldcursor = (0, 0, None)

logging.info("Starting tmux")
p = ptyprocess.PtyProcess.spawn(argv, dimensions=(rows, columns))

logging.info("Connecting display")
while True:
    data = p.read(4096)
    if not data:
        pass
    else:
        stream.feed(data)
        # get the current cursor
        cursor = (int(screen.cursor.x), int(screen.cursor.y), ord(screen.cursor.attrs.data))

        # do something only if content has changed or cursor was moved
        if (screen.dirty or oldcursor != cursor):
            # get the rows that changed
            dirtyrows = screen.dirty.copy()

            # treat the screen as clean    
            screen.dirty.clear()

            # add the cursor rows so they also get redrawn
            dirtyrows.add(cursor[1])
            dirtyrows.add(oldcursor[1])

            # iterate through all the changed characters
            for row in dirtyrows:
                for col in range(0, columns):
                    char = buff[row][col]

                    # check for bold attribute
                    if char.bold:
                        fgfill = theme[char.fg]  if char.fg != "default" else theme["foreground"]
                    else:
                        fgfill = theme[char.fg] if char.fg != "default" else theme["foreground"]
                    
                    # set the background
                    bgfill = theme[char.bg] if char.bg != "default" else theme["background"]
                    
                    # check for reverse attribute
                    if char.reverse:
                        fgfill, bgfill  = bgfill, fgfill
                    
                    # draw the background
                    draw.rectangle([(col * fontwidth, row * fontheight),(col * fontwidth + fontwidth - 1, row * fontheight + fontheight - 1)], outline=bgfill, fill=bgfill)
                    
                    # draw the character glyph, return "?" if the font doesn't have it
                    draw.bitmap((col * fontwidth, row * fontheight), glyphDict.get(ord(char.data if len(char.data) == 1 else "?"), glyphDict[63]), fill=fgfill)
                    
                    # check for underscore
                    if char.underscore:
                        draw.line([(col * fontwidth, row * fontheight + fontheight -1 ), (col * fontwidth + fontwidth - 1, row * fontheight + fontheight - 1)], fill=fgfill)

            # draw the cursor
            cur_x, cur_y = cursor[0], cursor[1]
            start_x = cur_x * fontwidth
            start_y = cur_y * fontheight + fontheight - 1
            draw.line((start_x, start_y, start_x + fontwidth, start_y), fill="white")        

            # send the image to the display
            disp.image(image, rotation)

            # save the cursor
            oldcursor = cursor

