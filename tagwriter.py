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

from sqlmodel import Session, select
from database import engine, get_db
from models import RFIDTag

import audio
import leds

reader = None


def get_reader():
    global reader
    if reader is None:
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        reader1_pin = DigitalInOut(board.D24)
        reader = PN532_SPI(spi, reader1_pin, debug=False)
        reader.SAM_configuration()
    return reader


def update_rfid_in_db(rfid_tag: str, name: str, rfid_type: str):
    """
    Update the database entry for a matching name and rfid_type with the given rfid_tag.
    """
    with Session(engine) as session:
        tag = session.exec(
            select(RFIDTag).where(RFIDTag.name == name, RFIDTag.rfid_type == rfid_type)
        ).first()
        if tag:
            tag.rfid_tag = rfid_tag
            session.add(tag)
            session.commit()
            session.refresh(tag)
            return True
        else:
            return False


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

    figure_list = []

    with full_path_input.open("r") as input_file_handle:
        for line in input_file_handle:
            figure_list.append(line.strip())

    rdr = get_reader()
    audio.espeaker(f"Starte das Schreiben für {input_file}")
    for figure in figure_list:
        audio.espeaker(f"Nächste Figur: {figure}")
        while True:
            tag_uid = rdr.read_passive_target(timeout=1.0)

            if tag_uid:
                tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])
                # Update DB instead of writing CSV
                category = Path(input_file).stem
                success = update_rfid_in_db(tag_uid_readable, figure, category)
                time.sleep(1)
                break

def write_missing_entries_for_category(category, missing_names_with_ids, path="figures"):
    """
    Für fehlende Einträge in einer Kategorie werden diese in die DB geschrieben.
    Die Zuordnung erfolgt durch Neu-Lesen der RFID Tags.
    missing_names_with_ids is a list of tuples: (name, RFIDTag id)
    """
    from crud import update_rfid_tag_by_id

    rdr = get_reader()
    audio.espeaker(f"{category}")
    for name, tag_id in missing_names_with_ids:
        audio.espeaker(f"{name}")
        print(f"Bitte halte Tag für '{category}': {name} auf den Leser!")

        tag_uid = None
        while not tag_uid:
            tag_uid = rdr.read_passive_target(timeout=1.0)

        tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])
        if tag_id is not None:
            from models import RFIDTag
            # Update the record with the actual RFID tag read from the hardware
            updated_tag = RFIDTag(id=tag_id, rfid_tag=tag_uid_readable, name=name, rfid_type=category)
            success = update_rfid_tag_by_id(tag_id, updated_tag)
        else:
            success = update_rfid_in_db(tag_uid_readable, name, category)

        time.sleep(1)

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
            # Instead of writing to file, update the DB here
            update_rfid_in_db(id_readable, figure, "figures")

    leds.reset()
    audio.espeaker("Ende der Datei erreicht, alle Daten in der DB gespeichert")


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
