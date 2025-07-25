#!/usr/bin/python3
# -*- coding: UTF8 -*-

# shutdown Raspberry Pi with button press

import os
import time

import board
import digitalio
from adafruit_debouncer import Debouncer

import audio
import leds


def wait_for_shutdown_button(
    btn_pin=board.D13,
    threshold_time=3,
    poll_interval=0.1,
):
    print("starting switch off")

    off_btn = digitalio.DigitalInOut(btn_pin)
    off_btn.direction = digitalio.Direction.INPUT
    off_btn.pull = digitalio.Pull.UP

    off = Debouncer(off_btn, interval=0.05)

    try:
        while True:
            off.update()

            # if button was released, check if it was pressed for at least threshold_time seconds
            if off.rose:
                if off.last_duration > threshold_time:
                    print("shutdown")
                    leds.blink = False
                    time.sleep(0.5)
                    leds.reset()
                    leds.switch_all_on_with_color((255, 0, 0))
                    audio.play_full(
                        "TTS", 3
                    )  # "Tschüss ich schalte mich jetzt aus"
                    os.system("shutdown -P now")
            time.sleep(poll_interval)
    finally:
        off_btn.deinit()


if __name__ == "__main__":
    wait_for_shutdown_button()
