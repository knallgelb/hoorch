#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import datetime
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import SQLModel

import admin
import audio
import crud
import database
import env_tools
import file_lib
import games
import leds
import rfidreaders
import tagwriter
from logger_util import get_logger
from models import RFIDTag, Usage
from utils import report_stats
import integrity_check

dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)

logger = get_logger(__name__, "logs/app.log")

SQLModel.metadata.create_all(database.engine)


def announce_ip_adress():
    output = None
    while True:
        output = subprocess.run(
            ["hostname", "-I"], stdout=subprocess.PIPE, check=False
        ).stdout.decode("utf-8")

        if output is None or output == "\n":
            audio.espeaker("WeiFei nicht verbunden")
            time.sleep(1.00)
        else:
            break

    ip_adress = output.split(" ", 1)
    audio.espeaker("Die eipi Adresse lautet")
    audio.espeaker(ip_adress[0])


def init():
    # Initialize game entry
    crud.add_game_entry(
        Usage(
            box_id=os.getenv("HOORCH_UID"),
            game="HOORCH",
            players=0,
            timestamp=datetime.datetime.utcnow(),
        )
    )
    logger.info("Initialisierung der Hardware")

    # Initialize RFID tags in database via CRUD
    crud.initialize_rfid_tags()

    # initialize audio
    audio.init()

    audio.play_full("TTS", 1)

    # initialize leds (macht evtl. nichts, ist nur placeholder für zukünftige Logik)
    leds.reset()  # Setzt alle LEDs aus (wird vom Server umgesetzt)

    all_tags = file_lib.load_all_tags()
    if len(all_tags.values()) < 1:
        tagwriter.write_all_sets()
        file_lib.load_all_tags()

    if integrity_check.any_missing_entries():
        audio.espeaker(
            "Unvollständige RFID Zuordnung. Fehlende Karten werden jetzt nachgezogen."
        )
        integrity_check.remap_missing_entries()

    # RFID-Reader initialisieren
    rfidreaders.init()

    rfidreaders.read_continuously = True

    if env_tools.str_to_bool(os.getenv("TEST_HARDWARE", "false")):
        announce_ip_adress()
        initial_hardware_test()


def initial_hardware_test():
    audio.espeaker("Jetzt wird die ganze Hardware getestet")

    audio.espeaker("Jetzt werden alle LEDs beleuchtet.")
    leds.rainbow_cycle(0.01)  # Diese Funktion sendet jetzt an den Server

    audio.espeaker("Wir testen jetzt die Ar ef eidi Leser.")
    for i in range(6):
        leds.switch_on_with_color(i, (255, 0, 0))
        audio.espeaker(f"Lege eine Karte auf Leser {i + 1}")
        while True:
            if rfidreaders.tags[i] is not None:
                break

    leds.reset()

    audio.espeaker(
        "Ich teste jetzt das Audio, die Aufnahme beginnt in 3 Sekunden und dauert 6 Sekunden"
    )
    time.sleep(3)
    leds.switch_all_on_with_color()

    logger.info("Aufnahme starten")
    subprocess.Popen(
        "AUDIODEV=plughw:0,0 rec -c 1 -r 44100 -b 16 --encoding signed-integer ./data/figures/test/test.aif",
        shell=True,
        stdout=None,
        stderr=None,
    )
    time.sleep(6)
    logger.info("Aufnahme beendet")
    subprocess.Popen("killall rec", shell=True, stdout=None, stderr=None)

    leds.reset()

    if Path("./data/figures/test/test.aif").exists():
        audio.espeaker("Ich spiele dir jetzt die Geschichte vor")
        leds.switch_all_on_with_color()
        audio.play_file("figures/test", "test.aif")
        time.sleep(7)
        leds.reset()
    else:
        audio.espeaker("Aufnahme hat nicht geklappt. Audio nicht gefunden")

    audio.espeaker("Test abgeschlossen.")


def main():
    logger.info("Starte Hauptschleife")
    shutdown_time = 300  # seconds until shutdown if no interaction happened
    shutdown_counter = time.time() + shutdown_time

    greet_time = time.time()

    # transfer data to Server
    report_stats.send_and_update_stats()

    while True:
        # Statt: leds.blink = True
        # => Falls dein Server Blinken unterstützt: Klasse:
        # leds.blinker()  # (implementier evtl. als toggelnden Effekt)
        pass
        # Du kannst hier auch einfach per Timer die Farbe zufällig setzen etc.
        # oder das blink-Pattern auf Server-Seite bauen und hier nur triggern.

        if greet_time < time.time():
            audio.play_full("TTS", 2)  # Welches Spiel wollt ihr spielen?
            greet_time = time.time() + 30

        logger.info(rfidreaders.tags)

        # Get all tags of type "game" from the database
        game_tags_db = file_lib.get_tags_by_type("games")

        # Match the detected tags by their rfid_tag string with those in game_tags_db
        game_tags = []
        for detected_tag in rfidreaders.tags:
            if detected_tag is None:
                continue
            rfid_tag_str = None
            if hasattr(detected_tag, "rfid_tag"):
                rfid_tag_str = detected_tag.rfid_tag
            elif isinstance(detected_tag, str):
                rfid_tag_str = detected_tag
            if rfid_tag_str and rfid_tag_str in game_tags_db:
                game_tags.append(game_tags_db[rfid_tag_str])

        if len(game_tags) > 0 and game_tags[0].name in games.games:
            logger.info(f"Game {game_tags[0].name} starten.")
            # leds.blink = False
            # => Stopp ggf. das Blinken per Server-Kommando, falls realisiert:
            # leds.blinker()  # toggelt aus
            leds.reset()
            games.games[game_tags[0].name].start()
            audio.play_full("TTS", 54)  # Das Spiel ist zu Ende
            report_stats.send_and_update_stats()
            shutdown_counter = time.time() + shutdown_time

        if "FRAGEZEICHEN" in rfidreaders.tags:
            logger.info("Hoorch Erklärung")
            # leds.blink = False
            leds.reset()
            audio.play_full("TTS", 65)  # Erklärung
            shutdown_counter = time.time() + shutdown_time

        hoerspiele_list = [
            os.path.splitext(h)[0] for h in os.listdir("./data/hoerspiele/")
        ]
        detected_hoerspiel_card = [
            i for i in hoerspiele_list if i in rfidreaders.tags
        ]

        figure_dir = "./data/figures/"
        figure_dirs = [
            name
            for name in os.listdir(figure_dir)
            if os.path.isdir(os.path.join(figure_dir, name))
        ]
        figure_with_recording = [
            k for k in figure_dirs if f"{k}.mp3" in os.listdir(figure_dir + k)
        ]
        detected_figure_with_recording = [
            j for j in figure_with_recording if j in rfidreaders.tags
        ]

        defined_figures = file_lib.get_tags_by_type("game")
        figure_without_recording = [
            i for i in defined_figures if i not in figure_with_recording
        ]
        detected_figure_without_recording = [
            m for m in figure_without_recording if m in rfidreaders.tags
        ]

        # Admin-Menü bei Erkennung von "JA" und "NEIN"
        if file_lib.check_tag_attribute(
            rfidreaders.tags, "JA", "name"
        ) and file_lib.check_tag_attribute(rfidreaders.tags, "NEIN", "name"):
            admin.main()
            shutdown_counter = time.time() + shutdown_time

        time.sleep(0.3)

    # Shutdown
    logger.info("Shutdown")
    audio.play_full("TTS", 196)
    # leds.blink = False
    leds.reset()
    # os.system("shutdown -P now")


if __name__ == "__main__":
    init()
    main()
