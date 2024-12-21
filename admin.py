#!/usr/bin/env python3
# -*- coding: UTF8 -*-
import time
import os
import subprocess
import datetime
import re
import dbus
import rfidreaders
import audio
from i18n import Translator


def main():
    translator = Translator(locale='de')  # Initialisiere Übersetzer mit deutschem Locale
    breaker = False

    # 2 minutes until exit if no user interaction occurs
    admin_exit_counter = time.time() + 120

    audio.espeaker(translator.translate("admin.admin_menu"))

    subprocess.run(['git', 'remote', 'update'], stdout=subprocess.PIPE, check=False)
    git_status = subprocess.run(['git', 'status', '-uno'], stdout=subprocess.PIPE, check=False).stdout.decode('utf-8')
    if "behind" in git_status:
        audio.espeaker(translator.translate("admin.update_available"))

    audio.espeaker(translator.translate("admin.use_number_cards"))
    audio.espeaker(translator.translate("admin.update_software"))
    audio.espeaker(translator.translate("admin.wifi_configuration"))
    audio.espeaker(translator.translate("admin.delete_figures"))
    audio.espeaker(translator.translate("admin.archive_stories"))
    audio.espeaker(translator.translate("admin.end_tag"))

    while admin_exit_counter > time.time():
        for tag_name in rfidreaders.tags:
            if tag_name is not None and re.search("^[A-z]*[0-9]$", tag_name):
                op = int(tag_name[-1])  # 1 from Hahn1

                if op == 1:
                    git()
                    admin_exit_counter = time.time() + 120
                elif op == 2:
                    wifi()
                    admin_exit_counter = time.time() + 120
                elif op == 3:
                    new_set()
                elif op == 4:
                    archive_stories()
                    admin_exit_counter = time.time() + 120
            elif tag_name == "ENDE":
                breaker = True
                break

        if breaker:
            break

    audio.espeaker(translator.translate("admin.admin_menu_end"))


def archive_stories():
    translator = Translator(locale='de')
    figure_dir = "./data/figures/"
    print("archive stories")
    recordings_list = os.listdir(figure_dir)

    for folder in recordings_list:
        if os.path.isdir(figure_dir + folder):
            if folder + ".mp3" in os.listdir(figure_dir + folder + "/"):
                now = datetime.datetime.now()
                os.rename(f"{figure_dir}{folder}/{folder}.mp3",
                          f"{figure_dir}{folder}/{folder}-{now:%Y-%m-%d-%H-%M}.mp3")
                print(folder + ".mp3 put into archive")
            else:
                print(folder + "-stories already in archive")

    audio.espeaker(translator.translate("admin.archive_complete"))


def new_set():
    translator = Translator(locale='de')
    print("delete figure_db.txt, restart hoorch")
    os.rename("figure_db.txt", "figure_db-{0}.txt".format(
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")))
    audio.espeaker(translator.translate("admin.db_deleted"))
    os.system("reboot")



def git():
    translator = Translator(locale='de')
    print("git update, restart hoorch")
    bus = dbus.SystemBus()
    # get comitup dbus object - https://davesteele.github.io/comitup/man/comitup.8.html
    nm = bus.get_object('com.github.davesteele.comitup',
                        '/com/github/davesteele/comitup')

    tpl = nm.state()

    # state is either 'HOTSPOT', 'CONNECTING', or 'CONNECTED'
    state = str(tpl[0])

    if state == "HOTSPOT":
        audio.espeaker(translator.translate("admin.wifi_disconnected"))
        audio.espeaker(translator.translate("admin.open_wifi_config"))

    elif state == "CONNECTED":
        audio.espeaker(translator.translate("admin.updating"))
        # Any local files that are not tracked by Git will not be affected:
        # git fetch downloads the latest from remote without trying to merge or rebase anything.
        # git reset resets the master branch to what you just fetched.
        # The --hard option changes all the files in your working tree to match the files in origin/master.
        subprocess.run(['git', 'fetch', '--all'], stdout=subprocess.PIPE, check=False)
        # subprocess.run(['git', 'branch', 'backup-master'], stdout=subprocess.PIPE)
        subprocess.run(['git', 'reset', '--hard', 'origin/master'], stdout=subprocess.PIPE, check=False)

        audio.espeaker(translator.translate("admin.update_complete"))
        os.system("reboot")


def wifi():
    translator = Translator(locale='de')
    print("wifi config")
    rfkill_output = subprocess.run(
        ['rfkill', 'list', 'wifi'], stdout=subprocess.PIPE, check=False).stdout.decode('utf-8')

    if "yes" in rfkill_output:
        # wifi blocked / off
        audio.espeaker(translator.translate("admin.wifi_off"))
        audio.espeaker(translator.translate("admin.wifi_turn_on"))

        while True:
            if "JA" in rfidreaders.tags:
                audio.espeaker(translator.translate("admin.wifi_starting"))
                os.system("rfkill unblock wifi")

                while not subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE, check=False).stdout.decode(
                        'utf-8'):
                    time.sleep(2)

                output = subprocess.run(
                    ['hostname', '-I'], stdout=subprocess.PIPE, check=False).stdout.decode('utf-8')
                ip_adress = output.split(" ", 1)
                print(ip_adress)

                audio.espeaker(translator.translate("admin.wifi_on"))
                audio.espeaker(translator.translate("admin.ip_address"))
                audio.espeaker(ip_adress[0])

                break

            elif "NEIN" in rfidreaders.tags or "ENDE" in rfidreaders.tags:
                break
    else:
        # wifi on

        bus = dbus.SystemBus()
        # get comitup dbus object - https://davesteele.github.io/comitup/man/comitup.8.html
        nm = bus.get_object('com.github.davesteele.comitup',
                            '/com/github/davesteele/comitup')

        tpl = nm.state()

        # state is either 'HOTSPOT', 'CONNECTING', or 'CONNECTED'
        state = str(tpl[0])

        # connection - ssid name for the current connection on the wifi device
        connection = tpl[1]

        # accesspoint hostname
        info = nm.get_info()
        hostname = str(info["apname"])

        if state == "HOTSPOT":
            audio.espeaker(translator.translate("admin.no_internet"))
            audio.espeaker(translator.translate("admin.hotspot_instructions", hostname=hostname))
            audio.espeaker(translator.translate("admin.set_wifi_password"))

        # connected to a wifi
        elif state == "CONNECTED":
            audio.espeaker(translator.translate("admin.wifi_connected", connection=connection))
            output = subprocess.run(
                ['hostname', '-I'], stdout=subprocess.PIPE, check=False).stdout.decode('utf-8')
            ip_adress = output.split(" ", 1)
            print(ip_adress)

            # say adress twice
            for i in range(2):
                audio.espeaker(translator.translate("admin.ip_address"))
                audio.espeaker(ip_adress[0])
            time.sleep(2)

            audio.espeaker(translator.translate("admin.should_turn_off"))

            while True:
                if "JA" in rfidreaders.tags:
                    # os.system("rfkill block wifi")
                    audio.espeaker(translator.translate("admin.wifi_stop"))
                    break

                elif "NEIN" in rfidreaders.tags or "ENDE" in rfidreaders.tags:
                    break

        # connecting
        else:
            audio.espeaker(
                translator.translate("internet_wait"))
            time.sleep(2)

    audio.espeaker(translator.translate("wifi_config_done"))
