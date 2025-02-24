#!/bin/sh
# installer.sh will install the necessary packages and config files for HOORCH
# Enter sudo-mode: sudo -i

# Install packages
echo "apt updating system. this may take some time..."
sudo apt update -y
sudo apt upgrade -y

echo "installing packages"
sudo apt install -y python3-full python3-pip sox libsox-fmt-mp3 espeak \
  libsdl2-mixer-2.0-0 git vim python3-venv

# Neuen Benutzer "pi" mit Passwort "listentothemusic" anlegen und Root-Rechte geben
echo "Erstelle Benutzer pi mit Root-Rechten"
if ! id "pi" >/dev/null 2>&1; then
  sudo useradd -m -s /bin/bash pi
  echo "pi:listentothemusic" | sudo chpasswd
  sudo usermod -aG sudo pi
  echo "pi ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/pi
else
  echo "Benutzer pi existiert bereits."
fi

# Gruppenrechte für GPIO, I2C, SPI und Audio setzen
sudo usermod -a -G gpio,i2c,spi,audio pi

# Klonen des Repositories
echo "Klonen des HOORCH Repositories"
if [ ! -d "/home/pi/hoorch" ]; then
  sudo -u pi git clone https://github.com/knallgelb/hoorch.git /home/pi/hoorch
else
  echo "Repository bereits vorhanden, überspringe Klonen."
fi

# Hier wird /etc/asound.conf mit deinen ALSA-Einstellungen erzeugt/überschrieben:
echo "Erstelle /etc/asound.conf"
sudo tee /etc/asound.conf >/dev/null <<EOF
pcm.!default {
  type hw
  card 0
  device 0
}

ctl.!default {
  type hw
  card 0
}
EOF

# Set up the virtual environment
echo "Setting up Python virtual environment"
sudo -u pi python3 -m venv /home/pi/hoorch/venv --system-site-packages
sudo -u pi /home/pi/hoorch/venv/bin/pip install --upgrade pip setuptools
sudo -u pi /home/pi/hoorch/venv/bin/pip install flask werkzeug ndeflib RPI.GPIO adafruit-circuitpython-pn532 \
  board pygame rpi_ws281x adafruit-circuitpython-neopixel adafruit-circuitpython-debouncer python-i18n pyyaml
sudo -u pi /home/pi/hoorch/venv/bin/pip install --force-reinstall adafruit-blinka
sudo -u pi /home/pi/hoorch/venv/bin/pip install --upgrade adafruit-python-shell

# Enable SPI
sudo sed -i "s/#dtparam=spi=on/dtparam=spi=on/g" "/boot/firmware/config.txt"

# i2s microphone
CONFIG_FILE="/boot/firmware/config.txt"
OVERLAY="dtoverlay=googlevoicehat-soundcard"

if ! grep -q "^${OVERLAY}$" "$CONFIG_FILE"; then
    echo "Add ${OVERLAY} to ${CONFIG_FILE}"
    echo "$OVERLAY" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "added ${OVERLAY} to ${CONFIG_FILE}!"
else
    echo "${OVERLAY} already ${CONFIG_FILE} exists."
fi

# Setup MAX98357
sudo sed -i 's/^\(dtparam=audio=on\)/dtparam=audio=off/' "/boot/firmware/config.txt"

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
sudo cp /home/pi/hoorch/*.service /etc/systemd/system
sudo cp /home/pi/hoorch/gpio-shutoff.sh /lib/systemd/system-shutdown/
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

# Disable unnecessary services
sudo systemctl enable NetworkManager.service

# Update comitup configuration
sudo sed -i "s/# ap_name: comitup-<nnn>/ap_name: hoorch-<nnn>/g" "/etc/comitup.conf"
sudo sed -i "s/# web_service:/web_service: hoorch-webserver.service/g" "/etc/comitup.conf"

echo "Installation complete, rebooting now"
sudo reboot
