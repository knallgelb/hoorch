#!/usr/bin/env python3
# -*- coding: UTF8 -*-
"""
Audio utility module for HOORCH.

Provides functions to play audio files (blocking and non-blocking), determine
audio durations using external tools (soxi and ffprobe fallback), record and
process story recordings, and helper utilities.

This file is designed to be robust when `soxi -D` outputs non-trivial text or
when the duration might appear on stderr. It attempts soxi first and falls back
to ffprobe. If both fail, a sensible default wait time is used.
"""

import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

import env_tools

# Load environment variables from .env file (override defaults)
dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)

# Read volume settings
HEADPHONES_VOLUME = int(os.getenv("HEADPHONES_VOLUME", "5"))
MIC_VOLUME = int(os.getenv("MIC_VOLUME", "95"))
STORY_VOLUME = int(os.getenv("STORY_VOLUME", "2"))
STORY_VOLUME_FLOAT = float(STORY_VOLUME)
# Note: environment variable name kept as in existing codebase (may be misspelled)
WAITTIME_OFFSET = float(os.getenv("WATINGTIME_OFFSET", "0.5"))

# Create 'logs' directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler(logs_dir / "audio.log")
file_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Attach handlers if not already attached (avoid duplicate handlers on reload)
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
else:
    # Ensure our handlers are present (idempotent)
    found_console = any(
        isinstance(h, logging.StreamHandler) for h in logger.handlers
    )
    found_file = any(
        isinstance(h, logging.FileHandler) for h in logger.handlers
    )
    if not found_console:
        logger.addHandler(console_handler)
    if not found_file:
        logger.addHandler(file_handler)

# Path to the data directory
data_path = Path("./data")


def init():
    """Initialize audio subsystem (placeholder)."""
    logger.info("Audio driver set to 'alsa' for sox recording.")


def wait_for_reader():
    currently_reading = env_tools.str_to_bool(
        os.getenv("CURRENTLY_READING", "True")
    )
    while currently_reading:
        time.sleep(0.01)


