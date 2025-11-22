#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import os
import threading
import time

# import unicodedata
import board
import busio
import ndef
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B
from adafruit_pn532.spi import PN532_SPI

# import digitalio
from digitalio import DigitalInOut
from sqlmodel import Session

import crud
import file_lib
import leds
import models
from database import engine
from logger_util import get_logger

sleeping_time = 0.1

# Create 'logs' directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure logging
logger = get_logger(__name__, "logs/rfid.log")

# GPIO pin assignments
# Reader 1: Pin18 - GPIO24
# Reader 2: Pin15 - GPIO22
# Reader 3: Pin7  - GPIO4
# Reader 4: Pin37 - GPIO26
# Reader 5: Pin13 - GPIO27
# Reader 6: Pin36 - GPIO16

reader_pins = [
    DigitalInOut(board.D24),
    DigitalInOut(board.D22),
    DigitalInOut(board.D4),
    DigitalInOut(board.D26),
    DigitalInOut(board.D27),
    DigitalInOut(board.D5),
]


readers = []
tags = []
timer = []

endofmessage = "#"  # chr(35)

read_continuously = True


auth_key = b"\xff\xff\xff\xff\xff\xff"


def init():
    file_lib.load_all_tags()
    logger.info("Initializing the RFID readers")
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

    for idx, reader_pin in enumerate(reader_pins):
        try:
            reader = PN532_SPI(spi, reader_pin, debug=False)
            #            reader = PN532_SPI(spi, reader_pin, debug=True)
            ic, ver, rev, support = reader.firmware_version
            logger.info(
                "Found PN532 with firmware version: {0}.{1}".format(ver, rev)
            )
            reader.SAM_configuration()
            readers.append(reader)
            tags.append(None)
            timer.append(0)
            logger.info(
                "Initialized and configured RFID/NFC reader %d", idx + 1
            )
        except Exception as e:
            logger.error("Could not initialize RFID reader %d: %s", idx + 1, e)
        time.sleep(0.03)

    logger.debug(tags)

    continuous_read()


def extract_mifare_card(reader, tag_uid):
    read_data = read_ndef_blocks(reader, tag_uid, start_block=4, num_blocks=4)
    if read_data is None:
        print("Failed to read NDEF data blocks.")
        return

    ndef_payload = extract_ndef_payload(read_data)

    if ndef_payload is None:
        print("No NDEF payload found in data.")
        # return None

    try:
        ndef_messages = list(ndef.message_decoder(ndef_payload))
        text_messages = list(
            map(
                lambda x: x.text,
                filter(lambda x: hasattr(x, "text"), ndef_messages),
            )
        )
        return text_messages
    except Exception as e:
        print("Error decoding NDEF message:", e)


def continuous_read():
    # logger.info("Tags: %s", tags)
    # logger.info("... continuous read function")

    for index, r in enumerate(readers):
        mifare = False
        ntag213 = False

        currently_reading = True

        leds.reset()

        try:
            # Increase passive target timeout to give tag more time to settle
            tag_uid = r.read_passive_target(timeout=0.1)
        except Exception as e:
            logger.error("Error reading from RFID reader %d: %s", index + 1, e)
            continue

        if tag_uid:
            # Convert tag_uid (bytearray) to a readable ID string (e.g., "4-7-26-160")
            id_readable = "-".join(str(number) for number in tag_uid[:4])

            # Check if it's a MIFARE tag (4 bytes UID)
            if len(tag_uid) == 4:
                mifare = True

            # Check if tag is NTAG213 (7 bytes typical UID length for NTAG213)
            elif len(tag_uid) == 7:
                ntag213 = True

            # Check if tag ID is in the figure database
            tag_name = file_lib.get_figure_from_database(id_readable)

            if not tag_name:
                logger.info("RFIDREADERS if not tag_name line called")
                leds.switch_on_with_color([index + 1], (128, 255, 0))
                if mifare:
                    tag_name = read_from_mifare(r, tag_uid)
                elif ntag213:
                    tag_name = read_from_ntag213(r, tag_uid)
                else:
                    tag_name = read_from_ntag2(r)

                if tag_name == "#error#":
                    continue

                currently_reading = False

                if not tag_name:
                    logger.info(
                        "Added new unknown gamer figure to the temporary gamer_figure list"
                    )
            else:
                logger.debug(
                    "Tag ID %s found in figures_db with name %s",
                    id_readable,
                    tag_name,
                )
        else:
            tag_name = None

        # Keep tags in array for 1 second to even out reading errors
        if tag_name is None and timer[index] < time.time():
            tags[index] = tag_name  # None
            timer[index] = 0  # Reset timer

        if tag_name is not None:
            timer[index] = time.time() + 1
            tags[index] = tag_name

    # logger.debug("Current tags: %s", tags)

    if read_continuously:
        # Only read when not playing or recording audio
        threading.Timer(sleeping_time, continuous_read).start()
        leds.reset()


