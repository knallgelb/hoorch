import time
import audio
import rfidreaders
import leds
import file_lib
import random
import copy

def check_end_tag():
    """Return True if the ENDE tag is detected, else False."""
    return file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name")

def announce(msg_id, path='TTS'):
    """Play a message by its ID from the given path and check for ENDE tag."""
    audio.play_full(path, msg_id)
    if check_end_tag():
        raise SystemExit

def announce_file(msg_id, path='TTS'):
    """Play a message by its ID from the given path and check for ENDE tag."""
    audio.play_file(path, msg_id)
    if check_end_tag():
        raise SystemExit

def wait_for_figure_placement(fields):
    """Ask players to place their figures on specified fields and wait."""
    leds.switch_on_with_color(fields)
    audio.play_file("sounds", "waiting.mp3")
    time.sleep(6)

def filter_players_on_fields(players, valid_fields, defined_figures):
    """Set players to None if they are not on the valid fields or not defined figures."""
    for i in range(len(players)):
        if (i in valid_fields
                or players[i] is None
                or players[i].rfid_tag not in defined_figures):
            players[i] = None
    return players

def blink_led(field_index, times=10, on_time=0.5, off_time=0.5):
    """Blink LED at field_index."""
    for _ in range(times):
        leds.switch_on_with_color(field_index)
        time.sleep(on_time)
        leds.switch_on_with_color(field_index, (0, 0, 0))
        time.sleep(off_time)

def get_solution_from_tags(i, players):
    """Calculate the solution from the tens and units tags."""
    tens = rfidreaders.tags[(i + 1) % len(players)]
    units = rfidreaders.tags[(i - 1) % len(players)]
    tens_digit = int(tens.number) * 10 if tens else 0
    unit_digit = int(units.number) if units else 0
    return tens_digit + unit_digit