def _get_duration_from_soxi_or_ffprobe(file_path: Path) -> Optional[float]:
    """
    Try to determine audio duration using `soxi -D`, fall back to `ffprobe`.

    Returns duration in seconds as float, or None if detection failed.
    """
    try:
        # First attempt: soxi -D
        cp = subprocess.run(
            ["soxi", "-D", str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        stdout = (cp.stdout or "").strip()
        stderr = (cp.stderr or "").strip()
        combined = "\n".join([stdout, stderr]).strip()

        # If stdout is a clean numeric string, try direct conversion
        if stdout:
            try:
                return float(stdout.splitlines()[0].strip())
            except Exception:
                # continue to more robust parsing
                pass

        # Try to find the first numeric token in combined output (handles comma as decimal separator)
        m = re.search(r"(\d+(?:[\.,]\d+)?)", combined)
        if m:
            num = m.group(1).replace(",", ".")
            try:
                return float(num)
            except Exception:
                pass

        # Fallback: ffprobe
        cp2 = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        ffout = (cp2.stdout or "").strip()
        if ffout:
            try:
                return float(ffout.splitlines()[0].strip())
            except Exception:
                m2 = re.search(r"(\d+(?:[\.,]\d+)?)", ffout)
                if m2:
                    return float(m2.group(1).replace(",", "."))

    except Exception as e:
        logger.debug("Duration detection exception for %s: %s", file_path, e)

    logger.error("Could not determine duration for %s", file_path)
    return None


def get_audio_length(folder, audiofile) -> Optional[float]:
    """
    Determine audio length.

    `folder` may be a Path-like relative to data/ or an absolute path starting with 'data'.
    `audiofile` is the filename.
    """
    if not str(folder).startswith("data"):
        file_path = Path(data_path) / folder / audiofile
    else:
        file_path = Path(folder) / audiofile

    return _get_duration_from_soxi_or_ffprobe(file_path)


def play_full(folder, audiofile):
    """
    Blocking play of a numbered TTS file located at data/<folder>/<nnn>.mp3

    `audiofile` expected to be an integer id for the filename formatting.
    """
    load_dotenv(override=True)
    SPEAKER_VOLUME = int(os.getenv("SPEAKER_VOLUME", "10"))

    file_path = data_path / folder / f"{audiofile:03d}.mp3"
    logger.info("Playing full audio file: %s", file_path)

    try:
        duration = get_audio_length(file_path.parent, file_path.name)
        waitingtime = (
            duration if duration is not None else 1.0
        ) + WAITTIME_OFFSET

        cmd = ["play", str(file_path), "vol", str(SPEAKER_VOLUME / 100)]
        logger.info("Executing: %s", " ".join(cmd))
        subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        logger.debug(
            "Waiting time for audio file %s: %s seconds", file_path, waitingtime
        )
        time.sleep(waitingtime)
    except Exception as e:
        logger.error("Error playing audio file %s: %s", file_path, e)


def play_file(
    folder, audiofile: str, return_process: bool = False
) -> Optional[Tuple[subprocess.Popen, float]]:
    """
    Non-blocking play for sounds in data/<folder>/<audiofile>.

    Returns either (process, waitingtime) if return_process=True, or None and sleeps for waitingtime.
    """
    load_dotenv(override=True)
    SPEAKER_VOLUME = int(os.getenv("SPEAKER_VOLUME", "50"))

    file_path = data_path / folder / audiofile
    duration = get_audio_length(file_path.parent, file_path.name)
    waitingtime = (duration if duration is not None else 1.0) + WAITTIME_OFFSET

    logger.info("Playing audio file: %s", file_path)
    logger.info("SpeakerVol: %s", SPEAKER_VOLUME / 100)
    cmd = ["play", str(file_path), "vol", str(SPEAKER_VOLUME / 100)]
    process = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    if return_process:
        return process, waitingtime
    else:
        time.sleep(waitingtime)
        return None


def play_story(figure_id):
    """
    Play a story file for a given figure (non-blocking).

    `figure_id` is expected to have attribute `rfid_tag`.
    """
    load_dotenv(override=True)
    SPEAKER_VOLUME = int(os.getenv("SPEAKER_VOLUME", "50"))

    file_path = (
        data_path / "figures" / figure_id.rfid_tag / f"{figure_id.rfid_tag}.mp3"
    )
    duration = get_audio_length(file_path.parent, file_path.name)
    waitingtime = (duration if duration is not None else 1.0) + WAITTIME_OFFSET

    logger.info("Playing story for figure: %s", figure_id.rfid_tag)
    logger.info("Waiting time: %s", waitingtime)

    cmd = ["play", str(file_path), "vol", str(SPEAKER_VOLUME / 100)]
    process = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(waitingtime)
    return process


def kill_sounds():
    """Stop all playing sounds by killing `play` processes."""
    logger.info("Stopping all sounds.")
    subprocess.Popen("killall play", shell=True, stdout=None, stderr=None)


def file_is_playing(audiofile: str) -> bool:
    """Return True if `audiofile` appears in the current process list."""
    output = subprocess.run(["ps", "ax"], stdout=subprocess.PIPE).stdout.decode(
        "utf-8"
    )
    is_playing = audiofile in output
    logger.debug("File %s is playing: %s", audiofile, is_playing)
    return is_playing


def record_story(figure):
    """Start recording a story into data/figures/<rfid_tag>/<rfid_tag>.mp3 (non-blocking)."""
    logger.info(
        "Recording story for figure: %s. Amplifier switched off.", figure
    )

    figure_dir = data_path / "figures" / figure.rfid_tag
    figure_dir.mkdir(parents=True, exist_ok=True)
    file_path = figure_dir / f"{figure.rfid_tag}.mp3"

    execute_record = f"AUDIODEV=plughw:0,0 rec -c 1 -r 48000 -b 16 --encoding signed-integer {file_path}"
    logger.info("Starting record: %s", execute_record)
    subprocess.Popen(execute_record, shell=True, stdout=None, stderr=None)
    logger.info("Started recording to %s", file_path)


def trim_normalize_clean_audio(
    file_path: Path,
    trim_length: float = 0.2,
    loudness: int = -24,
    bitrate: str = "192k",
) -> None:
    """
    Trim the start of an MP3, apply a highpass filter and loudness normalization,
    and overwrite the original file.
    """
    logger_local = logging.getLogger(__name__)

    trimmed_file = file_path.with_suffix(".trimmed.mp3")
    normalized_file = file_path.with_suffix(".normalized.mp3")

    try:
        # Trim beginning using ffmpeg (fast copy)
        trim_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(trim_length),
            "-i",
            str(file_path),
            "-c",
            "copy",
            str(trimmed_file),
        ]
        subprocess.run(
            trim_cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Apply highpass + loudnorm
        audio_filter = f"highpass=f=80,loudnorm=I={loudness}:TP=-2.0:LRA=11"
        normalize_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(trimmed_file),
            "-filter:a",
            audio_filter,
            "-c:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            str(normalized_file),
        ]
        subprocess.run(
            normalize_cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Replace original
        normalized_file.replace(file_path)
        trimmed_file.unlink(missing_ok=True)

        logger_local.info(
            "Processed audio: %s (trim=%ss, loudness=%s LUFS)",
            file_path,
            trim_length,
            loudness,
        )
    except subprocess.CalledProcessError as e:
        logger_local.error("ffmpeg process failed: %s", e)
    except Exception as e:
        logger_local.error("Error processing %s: %s", file_path, e)


def stop_recording(figure_id):
    """Stop recording (kill rec) and post-process the latest recording for the given figure."""
    subprocess.Popen("killall rec", shell=True, stdout=None, stderr=None)
    logger.info("Stopped recording for figure: %s", figure_id)

    figure_dir = data_path / "figures" / figure_id.rfid_tag
    mp3_file = figure_dir / f"{figure_id.rfid_tag}.mp3"

    # If file exists, process and possibly prune
    if mp3_file.is_file():
        trim_normalize_clean_audio(mp3_file)
        # If file is smaller than 50kB, delete it and handle directory contents
        if mp3_file.stat().st_size < 50000:
            mp3_file.unlink()
            logger.warning("Deleted small/incomplete recording: %s", mp3_file)
            files_in_dir = list(figure_dir.iterdir())

            if not files_in_dir:
                figure_dir.rmdir()
                logger.info("Deleted empty figure directory: %s", figure_dir)
            else:
                sorted_files = sorted(
                    files_in_dir, key=lambda x: x.stat().st_mtime, reverse=True
                )
                latest_file = sorted_files[0]
                latest_file.rename(mp3_file)
                logger.info(
                    "Renamed latest file %s to %s", latest_file, mp3_file
                )
        return True
    else:
        # No final mp3 file present yet; try to pick the latest temporary file
        files_in_dir = list(figure_dir.iterdir()) if figure_dir.exists() else []
        if not files_in_dir:
            if figure_dir.exists():
                figure_dir.rmdir()
                logger.info("Deleted empty figure directory: %s", figure_dir)
            return True
        else:
            sorted_files = sorted(
                files_in_dir, key=lambda x: x.stat().st_mtime, reverse=True
            )
            latest_file = sorted_files[0]
            latest_file.rename(mp3_file)
            logger.info("Renamed latest file %s to %s", latest_file, mp3_file)
            return True


def espeaker(words: str):
    """Speak given words using espeak and aplay (blocking)."""
    load_dotenv(dotenv_path, override=True)
    SPEAKER_VOLUME = int(os.getenv("SPEAKER_VOLUME", "10"))

    logger.info("Speaking words: %s", words)
    execute_espeak = f'espeak -v de+f2 -p 30 -g 12 -s 170 -a {SPEAKER_VOLUME} --stdout "{words}" | aplay -D "default"'
    os.system(execute_espeak)
    logger.debug("Executed eSpeak command for words: %s", words)


def delete_story(figure):
    """Delete stored story file for a figure."""
    figure_dir = data_path / "figures" / figure.rfid_tag
    mp3_file = figure_dir / f"{figure.rfid_tag}.mp3"

    if mp3_file.is_file():
        mp3_file.unlink()
        logger.info("Deleted story file: %s", mp3_file)

        if not any(figure_dir.iterdir()):
            figure_dir.rmdir()
            logger.info("Deleted empty figure directory: %s", figure_dir)
        return True
    else:
        logger.warning("Story file not found for deletion: %s", mp3_file)
        return False