def read_from_mifare(reader, tag_uid: str):
    read_data = bytearray(0)

    logger.info("tag_uid: %s", tag_uid)

    tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])

    tag_uid_database = file_lib.get_figure_from_database(tag_uid_readable)

    if tag_uid_database:
        return tag_uid_database

    data_list = extract_mifare_card(reader, tag_uid)

    last_created = None

    create_tags_list = []

    if data_list:
        for item in data_list:
            splitted = item.split(":")
            rfid_type = splitted[0]
            rfid_name = splitted[1]

            create_tags_list.append(
                models.RFIDTag(
                    rfid_tag=tag_uid_readable,
                    name=rfid_name,
                    rfid_type=rfid_type,
                )
            )

    with Session(engine) as session:
        # Persist the new RFID tag in the database
        for tag in create_tags_list:
            last_created = crud.create_rfid_tag(tag, db=session)
            if last_created is None:
                logger.warning(
                    f"RFID read, but could not create new tag in DB: {tag_uid_readable}"
                )
                return None
            else:
                logger.info(f"New RFID tag created in DB: {last_created}")

    return last_created


def read_from_ntag2(reader):
    read_data = bytearray(0)

    logger.info("called read_from_ntag2 function")

    # Read 4 bytes from blocks 0-11
    try:
        for i in range(0, 12):
            read_data.extend(reader.ntag2xx_read_block(i))
        to_decode = read_data[2 : read_data.find(b"\xfe")]

        text = list(ndef.message_decoder(to_decode))[0].text
        logger.info("Read NTAG2 tag with text: %s", text)
        return text

    except TypeError:
        logger.error(
            "NTAG2 Error while reading RFID tag content. Tag was probably removed before reading was completed."
        )
        # The figure could not be recognized. Leave it longer on the field.
        return "#error#"

    except ndef.record.DecodeError as e:
        logger.error("Error while decoding with ndeflib: %s", e)
        return "#error#"


