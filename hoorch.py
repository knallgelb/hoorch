#!/usr/bin/env python3
# -*- coding: UTF8 -*-

# require: see installer.sh
import os
import time
import subprocess
import audio
import file_lib
import rfidreaders
import leds
import games
import admin
import tagwriter
from pathlib import Path
import env_tools
from logger_util import get_logger

from models import RFIDTag
from games import game_utils

from dotenv import load_dotenv
dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)


logger = get_logger(__name__, "logs/app.log")


def announce_ip_adress():
    output = None
    while True:
        output = subprocess.run(
            ['hostname', '-I'], stdout=subprocess.PIPE, check=False).stdout.decode('utf-8')

        if output is None or output == '\n':
            audio.espeaker("WeiFei nicht verbunden")
            time.sleep(1.00)
            # if connected to router but internet on router is down, we need to open
            # comitup-cli and and delete connection with d and establish a new one

        else:
            break

    ip_adress = output.split(" ", 1)
    audio.espeaker("Die eipi Adresse lautet")
    audio.espeaker(ip_adress[0])


def init():
    logger.info("Initialisierung der Hardware")

    # initialize audio
    audio.init()

    audio.play_full("TTS", 1)

    # initialize leds
    leds.init()

    if len(file_lib.all_tags.values()) < 1:
        tagwriter.write_all_sets()
        file_lib.read_database_files()

    # RFID-Reader initialisieren
    rfidreaders.init()

    rfidreaders.read_continuously = True

    if env_tools.str_to_bool(os.getenv("TEST_HARDWARE", "false")):
        announce_ip_adress()
        initial_hardware_test()


def initial_hardware_test():
    # test run to check hardware on first hoorch start - will test leds, readers, speakers, microphone
    # leds.blink = False

    audio.espeaker("Jetzt wird die ganze Hardware getestet")

    audio.espeaker("Jetzt werden alle LEDs beleuchtet.")
    ## leds.rainbow_cycle(0.001)
    leds.rainbow_cycle(0.01)

    audio.espeaker("Wir testen jetzt die Ar ef eidi Leser.")
    for i in range(6):
        leds.switch_on_with_color(i, (255, 0, 0))
        audio.espeaker(f"Lege eine Karte auf Leser {i + 1}")
        while True:
            if rfidreaders.tags[i] is not None:
                break

    leds.reset()

    audio.espeaker(
        "Ich teste jetzt das Audio, die Aufnahme beginnt in 3 Sekunden und dauert 6 Sekunden")
    time.sleep(3)
    leds.switch_all_on_with_color()

    logger.info("Aufnahme starten")
    subprocess.Popen(
        "AUDIODEV=plughw:0,0 rec -c 1 -r 44100 -b 16 --encoding signed-integer ./data/figures/test/test.aif",
        shell=True, stdout=None, stderr=None)
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

    while True:
        leds.blink = True

        if greet_time < time.time():
            audio.play_full("TTS", 2)  # Welches Spiel wollt ihr spielen?
            greet_time = time.time() + 30

        # debug Message
        logger.info(rfidreaders.tags)

        # schauen, ob die Länge der Tags größer 0 ist
        # Extract der RFID-GAME-Tags
        game_tags = [tag for tag in rfidreaders.tags if isinstance(tag, RFIDTag) and tag.rfid_type == 'game']

        if len(game_tags) > 0 and games.games[game_tags[0].name]:
            logger.info(f"Game {game_tags[0].name} starten.")
            leds.blink = False
            games.games[game_tags[0].name].start()
            audio.play_full("TTS", 54)  # Das Spiel ist zu Ende
            shutdown_counter = time.time() + shutdown_time

        # Erklärung
        if "FRAGEZEICHEN" in rfidreaders.tags:
            logger.info("Hoorch Erklärung")
            leds.blink = False
            audio.play_full("TTS", 65)  # Erklärung
            shutdown_counter = time.time() + shutdown_time

        # Hörspiele
        hoerspiele_list = [os.path.splitext(h)[0] for h in os.listdir("./data/hoerspiele/")]
        detected_hoerspiel_card = [i for i in hoerspiele_list if i in rfidreaders.tags]

        figure_dir = "./data/figures/"
        figure_dirs = [name for name in os.listdir(figure_dir) if os.path.isdir(os.path.join(figure_dir, name))]
        figure_with_recording = [k for k in figure_dirs if f"{k}.mp3" in os.listdir(figure_dir + k)]
        detected_figure_with_recording = [j for j in figure_with_recording if j in rfidreaders.tags]

        defined_figures = file_lib.gamer_figures_db
        figure_without_recording = [i for i in defined_figures if i not in figure_with_recording]
        detected_figure_without_recording = [m for m in figure_without_recording if m in rfidreaders.tags]

        # Admin-Menü bei Erkennung von "JA" und "NEIN"
        if file_lib.check_tag_attribute(rfidreaders.tags, "JA", "name") and file_lib.check_tag_attribute(
                rfidreaders.tags, "NEIN", "name"):
            admin.main()
            shutdown_counter = time.time() + shutdown_time

        time.sleep(0.3)

    # Shutdown
    logger.info("Shutdown")
    audio.play_full("TTS", 196)
    leds.blink = False
    leds.led_value = [1, 1, 1, 1, 1, 1]
    # os.system("shutdown -P now")


if __name__ == "__main__":
    init()
    main()
