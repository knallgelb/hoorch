import pytest
from unittest.mock import MagicMock, call, patch
from conftest import filter_calls
import os

from games.game_utils import play_rounds  # Angenommen, die Funktion ist in games.game_utils

@patch("audio.espeaker")  # Mock espeaker function in the "audio" module
def test_espeaker_call(mock_espeaker, players):
    num_rounds = 3  # Change this to test different numbers of rounds

    # Act: Run play_rounds
    play_rounds(players=players, num_rounds=num_rounds, player_action=lambda _: True)

    # Dynamically generate expected calls
    expected_calls = []
    for round_num in range(1, num_rounds + 1):
        expected_calls.append(call(f"Starte Runde {round_num}..."))
        for player in players:
            expected_calls.append(call(f"Jetzt ist {player.name} an der Reihe."))
        expected_calls.append(call(f"Runde {round_num} abgeschlossen."))

    # Remove unwanted calls like call.__str__()
    filtered_calls = filter_calls(mock_espeaker)

    # Assert the filtered calls match the dynamically generated expected calls
    assert filtered_calls == expected_calls

def test_scores(players):
    num_rounds = 3
    score_list: dict = play_rounds(players=players, num_rounds=num_rounds, player_action=lambda _: True)

    for x in score_list.values():
        assert x == num_rounds