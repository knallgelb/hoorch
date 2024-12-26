import file_lib
from games import game_utils
from games.game_utils import announce_score
from models import RFIDTag
import audio
import rfidreaders

import random
import time
from typing import List


def start():
    defined_figures = file_lib.figures_db
    audio.espeaker("Spiel Zahlen legen")
    audio.espeaker("Setze die Spielfiguren auf das Spielfeld. Mögliche Felder sind 1, 3, 5")
    time.sleep(3.0)

    rfid_position = [1, 3, 5]

    players = game_utils.filter_players_on_fields(
        rfidreaders.tags,
        rfid_position,
        defined_figures
    )

    score_players = game_utils.play_rounds(
        players=players,
        num_rounds=3,  # Beispiel: 3 Runden
        player_action=lambda p: player_action(p, rfidreaders, file_lib, rfid_position)
    )

    game_utils.announce_score(score_players=score_players)
    audio.espeaker("Das Spiel ist zu Ende.")

    return score_players


def player_action(
        player: RFIDTag,
        rfidreaders,
        file_lib,
        rfid_position: List[int]
) -> bool:
    expected_value = random.choice(list(file_lib.animal_numbers_db.values()))
    game_utils.announce_score(expected_value.number)

    # Wir warten bis zu 3 Sekunden, prüfen aber zwischendurch immer wieder
    total_wait_seconds = 3.0
    start_time = time.time()

    while time.time() - start_time < total_wait_seconds:
        relevant_tags = [
            rfidreaders.tags[pos]
            for pos in rfid_position
            if pos < len(rfidreaders.tags)
        ]
        if any(
            tag == expected_value
            for tag in relevant_tags
            if tag.number == expected_value.number
        ):
            return True

        # Warten wir kurz und prüfen dann wieder
        time.sleep(0.3)

    # Wenn nach 3 Sekunden keine Übereinstimmung gefunden wurde, False
    return False


if __name__ == "__main__":
    rfidreaders.init()
    start()