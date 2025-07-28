#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import copy
import random
import time
from typing import List

import audio
import crud
import file_lib
import leds
import models
import rfidreaders
from logger_util import get_logger

from . import game_utils

logger = get_logger(__name__, "logs/game_tierlaute.log")


def start():
    defined_figures = file_lib.get_tags_by_type("figures")
    defined_animals = file_lib.get_tags_by_type("animals")

    animals_played = []  # store the already played animals to avoid repetition

    rfid_position = []

    audio.play_full("TTS", 4)  # Ihr spielt das Spiel Tierlaute erraten.
    leds.reset()  # reset leds

    if game_utils.check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.3)
        leds.reset()
        return

    audio.play_full("TTS", 5)  # Stelle deine Figur auf eines der Spielfelder

    if game_utils.check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.3)
        leds.reset()
        return

    audio.play_file("sounds", "waiting.mp3")  # play wait sound
    leds.rotate_one_round(1.11)

    if game_utils.check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.3)
        leds.reset()
        return

    players = game_utils.filter_players_on_fields(
        copy.deepcopy(rfidreaders.tags), rfid_position, defined_figures
    )

    figure_count = sum(p is not None for p in players)

    # Log Usage
    u = models.Usage(game="tierlaute", players=figure_count)
    crud.add_game_entry(usage=u)

    def action_with_led(player):
        idx = players.index(player) + 1
        leds.switch_on_with_color(idx, (0, 255, 0))  # grün für rate-Spielfigur
        result = player_action(
            player, rfidreaders, file_lib, rfid_position, animals_played
        )
        leds.switch_on_with_color(idx, (0, 0, 0))
        audio.kill_sounds()
        time.sleep(1)
        if result:
            game_utils.announce(27)
        else:
            game_utils.announce(26)
        return result

    score_players = game_utils.play_rounds(
        players=players,
        num_rounds=3,  # Beispiel: 3 Runden
        player_action=action_with_led,
    )

    game_utils.announce_score(score_players=score_players)

    leds.switch_all_on_with_color((0, 0, 255))
    time.sleep(0.3)
    leds.reset()
    return score_players


def player_action(
    player: models.RFIDTag,
    rfidreaders,
    file_lib,
    rfid_position: List[int],
    animals_played: list,
) -> bool:
    available_animals = [
        animal
        for animal in file_lib.get_tags_by_type("animals").values()
        if animal not in animals_played
    ]
    if not available_animals:
        logger.warning("No more unused animals left!")
        audio.espeaker("Es sind keine Tiere mehr übrig!")
        return False
    expected_value = random.choice(available_animals)
    animals_played.append(expected_value)

    proc, duration = audio.play_file(
        "animal_sounds", f"{expected_value.name}.mp3", return_process=True
    )

    start_time = time.time()
    audio_duration = audio.get_audio_length(
        "animal_sounds", f"{expected_value.name}.mp3"
    )

    while (time.time() - start_time) < audio_duration:
        # Prüfe RFID-Tags
        for tag in rfidreaders.tags:
            if expected_value in rfidreaders.tags:
                proc.terminate()
                time.sleep(0.3)
                return True
        time.sleep(0.1)

    return False
