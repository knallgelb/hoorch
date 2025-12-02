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
import integrity_check
import leds
import rfidreaders
import tagwriter
from logger_util import get_logger
from models import RFIDTag, Usage
from utils import report_stats

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

    if integrity_check.any_missing_entries():
        audio.espeaker(
            "Unvollständige RFID Zuordnung. Fehlende Karten werden jetzt nachgezogen."
        )
        integrity_check.remap_missing_entries()

    file_lib.load_all_tags()

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
    shutdown_counter = time.monotonic() + int(
        os.getenv("SHUTDOWN_TIMER", "300")
    )

    greet_time = time.monotonic()

    # transfer data to Server
    # report_stats.send_and_update_stats()

    # Get all tags of type "game" from the database
    game_tags_db = file_lib.get_tags_by_type("games")

    while True:
        if time.monotonic() >= shutdown_counter:
            logger.info(
                "Shutdown Timer abgelaufen. System wird heruntergefahren."
            )
            audio.play_full("TTS", 196)
            leds.reset()
            os.system("sudo shutdown -P now")
            break

        if file_lib.check_tag_attribute(
            rfidreaders.tags, "JA", "name"
        ) and file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name"):
            audio.play_full("TTS", 3)
            leds.reset()
            os.system("sudo shutdown -P now")
            break

        if greet_time < time.monotonic():
            audio.play_full("TTS", 2)  # Welches Spiel wollt ihr spielen?
            greet_time = time.monotonic() + 30

        logger.info(rfidreaders.tags)

        # Match the detected tags by their rfid_tag string with those in game_tags_db
        game_tags = []
        # get_tags_snapshot(True) may return None or a list; normalize to a list
        snapshot = rfidreaders.get_tags_snapshot(True)
        if snapshot is None:
            snapshot = []
        # Iterate over the normalized snapshot
        for detected_tag in snapshot:
            if detected_tag is None:
                continue
            # detected_tag can be a list/tuple (e.g. [tag_obj, ...]) or a single object/string.
            # Normalize to the candidate element that contains the rfid_tag (usually first element).
            candidate = None
            if (
                isinstance(detected_tag, (list, tuple))
                and len(detected_tag) > 0
            ):
                candidate = detected_tag[0]
            else:
                candidate = detected_tag
            # normalize to rfid_tag string
            if isinstance(candidate, str):
                rfid_tag_str = candidate
            else:
                rfid_tag_str = getattr(candidate, "rfid_tag", None)
            if rfid_tag_str and rfid_tag_str in game_tags_db:
                game_tags.append(game_tags_db[rfid_tag_str])

        if len(game_tags) > 0 and game_tags[0].name in games.games:
            logger.info(f"Game {game_tags[0].name} starten.")
            leds.reset()
            games.games[game_tags[0].name].start()
            audio.play_full("TTS", 54)  # Das Spiel ist zu Ende
            # report_stats.send_and_update_stats()
            shutdown_counter = time.monotonic() + int(
                os.getenv("SHUTDOWN_TIMER", "300")
            )

        if file_lib.check_tag_attribute(
            rfidreaders.tags, "FRAGEZEICHEN", "name"
        ):
            logger.info("Hoorch Erklärung")
            # leds.blink = False
            leds.reset()
            audio.play_full("TTS", 65)  # Erklärung
            shutdown_counter = time.monotonic() + int(
                os.getenv("SHUTDOWN_TIMER", "300")
            )

        # Admin-Menü bei Erkennung von "JA" und "NEIN"
        if file_lib.check_tag_attribute(
            rfidreaders.tags, "JA", "name"
        ) and file_lib.check_tag_attribute(rfidreaders.tags, "NEIN", "name"):
            admin.main()
            shutdown_counter = time.monotonic() + int(
                os.getenv("SHUTDOWN_TIMER", "300")
            )

        time.sleep(0.3)


if __name__ == "__main__":
    try:
        init()
        main()
    except games.game_utils.RestartRequested:
        logger.info(
            "Restart requested: performing cleanup and exiting to allow supervisor restart"
        )

        # Best effort cleanup: stop readers, stop audio, reset LEDs.
        try:
            # Stop continuous reading loop if running
            try:
                rfidreaders.read_continuously = False
            except Exception:
                pass

            # Shutdown each reader (powers down hardware where applicable)
            try:
                # rfidreaders.readers is a list; iterate by index to call shutdown_reader
                for i in range(len(rfidreaders.readers)):
                    try:
                        rfidreaders.shutdown_reader(i)
                    except Exception:
                        # continue shutting down remaining readers
                        pass
            except Exception:
                pass

            # Kill any playing sounds
            try:
                audio.kill_sounds()
            except Exception:
                pass

            # Reset LEDs to a safe state
            try:
                leds.reset()
            except Exception:
                pass

        except Exception as e:
            logger.exception("Exception during restart cleanup: %s", e)

        # Exit process so systemd / supervisor with Restart=always will restart the service.
        import sys

        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down")
        try:
            leds.reset()
        except Exception:
            pass
        try:
            audio.kill_sounds()
        except Exception:
            pass
        raise

# small change to test update - use `sudo git config --system --add safe.directory /home/pi/hoorch` to except git updates
# Update guide: add git command to except updates
# git pull
# edit hoorch.service `sudo vim /etc/systemd/system/hoorch.service`
# add the following lines
# Restart=always
# RestartSec=2
# Restart Service `sudo systemctl restart hoorch`