def read_from_ntag213(reader, tag_uid: str):
    read_data = bytearray(0)

    tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])

    # Check if tag already exists in DB
    tag_uid_database = file_lib.get_figure_from_database(tag_uid_readable)
    if tag_uid_database:
        return tag_uid_database

    # Before attempting to read blocks, behave like tagwriter: try to (re-)select the tag
    # to make sure the tag is really present/stable. This mirrors the interactive readers
    # that wait for a tag when writing/assigning missing tags.
    preselect_attempts = 3
    preselect_timeout = (
        1.0  # seconds, similar to tagwriter's interactive timeouts
    )
    uid_match = False
    for pre in range(preselect_attempts):
        try:
            uid_now = reader.read_passive_target(timeout=preselect_timeout)
        except Exception as e:
            logger.debug(f"Preselect attempt {pre + 1} failed: {e}")
            uid_now = None
        if uid_now is None:
            logger.debug(f"Preselect attempt {pre + 1}: no tag detected")
            continue
        # Compare first 4 UID bytes (the readable id format used elsewhere)
        try:
            if uid_now[:4] == tag_uid[:4]:
                uid_match = True
                logger.debug(
                    "Preselect matched tag UID before NTAG213 read (attempt %d)",
                    pre + 1,
                )
                break
            else:
                logger.debug(
                    "Preselect attempt %d: different tag detected (%s)",
                    pre + 1,
                    uid_now,
                )
                # Keep trying to allow the correct tag to be placed
                continue
        except Exception:
            # If comparison fails for any reason, just continue trying
            continue

    if not uid_match:
        logger.info(
            "Proceeding to read NTAG213 blocks for %s without confirmed re-select (tag may be unstable)",
            tag_uid_readable,
        )

    # Read NTAG213 blocks starting at user data area (block 4). Stop early when the
    # TLV terminator (0xFE) is found or when an NDEF payload can be extracted.
    # Keep retries/reselection and pad missing blocks with zeros so indices remain stable.
    max_attempts = 3
    retry_delay = 0.1  # seconds between retry attempts for the same block
    per_block_delay = 0.03  # small pause after a successful block read
    reselection_timeout = 0.3  # timeout for a quick re-check of tag presence
    start_block = 4
    end_block = 24

    # flag to break outer loop when we've found payload/terminator
    found_early_termination = False

    for i in range(start_block, end_block):
        success = False
        for attempt in range(1, max_attempts + 1):
            try:
                blk = reader.ntag2xx_read_block(i)
                if blk is None:
                    # Treat None as a transient failure and retry
                    raise RuntimeError("ntag2xx_read_block returned None")
                # Ensure we got a bytes-like object
                if not isinstance(blk, (bytes, bytearray)) or len(blk) < 1:
                    raise RuntimeError(
                        f"Unexpected block data for block {i}: {blk}"
                    )
                read_data.extend(blk)
                success = True

                # After adding this block, check if we already have a TLV terminator
                # or can extract the NDEF payload. If so, stop reading further blocks.
                try:
                    if b"\xfe" in read_data:
                        logger.debug(
                            f"Found TLV terminator after reading block {i}; stopping early"
                        )
                        found_early_termination = True
                    else:
                        payload_now = extract_ndef_payload(read_data)
                        if payload_now:
                            logger.debug(
                                f"Found NDEF payload after reading block {i}; stopping early"
                            )
                            found_early_termination = True
                except Exception as _:
                    # If extraction check fails, ignore and continue reading more blocks
                    pass

                break
            except Exception as e:
                logger.debug(
                    f"Attempt {attempt} failed reading NTAG213 block {i}: {e}"
                )
                # On the first failure do a quick re-selection to ensure the tag is still present
                if attempt == 1:
                    try:
                        uid_now = reader.read_passive_target(
                            timeout=reselection_timeout
                        )
                        if uid_now is None:
                            logger.debug(
                                "Tag not present on re-check before retry; will pad this block and continue"
                            )
                            break  # leave attempt loop -> will pad below
                        if uid_now != tag_uid:
                            logger.debug(
                                "Different tag detected on re-check; will pad this block and continue"
                            )
                            break
                    except Exception as e2:
                        logger.debug(f"Re-selection read failed: {e2}")
                # small backoff before next attempt
                if attempt < max_attempts:
                    time.sleep(retry_delay)
        if not success:
            # Instead of aborting the whole read, pad missing/empty blocks with zeros
            logger.warning(
                f"Could not read NTAG213 block {i} after {max_attempts} attempts — padding with zeros and continuing"
            )
            # NTAG block size is 4 bytes; pad with zeros so parsing keeps indices stable
            read_data.extend(b"\x00\x00\x00\x00")
        # small pause between blocks to give the PN532 some settling time
        time.sleep(per_block_delay)

        # If we detected a terminator or payload above, break outer loop now.
        if found_early_termination:
            break

    create_tags_list = []

    ndef_payload = extract_ndef_payload(read_data)
    if ndef_payload:
        try:
            ndef_messages = list(ndef.message_decoder(ndef_payload))
            for msg in ndef_messages:
                # Use text attributes if available, else skip
                if hasattr(msg, "text"):
                    splitted = msg.text.split(":")
                    if len(splitted) < 2:
                        continue
                    rfid_type = splitted[0]
                    rfid_name = splitted[1]
                    create_tags_list.append(
                        models.RFIDTag(
                            rfid_tag=tag_uid_readable,
                            name=rfid_name,
                            rfid_type=rfid_type,
                        )
                    )
        except Exception as e:
            logger.error(f"Error decoding NDEF message for NTAG213: {e}")
            # Fall back to a default placeholder entry below instead of aborting
    else:
        create_tags_list.append(
            models.RFIDTag(
                rfid_tag=tag_uid_readable,
                name="Custom Tag",
                rfid_type="custom_tag",
            )
        )
        logger.info(
            "No NDEF payload found on NTAG213 tag — will create fallback DB entry"
        )
        # fall through to create a placeholder entry below

    # If we couldn't extract any tag info (no payload or decode error), still create
    # a fallback database entry so the tag is registered.
    if not create_tags_list:
        logger.info(
            "Creating fallback RFID tag entry for NTAG213 tag %s (no NDEF text found)",
            tag_uid_readable,
        )
        create_tags_list.append(
            models.RFIDTag(
                rfid_tag=tag_uid_readable,
                name=tag_uid_readable,
                rfid_type="ntag213",
            )
        )

    last_created = None
    with Session(engine) as session:
        for tag in create_tags_list:
            last_created = crud.create_rfid_tag(tag, db=session)
            if last_created is None:
                logger.warning(
                    f"NTAG213 read, but could not create new tag in DB: {tag_uid_readable}"
                )
                return None
            else:
                logger.info(
                    f"New NTAG213 RFID tag created in DB: {last_created}"
                )

    return last_created


