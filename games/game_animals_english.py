#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import os
import time
import random
import copy
import audio
import rfidreaders
import leds
import file_lib
import models
import crud

from .game_utils import (
    check_end_tag,
    announce,
    filter_players_on_fields
)

from logger_util import get_logger

logger = get_logger(__name__, "logs/game_animals.log")


def start():
    defined_figures = file_lib.figures_db
    defined_animals = file_lib.animal_figures_db
    animals_played = []

    announce(192)  # "Wir lernen jetzt Tiernamen auf Englisch."
    leds.reset()

    if check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255)); time.sleep(0.2); leds.reset()
        return

    announce(193)  # Hinweise für das Aufstellen der Figuren
    if check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255)); time.sleep(0.2); leds.reset()
        return

    audio.play_file("sounds", "waiting.mp3")
    leds.rotate_one_round(1.11)

    players = copy.deepcopy(rfidreaders.tags)

    isthefirst = True

    if check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255)); time.sleep(0.2); leds.reset()
        return

    # Lehrmodus (FRAGEZEICHEN-Figur vorhanden)
    if any(p is not None and p.name == "FRAGEZEICHEN" for p in players):
        announce(192)
        announce(195)  # "Stelle einen Tier-Spielstein auf..."

        while True:
            if check_end_tag():
                audio.kill_sounds()
                leds.switch_all_on_with_color((0, 0, 255)); time.sleep(0.2); leds.reset()
                break

            figures_on_board = copy.deepcopy(rfidreaders.tags)

            for i, tag_obj in enumerate(figures_on_board):
                if tag_obj and tag_obj.rfid_tag in defined_animals:
                    leds.switch_on_with_color(i, (0, 255, 0))
                    animal_file = tag_obj.name + ".mp3"
                    if not audio.file_is_playing(animal_file):
                        audio.play_file("TTS/animals_en", animal_file)
                        time.sleep(2)
                    leds.switch_on_with_color(i, (0, 0, 0))
    # Spielmodus (kein FRAGEZEICHEN)
    else:
        players = filter_players_on_fields(copy.deepcopy(rfidreaders.tags), [], defined_figures)
        figure_count = sum(x is not None for x in players)

        # Log Usage
        u = models.Usage(game="animals", players=figure_count)
        crud.add_game_entry(usage=u)

        time.sleep(1)
        if figure_count == 0:
            announce(59)  # "Du hast keine Spielfigure auf das Spielfeld gestellt."
            leds.switch_all_on_with_color((0,0,255)); time.sleep(0.2); leds.reset()
            return

        announce(5 + figure_count)  # "Es spielen x Figuren mit"
        rounds = 3
        announce(20 + rounds)  # "Wir spielen x Runden"
        points = [0] * len(players)

        for r in range(rounds):
            for i, p in enumerate(players):
                if p is None:
                    continue

                leds.reset()
                leds.switch_on_with_color(i, (0, 255, 0))  # Spieler grün

                if r == 0 and isthefirst:
                    isthefirst = False
                    if figure_count > 1:
                        announce(12 + i)  # "Es beginnt die Spielfigur auf Spielfeld x"
                    announce(194)
                elif figure_count == 1:
                    announce(67)
                else:
                    announce(48 + i)

                if check_end_tag():
                    leds.switch_all_on_with_color((0, 0, 255)); time.sleep(0.2); leds.reset()
                    return

                # Tierauswahl
                if len(animals_played) == 20:
                    animals_played = animals_played[-1:]
                elif len(animals_played) == 0:
                    animals_played.append("dummy_animal")

                animal_tag = random.choice(list(defined_animals.values())).name
                while animal_tag in animals_played:
                    animal_tag = random.choice(list(defined_animals.values())).name

                audio.play_file("TTS/animals_en", animal_tag + ".mp3")
                time.sleep(2)

                if check_end_tag():
                    leds.switch_all_on_with_color((0, 0, 255)); time.sleep(0.2); leds.reset()
                    return

                while True:
                    if check_end_tag():
                        leds.switch_all_on_with_color((0, 0, 255)); time.sleep(0.2); leds.reset()
                        return

                    if not audio.file_is_playing(animal_tag + ".mp3"):
                        audio.play_file("TTS/animals_en", animal_tag + ".mp3")
                        time.sleep(3)

                    figure_on_field = copy.deepcopy(rfidreaders.tags[i])
                    if figure_on_field:
                        field_name = figure_on_field.name
                        # Bedingungen: korrekter Tierstein
                        if (field_name != p.rfid_tag and
                                field_name != animals_played[-1] and
                                file_lib.check_tag_attribute([figure_on_field], field_name)):
                            audio.kill_sounds()
                            if field_name == animal_tag:
                                time.sleep(0.2)
                                announce(27)  # "Richtig!"
                                audio.play_file("sounds", "winner.mp3")
                                leds.switch_on_with_color(i, (255, 215, 0))  # Gold für richtig
                                time.sleep(0.3)
                                points[i] += 1
                                rfidreaders.tags[i] = None
                                break
                            else:
                                time.sleep(0.2)
                                announce(26)  # "Falsch!"
                                audio.play_file("sounds", "loser.mp3")
                                leds.switch_on_with_color(i, (255, 0, 0))   # Rot für falsch
                                time.sleep(0.3)
                                rfidreaders.tags[i] = None
                                break

                animals_played.append(animal_tag)

    if not isthefirst:
        announce(80)  # "Ich verlese jetzt die Punkte"
        for i, p in enumerate(players):
            if p is not None:
                leds.reset()
                leds.switch_on_with_color(i, (30, 144, 255)) # blau für Punkteansage
                announce(74 + i)  # "Spielfigur auf Spielfeld x"
                time.sleep(0.2)
                announce(68 + points[i])  # "x Punkte"
                time.sleep(1)

    leds.switch_all_on_with_color((0,0,255))
    time.sleep(0.2)
    leds.reset()
