#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import json
import socket

SOCK_FILE = "/tmp/hoorch_led.sock"
num_pixels = 6


def send_led_command(cmd, **kwargs):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SOCK_FILE)
        cmdobj = dict(cmd=cmd)
        cmdobj.update(kwargs)
        s.sendall(json.dumps(cmdobj).encode())
        s.close()
    except Exception as e:
        print(f"LED-IPC ERROR: {e} (cmd={cmd} kwargs={kwargs})")


def reset():
    """Alle LEDs aus."""
    send_led_command("off")


def switch_all_on_with_color(color=None):
    """Alle LEDs auf eine Farbe setzen. Ohne Angabe zufällige Farbe."""
    if color is None:
        from random import randint

        color = (randint(0, 255), randint(0, 255), randint(0, 255))
    send_led_command("color", color=list(color))  # Farbtupel als Liste


def switch_on_with_color(number, color=None):
    """Einzelne LEDs oder Liste/Tuple ansteuern (z.B. switch_on_with_color([0,3,5], (128,255,0)))"""
    if color is None:
        from random import randint

        color = (randint(0, 255), randint(0, 255), randint(0, 255))
    if isinstance(number, int):
        leds = [number]
    else:
        leds = list(number)
    send_led_command("multi", leds=leds, color=list(color))


def rainbow_cycle(wait=0.01):
    """Starte Rainbow-Effect (optional: Dauer zwischen Steps, default 10ms)"""
    send_led_command("rainbow", wait=wait)


def rotate_one_round(time_per_led=0.2):
    """Rotiert eine Farbe rundherum."""
    send_led_command("rotate", delay=time_per_led)


def blinker():
    """Starte oder stoppe Blinken (toggle)."""
    send_led_command("blink")


def testr():
    """Einfacher LED-Farbtest."""
    switch_all_on_with_color((255, 0, 0))
    import time

    time.sleep(1)
    switch_all_on_with_color((0, 255, 0))
    time.sleep(1)
    switch_all_on_with_color((0, 0, 255))
    time.sleep(1)
    reset()


def wheel(pos):
    """Farbrad wie gewohnt"""
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b)


# Dummy blink state (da keine Hardware mehr) – falls Code darauf prüft
blink = False

if __name__ == "__main__":
    print("leds.py as main: Testlauf über Server")
    testr()
    reset()
