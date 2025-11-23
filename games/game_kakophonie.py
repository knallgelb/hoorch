#!/usr/bin/env python3
# -*- coding: UTF8 -*-
import time

import pygame

import crud
import file_lib
import leds
import models
import rfidreaders
from logger_util import get_logger

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
        end_found = False

        # take a synchronous snapshot from the readers and normalize to a list
        snapshot = list(rfidreaders.get_tags_snapshot(True) or [])

        # iterate over slots (a slot may be None, a tag object, or a list/tuple of tag objects)
        for i, slot in enumerate(snapshot):
            tag = None
            if slot is None:
                continue
            if isinstance(slot, (list, tuple)):
                # pick first non-None entry from the slot
                for el in slot:
                    if el is None:
                        continue
                    tag = el
                    break
            else:
                tag = slot

            # check for ENDE directly inside the loop
            if tag is not None and getattr(tag, "name", None) == "ENDE":
                end_found = True
                break

            # lookup numeric definition from DB (prefer explicit numeric type)
            if tag is not None and getattr(tag, "rfid_tag", None):
                try:
                    db_tag = crud.get_first_rfid_tag_by_id_and_type(
                        tag.rfid_tag, "numeric"
                    )
                except TypeError:
                    db_tag = crud.get_first_rfid_tag_by_id_and_type(
                        tag.rfid_tag
                    )
                    if (
                        db_tag
                        and getattr(db_tag, "rfid_type", None) != "numeric"
                    ):
                        db_tag = None

                if db_tag:
                    active_leds.append(i + 1)
                    try:
                        tag_number = int(db_tag.name)
                    except Exception:
                        continue
                    if 1 <= tag_number <= 6:
                        found_digits.append(tag_number - 1)

        leds.switch_on_with_color(active_leds)

        for i in range(0, 6):
            if i not in found_digits:
                phones[i].set_volume(0)
            else:
                phones[i].set_volume(0.5)

        # handle end condition detected inside the loop
        if end_found:
            for x in phones:
                x.set_volume(1.0)
                x.stop()
            pygame.mixer.quit()
            leds.blinker()
            leds.reset()
            return

    leds.blink = False
    leds.reset()
