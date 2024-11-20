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

sudo usermod -a -G gpio,i2c,spi,audio pi

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
CONFIG_FILE="/boot/firmware/config.txt"
OVERLAY="dtoverlay=googlevoicehat-soundcard"

# Prüfen, ob die Zeile bereits vorhanden ist
if ! grep -q "^${OVERLAY}$" "$CONFIG_FILE"; then
    echo "Add ${OVERLAY} to ${CONFIG_FILE}"
    echo "$OVERLAY" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "Zeile hinzugefügt!"
else
    echo "${OVERLAY} ist bereits in ${CONFIG_FILE} vorhanden."
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
