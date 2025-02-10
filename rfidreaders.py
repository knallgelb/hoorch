#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import time
import threading
import os
import logging
# import unicodedata
import board
import busio
from adafruit_pn532.spi import PN532_SPI
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B
# import digitalio
from digitalio import DigitalInOut
import ndef
from pathlib import Path

import file_lib

# Create 'logs' directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('logs/rfid.log')
file_handler.setLevel(logging.DEBUG)

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

endofmessage = "#"  # chr(35)

read_continuously = True
currently_reading = False

auth_key = b'\xFF\xFF\xFF\xFF\xFF\xFF'


def init():
    file_lib.read_database_files()
    logger.info("Initializing the RFID readers")
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

    reader_pins = [reader1_pin, reader2_pin, reader3_pin, reader4_pin, reader5_pin, reader6_pin]

    for idx, reader_pin in enumerate(reader_pins):
        try:
            reader = PN532_SPI(spi, reader_pin, debug=False)
            #            reader = PN532_SPI(spi, reader_pin, debug=True)
            ic, ver, rev, support = reader.firmware_version
            logger.info("Found PN532 with firmware version: {0}.{1}".format(ver, rev))
            reader.SAM_configuration()
            readers.append(reader)
            tags.append(None)
            timer.append(0)
            logger.info('Initialized and configured RFID/NFC reader %d', idx + 1)
        except Exception as e:
            logger.error("Could not initialize RFID reader %d: %s", idx + 1, e)
        time.sleep(0.03)

    logger.debug(tags)

    continuous_read()


def continuous_read():
    global currently_reading
    # logger.info("Tags: %s", tags)
    # logger.info("... continuous read function")

    for index, r in enumerate(readers):

        mifare = False

        currently_reading = True

        try:
            tag_uid = r.read_passive_target(timeout=0.2)
        except Exception as e:
            logger.error("Error reading from RFID reader %d: %s", index + 1, e)
            continue

        if tag_uid:
            # logger.debug("Found card with UID: %s", "-".join([str(i) for i in tag_uid]))

            # Convert tag_uid (bytearray) to a readable ID string (e.g., "4-7-26-160")
            id_readable = "-".join(str(number) for number in tag_uid[:4])

            # Check if it's a MIFARE tag
            if len(tag_uid) > 4:
                mifare = True

            # Check if tag ID is in the figure database
            tag_name = file_lib.get_figure_from_database(id_readable)

            if not tag_name:
                logger.info("RFIDREADERS if not tag_name line called")
                if mifare:
                    tag_name = read_from_mifare(r, tag_uid)
                else:
                    tag_name = read_from_ntag2(r)

                if tag_name == "#error#":
                    continue

                currently_reading = False

                if not tag_name:
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

    # logger.debug("Current tags: %s", tags)

    if read_continuously:
        # Only read when not playing or recording audio
        threading.Timer(0.02, continuous_read).start()


def read_from_mifare(reader, tag_uid: str):
    read_data = bytearray(0)

    logger.info("tag_uid: %s", tag_uid)

    tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])

    tag_uid_database = file_lib.get_figure_from_database(tag_uid_readable)

    if tag_uid_database:
        return tag_uid_database

    return tag_uid_readable


def read_from_ntag2(reader):
    read_data = bytearray(0)

    logger.info("called read_from_ntag2 function")

    # Read 4 bytes from blocks 4-11
    try:
        # for i in range(4, 12):
        for i in range(0, 12):
            read_data.extend(reader.ntag2xx_read_block(i))
        to_decode = read_data[2:read_data.find(b'\xfe')]

        text = list(ndef.message_decoder(to_decode))[0].text
        logger.info("Read NTAG2 tag with text: %s", text)
        return text

    except TypeError:
        logger.error(
            "NTAG2 Error while reading RFID tag content. Tag was probably removed before reading was completed.")
        # The figure could not be recognized. Leave it longer on the field.
        return "#error#"

    except ndef.record.DecodeError as e:
        logger.error("Error while decoding with ndeflib: %s", e)
        return "#error#"


# Start the script
if __name__ == "__main__":
    file_lib.read_database_files()
    read_continuously = True
    init()
