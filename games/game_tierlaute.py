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
from i18n import Translator
from logger_util import get_logger

from . import game_utils

logger = get_logger(__name__, "logs/game_tierlaute.log")

translator = None


def start():
    defined_figures = file_lib.get_tags_by_type("figures")

    animals_played = []  # store the already played animals to avoid repetition

    rfid_position = []

    rfidreaders.display_active_leds = False

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

    # take a synchronous snapshot from the readers, flattening will be handled by the filter function
    snapshot = list(rfidreaders.get_tags_snapshot(True) or [])
    players = game_utils.filter_players_on_fields(
        copy.deepcopy(snapshot), rfid_position, defined_figures
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
            pass  # leider falsch schon in player_action abgespielt
        return result

    if figure_count == 0:
        game_utils.announce(59)
        return None

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

    translator = Translator(locale="de")

    proc, duration = audio.play_file(
        "animal_sounds", f"{expected_value.name}.mp3", return_process=True
    )

    start_time = time.time()
    # Ensure audio_duration is numeric. audio.get_audio_length may return None;
    # coerce to float and fall back to a safe default timeout if necessary.
    try:
        audio_duration = float(
            audio.get_audio_length(
                "animal_sounds", f"{expected_value.name}.mp3"
            )
            or 0.0
        )
    except Exception:
        audio_duration = 0.0

    # If audio duration could not be determined, use a conservative fallback timeout.
    if audio_duration <= 0:
        audio_duration = 10.0

    while (time.time() - start_time) < audio_duration:
        # Prüfe RFID-Tags mittels Snapshot; ein Slot kann None, ein Tag-Objekt oder eine Liste/Tuple sein.
        snapshot = list(rfidreaders.get_tags_snapshot(True) or [])
        for slot in snapshot:
            if slot is None:
                continue
            tag_obj = None
            if isinstance(slot, (list, tuple)):
                # wähle das erste nicht-None Element im Slot
                for el in slot:
                    if el is not None:
                        tag_obj = el
                        break
            else:
                tag_obj = slot
            # Vergleiche über das rfid_tag-Feld mit dem erwarteten Tier
            if (
                tag_obj
                and getattr(tag_obj, "rfid_tag", None)
                == expected_value.rfid_tag
            ):
                proc.terminate()
                time.sleep(0.3)
                return True
        time.sleep(0.1)
    # erwarteter Wert
    game_utils.announce(26)
    audio.play_file("TTS", "267.mp3")
    audio.play_file(
        "TTS",
        translator.translate(f"standard_tags.{expected_value.name.lower()}"),
    )

    return False
