#!/bin/sh
# installer.sh will install the necessary packages and config files for HOORCH
# Run this as root (sudo -i)

# Update and upgrade system packages
echo "Updating and upgrading system..."
sudo apt update -y
sudo apt upgrade -y

echo "Installing necessary packages..."
sudo apt install -y python3-full python3-pip sox libsox-fmt-mp3 espeak \
  libsdl2-mixer-2.0-0 git vim python3-venv uuid-runtime

# Set hostname to HOORCH
echo "Setting hostname to HOORCH"
echo "HOORCH" | sudo tee /etc/hostname
sudo sed -i 's/127.0.0.1.*/127.0.0.1 HOORCH/' /etc/hosts
sudo hostname HOORCH

# Create user "pi" if it doesn't exist and give root privileges
echo "Creating user 'pi' with root privileges..."
if ! id "pi" >/dev/null 2>&1; then
  sudo useradd -m -s /bin/bash pi
  echo "pi:listentothemusic" | sudo chpasswd
  sudo usermod -aG sudo pi
else
  echo "User 'pi' already exists."
fi

# Allow passwordless sudo for user "pi"
echo "pi ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/pi
sudo chmod 0440 /etc/sudoers.d/pi

# Add user "pi" to required groups
sudo usermod -a -G gpio,i2c,spi,audio pi

# Clone the HOORCH repository
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

# Create ALSA config
echo "Creating /etc/asound.conf..."
sudo tee /etc/asound.conf >/dev/null <<EOF
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

# Set up the Python virtual environment
echo "Setting up Python virtual environment..."
sudo -u pi python3 -m venv /home/pi/hoorch/venv --system-site-packages
sudo -u pi /home/pi/hoorch/venv/bin/pip install --upgrade pip setuptools
sudo -u pi /home/pi/hoorch/venv/bin/pip install flask werkzeug ndeflib RPI.GPIO adafruit-circuitpython-pn532 \
  board pygame rpi_ws281x adafruit-circuitpython-neopixel adafruit-circuitpython-debouncer python-i18n pyyaml Adafruit-Blinka-Raspberry-Pi5-Neopixel
# Raspberry pi 5: Adafruit-Blinka-Raspberry-Pi5-Neopixel
sudo -u pi /home/pi/hoorch/venv/bin/pip install --force-reinstall adafruit-blinka
sudo -u pi /home/pi/hoorch/venv/bin/pip install --upgrade adafruit-python-shell


# Enable SPI
sudo sed -i "s/#dtparam=spi=on/dtparam=spi=on/g" "/boot/firmware/config.txt"

# Configure i2s microphone
CONFIG_FILE="/boot/firmware/config.txt"
OVERLAY="dtoverlay=googlevoicehat-soundcard"
DISABLE_HDMI_AUDIO="dtoverlay=vc4-kms-v3d,noaudio"

if ! grep -q "^${OVERLAY}$" "$CONFIG_FILE"; then
  echo "Adding microphone and HDMI audio overlay..."
  echo "$OVERLAY" | sudo tee -a "$CONFIG_FILE" > /dev/null
  echo "$DISABLE_HDMI_AUDIO" | sudo tee -a "$CONFIG_FILE" > /dev/null
else
  echo "Overlay already configured in $CONFIG_FILE."
fi

# Disable onboard audio (required for MAX98357)
sudo sed -i 's/^\(dtparam=audio=on\)/dtparam=audio=off/' "/boot/firmware/config.txt"

# Disable Bluetooth to save power
if ! grep -Fxq "dtoverlay=pi3-disable-bt" /boot/firmware/config.txt; then
  echo "dtoverlay=pi3-disable-bt" | sudo tee -a /boot/firmware/config.txt
fi

sudo systemctl disable bluetooth.service

# Disable rainbow splash screen
if ! grep -Fxq "disable_splash=1" /boot/firmware/config.txt; then
  echo "disable_splash=1" | sudo tee -a /boot/firmware/config.txt
fi

# Copy HOORCH service files
echo "Installing HOORCH systemd services..."
sudo cp /home/pi/hoorch/*.service /etc/systemd/system
sudo cp /home/pi/hoorch/gpio-shutoff.sh /lib/systemd/system-shutdown/
sudo chmod +x /lib/systemd/system-shutdown/gpio-shutoff.sh

# Enable and start HOORCH services
for service in /etc/systemd/system/hoorch*.service; do
  sudo systemctl enable "$(basename "$service")"
  sudo systemctl start "$(basename "$service")"
done

# Install log2ram
echo "Installing log2ram..."
echo "deb [signed-by=/usr/share/keyrings/azlux-archive-keyring.gpg] http://packages.azlux.fr/debian/ bookworm main" | sudo tee /etc/apt/sources.list.d/azlux.list
wget -O - https://azlux.fr/repo.gpg.key | gpg --dearmor | sudo tee /usr/share/keyrings/azlux-archive-keyring.gpg > /dev/null
sudo apt update
sudo apt install -y log2ram

# Disable swap
echo "Disabling swap file..."
sudo systemctl disable dphys-swapfile.service

# Enable NetworkManager (for comitup)
sudo systemctl enable NetworkManager.service

# Configure comitup
echo "Updating comitup configuration..."
sudo sed -i "s/# ap_name: comitup-<nnn>/ap_name: hoorch-<nnn>/g" "/etc/comitup.conf"
sudo sed -i "s/# web_service:/web_service: hoorch-webserver.service/g" "/etc/comitup.conf"

echo "Installation complete. Rebooting now..."
sudo reboot
