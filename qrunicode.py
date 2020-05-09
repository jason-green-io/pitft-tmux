#!/usr/bin/env python3
from collections import defaultdict
import qrcode
import argparse
import fileinput

parser = argparse.ArgumentParser(description='Print qrcodes using custom miniwi-qrunicode BDF font')
parser.add_argument('--reverse', action='store_true',
                    help='reverse qrcode colors')
parser.add_argument('files', metavar='FILE', nargs='*', help='files to read, if empty, stdin is used')

args = parser.parse_args()

map = [[1,8],
       [2,16],
       [4,32],
       [64,128]]

brailledecimal = 10240
qrdecimal = 60928

def qrunicode(data, reverse):

    code = qrcode.QRCode()

    code.add_data(data)
    code.border=1
    matrix = code.get_matrix()

    chars = defaultdict(int)

    for y, r in enumerate(matrix):
        yc, ymap = divmod(y, 4)
        ymax = yc
        for x, b in enumerate(r):
            xc, xmap = divmod(x, 2)
            xmax = xc
            if b:
                chars[yc,xc] += map[ymap][xmap]

    stringList = []

    for y in range(0, ymax + 1):
        string = ""
        for x in range(0, xmax + 1):
            string += chr(qrdecimal + chars[y, x])
        stringList.append(string) 
    
    codeString = "\n".join(stringList) 
   
    if reverse:    
        return "\x1B[7m" + codeString + "\x1B[27m"
    else:
        return codeString

data = "\n".join(fileinput.input(files=args.files))

print(qrunicode(data, args.reverse))
