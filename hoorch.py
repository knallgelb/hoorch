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

from models import RFIDTag

import logging

# Erstelle das Verzeichnis 'logs', falls es nicht existiert
if not os.path.exists('logs'):
    os.makedirs('logs')

# Logger erstellen
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Sie können hier die Log-Level einstellen

# Konsole-Handler erstellen und Level setzen
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Datei-Handler erstellen und Level setzen
file_handler = logging.FileHandler('logs/app.log')
file_handler.setLevel(logging.DEBUG)

# Formatter erstellen und zu den Handlern hinzufügen
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Handler zum Logger hinzufügen
logger.addHandler(console_handler)
logger.addHandler(file_handler)


def init():
    logger.info("Initialisierung der Hardware")

    # initialize audio
    audio.init()

    audio.play_full("TTS", 1)

    # initialize leds
    leds.init()

    # RFID-Reader initialisieren
    rfidreaders.init()

    # initialize figure_db if no tags defined for this hoorch set
    if not Path("figures/figures_db.txt").exists():
        # tell the ip adress
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

        initial_hardware_test()

        rfidreaders.read_continuously = False
        time.sleep(1)
        tagwriter.write_all_sets()
        rfidreaders.read_continuously = True
        # rfidreaders.continuous_read()


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

        # if detected_hoerspiel_card:
        #     logger.info("Hörspiele")
        #     leds.blink = False
        #     game_hoerspiele.start("hoerspiele/", detected_hoerspiel_card[0])
        #     shutdown_counter = time.time() + shutdown_time

        figure_dir = "./data/figures/"
        figure_dirs = [name for name in os.listdir(figure_dir) if os.path.isdir(os.path.join(figure_dir, name))]
        figure_with_recording = [k for k in figure_dirs if f"{k}.mp3" in os.listdir(figure_dir + k)]
        detected_figure_with_recording = [j for j in figure_with_recording if j in rfidreaders.tags]

        defined_figures = file_lib.gamer_figures_db
        figure_without_recording = [i for i in defined_figures if i not in figure_with_recording]
        detected_figure_without_recording = [m for m in figure_without_recording if m in rfidreaders.tags]

        # Priorität für Figuren mit Aufnahmen
        # if detected_figure_with_recording:
        #     logger.info("Geschichte abspielen - aus Hauptmenü")
        #     leds.blink = False
        #     game_hoerspiele.start(f"figures/{detected_figure_with_recording[0]}", detected_figure_with_recording[0])
        #     shutdown_counter = time.time() + shutdown_time
        #
        # if detected_figure_without_recording:
        #     logger.info("Geschichte aufnehmen - aus Hauptmenü")
        #     leds.blink = False
        #     game_aufnehmen.start(detected_figure_without_recording[0])
        #     shutdown_counter = time.time() + shutdown_time

        # Admin-Menü bei Erkennung von "JA" und "NEIN"
        if "JA" in rfidreaders.tags and "NEIN" in rfidreaders.tags:
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
