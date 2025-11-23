#!/usr/bin/env python3
# -*- coding: UTF8 -*-
import pathlib
import time

import pygame

import crud
import file_lib
import leds
import models
import rfidreaders
from logger_util import get_logger

from .game_utils import (
    announce,
)

logger = get_logger(__name__, "logs/game_tier_orchester.log")

phones = []


def start():
    defined_animals = file_lib.get_tags_by_type("animals")

    logger.info(f"Defined animals: {defined_animals}")
    logger.info(
        "The animal orchestra is starting. Place the animal figures on the game fields!"
    )

    # Log Usage
    u = models.Usage(game="tier_orchester", players=1)
    crud.add_game_entry(usage=u)

    announce(63)
    leds.reset()  # Reset LEDs

    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(frequency=22050, buffer=512)
        time.sleep(1)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(6)

        for s in range(0, 6):
            phones.append(
                pygame.mixer.Sound("data/phonie/00" + str(s + 1) + ".ogg")
            )
            phones[s].set_volume(0)
    else:
        pygame.mixer.unpause()

    # normalize playing_animals to a list of bools and found_animals to a list of optional Paths
    playing_animals: list[bool] = [False] * 6
    leds.blinker()

    found_animals: list = [None] * 6

    while True:
        # take a synchronous snapshot and normalize to a concrete list
        snapshot: list = list(rfidreaders.get_tags_snapshot(True) or [])
        end_found = False

        # iterate only up to the number of playing slots to avoid index errors;
        # a slot may be None, a tag object, or a list/tuple of tag objects
        for i in range(len(playing_animals)):
            slot = snapshot[i] if i < len(snapshot) else None
            tag = None
            if slot is None:
                playing_animals[i] = False
                continue

            if isinstance(slot, (list, tuple)):
                # pick first non-None element of the slot
                for el in slot:
                    if el is not None:
                        tag = el
                        break
            else:
                tag = slot

            # direct ENDE check inside the loop
            if tag is not None and getattr(tag, "name", None) == "ENDE":
                end_found = True
                break

            # only consider RFIDTag objects for playing animals
            if not isinstance(tag, models.RFIDTag):
                playing_animals[i] = False
                continue

            # mark slot as active and prepare sound if available
            playing_animals[i] = True
            sound_path = pathlib.Path(f"data/animal_sounds/{tag.name}.mp3")
            if sound_path not in found_animals and sound_path.exists():
                found_animals[i] = sound_path
                phones[i] = pygame.mixer.Sound(sound_path)
                phones[i].set_volume(0.05)
                leds_position = i + 1
                leds.switch_on_with_color(leds_position, (255, 255, 0))

        # if ENDE tag found, stop everything and exit
        if end_found:
            for x in phones:
                x.set_volume(1.0)
                x.stop()
            pygame.mixer.quit()
            leds.blinker()
            leds.reset()
            return

        for i, p in enumerate(phones):
            if not playing_animals[i]:
                p.set_volume(0)
                continue
            p.play()

    time.sleep(0.2)
    leds.blinker()
    leds.reset()