def extract_ndef_payload(data):
    i = 0
    logger.debug(f"extract_ndef_payload called with {len(data)} bytes")
    while i < len(data):
        b = data[i]

        # skip null TLV bytes
        if b == 0x00:
            i += 1
            continue

        # terminator TLV: stop scanning
        if b == 0xFE:
            logger.debug("Found TLV terminator at index %d", i)
            break

        # if this is the NDEF TLV, parse length and return payload if complete
        if b == 0x03:
            # need at least one length byte
            if i + 1 >= len(data):
                logger.debug("NDEF TLV at index %d has no length byte", i)
                return None
            length = data[i + 1]
            payload_start = i + 2

            # extended length form (0xFF) uses two subsequent bytes
            if length == 0xFF:
                if i + 3 >= len(data):
                    logger.debug(
                        "NDEF TLV at index %d uses extended length but length bytes missing",
                        i,
                    )
                    return None
                length = (data[i + 2] << 8) | data[i + 3]
                payload_start = i + 4

            payload_end = payload_start + length
            if payload_end > len(data):
                logger.debug(
                    "NDEF payload incomplete at index %d: expected %d bytes, have %d",
                    i,
                    length,
                    max(0, len(data) - payload_start),
                )
                return None

            logger.debug(
                "Found NDEF TLV at index %d with length %d (payload %d..%d)",
                i,
                length,
                payload_start,
                payload_end,
            )
            return data[payload_start:payload_end]

        # otherwise, advance one byte and keep searching for 0x03 or 0xFE
        i += 1

    # No complete NDEF payload found
    return None


def read_ndef_blocks(reader, uid, start_block=4, num_blocks=4):
    """
    Liest num_blocks hintereinander ab start_block aus.
    Authentifiziert vorher jeden Block.
    """
    data = bytearray()
    for blk in range(start_block, start_block + num_blocks):
        authenticated = reader.mifare_classic_authenticate_block(
            uid, blk, MIFARE_CMD_AUTH_B, auth_key
        )
        if not authenticated:
            print(f"Authentication failed for block {blk}")
            return None
        blk_data = reader.mifare_classic_read_block(blk)
        if blk_data is None:
            print(f"Reading block {blk} failed")
            return None
        data.extend(blk_data)
    return data


# Start the script
if __name__ == "__main__":
    file_lib.read_database_files()
    read_continuously = True
    init()
