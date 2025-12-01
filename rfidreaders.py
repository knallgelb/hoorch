#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import logging
import os
import threading
import time
from contextlib import contextmanager

# import unicodedata
import board
import busio
import ndef
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B
from adafruit_pn532.spi import PN532_SPI

# import digitalio
from digitalio import DigitalInOut, Direction
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

# Configure logging (only critical and above)
logger = get_logger(__name__, "logs/rfid.log")
logger.setLevel(logging.CRITICAL)

# GPIO pin assignments
# Reader 1: Pin18 - GPIO24
# Reader 2: Pin15 - GPIO22
# Reader 3: Pin7  - GPIO4
# Reader 4: Pin37 - GPIO26
# Reader 5: Pin13 - GPIO27
# Reader 6: Pin36 - GPIO16

reader_pins = []
# Initialize CS pins as outputs and deselect them (active-low: True = deselected)
for pin_board in (
    board.D24,
    board.D22,
    board.D4,
    board.D26,
    board.D27,
    board.D5,
):
    p = DigitalInOut(pin_board)
    p.direction = Direction.OUTPUT
    p.value = True
    reader_pins.append(p)


readers = [None] * len(reader_pins)
tags = [None] * len(reader_pins)
# Separate timers:
# - tag_timer remembers a detected tag for games (longer retention)
# - led_timer controls how long LEDs are shown for active readers (round window)
tag_timer = [0] * len(reader_pins)
led_timer = [0] * len(reader_pins)
# Lock to protect concurrent access to tags and timers (reads/writes from other threads)
tags_lock = threading.Lock()
# Lock to serialize explicit scan cycles (used when a caller requests an immediate scan)
scan_lock = threading.Lock()

endofmessage = "#"  # chr(35)

read_continuously = True

# We allow multiple readers to report tags within the same round.
# Individual reader validity is tracked per-reader using `timer` and `tags`.
# (global active_reader/active_round_end logic removed so multiple cards can be detected)

auth_key = b"\xff\xff\xff\xff\xff\xff"

# Optional hardware power control pins. If you have hardware switches / MOSFETs
# to cut VCC for each PN532, populate this list with DigitalInOut(board.DX)
# objects in the same order as `reader_pins` and set `use_power_control = True`.
power_pins = []  # e.g. [DigitalInOut(board.D6), DigitalInOut(board.D13), ...]
use_power_control = False

# Timing tuning
power_on_delay = 0.12  # seconds to wait after powering a PN532 before init
post_init_delay = 0.03  # small pause after SAM_configuration
round_duration = 0.3  # seconds: requested max round duration
# How long to remember a detected tag (seconds). Default value; games can override.
tag_memory_seconds = 6.5
last_update = None


# API to set/get and temporarily override tag memory per game.
# Games can call `rfidreaders.set_tag_memory_seconds(...)` to set a global value,
# or use the context manager `temporary_tag_memory(...)` to set it temporarily
# for the duration of a `with` block.
def set_tag_memory_seconds(seconds: float):
    """Set the global default tag memory duration (seconds)."""
    global tag_memory_seconds
    tag_memory_seconds = float(seconds)


def get_tag_memory_seconds() -> float:
    """Return the current global tag memory duration (seconds)."""
    return float(tag_memory_seconds)


@contextmanager
def temporary_tag_memory(seconds: float):
    """Context manager to temporarily override tag memory for a block.

    Usage:
        with temporary_tag_memory(10.0):
            # inside block tag memory is 10s
            ...
    """
    global tag_memory_seconds
    old = tag_memory_seconds
    try:
        tag_memory_seconds = float(seconds)
        yield
    finally:
        tag_memory_seconds = old


# Global shared round window end: when the first detection in a round occurs,
# all subsequent detections in that same round use the same expiry time so
# tags share a common validity window.
round_window_end = 0.0

# Ensure readers list exists and will be lazily initialized (None = not powered/created)


def _power_set(index, enable: bool):
    """Switch hardware power for a reader if power control is configured."""
    if not use_power_control:
        return
    try:
        p = power_pins[index]
        # Assume active-high enable; adapt if your circuit is inverted.
        p.value = bool(enable)
    except Exception:
        pass


def init_reader(index):
    """Power-on and initialize a single PN532 reader. Returns the reader or None."""
    global spi
    # Power on (if available) and give time for regulator/IC to stabilize
    _power_set(index, True)
    time.sleep(power_on_delay)

    try:
        # Ensure CS is deselected initially
        reader_pins[index].value = True
    except Exception:
        pass

    try:
        # Create PN532 instance for this reader
        reader = PN532_SPI(spi, reader_pins[index], debug=False)
        # Access firmware_version to ensure device responds
        _ = reader.firmware_version
        reader.SAM_configuration()
        time.sleep(post_init_delay)
        readers[index] = reader
        logger.info("Initialized and configured RFID/NFC reader %d", index + 1)
        return reader
    except Exception as e:
        logger.error("Could not initialize RFID reader %d: %s", index + 1, e)
        # If init failed, power off to avoid leaving it on in a bad state
        _power_set(index, False)
        readers[index] = None
        return None


