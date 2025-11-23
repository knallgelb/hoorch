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
    """Return True if the ENDE tag is detected, else False.

    This function requests a synchronous snapshot from the RFID readers and
    flattens any nested slot entries (a slot may contain a single tag object
    or a list/tuple of tag objects). It then checks whether any detected tag
    has its `name` attribute equal to "ENDE".
    """
    snapshot = rfidreaders.get_tags_snapshot(True)

    if not snapshot:
        return False

    for entry in snapshot:
        if entry is None:
            continue
        # If a slot contains multiple items (list/tuple), inspect them
        if isinstance(entry, (list, tuple)):
            for it in entry:
                if it is None:
                    continue
                if getattr(it, "name", None) == "ENDE":
                    return True
        else:
            if getattr(entry, "name", None) == "ENDE":
                return True

    return False


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

    NOTE: At the start we flatten the incoming `players` list:
    - Remove None entries
    - If an entry is a list/tuple, extract its elements (ignoring None)
    After flattening the local `players` variable is replaced with the flattened list.
    """
    # First: flatten the players sequence by removing None and unpacking lists/tuples
    flat_players = []
    for entry in players:
        if entry is None:
            flat_players.append(None)
            continue
        if isinstance(entry, (list, tuple)):
            # extend with non-None elements from the nested sequence
            flat_players.extend(it for it in entry if it is not None)
        else:
            flat_players.append(entry)

    # Replace the local players variable with the flattened list

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

    # Prepare result list (same length as (flattened) input)
    result = [None] * len(players)

    for i, p in enumerate(flat_players):
        if p in defined_figures.values():
            result[i] = p
            continue

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
