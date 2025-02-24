#!/usr/bin/env python3
# -*- coding: UTF8 -*-
import pdb
import subprocess
import time
import os
import digitalio
import board
from rfidreaders import currently_reading
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)

# Read volume settings
HEADPHONES_VOLUME = int(os.getenv('HEADPHONES_VOLUME', '5'))
MIC_VOLUME = int(os.getenv('MIC_VOLUME', '95'))
STORY_VOLUME = int(os.getenv('STORY_VOLUME', '2'))
STORY_VOLUME_FLOAT = float(STORY_VOLUME)

# Create 'logs' directory if it doesn't exist
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler(logs_dir / 'audio.log')
file_handler.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Path to the data directory
data_path = Path('./data')

# SD pin of I2S amp, GPIO6
# Default: switched on (3.3V), only switch off (0V) for recording (to avoid clicking)
# amp_sd = digitalio.DigitalInOut(board.D6)
# amp_sd.direction = digitalio.Direction.OUTPUT

def init():
    # Set environment variable for sox recording
    logger.info("Audio driver set to 'alsa' for sox recording.")

def wait_for_reader():
    # Wait for RFID reader reading pause to avoid undervoltage when amp and reader start simultaneously
    while True:
        if not currently_reading:
            break
        time.sleep(0.01)
    logger.debug("Waited for RFID reader to be ready.")

def play_full(folder, audiofile):
    # Blocking play, mostly for TTS
    wait_for_reader()
    SPEAKER_VOLUME = int(os.getenv('SPEAKER_VOLUME', '10'))

    file_path = data_path / folder / f"{audiofile:03d}.mp3"
    logger.info(f"Playing full audio file: {file_path}")

    try:
        waitingtime_output = subprocess.run(['soxi', '-D', str(file_path)], stdout=subprocess.PIPE, check=False)
        waitingtime = float(waitingtime_output.stdout.decode('utf-8').strip()) + 0.2
        execute_play = f"play {file_path} vol {SPEAKER_VOLUME / 100} 2>/dev/null"
        logger.info(execute_play)
        subprocess.Popen(execute_play, shell=True, stdout=None, stderr=None)
        logger.debug(f"Waiting time for audio file {file_path}: {waitingtime} seconds")
        time.sleep(waitingtime)
    except Exception as e:
        logger.error(f"Error playing audio file {file_path}: {e}")

def play_file(folder, audiofile):
    # Non-blocking play for sounds in /data and subfolders
    wait_for_reader()
    load_dotenv(override=True)
    SPEAKER_VOLUME = int(os.getenv('SPEAKER_VOLUME', '10'))

    file_path = data_path / folder / audiofile
    waitingtime_output = subprocess.run(['soxi', '-D', str(file_path)], stdout=subprocess.PIPE, check=False)
    waitingtime = float(waitingtime_output.stdout.decode('utf-8').strip()) + 0.2
    logger.info(f"Playing audio file: {file_path}")
    logger.info(f"SpeakerVol: {SPEAKER_VOLUME / 100}")
    subprocess.Popen(f"play {file_path} vol {SPEAKER_VOLUME / 100} 2>/dev/null", shell=True, stdout=None, stderr=None)
    time.sleep(waitingtime)

def play_story(figure_id):
    # Non-blocking play
    wait_for_reader()

    file_path = data_path / 'figures' / figure_id.rfid_tag / f"{figure_id.rfid_tag}.mp3"
    logger.info(f"Playing story for figure: {figure_id.rfid_tag}")
    # Increase volume by STORY_VOLUME_FLOAT for stories
    subprocess.Popen(f"play -v{STORY_VOLUME_FLOAT} {file_path} 2>/dev/null", shell=True, stdout=None, stderr=None)

def kill_sounds():
    logger.info("Stopping all sounds.")
    subprocess.Popen("killall play", shell=True, stdout=None, stderr=None)

def file_is_playing(audiofile):
    output = subprocess.run(['ps', 'ax'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    is_playing = audiofile in output
    logger.debug(f"File {audiofile} is playing: {is_playing}")
    return is_playing

def record_story(figure):
    # Switch off amp
    # global amp_sd
    # amp_sd.value = False
    logger.info(f"Recording story for figure: {figure}. Amplifier switched off.")

    figure_dir = data_path / 'figures' / figure.rfid_tag
    figure_dir.mkdir(parents=True, exist_ok=True)
    file_path = figure_dir / f"{figure.rfid_tag}.mp3"

    subprocess.Popen(f"AUDIODEV=plughw:1,0 rec -c 1 -r 44100 -b 16 --encoding signed-integer {file_path}", shell=True, stdout=None, stderr=None)
    logger.info(f"Started recording to {file_path}")

def stop_recording(figure_id):
    subprocess.Popen("killall rec", shell=True, stdout=None, stderr=None)
    logger.info("Stopped recording.")

    # global amp_sd

    # Switch on amp
    # amp_sd.value = True
    # logger.info("Amplifier switched on.")

    figure_dir = data_path / 'figures' / figure_id.rfid_tag
    mp3_file = figure_dir / f"{figure_id.rfid_tag}.mp3"

    # If file exists
    if mp3_file.is_file():
        # pdb.set_trace()
        # If file is smaller than 50kB, delete it
        if mp3_file.stat().st_size < 50000:
            mp3_file.unlink()
            logger.warning(f"Deleted small/incomplete recording: {mp3_file}")

            files_in_dir = list(figure_dir.iterdir())

            # If directory is empty
            if not files_in_dir:
                # Delete the folder
                figure_dir.rmdir()
                logger.info(f"Deleted empty figure directory: {figure_dir}")
            else:
                # Rename the latest file back to figure_id.mp3
                sorted_files = sorted(files_in_dir, key=lambda x: x.stat().st_mtime, reverse=True)
                latest_file = sorted_files[0]
                latest_file.rename(mp3_file)
                logger.info(f"Renamed latest file {latest_file} to {mp3_file}")

            return True
    else:
        # pdb.set_trace()
        files_in_dir = list(figure_dir.iterdir())

        if not files_in_dir:
            # Delete the folder
            figure_dir.rmdir()
            logger.info(f"Deleted empty figure directory: {figure_dir}")
        else:
            # Rename the latest file back to figure_id.mp3
            sorted_files = sorted(files_in_dir, key=lambda x: x.stat().st_mtime, reverse=True)
            latest_file = sorted_files[0]
            latest_file.rename(mp3_file)
            logger.info(f"Renamed latest file {latest_file} to {mp3_file}")

        return True

def espeaker(words):
    wait_for_reader()
    load_dotenv(dotenv_path, override=True)
    SPEAKER_VOLUME = int(os.getenv('SPEAKER_VOLUME', '10'))

    logger.info(f"Speaking words: {words}")

    # -v language, -p pitch, -g word gap, -s speed, -a amplitude (volume)
    execute_espeak = f"espeak -v de+f2 -p 30 -g 12 -s 170 -a {SPEAKER_VOLUME} --stdout \"{words}\" | aplay -D 'default'"
    os.system(execute_espeak)
    logger.info(execute_espeak)
    logger.debug(f"Executed eSpeak command for words: {words}")