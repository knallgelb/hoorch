#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import random
import threading
import time

import board
import neopixel

# LEDS

# Neopixel connected to GPIO12 / pin32
pixel_pin = board.D12

# The number of NeoPixels
num_pixels = 6

# The order of the pixel colors - RGB or GRB.
ORDER = neopixel.GRB

_pixels = None


def get_pixels():
    global _pixels
    if _pixels is None:
        _pixels = neopixel.NeoPixel(
            pixel_pin, num_pixels, brightness=0.9, auto_write=False, pixel_order=ORDER
        )
    return _pixels


# start random blinking of leds
blink = False


def init():
    # Optionale Initialisierung; ruft reset und ggf. blinker auf,
    # wird aber NICHT beim Import, sondern nur auf expliziten Wunsch ausgeführt!
    reset()
    blinker()


def testr():
    pixels = get_pixels()
    for i in range(0, 1):
        # rot
        pixels.fill((255, 0, 0))
        pixels.show()
        time.sleep(3)

        # gruen
        pixels.fill((0, 255, 0))
        pixels.show()
        time.sleep(3)

        # blau
        pixels.fill((0, 0, 255))
        pixels.show()
        time.sleep(3)
        reset()


def reset():
    pixels = get_pixels()
    # set all pixels to no color
    pixels.fill((0, 0, 0))
    pixels.show()


def rainbow_cycle(wait):
    pixels = get_pixels()
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)
    reset()


def rotate_one_round(time_per_led):
    pixels = get_pixels()
    color = wheel(random.randrange(0, 255))
    for i in range(len(pixels)):
        pixels.fill((0, 0, 0))
        pixels[i] = color
        pixels.show()
        time.sleep(time_per_led)
    reset()


def blinker():
    global blink
    pixels = get_pixels()
    if blink:
        pixels.fill((0, 0, 0))
        pixels[random.randrange(len(pixels))] = wheel(random.randrange(0, 255))
        pixels.show()
        # alle 0,5s wieder aufgerufen – Rekursion/Threading!
        threading.Timer(0.50, blinker).start()


def switch_all_on_with_color(color=None):
    switch_on_with_color(list(range(num_pixels)), color)


def switch_on_with_color(number, color=None):
    pixels = get_pixels()
    reset()
    # random color if none given
    if color is None:
        color = wheel(random.randrange(0, 255))

    if isinstance(number, tuple):
        # leds.switch_on_with_color((0,3,5), (200,200,100))
        for c in number:
            pixels[c] = color
    elif isinstance(number, list):
        # expect players list
        for i, p in enumerate(number):
            if p is not None:
                pixels[i] = color
    else:
        pixels[number] = color

    pixels.show()


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
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


if __name__ == "__main__":
    # Testfunktion nach Bedarf nachrüsten:
    # z.B. testr(), rainbow_cycle(0.01)
    print("leds.py as main: testrun (rot, grün, blau, aus)")
    testr()
    reset()
