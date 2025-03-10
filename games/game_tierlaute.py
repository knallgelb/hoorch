#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import random
import copy
import time
import audio
import leds
import rfidreaders
import file_lib
from models import RFIDTag
from typing import List

from . import game_utils


def start():
    defined_figures = file_lib.figures_db
    defined_animals = file_lib.animal_figures_db

    animals_played = []  # store the already played animals to avoid repetition

    rfid_position = [1, 3, 5]

    audio.play_full("TTS", 4)  # Ihr spielt das Spiel Tierlaute erraten.
    leds.reset()  # reset leds

    if game_utils.check_end_tag():
        return

    audio.play_full("TTS", 5)  # Stelle deine Figur auf eines der Spielfelder

    if game_utils.check_end_tag():
        return

    audio.play_file("sounds", "waiting.mp3")  # play wait sound
    leds.rotate_one_round(1.11)

    if game_utils.check_end_tag():
        return

    players = game_utils.filter_players_on_fields(
        copy.deepcopy(rfidreaders.tags),
        rfid_position,
        defined_figures
    )

    score_players = game_utils.play_rounds(
        players=players,
        num_rounds=3,  # Beispiel: 3 Runden
        player_action=lambda p: player_action(p, rfidreaders, file_lib, rfid_position)
    )

    game_utils.announce_score(score_players=score_players)

    return score_players


def player_action(
        player: RFIDTag,
        rfidreaders,
        file_lib,
        rfid_position: List[int]
) -> bool:
    expected_value = random.choice(list(file_lib.animal_figures_db.values()))
    game_utils.announce_file(f"{expected_value.name}.mp3", "animal_sounds")

    relevant_tags = [tag for tag in rfidreaders.tags if isinstance(tag, RFIDTag)]

    for tag in relevant_tags:
        # pdb.set_trace()
        if tag.name is not None and tag.name == expected_value.name:
            if tag == expected_value:
                return True

    time.sleep(0.3)

    return False
