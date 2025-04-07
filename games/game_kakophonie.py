#!/usr/bin/env python3
# -*- coding: UTF8 -*-
import pdb
import re
import pygame
import audio
import rfidreaders
import leds
import file_lib

from logger_util import get_logger

logger = get_logger(__name__, "logs/game_kakophonie.log")

from .game_utils import (
    check_end_tag,
    announce,
)

phones = []


def start():
    print("Wir spielen Kakophonie")

    defined_numbers = file_lib.animal_numbers_db

    volume = 0

    # Wir spielen Kakophonie. Stelle die Zahlen 1 bis 6 auf die Spielfelder!
    announce(64)
    leds.reset()  # reset leds

    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(frequency=22050, buffer=512)
        pygame.mixer.init()
        # pygame.mixer.init(buffer=4096)
        pygame.mixer.set_num_channels(6)

        for s in range(0, 6):
            phones.append(pygame.mixer.Sound("data/phonie/00"+str(s+1)+".ogg"))
            phones[s].set_volume(0)
    else:
        pygame.mixer.unpause()

    for p in phones:
        p.play(loops=-1)
    leds.blink = True

    while True:
        found_digits = []
        for i, tag in enumerate(rfidreaders.tags):
            if tag is not None and tag.number is not None:
                found_digits.append(int(rfidreaders.tags[i].number))  # get digit

        for i in range(0, 6):
            if i not in found_digits:
                phones[i].set_volume(0)
            else:
                phones[i].set_volume(0.5)

        if check_end_tag():
            # pdb.set_trace()
            for x in phones:
                x.set_volume(1.0)
                x.stop()
            pygame.mixer.quit()
            return

    leds.blink = False
    leds.reset()
