import file_lib
from games import game_utils
from models import RFIDTag
import audio
import rfidreaders
import leds

import copy

import random
import time
from typing import List


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

    score_players = game_utils.play_rounds(
        players=players,
        num_rounds=3,  # Beispiel: 3 Runden
        player_action=lambda p: player_action(p, rfidreaders, file_lib, rfid_position)
    )

    game_utils.announce_score(score_players=score_players)

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
    leds.switch_on_with_color(rfidreaders.tags.index(player), (0,255,0))

    while time.time() - start_time < total_wait_seconds:
        relevant_tags = [tag for tag in rfidreaders.tags if isinstance(tag, RFIDTag)]

        for tag in relevant_tags:
            # pdb.set_trace()
            if tag.number is not None and tag.number == expected_value.number:
                if tag == expected_value:
                    return True

        time.sleep(0.3)

    return False


if __name__ == "__main__":
    rfidreaders.init()
    start()
