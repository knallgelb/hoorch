#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import csv
import sys
import time
from pathlib import Path

import board
import busio
import ndef
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B
from adafruit_pn532.spi import PN532_SPI
from digitalio import DigitalInOut

import audio
import leds

# KEINE Hardware-Initialisierung auf Modulebene!
reader = None


def get_reader():
    global reader
    if reader is None:
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        reader1_pin = DigitalInOut(board.D24)
        reader = PN532_SPI(spi, reader1_pin, debug=False)
        reader.SAM_configuration()
    return reader


path = "./figure_ids.txt"
with open(path, mode="r", encoding="utf-8") as file:
    figures = file.readlines()

figure_database = []

# to write to block 1 and 2 to mifare cards+chips
mifare_block1_2 = b"\x14\x01\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1\x03\xe1"

prefix = b"\x03"
suffix = b"\xfe"

key = b"\xff\xff\xff\xff\xff\xff"


def write_single(word):
    leds.switch_on_with_color(0)
    print("Place tag on reader1. Will write this to tag: " + str(word))
    time.sleep(2)
    rdr = get_reader()
    tag_uid = rdr.read_passive_target(timeout=0.2)

    if tag_uid:
        id_readable = ""

        for counter, number in enumerate(tag_uid):
            if counter < 4:
                id_readable += str(number) + "-"
            else:
                id_readable = id_readable[:-1]
                break

        success = write_on_tag(tag_uid, word, id_readable)

        if id_readable.endswith("-"):
            id_readable = id_readable[:-1]

        if success:
            print("Successfully wrote " + str(word) + " to tag")
            print("Now writing to database")
            audio.espeaker("Schreiben erfolgreich, füge Tag zu Datenbank hinzu")

            with open("figure_db.txt", "a") as db_file:
                db_file.write(id_readable + ";" + word + "\n")
        else:
            print("Error occurred while writing, try again.")
    else:
        print("No tag on RFID reader")
        audio.espeaker(
            "Du hast keinen Tag auf das Spielfeld platziert. Tag wurde nicht beschrieben."
        )


def delete_all_sets():
    filenames = ["actions", "animals", "figures", "games", "numeric"]
    path_files = "/home/pi/hoorch/figures"

    for filename in filenames:
        path_db_file = Path(path_files) / Path(f"{filename}_db.txt")
        if path_db_file.exists():
            print(f"deleted {path_db_file}")
            path_db_file.unlink()


def write_all_sets():
    leds.reset()  # Reset LEDs
    leds.switch_on_with_color(0)

    filenames = ["actions", "animals", "figures", "games", "numeric"]
    path_files = "/home/pi/hoorch/figures"

    for filename in filenames:
        input_filename = f"{filename}.txt"
        output_filename = f"{filename}_db.txt"
        path_db_file = Path(path_files) / Path(f"{filename}_db.txt")
        print(path_db_file)
        print(path_db_file.exists())
        if path_db_file.exists():
            continue
        write_set_from_file(
            input_file=input_filename, output_file=output_filename, path=path_files
        )


def write_set_from_file(input_file: str, output_file: str, path: str) -> None:
    audio.espeaker(f"Set {input_file}")

    full_path_input = Path(path) / Path(input_file)
    full_path_output = Path(path) / Path(output_file)

    figure_list = []

    fieldnames = ["RFID_TAG", "NAME"]

    with full_path_input.open("r") as input_file_handle:
        for line in input_file_handle:
            figure_list.append(line.strip())

    with full_path_output.open("w") as output_file_handle:
        csv_writer = csv.DictWriter(
            output_file_handle, fieldnames=fieldnames, delimiter=";"
        )
        csv_writer.writeheader()

        rdr = get_reader()
        for figure in figure_list:
            audio.espeaker(f"Nächste Figur: {figure}")
            while True:
                tag_uid = rdr.read_passive_target(timeout=1.0)

                if tag_uid:
                    tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])
                    csv_writer.writerow({"RFID_TAG": tag_uid_readable, "NAME": figure})
                    time.sleep(1.5)
                    break

