#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import copy
import random
import time

import crud
import file_lib
import leds
import models
import rfidreaders
from logger_util import get_logger

from .game_utils import (
    announce,
    blink_led,
    check_end_tag,
    filter_players_on_fields,
    get_solution_from_tags,
    wait_for_figure_placement,
)

logger = get_logger(__name__, "logs/game_einmaleins.log")


def start():
    defined_figures = file_lib.get_tags_by_type("figures")
    all_tags = file_lib.load_all_tags()

    announce(85)  # "We are now practicing multiplication."
    leds.reset()

    # Prompt players
    announce(86)  # "Place your figures..."
    wait_for_figure_placement((1, 3, 5))

    players = filter_players_on_fields(
        copy.deepcopy(rfidreaders.tags), [1, 3, 5], defined_figures
    )
    figure_count = sum(p is not None for p in players)

    # Log Usage
    u = models.Usage(game="einmaleins", players=figure_count)
    crud.add_game_entry(usage=u)

    if figure_count == 0:
        announce(59)  # "No figures placed."
        leds.switch_all_on_with_color((0, 0, 255))
        time.sleep(0.2)
        leds.reset()
        return

    announce(5 + figure_count)  # "x figures are playing"

    rounds = 3
    announce(20 + rounds)  # "We will play x rounds"
    points = [0] * len(players)

    is_first_round = True
    for _ in range(rounds):
        for i, player in enumerate(players):
            if player is None:
                continue
            leds_position = i + 1
            leds.reset()
            leds.switch_on_with_color(leds_position, (0, 255, 0))

            if is_first_round:
                is_first_round = False
                announce(12 + i)  # "The figure on field x starts"
                announce(89)  # "Place the tens digit..."
            elif figure_count == 1:
                announce(67)  # "It's your turn again"
            else:
                announce(48 + i)  # "The next figure on field x"

            # Generate and announce math problem
            num1, num2 = random.randint(1, 9), random.randint(1, 9)
            solution = num1 * num2

            announce(87)  # "How much is..."
            announce(90 + num1)  # first number
            announce(88)  # "times"
            announce(90 + num2)  # second number

            blink_led(leds_position, times=6, on_time=1.0, off_time=1.0)

            # Check solution
            player_solution = get_solution_from_tags(i, player)
            if int(player_solution) == solution:
                announce(27)
                leds.switch_on_with_color(leds_position, (50, 255, 50))
                points[i] += 1
            else:
                announce(26)
                leds.switch_on_with_color(leds_position, (255, 0, 0))
            time.sleep(0.3)

    # Announce scores
    announce(80)  # "I will now announce the scores"
    for i, player in enumerate(players):
        leds_position = i + 1
        if player is not None:
            leds.reset()
            leds.switch_on_with_color(leds_position, (30, 144, 255))
            announce(74 + i)  # "Figure on field x"
            announce(68 + points[i])  # "x points"
            time.sleep(1)

    leds.switch_all_on_with_color((0, 0, 255))
    time.sleep(0.2)
    leds.reset()
