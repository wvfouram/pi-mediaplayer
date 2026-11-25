#!/bin/bash
# Removes Media Player.
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo)."
  exit 1
fi

# put back the apps that opened these file types before
if [ -f "$HOME/.config/pi-mediaplayer/old-defaults" ]; then
  while read -r t old; do
    [ -n "$old" ] && xdg-mime default "$old" "$t" 2>/dev/null || true
  done < "$HOME/.config/pi-mediaplayer/old-defaults"
  rm -f "$HOME/.config/pi-mediaplayer/old-defaults"
fi

sudo rm -rf /opt/pi-mediaplayer /usr/local/bin/pi-mediaplayer /usr/share/applications/pi-mediaplayer.desktop \
  /usr/share/icons/hicolor/scalable/apps/pi-mediaplayer.svg
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true
echo "Media Player removed. Your settings are still in ~/.config/pi-mediaplayer (delete that folder to remove them)."