def write_missing_entries_for_category(category, missing_names, path="figures"):
    """
    Für fehlende Einträge in einer Kategorie werden diese in die passende DB geschrieben.
    category: z.B. 'actions', 'animals', 'figures', 'games', 'numeric'
    missing_names: Iterable der Strings (Einträge in txt-Datei, noch nicht in _db.txt)
    """
    # Nicer Outputfile bestimmen
    output_filename = f"{category}_db.txt"
    full_path_output = Path(path) / Path(output_filename)

    # Prüfe, ob Datei existiert, sonst lege sie mit Header neu an
    if not full_path_output.exists():
        with full_path_output.open("w", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["RFID_TAG", "NAME"])  # immer diese beiden Spalten für alle bis auf numeric

    # Fieldnames & CSV
    fieldnames = ["RFID_TAG", "NAME"]
    if category == "numeric":
        fieldnames = ["RFID_TAG", "NUMBER"]

    # Öffne im "a" Append-modus, damit nichts verloren geht!
    with full_path_output.open("a", encoding="utf-8") as f:
        csv_writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        rdr = get_reader()
        audio.espeaker(f"{category}")
        for name in missing_names:
            audio.espeaker(f"{name}")
            print(f"Bitte halte Tag für '{category}': {name} auf den Leser!")

            tag_uid = None
            while not tag_uid:
                tag_uid = rdr.read_passive_target(timeout=1.0)

            tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])
            if category == "numeric":
                csv_writer.writerow({"RFID_TAG": tag_uid_readable, "NUMBER": name})
            else:
                csv_writer.writerow({"RFID_TAG": tag_uid_readable, "NAME": name})
            time.sleep(1.5)

    audio.espeaker(f"Alle fehlenden Tags für {category} fertig!")

def write_set():
    audio.espeaker(
        "Wir beschreiben das gesamte Spieleset. Stelle die Figuren bei Aufruf auf Spielfeld 1"
    )
    leds.reset()  # Reset LEDs
    leds.switch_on_with_color(0)

    rdr = get_reader()
    for figure in figures:
        figure = figure.strip()

        if figure == "+":
            audio.espeaker("Nächster Abschnitt")
            figure_database.append(["", ""])
            continue
        else:
            success = False
            audio.espeaker("Nächste Figur:")
            audio.espeaker(figure)

            while not success:
                tag_uid = None
                audio.espeaker("Figur stehen lassen")

                while not tag_uid:
                    tag_uid = rdr.read_passive_target(timeout=1.0)

                id_readable = ""

                for counter, number in enumerate(tag_uid):
                    if counter < 4:
                        id_readable += str(number) + "-"
                    else:
                        id_readable = id_readable[:-1]
                        break

                success = write_on_tag(tag_uid, figure, id_readable)

            if id_readable.endswith("-"):
                id_readable = id_readable[:-1]

            figure_database.append([id_readable, figure])
            print("Added figure to figure database")

    leds.reset()
    audio.espeaker("Ende der Datei erreicht, schreibe die Datenbank")

    with open("figure_db.txt", "w") as db_file:
        for pair in figure_database:
            db_file.write(str(pair[0]) + ";" + str(pair[1]) + "\n")


def write_on_tag(tag_uid, word, id_readable):
    record = ndef.TextRecord(word, "en")
    payload = b"".join(ndef.message_encoder([record]))
    length_ndef_msg = bytearray([len(payload)])

    full_payload = prefix + length_ndef_msg + payload + suffix

    data = bytearray(32)
    data[0 : len(full_payload)] = full_payload

    verify_data = bytearray(0)
    rdr = get_reader()

    try:
        # MIFARE 1K Layout (Chip + Karte)
        if id_readable.endswith("-"):
            id_readable = id_readable[:-1]

            data_mifare = mifare_block1_2 + data

            chunk_size = 16
            send = [
                data_mifare[i : i + chunk_size]
                for i in range(0, len(data_mifare), chunk_size)
            ]

            for i, s in enumerate(send):
                x = i + 1
                if x > 2:
                    x = x + 1

                print("Authenticating block " + str(x))
                authenticated = rdr.mifare_classic_authenticate_block(
                    tag_uid, x, MIFARE_CMD_AUTH_B, key
                )
                if not authenticated:
                    print("Authentication failed!")

                rdr.mifare_classic_write_block(x, s)

                if x > 3:
                    verify_data.extend(rdr.mifare_classic_read_block(x))
        # NTAG2 Tags
        else:
            chunk_size = 4
            send = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

            for i, s in enumerate(send):
                rdr.ntag2xx_write_block(4 + i, s)

            time.sleep(0.5)

            for i in range(4, 12):
                verify_data.extend(rdr.ntag2xx_read_block(i))
    except TypeError:
        print(
            "Error while reading RFID-tag content. Tag was probably removed before reading was completed."
        )
        audio.play_full("TTS", 199)

    return verify_data == data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        write_single(sys.argv[1])
    else:
        write_all_sets()
