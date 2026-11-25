#!/bin/bash
# Installer for Media Player (Windows 11 style) on Raspberry Pi
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo). It will ask for sudo when needed."
  exit 1
fi

echo "==> Installing packages"
sudo apt-get update
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-gtk3 gstreamer1.0-plugins-good gstreamer1.0-plugins-base xdg-utils
sudo apt-get install -y fonts-open-sans || echo "   (Open Sans font not available, using system font)"
for p in gstreamer1.0-libav gstreamer1.0-plugins-ugly ffmpegthumbnailer; do
  sudo apt-get install -y "$p" || echo "   ($p not available, skipping)"
done

echo "==> Installing app"
sudo install -d /opt/pi-mediaplayer
sudo install -m 644 "$SRC/pi_mediaplayer.py" /opt/pi-mediaplayer/pi_mediaplayer.py
printf '#!/bin/sh\nexec /usr/bin/python3 /opt/pi-mediaplayer/pi_mediaplayer.py "$@"\n' | sudo tee /usr/local/bin/pi-mediaplayer >/dev/null
sudo chmod 755 /usr/local/bin/pi-mediaplayer

echo "==> Adding menu entry and icon"
sudo install -D -m 644 "$SRC/pi-mediaplayer.svg" /usr/share/icons/hicolor/scalable/apps/pi-mediaplayer.svg
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
sudo tee /usr/share/applications/pi-mediaplayer.desktop >/dev/null <<'DESK'
[Desktop Entry]
Type=Application
Name=Media Player
GenericName=Media Player
Comment=Play music and videos
Exec=pi-mediaplayer %F
Icon=pi-mediaplayer
Terminal=false
Categories=AudioVideo;Audio;Video;Player;GTK;
MimeType=audio/mpeg;audio/flac;audio/x-flac;audio/ogg;audio/x-wav;audio/wav;audio/mp4;audio/aac;audio/x-m4a;audio/opus;video/mp4;video/x-matroska;video/webm;video/quicktime;video/x-msvideo;video/mpeg;
StartupWMClass=pi-mediaplayer
StartupNotify=true
DESK
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true

echo "==> Making Media Player the default app for its file types"
mkdir -p "$HOME/.config/pi-mediaplayer"
for t in audio/mpeg audio/flac audio/x-flac audio/ogg audio/x-wav audio/wav audio/mp4 audio/aac audio/x-m4a audio/opus video/mp4 video/x-matroska video/webm video/quicktime video/x-msvideo video/mpeg; do
  old=$(xdg-mime query default "$t" 2>/dev/null || true)
  if [ -n "$old" ] && [ "$old" != "pi-mediaplayer.desktop" ]; then
    echo "$t $old" >> "$HOME/.config/pi-mediaplayer/old-defaults"
  fi
  xdg-mime default pi-mediaplayer.desktop "$t" 2>/dev/null || true
done

echo
echo "Done. Open Media Player from the menu or run: pi-mediaplayer"
