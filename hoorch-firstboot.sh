#!/bin/sh
ENV="/home/pi/hoorch/.env"
# Nur wenn noch kein individueller Wert drinsteht:
if grep -q '^HOORCH_UID=' "$ENV"; then
  ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
  sed -i "s/^HOORCH_UID=.*/HOORCH_UID=$ID/" "$ENV"
fi
# Self-cleanup: Service deaktivieren und Script entfernen
systemctl disable hoorch-firstboot.service
rm -f /usr/local/bin/hoorch-firstboot.sh
