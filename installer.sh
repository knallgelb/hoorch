#!/bin/sh
# installer.sh will install the necessary packages and config files for HOORCH
# Enter sudo-mode: sudo -i

# Install packages
echo "apt updating system. this may take some time..."
sudo apt update -y
sudo apt upgrade -y

echo "installing packages"
sudo apt install -y python3-full
sudo apt install -y python3-pip
sudo apt install -y sox
sudo apt install -y libsox-fmt-mp3
sudo apt install -y espeak
sudo apt install -y libsdl2-mixer-2.0-0
sudo apt install -y git
sudo apt install -y vim

python3 -m venv venv
source venv/bin/activate

pip3 install --upgrade setuptools
pip3 install flask werkzeug ndeflib RPI.GPIO adafruit-circuitpython-pn532 board pygame rpi_ws281x adafruit-circuitpython-neopixel adafruit-circuitpython-debouncer
python3 -m pip install --force-reinstall adafruit-blinka
pip3 install --upgrade adafruit-python-shell

#enable SPI
sudo sed -i "s/#dtparam=spi=on/dtparam=spi=on/g" "/boot/firmware/config.txt"

# i2s microphone
#wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/i2smic.py
#sudo python3 i2smic.py
sudo apt install dkms raspberrypi-kernel-headers -y
wget https://github.com/opencardev/snd-i2s_rpi/releases/download/v0.0.2/snd-i2s-rpi-dkms_0.0.2_all.deb
sudo dpkg -i snd-i2s-rpi-dkms_0.0.2_all.deb
sudo modprobe snd-i2s_rpi rpi_platform_generation=0

# i2s microphone - add volume control
# bash -c 'cat .asoundrc >> /etc/asound.conf'

# i2s amplifier
# curl -sS https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/i2samp.sh | bash
sudo tee /etc/asound.conf > /dev/null << EOF
pcm.speakerbonnet {
   type hw card 0
}

pcm.dmixer {
   type dmix
   ipc_key 1024
   ipc_perm 0666
   slave {
     pcm "speakerbonnet"
     period_time 0
     period_size 1024
     buffer_size 8192
     rate 44100
     channels 2
   }
}

ctl.dmixer {
   type hw card 0
}

pcm.softvol {
   type softvol
   slave.pcm "dmixer"
   control.name "PCM"
   control.card 0
}

ctl.softvol {
   type hw card 0
}

pcm.!default {
   type plug
   slave.pcm "softvol"
}
EOF

sudo sed -i "s/#dtparam=spi=on/dtparam=spi=on/g" "/boot/firmware/config.txt"

# Setup MAX98357
sudo sed -i 's/^\(dtparam=audio=on\)/#\1/' "/boot/firmware/config.txt"

# Überprüfen, ob dtoverlay=hifiberry-dac bereits vorhanden ist, sonst hinzufügen
if ! grep -Fxq "dtoverlay=hifiberry-dac" /boot/firmware/config.txt; then
  echo "dtoverlay=hifiberry-dac" | sudo tee -a /boot/firmware/config.txt
fi

# Überprüfen, ob dtoverlay=i2s-mmap bereits vorhanden ist, sonst hinzufügen
if ! grep -Fxq "dtoverlay=i2s-mmap" /boot/firmware/config.txt; then
  echo "dtoverlay=i2s-mmap" | sudo tee -a /boot/firmware/config.txt
fi


#disable hdmi (enable: -p) - to safe power - i need hdmi connection 
#/opt/vc/bin/tvservice -o

# Disable the ACT LED.
#sh -c "echo 'dtparam=act_led_trigger=none' >> /boot/config.txt"
#sh -c "echo 'dtparam=act_led_activelow=off' >> /boot/config.txt"

# Disable the PWR LED.
#sh -c "echo 'dtparam=pwr_led_trigger=none' >> /boot/config.txt"
#sh -c "echo 'dtparam=pwr_led_activelow=off' >> /boot/config.txt"

#disable bluetooth - to safe power
# Überprüfen, ob dtoverlay=i2s-mmap bereits vorhanden ist, sonst hinzufügen
if ! grep -Fxq "dtoverlay=pi3-disable-bt" /boot/firmware/config.txt; then
  echo "dtoverlay=pi3-disable-bt" | sudo tee -a /boot/firmware/config.txt
fi

sudo systemctl disable bluetooth.service

# Disable the rainbow splash screen
if ! grep -Fxq "disable_splash=1" /boot/firmware/config.txt; then
  echo "disable_splash=1" | sudo tee -a /boot/firmware/config.txt
fi

# Set the bootloader delay to 0 seconds. The default is 1s if not specified.
#sh -c "echo 'boot_delay=0' >> /boot/config.txt"

echo "copying HOORCH files"

#copy service-files to /etc/systemd/system
cp *.service /etc/systemd/system

#copy gpio shutoff script for OnOff Shim and make it executeable
cp gpio-shutoff.sh /lib/systemd/system-shutdown/
chmod +x /lib/systemd/system-shutdown/gpio-shutoff.sh

#enable and start the services
#systemctl enable hoorch*.service
#systemctl start hoorch*.service 

#will be started manually by user, see installation manual


#install log2ram
echo "deb [signed-by=/usr/share/keyrings/azlux-archive-keyring.gpg] http://packages.azlux.fr/debian/ bookworm main" | sudo tee /etc/apt/sources.list.d/azlux.list
wget -O - https://azlux.fr/repo.gpg.key | gpg --dearmor | sudo tee /usr/share/keyrings/azlux-archive-keyring.gpg > /dev/null
sudo apt update
sudo apt install log2ram

#disable swapping
sudo systemctl disable dphys-swapfile.service

#change SIZE=40M to SIZE=100M /etc/log2ram.conf
sudo sed -i 's/SIZE=40M/SIZE=100M/g' /etc/log2ram.conf

#start/restart networking service (NetworkManager)
sudo systemctl restart networking

#install comitup - wifi:
#1 install package .deb
sudo apt update
# apt install comitup comitup-watch -y
sudo apt install comitup -y

#2: Allow NetworkManager to manage the wifi interfaces by removing references to them from /etc/network/interfaces.
sudo mv /etc/network/interfaces /etc/network/interfaces.bak

#3: Rename  /etc/wpa_supplicant/wpa_supplicant.conf.
sudo mv /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.confbak

#4: The systemd.resolved service should be disabled and masked to avoid contention for providing DNS service.
sudo systemctl mask dnsmasq.service
sudo systemctl mask systemd-resolved.service
sudo systemctl mask dhcpd.service
sudo systemctl mask dhcpcd.service
sudo systemctl mask wpa-supplicant.service
sudo systemctl enable NetworkManager.service

#5: #rename the comitup-wifi-name to hoorch-<nn> - https://davesteele.github.io/comitup/man/comitup-conf.5.html
sudo sed -i "s/# ap_name: comitup-<nnn>/ap_name: hoorch-<nnn>/g" "/etc/comitup.conf"

#6 #add web_service to be started in CONNECTED stage of compitup
#web_service: This defines a user web service to be controlled by comitup. This service will be disabled in the HOTSPOT state in preference of the comitup web service, and will be enabled in the CONNECTED state. This should be the name of the systemd web service, such as apache2.service or nginx.service. This defaults to a null string, meaning no service is controlled
sudo sed -i "s/# web_service:/web_service: hoorch-webserver.service/g" "/etc/comitup.conf"

echo "Installation complete, rebooting now"
sudo reboot
