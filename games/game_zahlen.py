import copy
import random
import time
from typing import List

import audio
import crud
import file_lib
import leds
import models
import rfidreaders
from games import game_utils
from logger_util import get_logger
from models import RFIDTag

logger = get_logger(__name__, "logs/game_zahlen.log")


def start():
    defined_figures = file_lib.get_tags_by_type("figures")
    game_utils.announce(202)
    game_utils.announce(86)
    rfidreaders.display_active_leds = False
    game_utils.wait_for_figure_placement((1, 3, 5))
    time.sleep(3.0)

    rfid_position = [1, 3, 5]

    players = game_utils.filter_players_on_fields(
        rfidreaders.get_tags_snapshot(True), rfid_position, defined_figures
    )

    figure_count = sum(p is not None for p in players)

    # Log Usage
    u = models.Usage(game="zahlen", players=figure_count)
    crud.add_game_entry(usage=u)

    def action_with_led(player):
        idx = players.index(player) + 1
        result = player_action(player, rfidreaders, file_lib, rfid_position)
        leds.switch_on_with_color(idx, (0, 0, 0))
        return result

    score_players = game_utils.play_rounds(
        players=players,
        num_rounds=3,  # Beispiel: 3 Runden
        player_action=action_with_led,
    )

    game_utils.announce_score(score_players=score_players)

    leds.switch_all_on_with_color((0, 0, 255))
    time.sleep(0.2)
    leds.reset()
    return score_players


def player_action(
    player: RFIDTag, rfidreaders, file_lib, rfid_position: List[int]
) -> bool:
    numeric_tags = list(file_lib.get_tags_by_type("numeric").values())
    logger.debug(
        f"Numeric tags types before random choice: {[type(tag) for tag in numeric_tags]}"
    )
    expected_value = random.choice(numeric_tags)
    game_utils.announce(90 + int(expected_value.name))  # Zahlen

    total_wait_seconds = 6.0
    start_time = time.time()

    leds.reset()
    game_utils.leds_switch_on_with_color(player=player, color=(0, 255, 0))

    while time.time() - start_time < total_wait_seconds:
        relevant_tags = []
        # Request a fresh snapshot (synchronous scan) and flatten nested entries.
        current_tags = rfidreaders.get_tags_snapshot(True)
        flat_items = []
        if current_tags:
            for entry in current_tags:
                if entry is None:
                    continue
                if isinstance(entry, (list, tuple)):
                    for it in entry:
                        if it is not None and not it.rfid_type == "numeric":
                            continue
                        flat_items.append(it)
                else:
                    if not it.rfid_type == "numeric":
                        continue
                    flat_items.append(entry)

        # Snapshot already contains RFIDTag objects (or None). Use them directly.
        for item in flat_items:
            if isinstance(item, RFIDTag):
                relevant_tags.append(item)

        for tag in relevant_tags:
            if tag.name is not None and tag.name == expected_value.name:
                game_utils.announce(27)
                return True

        time.sleep(0.3)
    # Wrong answer
    game_utils.announce(26)
    # your solution is
    game_utils.announce(268)

    found_numbers = set()

    for entry in rfidreaders.get_tags_snapshot(True):
        if entry is None:
            continue
        if isinstance(entry, (list, tuple)):
            for it in entry:
                if it is not None and not it.rfid_type == "numeric":
                    continue
                found_numbers.add(it)
            continue
        if entry is not None:
            found_numbers.add(entry)

    if len(found_numbers) == 0:
        game_utils.announce(191)

    for tag in set(found_numbers):
        # for each numeric tag, say number
        game_utils.announce(90 + int(tag.name))

    return False


if __name__ == "__main__":
    rfidreaders.init()
    start()
