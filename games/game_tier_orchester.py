#!/usr/bin/env python3
# -*- coding: UTF8 -*-
import pygame

import copy
import time
import audio
import rfidreaders
import leds
import file_lib
import models
import crud
import pathlib


from .game_utils import (
    check_end_tag,
    announce,
    announce_file,
)

from logger_util import get_logger

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

    playing_animals = [None, None, None, None, None, None]
    leds.blinker()

    found_animals = [None, None, None, None, None, None]

    while True:
        for i, animal in enumerate(rfidreaders.tags):
            if check_end_tag():
                # pdb.set_trace()
                for x in phones:
                    x.set_volume(1.0)
                    x.stop()
                pygame.mixer.quit()
                leds.blinker()
                leds.reset()
                return

            if not isinstance(animal, models.RFIDTag):
                playing_animals[i] = False
                continue

            if animal is not None:
                playing_animals[i] = True
                sound_path = pathlib.Path(
                    f"data/animal_sounds/{animal.name}.mp3"
                )
                if sound_path not in found_animals and sound_path.exists():
                    found_animals[i] = sound_path
                    phones[i] = pygame.mixer.Sound(sound_path)
                    phones[i].set_volume(0.05)
                    leds_position = i + 1
                    leds.switch_on_with_color(leds_position, (255, 255, 0))

        for i, p in enumerate(phones):
            if not playing_animals[i]:
                p.set_volume(0)
                continue
            p.play()

    time.sleep(0.2)
    leds.blinker()
    leds.reset()