def shutdown_reader(index):
    """Shutdown a reader: deselect CS, delete reference and power off (if available)."""
    try:
        r = readers[index]
        # Deselect CS
        try:
            reader_pins[index].value = True
        except Exception:
            pass
        # Remove reference so object is freed
        readers[index] = None
    finally:
        # Cut power if hardware control exists and give the board a moment to fully power down
        _power_set(index, False)
        time.sleep(0.02)


def get_tags_snapshot(trigger_scan: bool = False):
    """Return a shallow copy of the tags list in a thread-safe manner.

    If `trigger_scan` is True, attempt to run a single synchronous scan cycle
    before returning the snapshot so the caller gets an up-to-date view.
    Scans are serialized with `scan_lock` to avoid concurrent scanning.
    If a scan is already in progress, this function will wait for it to finish
    (without starting a new one) and then return the snapshot.

    Note: `do_scan_cycle()` may be defined later in the module; use a lookup
    from globals() so calling this function before that definition does not
    raise a NameError.
    """
    sc = globals().get("do_scan_cycle")
    global last_update
    if last_update + tag_memory_seconds > time.time():
        return [t for t in tags]
    if trigger_scan and sc is not None:
        # Try to start a scan if none is running; otherwise wait for the running one.
        acquired = scan_lock.acquire(blocking=False)
        if acquired:
            try:
                sc()
            finally:
                scan_lock.release()
        else:
            # Another scan is in progress; wait until it finishes
            with scan_lock:
                pass
    with tags_lock:
        return [t for t in tags]


def init():
    # Prepare internal tag database and start SPI bus only.
    # We no longer instantiate all PN532 objects at startup. Each reader will be
    # powered/initialized on demand per round (init_reader/shutdown_reader).
    file_lib.load_all_tags()
    global last_update
    last_update = time.time()
    logger.info("Initializing the RFID readers (lazy-per-reader init)")

    # Expose spi as a module-global used by init_reader()
    # Note: expose tag_timer and led_timer so init() can reset them as needed
    global spi, tags, tag_timer, led_timer
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

    # Ensure tags and timers match the number of reader pins.
    # Use slice assignment to preserve list identity for callers that keep references.
    tags[:] = [None] * len(reader_pins)
    tag_timer[:] = [0] * len(reader_pins)
    led_timer[:] = [0] * len(reader_pins)

    # Prepare hardware power control pins (if configured)
    if use_power_control:
        if len(power_pins) != len(reader_pins):
            logger.warning(
                "use_power_control is True but number of power_pins (%d) != number of reader_pins (%d).",
                len(power_pins),
                len(reader_pins),
            )
        for idx, p in enumerate(power_pins):
            try:
                p.direction = Direction.OUTPUT
                # Start with power off to avoid interference until explicitly enabled
                p.value = False
            except Exception as e:
                logger.debug("Could not configure power pin %d: %s", idx, e)

    logger.debug(
        "SPI initialized; readers will be initialized on-demand per round"
    )

    # Start the read loop
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


