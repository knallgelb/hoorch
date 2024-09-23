#!/usr/bin/env python3
# -*- coding: UTF8 -*-

import subprocess
import time
import os
import digitalio
import board
from rfidreaders import currently_reading

path = "./data/"

# SD pin of i2s amp , GPIO6
# default: switched on (3.3V), only switch off (0V) for recording (to avoid clicking)
amp_sd = digitalio.DigitalInOut(board.D6)
amp_sd.direction = digitalio.Direction.OUTPUT


def init():
    # set environment variable for sox rec
    os.environ['AUDIODRIVER'] = "alsa"

    if is_headphones_connected():
        # set audio output level to 30% when headphones are connected
        os.system("amixer -q sset PCM 30%")
    else:
        # set audio output level to 90% when headphones are not connected
        os.system("amixer -q sset PCM 90%")

    # set mic record level to 95% (92 in alsamixer)
    os.system("amixer -q sset Boost 95%")

    # switch on amp by default
    global amp_sd
    amp_sd.value = True


def is_headphones_connected():
    # Adjust the command to match your system's control name
    status = os.popen("amixer cget name='Headphone Jack' | grep ': values='").read()
    if 'values=on' in status or 'values=1' in status:
        return True
    else:
        return False


def wait_for_reader():
    # wait for rfid reader reading pause to avoid undervoltage when amp and reader start simultaneously
    while True:
        if not currently_reading:
            break
        time.sleep(0.01)


def play_full(folder, audiofile):
    # blocking play, mostly for TTS
    wait_for_reader()

    file_path = path + folder + "/" + "{:03d}".format(audiofile) + ".mp3"
    waitingtime = float(subprocess.run(
        ['soxi', '-D', file_path], stdout=subprocess.PIPE, check=False).stdout.decode('utf-8'))
    subprocess.Popen("play " + file_path + " 2>/dev/null",
                     shell=True, stdout=None, stderr=None)
    time.sleep(waitingtime)


def play_file(folder, audiofile):
    # non-blocking
    # for sounds in /data and subsequent folders (i.e sounds, animal_sounds, TTS/animals_en, hoerspiele, figures)
    wait_for_reader()

    subprocess.Popen(f"play {path}/{folder}/{audiofile}  2>/dev/null", shell=True, stdout=None, stderr=None)
    print("playing file " + str(audiofile))


def play_story(figure_id):
    # non-blocking
    wait_for_reader()

    print("play story of " + str(figure_id))
    # increase volume by -2db for stories as their recording volume is lower
    subprocess.Popen(f"play -v2 {path}figures/{figure_id}/{figure_id}.mp3  2>/dev/null", shell=True, stdout=None,
                     stderr=None)


def kill_sounds():
    subprocess.Popen("killall play", shell=True, stdout=None, stderr=None)


def file_is_playing(audiofile):
    output = subprocess.run(
        ['ps', 'ax'], stdout=subprocess.PIPE).stdout.decode('utf-8')

    if audiofile in output:
        # print("file is playing")
        return True
    else:
        # print("file is not playing")
        return False


def record_story(figure):
    # switching off amp
    global amp_sd
    amp_sd.value = False

    # subprocess.Popen("AUDIODEV=hw:1 rec "+path+"figures/"+figure+"/"+figure+".mp3"+" ", shell=True, stdout=None, stderr=None)

    subprocess.Popen("AUDIODEV=dmic_sv rec -c 1 " + path + "figures/" +
                     figure + "/" + figure + ".mp3", shell=True, stdout=None, stderr=None)

    # trim of the first 0.3 seconds - needed with /dev/zero??
    # subprocess.Popen("sox "+path+"figures/"+figure+"/"+figure+".mp3"+" "+path+"figures/"+figure+"/"+figure+".mp3"+" trim 0.3", shell=True, stdout=None, stderr=None)

    # TODO-maybe normalize, so volume boost at play_story can be removed -needs to be in other function because rec gets aborted
    # for example in the else block of stop_recording!
    # infile = path+"figures/"+folder+"/"+audiofile+".mp3"
    # outfile = path+"figures/"+folder+"/"+audiofile+"_normalized.mp3"
    # subprocess.Popen("sox --norm=-3 "+infile+" "+outfile+" 2>/dev/null",shell=True, stdout=None, stderr=None)
    # sox −−norm=−3 infile outfile


def stop_recording(figure_id):
    subprocess.Popen("killall rec", shell=True, stdout=None, stderr=None)

    global amp_sd

    # switching on amp
    amp_sd.value = True

    figure_dir = path + "figures/" + figure_id

    # if file (koenigin.mp3 i.e.) exists (could not have been saved due to error in rec)
    if os.path.isfile(figure_dir + "/" + figure_id + ".mp3"):
        # if file is smaller than 50kB, delete it
        if os.path.getsize(figure_dir + "/" + figure_id + ".mp3") < 50000:
            os.remove(figure_dir + "/" + figure_id + ".mp3")

            files_in_dir = os.listdir(figure_dir)

            # if directory is empty:
            if not files_in_dir:
                # delete the folder
                os.rmdir(figure_dir)

            # if not empty, meaning there is still one or more files (like koenigin2021-02-01-10-26.mp3)
            else:
                # rename the latest file back to koenigin.mp3 i.e.
                sorted_files = sorted(files_in_dir)
                os.rename(figure_dir + "/" +
                          sorted_files[0], figure_dir + "/" + figure_id + ".mp3")

            return True

    # if file does not exist
    else:
        files_in_dir = os.listdir(figure_dir)

        # if directory is empty (or if there is still a file like koenigin2021-02-01-10-26.mp3)
        if not files_in_dir:
            # delete the folder
            os.rmdir(figure_dir)

        # if not empty, meaning there is still one or more files (like koenigin2021-02-01-10-26.mp3)
        else:
            # rename the latest file back to koenigin.mp3 i.e.
            sorted_files = sorted(files_in_dir)
            os.rename(figure_dir + "/" +
                      sorted_files[0], figure_dir + "/" + figure_id + ".mp3")

        return True


def espeaker(words):
    wait_for_reader()

    # -v language, -p pitch, -g word gap, -s speed, -a amplitude (volume)
    os.system(f"espeak -v de+f2 -p 30 -g 12 -s 170 -a 80 --stdout \"{words}\" | aplay -D 'default'")
    # espeak -v de+f2 -p 30 -g 12 -s 150 --stdout "apfelbaum" | aplay -D 'default'
