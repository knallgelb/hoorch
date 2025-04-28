import file_lib
from games import game_utils
from models import RFIDTag
import audio
import rfidreaders
import leds
import models
import crud

import copy

import random
import time
from typing import List
from logger_util import get_logger

logger = get_logger(__name__, "logs/game_zahlen.log")

def start():
    defined_figures = file_lib.all_tags
    audio.espeaker("Spiel Zahlen legen")
    audio.espeaker("Setze die Spielfiguren auf das Spielfeld. Mögliche Felder sind 1, 3, 5")
    time.sleep(3.0)

    rfid_position = [1, 3, 5]

    players = game_utils.filter_players_on_fields(
        copy.deepcopy(rfidreaders.tags),
        rfid_position,
        defined_figures
    )

    figure_count = sum(p is not None for p in players)

    # Log Usage
    u = models.Usage(game="zahlen", players=figure_count)
    crud.add_game_entry(usage=u)

    def action_with_led(player):
        idx = players.index(player)
        leds.switch_on_with_color(idx, (0,255,0))
        result = player_action(player, rfidreaders, file_lib, rfid_position)
        leds.switch_on_with_color(idx, (0,0,0))
        return result

    score_players = game_utils.play_rounds(
        players=players,
        num_rounds=3,  # Beispiel: 3 Runden
        player_action=action_with_led
    )

    game_utils.announce_score(score_players=score_players)

    leds.switch_all_on_with_color((0,0,255))
    time.sleep(0.2)
    leds.reset()
    return score_players


def player_action(
        player: RFIDTag,
        rfidreaders,
        file_lib,
        rfid_position: List[int]
) -> bool:
    expected_value = random.choice(list(file_lib.animal_numbers_db.values()))
    audio.espeaker(expected_value.number)

    total_wait_seconds = 6.0
    start_time = time.time()

    leds.reset()
    game_utils.leds_switch_on_with_color(player=player, color=(0, 255, 0))

    while time.time() - start_time < total_wait_seconds:
        relevant_tags = [tag for tag in rfidreaders.tags if isinstance(tag, RFIDTag)]

        for tag in relevant_tags:
            # pdb.set_trace()
            if tag.number is not None and tag.number == expected_value.number:
                return True

        time.sleep(0.3)

    return False


if __name__ == "__main__":
    rfidreaders.init()
    start()
