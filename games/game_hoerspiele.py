#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import time
import subprocess
import rfidreaders
import leds
import audio

from logger_util import get_logger

logger = get_logger(__name__, "logs/game_hoerspiele.log")

def start(folder, audiofile):

    leds.reset()  # reset leds
    #swith on led where tag is placed
    leds.switch_on_with_color(rfidreaders.tags.index(audiofile), (0, 255, 0))

    audio.play_file(folder, f"{audiofile}.mp3")
    waitingtime = time.time() + float(subprocess.run(
                    ['soxi', '-D', f'./data/{folder}/{audiofile}.mp3'], stdout=subprocess.PIPE, check=False).stdout.decode('utf-8')) + 10
    print(waitingtime)

    while True:
        if audiofile not in rfidreaders.tags or waitingtime < time.time():
            audio.kill_sounds()
            break

    leds.switch_all_on_with_color((0,0,255))
    time.sleep(0.1)
    leds.reset()
