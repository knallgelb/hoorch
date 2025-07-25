#!/usr/bin/env python3
import json
import os
import socket
import time

import board
import neopixel

SOCK_FILE = "/tmp/hoorch_led.sock"

# Hardware-Setup
pixel_pin = board.D12
num_pixels = 7
ORDER = neopixel.GRB
pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.9, auto_write=False, pixel_order=ORDER
)


def blink(color, times=5, interval=0.3, leds=None):
    """
    Lässt LEDs blinken.
    :param color: Farbe als [R, G, B]
    :param times: Anzahl der Blinks
    :param interval: Pause zwischen Ein/Aus (Sekunden)
    :param leds: Liste der LEDs (oder Einzel-LED), None für alle
    """
    c = tuple(color)
    if leds is not None:
        if isinstance(leds, int):
            leds = [leds]
    for _ in range(times):
        if leds is None:
            pixels.fill(c)
        else:
            reset()
            for led in leds:
                pixels[led] = c
        pixels.show()
        time.sleep(interval)
        reset()
        time.sleep(interval)


def reset():
    pixels.fill((0, 0, 0))
    pixels.show()


def switch_all_on_with_color(color):
    pixels.fill(tuple(color))
    pixels.show()


def switch_on_with_color(leds, color):
    reset()
    c = tuple(color)
    if isinstance(leds, int):
        leds = [leds]
    for led in leds:
        pixels[led] = c
    pixels.show()


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            idx = (i * 256 // num_pixels) + j
            pixels[i] = wheel(idx & 255)
        pixels.show()
        time.sleep(wait)
    reset()


def wheel(pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (int(pos * 3), int(255 - pos * 3), 0)
    if pos < 170:
        pos -= 85
        return (int(255 - pos * 3), 0, int(pos * 3))
    pos -= 170
    return (0, int(pos * 3), int(255 - pos * 3))


if os.path.exists(SOCK_FILE):
    os.remove(SOCK_FILE)
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(SOCK_FILE)
server.listen(1)

print("leds_server läuft und wartet auf Befehle via", SOCK_FILE)

try:
    while True:
        conn, _ = server.accept()
        data = conn.recv(1024)
        try:
            cmd = json.loads(data.decode())
            if cmd["cmd"] == "color":
                switch_all_on_with_color(cmd["color"])
            elif cmd["cmd"] == "off":
                reset()
            elif cmd["cmd"] == "multi":
                switch_on_with_color(cmd["leds"], cmd["color"])
            elif cmd["cmd"] == "rainbow":
                rainbow_cycle(cmd.get("wait", 0.01))
            elif cmd["cmd"] == "blink":
                blink(
                    cmd.get("color", [255, 255, 255]),
                    cmd.get("times", 5),
                    cmd.get("interval", 0.3),
                    cmd.get("leds"),
                )
        except Exception as e:
            print("Fehler beim Verarbeiten des Kommandos:", e)
        conn.close()
finally:
    server.close()
    os.remove(SOCK_FILE)
