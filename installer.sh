#!/bin/bash
# installer.sh installs required packages and config files for HOORCH
# Run via: curl -sSL https://.../installer.sh | sudo bash

set -e

sudo apt full-upgrade -y
sudo rpi-eeprom-update -a

# 1. Update and upgrade system packages
echo "Updating and upgrading system..."
sudo apt update -y && sudo apt upgrade -y

# 2. Install necessary packages
echo "Installing required packages..."
sudo apt install -y python3-full python3-pip sox libsox-fmt-mp3 espeak \
  libsdl2-mixer-2.0-0 git vim python3-venv uuid-runtime sqlite3 ffmpeg

# 3. Set hostname to HOORCH
echo "Setting hostname to HOORCH"
echo "HOORCH" | sudo tee /etc/hostname > /dev/null
sudo sed -i 's/127.0.0.1.*/127.0.0.1 HOORCH/' /etc/hosts
sudo hostname HOORCH

# 4. Create user 'pi' with sudo
echo "Creating user 'pi' with sudo privileges..."
if ! id "pi" >/dev/null 2>&1; then
  sudo useradd -m -s /bin/bash pi
  echo "pi:listentothemusic" | sudo chpasswd
  sudo usermod -aG sudo pi
else
  echo "User 'pi' already exists."
fi

# 5. Configure sudoers and groups
echo "Configuring sudoers and adding groups..."
echo "pi ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/pi > /dev/null
sudo chmod 0440 /etc/sudoers.d/pi
sudo usermod -a -G gpio,i2c,spi,audio pi

# 6. Clone HOORCH repository
echo "Cloning the HOORCH repository..."
if [ ! -d "/home/pi/hoorch" ]; then
  sudo -u pi git clone https://github.com/knallgelb/hoorch.git /home/pi/hoorch
else
  echo "Repository already exists, skipping clone."
fi

# Generate a unique UID for this HOORCH box and store it in .env
echo "Generating unique HOORCH UID..."
UNIQUE_ID=$(uuidgen | tr 'A-Z' 'a-z')
ENV_PATH="/home/pi/hoorch/.env"
ENV_TEMPLATE="/home/pi/hoorch/.env.example"

if [ -f "$ENV_TEMPLATE" ]; then
  cp "$ENV_TEMPLATE" "$ENV_PATH"
  sed -i "s/^HOORCH_UID=.*/HOORCH_UID=$UNIQUE_ID/" "$ENV_PATH"
else
  echo "Creating new .env file with UID"
  echo "HOORCH_UID=$UNIQUE_ID" > "$ENV_PATH"
fi

chown pi:pi "$ENV_PATH"

# 7. Install first-boot hook for unique UUID
echo "Installing first-boot hook..."
sudo cp /home/pi/hoorch/services/hoorch-firstboot.sh /usr/local/bin/hoorch-firstboot.sh
sudo chmod +x /usr/local/bin/hoorch-firstboot.sh
sudo cp /home/pi/hoorch/services/hoorch-firstboot.service /etc/systemd/system/hoorch-firstboot.service
sudo systemctl enable hoorch-firstboot.service


# 8. Set up Python virtual environment and install dependencies
echo "Setting up Python virtual environment..."
sudo -u pi python3 -m venv /home/pi/hoorch/venv --system-site-packages
sudo -u pi /home/pi/hoorch/venv/bin/pip install --upgrade pip setuptools
sudo -u pi /home/pi/hoorch/venv/bin/pip install \
  flask werkzeug ndeflib RPI.GPIO adafruit-circuitpython-pn532 \
  board pygame rpi_ws281x adafruit-circuitpython-neopixel \
  adafruit-circuitpython-debouncer python-i18n pyyaml pydantic \
  Adafruit-Blinka-Raspberry-Pi5-Neopixel sqlmodel httpx dotenv fastapi[standard]
sudo -u pi /home/pi/hoorch/venv/bin/pip install --force-reinstall adafruit-blinka
sudo -u pi /home/pi/hoorch/venv/bin/pip install --upgrade adafruit-python-shell

# 9. Create ALSA config
echo "Creating /etc/asound.conf..."
cat <<EOF | sudo tee /etc/asound.conf > /dev/null
pcm.!default {
  type asym
  playback.pcm {
    type plug
    slave.pcm "hw:0,0"
  }
  capture.pcm {
    type plug
    slave.pcm "hw:0,0"
  }
}
ctl.!default {
  type hw
  card 0
}
EOF

# 10. Enable SPI and configure overlays
echo "Configuring SPI and audio overlays..."
CONFIG_FILE="/boot/firmware/config.txt"
# Enable SPI
sudo sed -i "s/#dtparam=spi=on/dtparam=spi=on/" "$CONFIG_FILE"
# I2S microphone overlay
sudo grep -q "^dtoverlay=googlevoicehat-soundcard$" "$CONFIG_FILE" || echo "dtoverlay=googlevoicehat-soundcard" | sudo tee -a "$CONFIG_FILE" > /dev/null
# Disable HDMI audio
sudo grep -q "^dtoverlay=vc4-kms-v3d,noaudio$" "$CONFIG_FILE" || echo "dtoverlay=vc4-kms-v3d,noaudio" | sudo tee -a "$CONFIG_FILE" > /dev/null
# Disable onboard audio
sudo sed -i "s/^dtparam=audio=on/dtparam=audio=off/" "$CONFIG_FILE"
# Disable rainbow splash
sudo grep -q "^disable_splash=1$" "$CONFIG_FILE" || echo "disable_splash=1" | sudo tee -a "$CONFIG_FILE" > /dev/null

# 11. Disable Bluetooth to save power
echo "Disabling Bluetooth..."
sudo grep -q "^dtoverlay=pi3-disable-bt$" "$CONFIG_FILE" || echo "dtoverlay=pi3-disable-bt" | sudo tee -a "$CONFIG_FILE" > /dev/null
sudo systemctl disable bluetooth.service

# 12. Configure comitup
echo "Configuring comitup settings..."
sudo sed -i "s/# ap_name: comitup-<nnn>/ap_name: hoorch-<nnn>/" /etc/comitup.conf
sudo sed -i "s/# web_service:/web_service: hoorch-webserver.service/" /etc/comitup.conf

# 13. Deploy HOORCH systemd services and shutdown script

if [ -f "/home/pi/hoorch/services/leds_server.service" ]; then
  sudo cp /home/pi/hoorch/services/leds_server.service /etc/systemd/system/
  sudo systemctl enable leds_server.service
  sudo systemctl start leds_server.service
else
  echo "Warnung: leds_server.service wurde nicht gefunden!"
fi

echo "Installing HOORCH systemd services..."
sudo cp /home/pi/hoorch/services/*.service /etc/systemd/system/
sudo cp /home/pi/hoorch/gpio-shutoff.sh /lib/systemd/system-shutdown/
sudo chmod +x /lib/systemd/system-shutdown/gpio-shutoff.sh

for svc in /etc/systemd/system/hoorch*.service; do
  sudo systemctl enable "$(basename "$svc")"
  sudo systemctl start "$(basename "$svc")"
done


echo "Installation complete. Please reboot to apply all changes."

sudo reboot
