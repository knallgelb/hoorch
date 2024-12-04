#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import random
import copy
import re
import time
import audio
import rfidreaders
import leds
import file_lib
import pdb

def start():
    # Accessing databases from file_lib
    defined_figures = file_lib.figures_db  # Game figures
    all_tags = file_lib.all_tags  # All known tags

    audio.play_full("TTS", 85)  # We are now practicing multiplication.
    leds.reset()  # Reset LEDs

    # Prompt players to place their figures
    audio.play_full("TTS", 86)  # Place your figures on fields 1, 3, or 5 where the lights are on.
    leds.switch_on_with_color((0, 2, 4))
    audio.play_file("sounds", "waiting.mp3")  # Play waiting sound
    time.sleep(6)

    # Check the figures on the board
    players = copy.deepcopy(rfidreaders.tags)

    # Only consider fields 1, 3, and 5
    fields_to_set_none = [1,3,5]

    for i in range(len(players)):
        if (i in fields_to_set_none
                or players[i] is None
                or players[i].rfid_tag not in defined_figures.keys()):
            players[i] = None

    figure_count = sum(x is not None for x in players)

    if figure_count == 0:
        # No game figures placed
        audio.play_full("TTS", 59)
        return

    audio.play_full("TTS", 5 + figure_count)  # x figures are playing

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        return

    rounds = 3  # Number of rounds
    audio.play_full("TTS", 20 + rounds)  # We will play x rounds
    points = [0] * len(players)  # Points for each player

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        return

    is_first_round = True
    for r in range(rounds):
        for i, player in enumerate(players):
            if player is not None:
                leds.reset()
                leds.switch_on_with_color(i)

                if is_first_round:
                    is_first_round = False
                    audio.play_full("TTS", 12 + i)  # The figure on field x starts
                    audio.play_full("TTS", 89)  # Place the tens digit to the left and the units digit to the right...

                elif figure_count == 1:
                    audio.play_full("TTS", 67)  # It's your turn again
                else:
                    audio.play_full("TTS", 48 + i)  # The next figure on field x

                if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
                    return

                # Generate a math problem
                num1, num2 = random.randint(1, 9), random.randint(1, 9)
                solution = num1 * num2

                audio.play_full("TTS", 87)  # How much is...
                audio.play_full("TTS", 90 + num1)  # Number 1
                audio.play_full("TTS", 88)  # times
                audio.play_full("TTS", 90 + num2)  # Number 2

                if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
                    return

                # LEDs blinking to indicate waiting for the answer
                for _ in range(10):
                    leds.switch_on_with_color(i)
                    time.sleep(0.5)
                    leds.switch_on_with_color(i, (0, 0, 0))
                    time.sleep(0.5)

                if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
                    return

                # pdb.set_trace()

                # Validate the answer
                tens = rfidreaders.tags[(i + 1) % len(players)]  # Tens digit field
                units = rfidreaders.tags[(i - 1) % len(players)]  # Units digit field

                tens_digit = int(tens.number) * 10 if tens else 0
                unit_digit = int(units.number) if units else 0

                if tens_digit + unit_digit == solution:
                    audio.play_full("TTS", 27)  # Correct!
                    points[i] += 1
                else:
                    audio.play_full("TTS", 26)  # Wrong!

                if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
                    return

    # Announce the scores
    audio.play_full("TTS", 80)  # I will now announce the scores
    for i, player in enumerate(players):
        if player is not None:
            leds.reset()
            leds.switch_on_with_color(i)
            audio.play_full("TTS", 74 + i)  # Figure on field x
            audio.play_full("TTS", 68 + points[i])  # x points
            time.sleep(1)

    leds.reset()
