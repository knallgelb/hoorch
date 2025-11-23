#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import random
import time

import audio
import crud
import file_lib
import leds
import models
import rfidreaders
from logger_util import get_logger

from .game_utils import announce, check_end_tag, filter_players_on_fields

logger = get_logger(__name__, "logs/game_animals.log")


def start():
    defined_figures = file_lib.get_tags_by_type("figures")
    defined_animals = file_lib.get_tags_by_type("animals")
    animals_played = []
    points = []

    announce(192)  # "Wir lernen jetzt Tiernamen auf Englisch."
    leds.reset()

    if check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    announce(193)  # Hinweise für das Aufstellen der Figuren
    if check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    audio.play_file("sounds", "waiting.mp3")
    leds.rotate_one_round(1.11)

    current_tags = rfidreaders.get_tags_snapshot(True)
    # Normalize per-slot entries: if an entry is a list/tuple, keep the first element
    # This preserves the reader/LED slot alignment while allowing callers that use
    # get_tags_snapshot(True) which might return nested entries.
    players = []
    if current_tags:
        for entry in current_tags:
            if entry is None:
                players.append(None)
            elif isinstance(entry, (list, tuple)) and len(entry) > 0:
                players.append(entry[0])
            else:
                players.append(entry)

    isthefirst = True

    if check_end_tag():
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    # Lehrmodus (FRAGEZEICHEN-Figur vorhanden)
    if any(p is not None and p.name == "FRAGEZEICHEN" for p in players):
        announce(192)
        announce(195)  # "Stelle einen Tier-Spielstein auf..."

        while True:
            if check_end_tag():
                audio.kill_sounds()
                leds.switch_all_on_with_color((0, 0, 255))
                time.sleep(0.2)
                leds.reset()
                break

            figures_on_board = rfidreaders.get_tags_snapshot(True) or []
            # Normalize each slot to its primary tag object (preserve positions)
            normalized_figures = []
            for entry in figures_on_board:
                if entry is None:
                    normalized_figures.append(None)
                elif isinstance(entry, (list, tuple)) and len(entry) > 0:
                    normalized_figures.extend(entry)
                else:
                    normalized_figures.append(entry)
            figures_on_board = normalized_figures

            for i, tag_obj in enumerate(figures_on_board):
                leds_position = i + 1
                if (
                    tag_obj
                    and tag_obj.rfid_type == "animals"
                    and tag_obj.rfid_tag in defined_animals
                ):
                    leds.switch_on_with_color(leds_position, (0, 255, 0))
                    animal_file = tag_obj.name + ".mp3"
                    if not audio.file_is_playing(animal_file):
                        audio.play_file("TTS/animals_en", animal_file)
                        time.sleep(2)
                    leds.switch_on_with_color(leds_position, (0, 0, 0))
    # Spielmodus (kein FRAGEZEICHEN)
    else:
        players = filter_players_on_fields(
            rfidreaders.get_tags_snapshot(True), [], defined_figures
        )
        figure_count = sum(x is not None for x in players)

        # Log Usage
        u = models.Usage(game="animals", players=figure_count)
        crud.add_game_entry(usage=u)

        time.sleep(1)
        if figure_count == 0:
            announce(
                59
            )  # "Du hast keine Spielfigure auf das Spielfeld gestellt."
            leds.switch_all_on_with_color((0, 0, 255))
            time.sleep(0.2)
            leds.reset()
            return

        announce(5 + figure_count)  # "Es spielen x Figuren mit"
        rounds = 3
        announce(20 + rounds)  # "Wir spielen x Runden"
        points = [0] * len(players)

        for r in range(rounds):
            for i, p in enumerate(players):
                leds_position = i + 1
                if p is None:
                    continue

                leds.reset()
                leds.switch_on_with_color(
                    leds_position, (0, 255, 0)
                )  # Spieler grün

                if r == 0 and isthefirst:
                    isthefirst = False
                    if figure_count > 1:
                        announce(
                            12 + i
                        )  # "Es beginnt die Spielfigur auf Spielfeld x"
                    announce(194)
                elif figure_count == 1:
                    announce(67)
                else:
                    announce(48 + i)

                if check_end_tag():
                    leds.switch_all_on_with_color((0, 0, 255))
                    time.sleep(0.2)
                    leds.reset()
                    return

                # Tierauswahl
                if len(animals_played) == 20:
                    animals_played = animals_played[-1:]
                elif len(animals_played) == 0:
                    animals_played.append("dummy_animal")

                animal_tag = random.choice(list(defined_animals.values())).name
                while animal_tag in animals_played:
                    animal_tag = random.choice(
                        list(defined_animals.values())
                    ).name

                audio.play_file("TTS/animals_en", animal_tag + ".mp3")
                time.sleep(2)

                if check_end_tag():
                    leds.switch_all_on_with_color((0, 0, 255))
                    time.sleep(0.2)
                    leds.reset()
                    return

                while True:
                    if check_end_tag():
                        leds.switch_all_on_with_color((0, 0, 255))
                        time.sleep(0.2)
                        leds.reset()
                        return

                    if not audio.file_is_playing(animal_tag + ".mp3"):
                        audio.play_file("TTS/animals_en", animal_tag + ".mp3")
                        time.sleep(3)

                    current_snapshot = rfidreaders.get_tags_snapshot(True) or []
                    figure_on_field = None
                    if i < len(current_snapshot):
                        entry = current_snapshot[i]
                        if isinstance(entry, (list, tuple)) and len(entry) > 0:
                            figure_on_field = entry[0]
                        else:
                            figure_on_field = entry
                    if figure_on_field:
                        field_name = figure_on_field.name
                        # Bedingungen: korrekter Tierstein
                        if (
                            field_name != p.rfid_tag
                            and field_name != animals_played[-1]
                            and file_lib.check_tag_attribute(
                                [figure_on_field], field_name
                            )
                        ):
                            audio.kill_sounds()
                            if field_name == animal_tag:
                                time.sleep(0.2)
                                announce(27)  # "Richtig!"
                                audio.play_file("sounds", "winner.mp3")
                                leds.switch_on_with_color(
                                    leds_position, (255, 215, 0)
                                )  # Gold für richtig
                                time.sleep(0.3)
                                points[i] += 1
                                rfidreaders.tags[i] = None
                                break
                            else:
                                time.sleep(0.2)
                                announce(26)  # "Falsch!"
                                audio.play_file("sounds", "loser.mp3")
                                leds.switch_on_with_color(
                                    leds_position, (255, 0, 0)
                                )  # Rot für falsch
                                time.sleep(0.3)
                                rfidreaders.tags[i] = None
                                break

                animals_played.append(animal_tag)

    if not isthefirst:
        announce(80)  # "Ich verlese jetzt die Punkte"
        for i, p in enumerate(players):
            leds_position = i + 1
            if p is not None:
                leds.reset()
                leds.switch_on_with_color(
                    leds_position, (30, 144, 255)
                )  # blau für Punkteansage
                announce(74 + i)  # "Spielfigur auf Spielfeld x"
                time.sleep(0.2)
                announce(68 + points[i])  # "x Punkte"
                time.sleep(1)

    leds.switch_all_on_with_color((0, 0, 255))
    time.sleep(0.2)
    leds.reset()
