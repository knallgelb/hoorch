#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import copy
import time
import audio
import rfidreaders
import leds
import logging
import os
import file_lib

# Create 'logs' directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Get the log filename based on the script's name
log_filename = os.path.join('logs', os.path.splitext(os.path.basename(__file__))[0] + '.log')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def start():
    defined_animals = file_lib.animal_figures_db

    logger.info(f"Defined animals: {defined_animals}")
    logger.info("The animal orchestra is starting. Place the animal figures on the game fields!")
    audio.play_full("TTS", 63)
    leds.reset()  # Reset LEDs

    playing_animals = [None, None, None, None, None, None]
    leds.blink = True
    while True:
        animals = copy.deepcopy(rfidreaders.tags)
        logger.debug(f"Current animals on fields: {animals}")

        if "ENDE" in animals:
            leds.blink = False
            leds.reset()
            audio.kill_sounds()
            logger.info("Game ended by detecting 'ENDE' tag.")
            break

        for i, animal in enumerate(animals):
            if animal is not None:
                animal = animal[:-1]
            if animal not in defined_animals:
                if animal is not None:
                    logger.warning(f"Undefined animal '{animal}' detected on field {i + 1}")
                animal = None
            if animal is not None:
                if not audio.file_is_playing(animal + ".mp3"):
                    audio.play_file("animal_sounds", animal + ".mp3")
                    playing_animals[i] = animal
                    logger.info(f"Playing sound for animal '{animal}' on field {i + 1}")

        time.sleep(0.2)
