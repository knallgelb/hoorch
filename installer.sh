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
sudo apt install -y python3-venv

# Set up the virtual environment
echo "Setting up Python virtual environment"
python3 -m venv venv --system-site-packages
. venv/bin/activate

# Install Python dependencies inside the virtual environment
echo "Installing Python dependencies"
pip install --upgrade pip setuptools
pip install flask werkzeug ndeflib RPI.GPIO adafruit-circuitpython-pn532 board pygame rpi_ws281x adafruit-circuitpython-neopixel adafruit-circuitpython-debouncer
pip install --force-reinstall adafruit-blinka
pip install --upgrade adafruit-python-shell

# Enable SPI
sudo sed -i "s/#dtparam=spi=on/dtparam=spi=on/g" "/boot/firmware/config.txt"

# i2s microphone
sudo apt install dkms raspberrypi-kernel-headers -y
wget https://github.com/opencardev/snd-i2s_rpi/releases/download/v0.0.2/snd-i2s-rpi-dkms_0.0.2_all.deb
sudo dpkg -i snd-i2s-rpi-dkms_0.0.2_all.deb
sudo modprobe snd-i2s_rpi rpi_platform_generation=0

# i2s amplifier configuration
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

# Setup MAX98357
sudo sed -i 's/^\(dtparam=audio=on\)/#\1/' "/boot/firmware/config.txt"

# Add overlays if not already present
if ! grep -Fxq "dtoverlay=hifiberry-dac" /boot/firmware/config.txt; then
  echo "dtoverlay=hifiberry-dac" | sudo tee -a /boot/firmware/config.txt
fi

if ! grep -Fxq "dtoverlay=i2s-mmap" /boot/firmware/config.txt; then
  echo "dtoverlay=i2s-mmap" | sudo tee -a /boot/firmware/config.txt
fi

# Disable Bluetooth to save power
if ! grep -Fxq "dtoverlay=pi3-disable-bt" /boot/firmware/config.txt; then
  echo "dtoverlay=pi3-disable-bt" | sudo tee -a /boot/firmware/config.txt
fi

sudo systemctl disable bluetooth.service

# Disable the rainbow splash screen
if ! grep -Fxq "disable_splash=1" /boot/firmware/config.txt; then
  echo "disable_splash=1" | sudo tee -a /boot/firmware/config.txt
fi

# Copy HOORCH files
echo "Copying HOORCH files"
sudo cp *.service /etc/systemd/system
sudo cp gpio-shutoff.sh /lib/systemd/system-shutdown/
sudo chmod +x /lib/systemd/system-shutdown/gpio-shutoff.sh

# Enable and start HOORCH services
sudo systemctl enable hoorch*.service
sudo systemctl start hoorch*.service

# Install log2ram
echo "Installing log2ram"
echo "deb [signed-by=/usr/share/keyrings/azlux-archive-keyring.gpg] http://packages.azlux.fr/debian/ bookworm main" | sudo tee /etc/apt/sources.list.d/azlux.list
wget -O - https://azlux.fr/repo.gpg.key | gpg --dearmor | sudo tee /usr/share/keyrings/azlux-archive-keyring.gpg > /dev/null
sudo apt update
sudo apt install log2ram

# Disable swapping
sudo systemctl disable dphys-swapfile.service

# Update log2ram configuration
sudo sed -i 's/SIZE=40M/SIZE=100M/g' /etc/log2ram.conf

# Restart networking service
sudo systemctl restart networking

# Install comitup - wifi setup
sudo apt update
sudo apt install comitup -y
sudo mv /etc/network/interfaces /etc/network/interfaces.bak
sudo mv /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.confbak

# Disable unnecessary services
sudo systemctl mask dnsmasq.service
sudo systemctl mask systemd-resolved.service
sudo systemctl mask dhcpd.service
sudo systemctl mask dhcpcd.service
sudo systemctl mask wpa-supplicant.service
sudo systemctl enable NetworkManager.service

# Update comitup configuration
sudo sed -i "s/# ap_name: comitup-<nnn>/ap_name: hoorch-<nnn>/g" "/etc/comitup.conf"
sudo sed -i "s/# web_service:/web_service: hoorch-webserver.service/g" "/etc/comitup.conf"

echo "Installation complete, rebooting now"
sudo reboot
