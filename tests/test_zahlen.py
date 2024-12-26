from unittest.mock import patch
import pytest

from games.game_zahlen import player_action


def test_player_action_should_return_true_when_expected_value_is_found(
        players,
        mock_rfidreaders,
        mock_file_lib
):
    chosen_tag = mock_file_lib.animal_numbers_db[0]

    with patch("games.game_zahlen.random.choice", return_value=chosen_tag), \
            patch("games.game_zahlen.sleep", return_value=None) as mock_sleep, \
            patch("games.game_zahlen.announce_score") as mock_announce_score:
        result = player_action(
            player=players[0],  # Nur exemplarisch
            rfidreaders=mock_rfidreaders,  # Unser Fixture: mock_rfidreaders
            file_lib=mock_file_lib,  # Unser Fixture: mock_file_lib
            rfid_position=[1, 3]  # Z. B. Positionen 1 und 3 abfragen
        )

        assert result is True, "player_action sollte True zurückgeben, wenn der Tag gefunden wird."

        mock_announce_score.assert_called_once_with(chosen_tag.number)


def test_player_action_should_return_false_when_expected_value_is_not_found(
        players,
        mock_rfidreaders,
        mock_file_lib
):
    chosen_tag = mock_file_lib.animal_numbers_db[1]

    with patch("games.game_zahlen.random.choice", return_value=chosen_tag), \
            patch("games.game_zahlen.sleep", return_value=None) as mock_sleep, \
            patch("games.game_zahlen.announce_score") as mock_announce_score:
        result = player_action(
            player=players[0],
            rfidreaders=mock_rfidreaders,
            file_lib=mock_file_lib,
            rfid_position=[0]  # Nur Position 0 checken
        )

        assert result is False, "player_action sollte False zurückgeben, wenn Tag nicht gefunden wird."

        mock_announce_score.assert_called_once_with(chosen_tag.number)
