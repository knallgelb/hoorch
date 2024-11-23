#!/usr/bin/python3
# -*- coding: UTF8 -*-

import os
import subprocess
from shlex import split
import board
import digitalio
from adafruit_debouncer import Debouncer
import time

from dotenv import load_dotenv, set_key
from gi.overrides import override

print("starting adjust volume")

vol_up_btn = digitalio.DigitalInOut(board.D2)
vol_up_btn.direction = digitalio.Direction.INPUT
vol_up_btn.pull = digitalio.Pull.UP

vol_down_btn = digitalio.DigitalInOut(board.D3)
vol_down_btn.direction = digitalio.Direction.INPUT
vol_down_btn.pull = digitalio.Pull.UP

vol_up = Debouncer(vol_up_btn, interval=0.05)
vol_down = Debouncer(vol_down_btn, interval=0.05)

dotenv_path = ".env"


def volume_up():
    load_dotenv(dotenv_path, override=True)

    print("volume up")

    SPEAKER_VOLUME = int(os.getenv("SPEAKER_VOLUME", "50"))
    SPEAKER_VOLUME = min(SPEAKER_VOLUME + 10, 90)
    os.environ["SPEAKER_VOLUME"] = str(SPEAKER_VOLUME)
    set_key(dotenv_path, "SPEAKER_VOLUME", SPEAKER_VOLUME, quote_mode="never")
    log_volume(SPEAKER_VOLUME)

def log_volume(vol):
    print(f"Current VOLUME: {vol}")

def volume_down():
    print("volume down")
    load_dotenv(dotenv_path, override=True)
    SPEAKER_VOLUME = int(os.getenv("SPEAKER_VOLUME", "50"))
    SPEAKER_VOLUME = max(SPEAKER_VOLUME - 10, 0)
    os.environ["SPEAKER_VOLUME"] = str(SPEAKER_VOLUME)
    set_key(dotenv_path, "SPEAKER_VOLUME", SPEAKER_VOLUME, quote_mode="never")
    log_volume(SPEAKER_VOLUME)


while True:
    vol_up.update()
    vol_down.update()

    if vol_up.fell:
        #volume up button pressed
        volume_up()
    elif vol_down.fell:
        #volume down button pressed
        volume_down()
    time.sleep(0.1)