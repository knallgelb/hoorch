import pytest
from unittest import mock

import rfidreaders
from games import game_zahlen

def test_zahlen_success(players, numbers):
    # will überprüfen, ob auf dem Index neben dem Player die richtige Zahl (RFID-Tag) steht
    assert game_zahlen.player_action(player_position=0, rfid_position=[1,5], expected_value=numbers[0], tag_list=[numbers[1],numbers[0],numbers[3],numbers[4],numbers[5],numbers[6]]) == True
    assert game_zahlen.player_action(player_position=0, rfid_position=[1,5], expected_value=numbers[0], tag_list=[numbers[1],numbers[5],numbers[6],numbers[4],numbers[5],numbers[0]]) == True

def test_zahlen_failure(players, numbers):
    # will überprüfen, ob auf dem Index neben dem Player die richtige Zahl (RFID-Tag) steht
    assert game_zahlen.player_action(player_position=0, rfid_position=[1,5], expected_value=numbers[0], tag_list=[numbers[1],numbers[1],numbers[0],numbers[4],numbers[5],numbers[6]]) == False
    assert game_zahlen.player_action(player_position=0, rfid_position=[1,5], expected_value=numbers[0], tag_list=[numbers[1],numbers[5],numbers[6],numbers[4],numbers[0],numbers[1]]) == False