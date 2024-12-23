from random import randint
from time import sleep
import copy

import file_lib
from games import game_utils
from models import RFIDTag
import audio
import rfidreaders


def start():
    defined_figures = file_lib.figures_db
    audio.espeaker("Spiel Zahlen legen")
    audio.espeaker("Setze die Spielfiguren auf das Spielfeld. Mögliche Felder sind 1,3,5")
    # wait
    sleep(3.0)
    players = game_utils.filter_players_on_fields(copy.deepcopy(rfidreaders.tags), [1, 3, 5], defined_figures)

    game_utils.play_rounds(players=players, num_rounds=1, player_action=player_action)


def player_action(player_position: int, rfid_position: list, expected_value: RFIDTag, tag_list: list[RFIDTag]) -> bool:
    relevant_tags = [tag_list[pos] for pos in rfid_position if pos < len(tag_list)]
    return any(tag == expected_value for tag in relevant_tags if tag.number == expected_value.number)
