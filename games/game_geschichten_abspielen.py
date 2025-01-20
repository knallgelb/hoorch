#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import os
import copy
import subprocess
import time
import audio
import rfidreaders
import leds
import file_lib
import pathlib
import pdb
from . import game_utils


def start():
    base_path = pathlib.Path("data") / "figures"
    defined_figures = file_lib.all_tags
    audio.play_full("TTS", 60)  # Wir spielen die Geschichte für deine Figur ab

    leds.reset()  # reset leds

    audio.play_full("TTS", 5)  # Stelle deine Figur auf eines der Spielfelder

    audio.play_file("sounds", "waiting.mp3")  # play wait sound
    leds.rotate_one_round(1.11)

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        return

    rfid_position = []

    players = game_utils.filter_players_on_fields(
        copy.deepcopy(rfidreaders.tags),
        rfid_position,
        defined_figures
    )

    figure_count = sum(x is not None for x in players)
    if figure_count == 0:
        # Du hast keine Spielfigur auf das Spielfeld gestellt
        audio.play_full("TTS", 59)
        return

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        return

    # remove figures without a recorded story from list
    for i, figure_id in enumerate(players):
        if figure_id is not None:
            file_path = base_path / pathlib.Path(f"{figure_id.rfid_tag}/{figure_id.rfid_tag}.mp3")
            if file_path.exists():
                continue
            players[i] = None

    figure_count = sum(x is not None for x in players)
    if figure_count == 0:
        # Keine deiner Spielfiguren hat eine Geschichte gespeichert.
        audio.play_full("TTS", 201)
        return

    # switch on leds at player field
    leds.switch_on_with_color(players, (100, 100, 100))

    # TODO: x figuren haben eine geschichte gespeichert
    audio.play_full("TTS", 5 + figure_count)

    if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
        return

    first_round = True
    for i, figure_id in enumerate(players):
        leds.reset()
        if figure_id is not None:
            leds.switch_on_with_color(i, (0, 255, 0))

            if first_round:  # at start
                if figure_count > 1:
                    # Es beginnt die Spielfigur auf Spielfeld x
                    audio.play_full("TTS", 12 + i)
                first_round = False
                # Ich Spiele dir jetzt deine Geschichte vor, wenn du stoppen willst nimm deine Spielfigur vom Spielfeld
                audio.play_full("TTS", 61)
            else:
                # Die nächste Spielfigur steht auf Spielfeld x
                audio.play_full("TTS", 47 + i)

            if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
                return

            # when figure folder exists and contains i.e. roboter.mp3
            # if figure_id in recordings_list and figure_id+'.mp3' in os.listdir(figure_dir):
            file_path = base_path / pathlib.Path(f"{figure_id.rfid_tag}/{figure_id.rfid_tag}.mp3")
            if file_path.exists():
                # play story
                audio.play_story(figure_id)
                # waitingtime = time.time() + float(subprocess.run(
                #     ['soxi', '-D', './data/figures/' + figure_id + '/' + figure_id + '.mp3'], stdout=subprocess.PIPE,
                #     check=False).stdout.decode('utf-8'))
                # print(waitingtime)
            else:
                # Du hast noch keine Geschichte aufgenommen!
                audio.play_full("TTS", 62)
                continue

            # while True:
            #     if rfidreaders.tags[i] != figure_id or waitingtime < time.time() or "ENDE" in rfidreaders.tags:
            #         audio.kill_sounds()
            #         break

            if file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
                return