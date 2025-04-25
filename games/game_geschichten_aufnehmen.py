#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import os
import copy
import subprocess
import time
import datetime
import audio
import rfidreaders
import leds
import file_lib
import pathlib
import models
import crud

from logger_util import get_logger

logger = get_logger(__name__, "logs/game_aufnehmen.log")

from . import game_utils

def init_recording(mp3_path: pathlib.Path):
    if not mp3_path.is_dir():
        mp3_path.mkdir()

def start():
    base_path = pathlib.Path("data") / "figures"

    init_recording(base_path)

    defined_figures = file_lib.figures_db

    # Wir nehmen eine Geschichte für deine Figur auf
    audio.play_full("TTS", 55)
    print("Wir nehmen eine Geschichte für deine Figur auf")

    leds.reset()  # reset leds

    rfid_position = []

    audio.play_full("TTS", 5)  # Stelle deine Figur auf eines der Spielfelder

    audio.play_file("sounds", "waiting.mp3")  # play wait sound
    leds.rotate_one_round(1.11)

    players = game_utils.filter_players_on_fields(
        copy.deepcopy(rfidreaders.tags),
        rfid_position,
        defined_figures
    )

    figure_count = sum(x is not None for x in players)

    # Log Usage
    u = models.Usage(game="aufnehmen", players=figure_count)
    crud.add_game_entry(usage=u)

    if figure_count == 0:
        # "Du hast keine Spielfigure auf das Spielfeld gestellt."
        game_utils.announce(59)
        return

    time.sleep(0.5)

    # switch on leds at player field
    leds.switch_on_with_color(players, (100, 100, 100))

    game_utils.announce(5 + figure_count)  # Es spielen x Figuren mit

    if game_utils.check_end_tag():
        return

    first_round = True
    for i, figure_id in enumerate(players):
        leds.reset()
        if figure_id is not None:
            leds.switch_on_with_color(i, (0, 255, 0))

            new_recording = False
            error_recording = False

            if figure_count > 1:
                if first_round:  # at start
                    # Es beginnt die Spielfigur auf Spielfeld x
                    game_utils.announce(12 + i)
                    first_round = False
                else:
                    # Die nächste Spielfigur steht auf Spielfeld x
                    game_utils.announce(47 + i)

            if game_utils.check_end_tag():
                return

            recordings_list = list(base_path.iterdir())
            figure_dir = base_path / figure_id.rfid_tag

            if not figure_dir.is_dir():
                figure_dir.mkdir()

            # when figure folder and audio file (i.e. roboter.mp3) exist
            if figure_id in recordings_list and figure_id.rfid_tag + '.mp3' in os.listdir(figure_dir):

                # Diese Figur hat schon eine Geschichte gespeichert...
                game_utils.announce(84)
                # files = os.listdir(figure_dir)
                audio.play_story(figure_id)

                # wait 60 seconds longer than recording otherwise continue to next figure - prevent program from freezing
                waitingtime = time.time() + float(subprocess.run(
                    ['soxi', '-D', figure_dir + '/' + figure_id + '.mp3'], stdout=subprocess.PIPE,
                    check=False).stdout.decode('utf-8')) + 60

                while waitingtime > time.time():
                    if file_lib.check_tag_attribute(rfidreaders.tags, "JA", "name"):
                        # if rfidreaders.tags[i] == "JA":
                        audio.kill_sounds()

                        # Stelle deine Figur wieder auf dein Spielfeld.
                        game_utils.announce(200)

                        # rename old story
                        archived_file = figure_id + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")
                        os.rename(figure_dir + "/" + figure_id + ".mp3",
                                  figure_dir + "/" + archived_file + ".mp3")

                        # Die Aufnahme beginnt in 3 Sekunden! Wenn du fertig bist, nimm deine Spielfigur vom Spielfeld"
                        game_utils.announce(56)
                        game_utils.announce(66)  # 3 2 1 Los

                        # change color to red for recording
                        leds.switch_on_with_color(i, (255, 0, 0))

                        # most recent story has only figure_id as filename, record_story(figure_id)
                        audio.record_story(figure_id)

                        record_timer = time.time() + 600  # 600 sekunden(60*10min) counter until stop
                        while True:
                            if rfidreaders.tags[
                                i] is None or record_timer < time.time() or file_lib.check_tag_attribute(
                                rfidreaders.tags, "ENDE", "name"):
                                error_recording = audio.stop_recording(
                                    figure_id)
                                # change led color to green
                                leds.switch_on_with_color(i, (0, 255, 0))

                                # Aufnahme ist zu Ende
                                game_utils.announce(57)
                                new_recording = True
                                break
                        break

                    # elif rfidreaders.tags[i] == "NEIN" or "ENDE" in rfidreaders.tags:
                    elif (file_lib.check_tag_attribute(rfidreaders.tags, "NEIN", "name")
                          or file_lib.check_tag_attribute(
                                rfidreaders.tags, "ENDE", "name")):
                        audio.kill_sounds()
                        # new_recording = False
                        break

            else:
                print("no story recorded yet")

                # Die Aufnahme beginnt in 3 Sekunden! Wenn du fertig bist, nimm deine Spielfigur vom Spielfeld"
                game_utils.announce(56)
                # leds.rotate_one_round(0.4)
                game_utils.announce(66)  # 3 2 1 Los
                # time.sleep(1)
                leds.switch_on_with_color(i, (255, 0, 0))

                # most recent story has only figure_id as filename, record_story(figure_id)
                audio.record_story(figure_id)

                record_timer = time.time() + 600  # 600 sec (=10min) counter until stop
                while True:
                    if rfidreaders.tags[i] is None or record_timer < time.time() or file_lib.check_tag_attribute(
                            rfidreaders.tags, "NEIN", "name"):
                        error_recording = audio.stop_recording(figure_id)
                        game_utils.announce(57)  # Aufnahme ist zu Ende"
                        new_recording = True
                        break

            if new_recording:

                if error_recording:
                    print("error while recording!")
                    # Bei der Aufname ist ein Fehler passiert. Lass die Figur beim nächsten mal länger stehen
                    game_utils.announce(197)
                    continue

                # play audio after recording
                # Ich spiele dir jetzt die Aufnahme vor. Verwende zum Speichern den Ja-Spielstein. Zum Verwerfen den Nein-Spielstein
                game_utils.announce(81)

                audio.play_story(figure_id)

                # wait 60 seconds longer than recording otherwise continue to next figure - prevent program from freezing
                waitingtime = time.time() + float(subprocess.run(
                    ['soxi', '-D', str(figure_dir) + '/' + figure_id.rfid_tag + '.mp3'], stdout=subprocess.PIPE,
                    check=False).stdout.decode('utf-8')) + 60

                while waitingtime > time.time():
                    # if rfidreaders.tags[i] == "JA":
                    if file_lib.check_tag_attribute(
                            rfidreaders.tags, "JA", "name"):
                        audio.kill_sounds()
                        audio.play_full("TTS", 82)  # Geschichte gespeichert
                        break

                    elif file_lib.check_tag_attribute(
                            rfidreaders.tags, "NEIN", "name") or file_lib.check_tag_attribute(
                        rfidreaders.tags, "ENDE", "name"):
                        # elif rfidreaders.tags[i] == "NEIN" or "ENDE" in rfidreaders.tags:
                        audio.kill_sounds()

                        audio_file = figure_dir / figure_id.rfid_tag

                        if audio_file.exists():
                            audio_file.unlink()

                        # Geschichte nicht gespeichert
                        game_utils.announce(83)
                        break
