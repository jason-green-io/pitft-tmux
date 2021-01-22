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
import os 
import sys
import random
from gpiozero import Button
import subprocess

tmux = "/usr/bin/tmux"
tmuxPty = "tty"

left = Button(23)
right = Button(24)


def previousWindow():
    subprocess.Popen([tmux, "previous-window", "-t", tmuxPty],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    logging.info("button: previous window")

def nextWindow():
    subprocess.Popen([tmux, "next-window", "-t", tmuxPty],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    logging.info("button: next window")

left.when_pressed = previousWindow
right.when_pressed = nextWindow

dir_path = os.path.dirname(os.path.realpath(__file__))

#setup logging
logging.basicConfig(level=logging.DEBUG)

# open theme file
with open(os.path.join(dir_path, "theme.json"), "r") as handle:
    logging.info("Loading color theme")
    theme = json.load(handle)

# load miniwi
with open(os.path.join(dir_path, "miniwi-qrunicode.bdf"), "rb") as handle:
    logging.info("Reading font file")
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
logging.info("Loading glyphs from font")
glyphDict = {cp: getGlyph(cp, bdffont) for cp in bdffont.codepoints()}

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
# get the display size
width = disp.width
height = disp.height

# set the orientation
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
argv = shlex.split("bash -c 'TERM=xterm-256color tmux -2 new-session -A -s tty'")

def getX(row, rotation=rotation):
    """return the X coordinate base on the orientation and update row"""
    if rotation == 0:
        return 0
    elif rotation == 180:
        return 0
    elif rotation == 90:
        return row * fontheight
    elif rotstion == 270:
        return (rows - row -1) * fontheight
    
def getY(row, rotation=rotation):
    """return the Y coordinate base on the orientation and update row"""
    if rotation == 0:
        return row * fontheight
    elif rotation == 180:
        return (rows - row - 1) * fontheight
    elif rotation == 90:
        return 0
    elif rotstion == 270:
        return 0

def writer():
    """read from the process in a pseudo termnial and write it to the terminal emulator"""
    p = ptyprocess.PtyProcess.spawn(argv, dimensions=(rows, columns))

    while True:
        try:
            data = p.read(4096)
        except:
            logging.info("Something went wrong with reading the pty")
            sys.exit(1)
        if not data:
            pass
        else:
            stream.feed(data)

# start tmux and write to the terminal emulator
writerThread = threading.Thread(target=writer, name="glue")
writerThread.daemon = True
writerThread.start()
logging.info("Started writer")

# create the image for the display
image = Image.new("RGB", (width, fontheight), "black")

# get a draw object to paste the font glyphs and stuff
draw = ImageDraw.Draw(image)

# create the old cursor
oldcursor = (0, 0, None)

logging.info("Starting screen")

while writerThread.is_alive():
    
    # get the current cursor
    cursor = (int(screen.cursor.x), int(screen.cursor.y), ord(screen.cursor.attrs.data))

    # do something only if content has changed or cursor was moved
    if (screen.dirty or oldcursor != cursor):

        # get the rows that changed, an clean the dirty
        dirtyrows = screen.dirty.copy()
        screen.dirty.clear()

        # add the cursor rows so they also get redrawn
        dirtyrows.add(cursor[1])
        dirtyrows.add(oldcursor[1])

        logging.debug("screen: dirty %s", dirtyrows)
        
        # iterate through all the changed characters
        for row in dirtyrows:
            for col in range(columns):
                char = screen.buffer[row][col]
                # check for bold attribute
                if char.bold:
                    fgfill = theme.get(char.fg, "#" + char.fg) if char.fg != "default" else theme["foreground"]
                else:
                    fgfill = theme.get(char.fg, "#" + char.fg) if char.fg != "default" else theme["foreground"]
                
                # set the background
                bgfill = theme.get(char.bg, "#" + char.bg) if char.bg != "default" else theme["background"]
                
                # check for reverse attribute
                if char.reverse:
                    fgfill, bgfill  = bgfill, fgfill
                
                # draw the background
                draw.rectangle([(col * fontwidth, 0),(col * fontwidth + fontwidth - 1, fontheight - 1)], outline=bgfill, fill=bgfill)
                
                # draw the character glyph, return "?" if the font doesn't have it
                draw.bitmap((col * fontwidth, 0), glyphDict.get(ord(char.data if len(char.data) == 1 else "?"), glyphDict[63]), fill=fgfill)
                
                # check for underscore
                if char.underscore:
                    draw.line([(col * fontwidth, fontheight -1 ), (col * fontwidth + fontwidth - 1, fontheight - 1)], fill=fgfill)
                
                # draw the cursor if it's on this row 
                if cursor[1] == row:
                    cur_x, cur_y = cursor[0], cursor[1]
                    start_x = cur_x * fontwidth
                    start_y = fontheight - 1
                    draw.line((start_x, start_y, start_x + fontwidth, start_y), fill="white")        
            
            # draw the row on the screen
            disp.image(image, rotation, x=getX(row), y=getY(row)) 
        
        # save the cursor
        oldcursor = cursor
    else:

        # sleep a bit before chercking for updates
        time.sleep(sleep)