def do_scan_cycle():
    """Perform a single scan cycle: power-cycle each reader once and update tags/timers/LEDs.

    This function is intended to be called either by the periodic `continuous_read()`
    loop or synchronously by callers that request an immediate scan via
    `get_tags_snapshot(trigger_scan=True)`. The caller is responsible for
    serializing access with `scan_lock` if necessary.
    """
    # Poll readers by powering/initializing each one in turn, then shutting it down.
    # Readers are allowed to report tags in the same round; we track validity per reader
    # via `tag_timer` and `tags` rather than using a single global active reader lock.
    now = time.time()
    global last_update

    # Iterate over reader indices and perform a single power-cycle read per reader.
    for index in range(len(reader_pins)):
        # Clear stale tag for this reader if its tag memory expired
        if tags[index] is not None and tag_timer[index] < time.time():
            # Protect changes with the lock so readers/games seeing tags get a consistent view
            with tags_lock:
                tags[index] = None
                # also clear associated timers to be explicit
                tag_timer[index] = 0
                led_timer[index] = 0

        # Initialize (power on + create PN532 object) for this reader
        r = init_reader(index)
        if r is None:
            # Could not initialize; skip and ensure it's powered down
            shutdown_reader(index)
            continue

        mifare = False
        ntag213 = False
        tag_name = None

        try:
            # Increase robustness: deselect other readers' CS, select this reader's CS,
            # then perform a small retry loop to account for transient RF instability.
            for j, p in enumerate(reader_pins):
                try:
                    if j != index:
                        p.value = True
                except Exception:
                    pass

            try:
                reader_pins[index].value = False
            except Exception:
                pass

            tag_uid = None
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    tag_uid = r.read_passive_target(timeout=0.15)
                except Exception:
                    tag_uid = None
                if tag_uid:
                    break
                # small backoff between attempts to allow tag/reader to settle
                time.sleep(0.04)

            # Deselect this reader's CS immediately after attempts to avoid leaving it active
            try:
                reader_pins[index].value = True
            except Exception:
                pass

            # proceed — if no tag_uid was found, tag_uid will be None and the logic below handles that
        except Exception as e:
            # On read/setup error skip this reader iteration
            shutdown_reader(index)
            continue

        if tag_uid:
            # Convert tag_uid (bytearray) to a readable ID string (e.g., "4-7-26-160")
            id_readable = "-".join(str(number) for number in tag_uid[:4])

            tags[index] = id_readable

            # Check type by UID length
            if len(tag_uid) == 4:
                mifare = True
            elif len(tag_uid) == 7:
                ntag213 = True

            # Lookup in database
            tag_name = file_lib.get_all_figures_by_rfid_tag(id_readable)

            if not tag_name:
                if mifare:
                    tag_name = read_from_mifare(r, tag_uid)
                elif ntag213:
                    tag_name = read_from_ntag213(r, tag_uid)
                else:
                    tag_name = read_from_ntag2(r)

                if tag_name == "#error#":
                    # On error, do not set any timers; shutdown and continue
                    shutdown_reader(index)
                    continue

        # Update tag storage/timers. If no tag and previous tag_timer expired, clear.
        if tag_name is None and tag_timer[index] < time.time():
            with tags_lock:
                tags[index] = None
                tag_timer[index] = 0

        active_leds = [i + 1 for i, t in enumerate(tags) if t is not None]
        if len(active_leds) > 0:
            leds.switch_on_with_color(active_leds, (0, 255, 0))
        else:
            leds.reset()

        if tag_name is not None:
            # If this is the first detection in this loop, set the shared LED expiry window
            global round_window_end
            now = time.time()
            if round_window_end < now:
                round_window_end = now + round_duration

            # Store the tag in tags[] and keep it in memory for games for a longer duration
            # so games that copy the tags list later still find the tag.
            with tags_lock:
                tag_timer[index] = time.time() + tag_memory_seconds
                # For LED display, use the shared round window end so all LEDs for this pass
                # have the same expiry and none expire before the loop completes.
                led_timer[index] = round_window_end
                tags[index] = tag_name

            # Critical log for detection (only these are visible with current logger level)
            logger.critical(
                "Reader %d: detected tag '%s' — tag_timer until %.3f (memory %.3fs), led_timer until %.3f",
                index + 1,
                tag_name,
                tag_timer[index],
                tag_memory_seconds,
                led_timer[index],
            )

        # Shutdown this reader (power off / remove object) to avoid interference.
        shutdown_reader(index)

    # Emit a concise snapshot log of current tags (critical so it is visible)
    logger.critical("Current Tags %s", get_tags_snapshot())
    last_update = time.time()


def continuous_read():
    """Periodic driver that schedules a scan cycle.

    The actual scanning logic lives in do_scan_cycle(); continuous_read simply
    serializes access via `scan_lock` and reschedules itself.
    """
    # If another scan is currently running, do not start a new one.
    acquired = scan_lock.acquire(blocking=False)
    if not acquired:
        # schedule next attempt and return
        if read_continuously:
            threading.Timer(sleeping_time, continuous_read).start()
        return

    try:
        # perform exactly one scan cycle
        do_scan_cycle()
    finally:
        scan_lock.release()

    # schedule next poll
    if read_continuously:
        threading.Timer(sleeping_time, continuous_read).start()


def read_from_mifare(reader, tag_uid: str):
    read_data = bytearray(0)

    logger.info("tag_uid: %s", tag_uid)

    tag_uid_readable = "-".join(str(number) for number in tag_uid[:4])

    tag_uid_database = file_lib.get_all_rfid_tags_by_tag_id(tag_uid_readable)

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
            #  if attempt < max_attempts:
            #      time.sleep(retry_delay)
        if not success:
            # Instead of aborting the whole read, pad missing/empty blocks with zeros
            logger.warning(
                f"Could not read NTAG213 block {i} after {max_attempts} attempts — padding with zeros and continuing"
            )
            # NTAG block size is 4 bytes; pad with zeros so parsing keeps indices stable
            read_data.extend(b"\x00\x00\x00\x00")
        # small pause between blocks to give the PN532 some settling time
        # time.sleep(per_block_delay)

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
