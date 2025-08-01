#!/usr/bin/env python3
# -*- coding: UTF8 -*-
import pygame

import crud
import file_lib
import leds
import models
import rfidreaders
from logger_util import get_logger
import time

logger = get_logger(__name__, "logs/game_kakophonie.log")

from .game_utils import (
    announce,
    check_end_tag,
)

phones = []


def start():
    print("Wir spielen Kakophonie")

    defined_numbers = file_lib.get_tags_by_type("numeric")

    # Log Usage
    u = models.Usage(game="kakophonie", players=1)
    crud.add_game_entry(usage=u)

    volume = 0

    # Wir spielen Kakophonie. Stelle die Zahlen 1 bis 6 auf die Spielfelder!
    announce(64)
    leds.reset()  # reset leds

    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(frequency=22050, buffer=512)
        time.sleep(1)
        pygame.mixer.init()
        # pygame.mixer.init(buffer=4096)
        pygame.mixer.set_num_channels(6)

        for s in range(0, 6):
            phones.append(
                pygame.mixer.Sound("data/phonie/00" + str(s + 1) + ".ogg")
            )
            phones[s].set_volume(0)
    else:
        pygame.mixer.unpause()

    for p in phones:
        p.play(loops=-1)
    leds.blinker()

    while True:
        found_digits = []
        active_leds = []
        for i, tag in enumerate(rfidreaders.tags):
            if tag is not None and tag.name is not None:
                tag = crud.get_first_rfid_tag_by_id_and_type(tag.rfid_tag)
                active_leds.append(i + 1)
                if tag:
                    tag_number = int(tag.name)
                    if 1 <= tag_number <= 6:
                        found_digits.append(tag_number - 1)

        leds.switch_on_with_color(
            active_leds
        )

        for i in range(0, 6):
            if i not in found_digits:
                phones[i].set_volume(0)
            else:
                phones[i].set_volume(0.5)

        if check_end_tag():
            for x in phones:
                x.set_volume(1.0)
                x.stop()
            pygame.mixer.quit()
            leds.blinker()
            leds.reset()
            return

    leds.blink = False
    leds.reset()
