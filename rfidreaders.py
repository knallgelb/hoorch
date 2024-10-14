#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import time
import threading
import os
import logging
import csv
# import unicodedata
import board
import busio
from adafruit_pn532.spi import PN532_SPI
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B
# import digitalio
from digitalio import DigitalInOut
import ndef
import audio

# Create 'logs' directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('logs/rfid.log')
file_handler.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# GPIO pin assignments
# Reader 1: Pin18 - GPIO24
# Reader 2: Pin15 - GPIO22
# Reader 3: Pin7  - GPIO4
# Reader 4: Pin37 - GPIO26
# Reader 5: Pin13 - GPIO27
# Reader 6: Pin36 - GPIO16
reader1_pin = DigitalInOut(board.D24)
reader2_pin = DigitalInOut(board.D22)
reader3_pin = DigitalInOut(board.D4)
reader4_pin = DigitalInOut(board.D26)
reader5_pin = DigitalInOut(board.D27)
reader6_pin = DigitalInOut(board.D16)

readers = []
tags = []
timer = []

figures_db = {}     # Figure database is a dictionary with tag ID and tag name
gamer_figures = []  # e.g., knight, queen,...
animal_figures = [] # e.g., lion, elephant,...
animal_numbers = [] # e.g., 0, 1, 2,...

endofmessage = "#"  # chr(35)

read_continuously = True
currently_reading = False

auth_key = b'\xFF\xFF\xFF\xFF\xFF\xFF'


def init():
    logger.info("Initializing the RFID readers and loading 'figure_db.txt'")
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

    reader_pins = [reader1_pin, reader2_pin, reader3_pin, reader4_pin, reader5_pin, reader6_pin]

    for idx, reader_pin in enumerate(reader_pins):
        try:
            reader = PN532_SPI(spi, reader_pin, debug=False)
            reader.SAM_configuration()
            readers.append(reader)
            tags.append(None)
            timer.append(0)
            logger.info('Initialized and configured RFID/NFC reader %d', idx + 1)
        except Exception as e:
            logger.error("Could not initialize RFID reader %d: %s", idx + 1, e)
        time.sleep(0.03)

    # Initialize figure database using csv module
    path = "./figure_db.txt"

    if os.path.exists(path):
        with open(path, mode="r", encoding="utf-8") as file:
            csv_reader = csv.reader(file, delimiter=';')
            section = 0

            for row in csv_reader:
                if not row or row[0].startswith(';'):
                    section += 1  # Empty line or line starting with ';' indicates section change
                    continue

                # Assign column names
                tag_id = row[0]
                tag_name = row[1]

                figures_db[tag_id] = tag_name

                if section == 2:
                    gamer_figures.append(tag_name)
                elif section == 3:
                    # Separate number from animal name
                    import re
                    match = re.match(r'([A-Za-z]+)(\d+)', tag_name)
                    if match:
                        animal_name = match.group(1)
                        animal_number = match.group(2)
                        animal_figures.append(animal_name)
                        animal_numbers.append(animal_number)
                    else:
                        animal_figures.append(tag_name)
                        animal_numbers.append(None)

    continuous_read()


def continuous_read():
    global currently_reading

    for index, r in enumerate(readers):

        mifare = False

        currently_reading = True

        try:
            tag_uid = r.read_passive_target(timeout=0.2)
        except Exception as e:
            logger.error("Error reading from RFID reader %d: %s", index + 1, e)
            continue

        if tag_uid:
            # Convert tag_uid (bytearray) to a readable ID string (e.g., "4-7-26-160")
            id_readable = "-".join(str(number) for number in tag_uid[:4])

            # Check if it's a MIFARE tag
            if len(tag_uid) > 4:
                mifare = True

            # Check if tag ID is in the figure database
            tag_name = figures_db.get(id_readable)

            if not tag_name:
                if mifare:
                    tag_name = read_from_mifare(r, tag_uid)
                else:
                    tag_name = read_from_ntag2(r)

                # Optionally power down the reader to save energy
                # r.power_down()

                if tag_name == "#error#":
                    continue

                currently_reading = False

                # If tag_name is empty, use id_readable
                if not tag_name:
                    tag_name = id_readable

                # If a figure from another game is used, add it to the figures_db
                elif tag_name in figures_db.values():
                    figures_db[id_readable] = tag_name
                else:
                    # Else, treat it as a gamer figure
                    if tag_name not in gamer_figures:
                        gamer_figures.append(tag_name)
                        logger.info("Added new unknown gamer figure to the temporary gamer_figure list")
            else:
                logger.debug("Tag ID %s found in figures_db with name %s", id_readable, tag_name)
        else:
            tag_name = None

        # Keep tags in array for 1 second to even out reading errors
        if tag_name is None and timer[index] < time.time():
            tags[index] = tag_name  # None
            timer[index] = 0  # Reset timer

        if tag_name is not None:
            timer[index] = time.time() + 1
            tags[index] = tag_name

        # Sleep between readers to reduce power load
        time.sleep(0.2)

    logger.debug("Current tags: %s", tags)

    if read_continuously:
        # Only read when not playing or recording audio
        threading.Timer(0.02, continuous_read).start()


def read_from_mifare(reader, tag_uid):
    read_data = bytearray(0)

    try:
        # Read 16 bytes from blocks 4 and 5
        for i in range(4, 6):
            authenticated = reader.mifare_classic_authenticate_block(tag_uid, i, MIFARE_CMD_AUTH_B, auth_key)
            if not authenticated:
                logger.warning("Authentication failed for block %d!", i)
            # Read blocks
            read_data.extend(reader.mifare_classic_read_block(i))

        to_decode = read_data[2:read_data.find(b'\xfe')]
        text = list(ndef.message_decoder(to_decode))[0].text
        logger.info("Read MIFARE tag with text: %s", text)
        return text

    except TypeError:
        logger.error("Error while reading RFID tag content. Tag was probably removed before reading was completed.")
        # The figure could not be recognized. Leave it longer on the field.
        audio.play_full("TTS", 199)
        return "#error#"

    except ndef.record.DecodeError as e:
        logger.error("Error while decoding with ndeflib: %s", e)
        return "#error#"


def read_from_ntag2(reader):
    read_data = bytearray(0)

    # Read 4 bytes from blocks 4-11
    try:
        for i in range(4, 12):
            read_data.extend(reader.ntag2xx_read_block(i))
        to_decode = read_data[2:read_data.find(b'\xfe')]

        text = list(ndef.message_decoder(to_decode))[0].text
        logger.info("Read NTAG2 tag with text: %s", text)
        return text

    except TypeError:
        logger.error("Error while reading RFID tag content. Tag was probably removed before reading was completed.")
        # The figure could not be recognized. Leave it longer on the field.
        audio.play_full("TTS", 199)
        return "#error#"

    except ndef.record.DecodeError as e:
        logger.error("Error while decoding with ndeflib: %s", e)
        return "#error#"


# Start the script
if __name__ == "__main__":
    init()
