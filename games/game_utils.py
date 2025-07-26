from crud import get_first_rfid_tag_by_id_and_type

import time

import audio
import file_lib
import leds
import rfidreaders
from logger_util import get_logger
from models import RFIDTag
from i18n import Translator

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
        blink_led(
            rfidreaders.tags.index(player) + 1,
            times=5,
            on_time=0.1,
            off_time=0.1,
        )
        audio.play_file("TTS", f"standard_tags.{player.name.lower()}")
        announce(68 + score)


def wait_for_figure_placement(fields):
    """Ask players to place their figures on specified fields and wait."""
    leds.switch_on_with_color(fields)
    audio.play_file("sounds", "waiting.mp3")
    time.sleep(1)


def filter_players_on_fields(players, valid_fields, defined_figures):
    """Set players to None if they are not on the valid fields or not defined figures."""
    for i in range(len(players)):
        if (
            i in valid_fields
            or players[i] is None
            or players[i].rfid_tag not in defined_figures
        ):
            players[i] = None
    return players


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
                    translator.translate(f"game.player_turn_start"),
                )
                audio.play_file(
                    "TTS",
                    translator.translate(
                        f"standard_tags.{player.name.lower()}"
                    ),
                )
                audio.play_file(
                    "TTS",
                    translator.translate(f"game.player_turn_end"),
                )
                # audio.espeaker(f"Jetzt ist {player.name} an der Reihe.")
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
