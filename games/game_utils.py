import time

import audio
import file_lib
import leds
import rfidreaders
from crud import get_first_rfid_tag_by_id_and_type
from i18n import Translator
from logger_util import get_logger
from models import RFIDTag

logger = get_logger(__name__, "logs/game_utils.log")


def check_end_tag():
    """Return True if the ENDE tag is detected, else False."""
    return file_lib.check_tag_attribute(rfidreaders.tags, "ENDE", "name")


def announce(msg_id, path="TTS"):
    """Play a message by its ID from the given path and check for ENDE tag."""
    audio.play_full(path, msg_id)
    if check_end_tag():
        raise SystemExit


def announce_file(msg_id, path="TTS"):
    """Play a message by its ID from the given path and check for ENDE tag."""
    audio.play_file(path, msg_id)
    if check_end_tag():
        raise SystemExit


def announce_score(score_players: dict):
    """Play a message by its ID from the given path and check for ENDE tag."""
    translator = Translator(
        locale="de"
    )  # Initialisiere Übersetzer mit deutschem Locale
    audio.play_full("TTS", 80)
    for player, score in score_players.items():
        if not isinstance(player, RFIDTag):
            continue
        if player in rfidreaders.tags:
            blink_led(
                rfidreaders.tags.index(player) + 1,
                times=5,
                on_time=0.1,
                off_time=0.1,
            )
        audio.play_file(
            "TTS", translator.translate(f"standard_tags.{player.name.lower()}")
        )
        announce(68 + score)


def wait_for_figure_placement(fields):
    """Ask players to place their figures on specified fields and wait."""
    leds.switch_on_with_color(fields)
    audio.play_file("sounds", "waiting.mp3")
    time.sleep(1)


def filter_players_on_fields(players, valid_fields, defined_figures):
    """Return a new list of players where only players on valid fields and defined figures remain.

    The `players` sequence may contain:
    - None
    - a string (rfid_tag)
    - an RFIDTag instance (object with attribute `rfid_tag`)
    - a list/tuple where the first element is the tag object/string (e.g. [tag_obj, ...])

    This function normalizes each entry and returns a new list where positions not
    matching `valid_fields` or not present in `defined_figures` are set to None.
    The input `players` list is not modified.
    """
    # Normalize valid_fields to a set of zero-based indices
    valid_set = set(valid_fields) if valid_fields is not None else set()
    # Detect common 1-based input pattern: no 0 present and all values between 1..len(players)
    if (
        (0 not in valid_set)
        and valid_set
        and all(
            isinstance(v, int) and 1 <= v <= len(players) for v in valid_set
        )
    ):
        # Convert to 0-based
        valid_set = set(v - 1 for v in valid_set)

    # Prepare result list (same length as input)
    result = [None] * len(players)

    for i, p in enumerate(players):
        # If there's nothing in the slot, leave None
        if p is None:
            result[i] = None
            continue

        # Normalize candidate: if the entry is a list/tuple, take its first element
        if isinstance(p, (list, tuple)) and len(p) > 0:
            candidate = p[0]
        else:
            candidate = p

        # Extract rfid_tag string from candidate
        if isinstance(candidate, str):
            rfid_tag_str = candidate
        else:
            rfid_tag_str = getattr(candidate, "rfid_tag", None)

        # Keep the player only if index is in valid_set and rfid_tag is recognized
        if i in valid_set and rfid_tag_str in defined_figures:
            # store normalized candidate
            result[i] = candidate
        else:
            result[i] = None

    return result


def blink_led(field_index, times=5, on_time=0.5, off_time=0.5):
    """Blink LED at field_index."""
    for _ in range(times):
        leds.switch_on_with_color(field_index)
        time.sleep(on_time)
        leds.switch_on_with_color(field_index, (0, 0, 0))
        time.sleep(off_time)


def get_solution_from_tags(i, players):
    """Calculate the solution from the tens and units tags."""
    tens_tag = rfidreaders.tags[i + 1]
    units_tag = rfidreaders.tags[i - 1]

    tens_digit = "0"
    unit_digit = "0"

    if tens_tag and get_first_rfid_tag_by_id_and_type(tens_tag.rfid_tag):
        tens_digit = get_first_rfid_tag_by_id_and_type(tens_tag.rfid_tag).name
    if units_tag and get_first_rfid_tag_by_id_and_type(units_tag.rfid_tag):
        unit_digit = get_first_rfid_tag_by_id_and_type(units_tag.rfid_tag).name

    return tens_digit + unit_digit


def play_rounds(players, num_rounds, player_action) -> dict:
    """
    Play a set number of rounds where each player takes an action in each round.

    :param players: List of players (e.g., RFIDTag instances or player identifiers).
    :param num_rounds: The total number of rounds to play.
    :param player_action: A function that defines what happens when a player takes their turn.
                          This function should take a single argument: the player.
    """
    score_players = {player: 0 for player in players}
    translator = Translator(
        locale="de"
    )  # Initialisiere Übersetzer mit deutschem Locale

    for round_num in range(1, num_rounds + 1):
        # audio.espeaker(f"Starte Runde {round_num}...")
        audio.play_file(
            "TTS", translator.translate(f"game.start_round_{round_num}")
        )

        for player in players:
            if player is not None:
                audio.play_file(
                    "TTS",
                    translator.translate(f"turn_tags.{player.name.lower()}"),
                )
                if player_action(player):
                    score_players[player] += 1

        audio.play_file(
            "TTS", translator.translate(f"game.end_round_{round_num}")
        )

    leds.blinker()

    return score_players


def leds_switch_on_with_color(
    player: RFIDTag, color: tuple[int, int, int]
) -> None:
    try:
        if rfidreaders.tags.index(player):
            leds.switch_on_with_color(
                rfidreaders.tags.index(player) + 1, color=color
            )
            return
    except ValueError:
        leds.blinker()
