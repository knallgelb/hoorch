#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import copy
import time
import audio
import rfidreaders
import leds
import file_lib
import models
import crud


from .game_utils import (
    check_end_tag,
    announce,
    announce_file,
)

from logger_util import get_logger

logger = get_logger(__name__, "logs/game_tier_orchester.log")


def start():
    defined_animals = file_lib.get_tags_by_type("animals")

    logger.info(f"Defined animals: {defined_animals}")
    logger.info("The animal orchestra is starting. Place the animal figures on the game fields!")

    # Log Usage
    u = models.Usage(game="tier_orchester", players=1)
    crud.add_game_entry(usage=u)

    announce(63)
    leds.reset()  # Reset LEDs

    playing_animals = [None, None, None, None, None, None]
    leds.blinker()
    while True:
        animals = [tag for tag in copy.deepcopy(rfidreaders.tags) if
                   isinstance(tag, models.RFIDTag) and tag.rfid_type == 'animals']
        logger.debug(f"Current animals on fields: {animals}")

        if check_end_tag():
            leds.blinker()
            leds.reset()
            audio.kill_sounds()
            logger.info("Game ended by detecting 'ENDE' tag.")
            return

        for i, animal in enumerate(animals):
            assert isinstance(animal, models.RFIDTag)
            if animal is not None:
                if not audio.file_is_playing(animal.name + ".mp3"):
                    leds.switch_on_with_color(i, (255, 255, 0))  # Gelb für aktuelles Tier
                    announce_file(msg_id=animal.name + ".mp3", path="animal_sounds")
                    playing_animals[i] = animal
                    logger.info(f"Playing sound for animal '{animal}' on field {i + 1}")
                    time.sleep(0.3)
                    leds.switch_on_with_color(i, (0, 0, 0))      # wieder LED aus

    time.sleep(0.2)
leds.blinker()
leds.reset()
