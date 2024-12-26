import pytest
from unittest import mock

from games import game_utils


@mock.patch("audio.espeaker")
def test_announce_score(espeaker, players):
    score_players = {player: i for i, player in enumerate(players)}

    assert len(score_players.items()) == 3

    score_calls = [mock.call("Ritter hat 0 richtige Antworten."), mock.call("Königin hat 1 richtige Antworten."),
                   mock.call("Frau hat 2 richtige Antworten.")]

    game_utils.announce_score(score_players)

    assert espeaker.call_args_list == score_calls
