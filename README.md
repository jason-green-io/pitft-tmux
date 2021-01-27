# pitft-tmux

## What is it?

* terminal emulator supporting 16, 256 and 24bit colors of foreground/background, underline, reverse and bold
* [miniwi](https://git.z0.is/miniwi/log.html) BDF font (with a few additional custom qrcode glyphs) supporting line drawing characters, drawille
* qrcode utility to use custom glyphs
* runs tmux, used to connect to a session to remote control the display
* use simple shell scripts to output whatever you like
* 60 columns * 30 rows on a 1.3" display (pretty much unreadable without a magnifying glass)
* buttons switch tmux window

## Examples

This is my Pi Zero W and the Adafruit PiTFT 1.3" hat.

reddit TIL
figlet
trivia
weather wttr.in
temperature graph
count down
ansi art
pixterm

## Prerequisites

`apt install tmux python3-pip`

`pip3 install adafruit-circuitpython-rgb-display spidev bdflib pyte qrcode ptyprocess gpiozero`

## How to run

Includes a systemd service file to connect the display to tmux. Copy `pitft-tmux.service` to `/etc/systemd/system`. Then run `systemctl enable pitft-tmux.service` and start it with `systemctl start pitft-tmux.service`.

Include this in your `.bashrc` to autorun `tmux` on login and relaunch if it gets disconnected.

```
if [[ $(tty) == "/dev/tty1" ]] && [[ -z "$TMUX" ]]; then 
        while true; do      
             tmux new-session -A -s "tty"
        done         
fi        
```

You'll probably want to auto login the `pi` user via raspi-config

```
Choose option 3: Boot Options
Choose option B2: Console Autologin
Select Finish, and reboot the Raspberry Pi.
```

## pitft-tmux.py

Manually run it with `./pitft-tmux.py`. Then connect to the `tmux` session with `tmux new-session -A -s "tty"`

## theme.json

Color definitions, default is set to [gruvbox](https://github.com/morhetz/gruvbox).

## qrunicode

Custom glyphs are in the unused ee00:eeff range of unicode. `qrunicode` converts a qrcode matrix to these glyphs to fit more bits on the screen than the traditional block glyphs.


```
usage: qrunicode.py [-h] [--reverse] [FILE [FILE ...]]

Print qrcodes using custom miniwi-qrunicode BDF font

positional arguments:
  FILE        files to read, if empty, stdin is used

optional arguments:
  -h, --help  show this help message and exit
  --reverse   reverse qrcode colors
```
