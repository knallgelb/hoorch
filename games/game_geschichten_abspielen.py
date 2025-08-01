#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import copy
import pathlib
import time

import audio
import crud
import file_lib
import leds
import models
import rfidreaders
from i18n import Translator
from logger_util import get_logger
from models import RFIDTag

from . import game_utils

logger = get_logger(__name__, "logs/game_abspielen.log")


def start():
    translator = Translator(
        locale="de"
    )  # Initialisiere Übersetzer mit deutschem Locale
    base_path = pathlib.Path("data") / "figures"
    defined_figures = file_lib.load_all_tags()
    audio.play_full("TTS", 60)  # Wir spielen die Geschichte für deine Figur ab

    leds.reset()  # reset leds

    audio.play_full("TTS", 5)  # Stelle deine Figur auf eines der Spielfelder

    audio.play_file("sounds", "waiting.mp3")  # play wait sound
    leds.rotate_one_round(0.55)

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    rfid_position = []

    players = game_utils.filter_players_on_fields(
        copy.deepcopy(rfidreaders.tags), rfid_position, defined_figures
    )

    figure_count = sum(x is not None for x in players)

    # Log Usage
    u = models.Usage(game="abspielen", players=figure_count)
    crud.add_game_entry(usage=u)

    if figure_count == 0:
        # Du hast keine Spielfigur auf das Spielfeld gestellt
        audio.play_full("TTS", 59)
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    figure_count = sum(x is not None for x in players)
    if figure_count == 0:
        # Keine deiner Spielfiguren hat eine Geschichte gespeichert.
        audio.play_full("TTS", 201)
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    # switch on leds at player field
    player_positions = [
        i + 1 for i, x in enumerate(rfidreaders.tags) if x is not None
    ]
    leds.switch_on_with_color(player_positions, (0, 255, 0))

    # TODO: x figuren haben eine geschichte gespeichert
    audio.play_full("TTS", 5 + figure_count)

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    for i, player in enumerate(players):
        leds.reset()
        player_position = i + 1
        leds.switch_on_with_color(player_position, (0, 255, 0))

        if not isinstance(player, RFIDTag):
            continue

        file_path = base_path / pathlib.Path(
            f"{player.rfid_tag}/{player.rfid_tag}.mp3"
        )
        if file_path.exists():
            audio.play_story(player)
            audio.play_file("sounds", "page_turned_next_audio.mp3")
        else:
            # Du hast noch keine Geschichte aufgenommen!
            audio.play_full("TTS", 62)
            continue

        if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
            leds.switch_all_on_with_color((0, 0, 255))
            time.sleep(0.2)
            leds.reset()
            return

    leds.switch_all_on_with_color((0, 0, 255))
    time.sleep(0.2)
    leds.reset()
    audio.play_file("sounds", translator.translate("story.finished"))
