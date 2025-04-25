#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import random
import copy
import time
import audio
import rfidreaders
import leds
import file_lib
import models
import crud


from .game_utils import (
    check_end_tag,
    announce,
    wait_for_figure_placement,
    filter_players_on_fields,
    blink_led,
    get_solution_from_tags
)

from logger_util import get_logger

logger = get_logger(__name__, "logs/game_einmaleins.log")

def start():
    defined_figures = file_lib.figures_db
    all_tags = file_lib.all_tags

    announce(85)  # "We are now practicing multiplication."
    leds.reset()

    # Prompt players
    announce(86)  # "Place your figures..."
    wait_for_figure_placement((0, 2, 4))

    players = filter_players_on_fields(copy.deepcopy(rfidreaders.tags), [1, 3, 5], defined_figures)
    figure_count = sum(p is not None for p in players)

    # Log Usage
    u = models.Usage(game="einmaleins", players=figure_count)
    crud.add_game_entry(usage=u)

    if figure_count == 0:
        announce(59)  # "No figures placed."
        return

    announce(5 + figure_count)  # "x figures are playing"

    if check_end_tag():
        return

    rounds = 3
    announce(20 + rounds)  # "We will play x rounds"
    points = [0] * len(players)

    if check_end_tag():
        return

    is_first_round = True
    for _ in range(rounds):
        for i, player in enumerate(players):
            if player is None:
                continue

            leds.reset()
            leds.switch_on_with_color(i)

            if is_first_round:
                is_first_round = False
                announce(12 + i)  # "The figure on field x starts"
                announce(89)      # "Place the tens digit..."
            elif figure_count == 1:
                announce(67)      # "It's your turn again"
            else:
                announce(48 + i)  # "The next figure on field x"

            if check_end_tag():
                return

            # Generate and announce math problem
            num1, num2 = random.randint(1, 9), random.randint(1, 9)
            solution = num1 * num2

            announce(87)             # "How much is..."
            announce(90 + num1)      # first number
            announce(88)             # "times"
            announce(90 + num2)      # second number

            if check_end_tag():
                return

            blink_led(i)

            if check_end_tag():
                return

            # Check solution
            player_solution = get_solution_from_tags(i, players)
            announce(27 if player_solution == solution else 26)  # "Correct!" or "Wrong!"
            if player_solution == solution:
                points[i] += 1

            if check_end_tag():
                return

    # Announce scores
    announce(80)  # "I will now announce the scores"
    for i, player in enumerate(players):
        if player is not None:
            leds.reset()
            leds.switch_on_with_color(i)
            announce(74 + i)        # "Figure on field x"
            announce(68 + points[i])# "x points"
            time.sleep(1)

    leds.reset()
