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

    # figure_count = sum(x is not None for x in players)

    # # check for figures on board, filter other tags
    # players = copy.deepcopy(rfidreaders.tags)
    #
    # for i, p in enumerate(players):
    #     if p not in defined_figures:
    #         players[i] = None
    #
    # figure_count = sum(x is not None for x in players)
    #
    # time.sleep(1)
    # if figure_count == 0:
    #     # Du hast keine Spielfigure auf das Spielfeld gestellt.
    #     audio.play_full("TTS", 59)
    #     return
    #
    # # switch on leds at player field
    # leds.switch_on_with_color(players, (100, 100, 100))
    #
    # audio.play_full("TTS", 5+figure_count)  # Es spielen x Figuren mit
    #
    # rounds = 3  # 1-5 rounds possible
    # audio.play_full("TTS", 20+rounds)  # Wir spielen 1-5 Runden
    # points = [0, 0, 0, 0, 0, 0]
    #
    # first_round = True
    # for r in range(0, rounds):
    #     # print(players)
    #     for i, p in enumerate(players):
    #         if p is not None:
    #             leds.reset()
    #             leds.switch_on_with_color(i)
    #
    #             if "ENDE" in rfidreaders.tags:
    #                 return
    #
    #             if r == 0 and first_round is True:  # first round
    #                 first_round = False
    #                 if figure_count > 1:
    #                     # Es beginnt die Spielfigur auf Spielfeld x
    #                     audio.play_full("TTS", 12+i)
    #                 # Ich spiele dir jetzt die Laute eines Tiers vor. Wenn du das Tier erkennst, tausche deine Spielfigur gegen den Tier-Spielstein.
    #                 audio.play_full("TTS", 19)
    #             elif figure_count == 1:
    #                 audio.play_full("TTS", 67)  # Du bist nochmal dran
    #             else:
    #                 # Die nächste Spielfigur steht auf Spielfeld x
    #                 audio.play_full("TTS", 48+i)
    #
    #             # 20 different animals, up to 6 players, up to 5 rounds, need to empty animals_played when 20 reached
    #             if len(animals_played) == 20:
    #                 animals_played = animals_played[-1]
    #             # very first round, add dummy animal
    #             elif len(animals_played) == 0:
    #                 animals_played.append("dummy_animal")
    #
    #             animal = random.choice(defined_animals)
    #             while animal in animals_played:
    #                 animal = random.choice(defined_animals)
    #
    #             while True:
    #                 if "ENDE" in rfidreaders.tags:
    #                     audio.kill_sounds()
    #                     return
    #
    #                 if not audio.file_is_playing(animal+".mp3"):
    #                     audio.play_file("animal_sounds", animal+".mp3")
    #
    #                 figure_on_field = copy.deepcopy(rfidreaders.tags[i])
    #
    #                 if figure_on_field is not None:
    #                     # remove single digit from the end (Hahn1)
    #                     figure_on_field = figure_on_field[:-1]
    #
    #                     if figure_on_field != p and figure_on_field != animals_played[-1] and figure_on_field in defined_animals:
    #                         audio.kill_sounds()
    #
    #                         if figure_on_field == animal:
    #                             time.sleep(0.2)
    #                             audio.play_full("TTS", 27)
    #                             print("richtig")
    #                             audio.play_file("sounds", "winner.mp3")
    #                             time.sleep(0.2)
    #                             points[i] += 1
    #                             print("Du hast schon " +
    #                                   str(points[i])+" richtige Antworten")
    #                             rfidreaders.tags[i] = None
    #                             break
    #                         else:
    #                             time.sleep(0.2)
    #                             audio.play_full("TTS", 26)
    #                             print("falsch")
    #                             audio.play_file("sounds", "loser.mp3")
    #                             time.sleep(0.2)
    #                             rfidreaders.tags[i] = None
    #                             break
    #
    #             # add the current animal to the already played list
    #             animals_played.append(animal)

    # tell the points
    # audio.play_full("TTS", 80)  # Ich verlese jetzt die Punkte
    # for i, p in enumerate(players):
    #     if p is not None:
    #         leds.reset()
    #         leds.switch_on_with_color(i)
    #         audio.play_full("TTS", 74 + i)  # Spielfigur auf Spielfeld 1,2...6
    #         time.sleep(0.2)
    #         print("Du hast " + str(points[i]) + " Antworten richtig")
    #         audio.play_full("TTS", 68 + points[i])
    #         time.sleep(1)
    #
    # leds.reset()


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
