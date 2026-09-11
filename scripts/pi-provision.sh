#!/usr/bin/env bash
# Installs everything Sonic's face needs, on the Pi. Idempotent: safe to re-run
# after every deploy.
#
# Do not run this by hand — scripts/deploy-to-pi.sh copies the repo across and
# then calls it. It deliberately holds no credentials: the code arrives over
# rsync from your laptop, so the Pi never needs a GitHub key or a login.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PI_USER="$(id -un)"

say() { printf '\n\033[1;34m>> %s\033[0m\n' "$1"; }

say "Repo is at $REPO, running as $PI_USER"
. /etc/os-release 2>/dev/null || true
echo "   OS: ${PRETTY_NAME:-unknown}"
echo "   Model: $(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo unknown)"

# Ask for sudo once, up front. Raspberry Pi OS does not always grant the first
# user passwordless sudo, and a cached credential from someone typing `sudo` at
# the Pi makes it look like it does -- until the next reboot clears the cache
# and the install dies halfway through.
say "Checking sudo"
if sudo -n true 2>/dev/null; then
  echo "   passwordless"
elif [ -t 0 ]; then
  sudo -v
else
  echo "   !! sudo needs a password and no terminal is attached." >&2
  echo "      Run scripts/deploy-to-pi.sh from a terminal so it can prompt." >&2
  exit 1
fi

# ---------------------------------------------------------------- packages --
say "Installing packages"
sudo apt-get update -qq

# Chromium is "chromium-browser" on bookworm and "chromium" on trixie; ask apt
# which one this release actually has rather than guessing.
CHROMIUM_PKG=""
for candidate in chromium-browser chromium; do
  if apt-cache show "$candidate" >/dev/null 2>&1; then CHROMIUM_PKG="$candidate"; break; fi
done
if [ -z "$CHROMIUM_PKG" ]; then
  echo "   !! no chromium package found; the eyes page will have nothing to draw in" >&2
fi

sudo apt-get install -y -qq python3-flask python3-paho-mqtt curl ${CHROMIUM_PKG}

# The broker, for the ESP32 robot. The eyes never need it and never wait for
# it, but the robot's drive, lights and lock all ride on it.
say "Installing the MQTT broker"
sudo apt-get install -y -qq mosquitto mosquitto-clients
sudo tee /etc/mosquitto/conf.d/sonic.conf >/dev/null <<'CONF'
listener 1883 0.0.0.0
allow_anonymous true
# Keep retained messages across a broker restart, so a robot that reboots
# still learns the tuned speed and the state of its lights and lock.
persistence true
persistence_location /var/lib/mosquitto/
CONF
sudo systemctl enable --now mosquitto
sudo systemctl restart mosquitto

# flask-sock is not packaged for Raspberry Pi OS. On Debian bookworm and newer
# pip refuses to touch the system environment without this flag.
if python3 -c 'import flask_sock' 2>/dev/null; then
  echo "   flask-sock already present"
else
  say "Installing flask-sock from pip"
  sudo pip install --break-system-packages --quiet flask-sock
fi

# --------------------------------------------------------------- services --
say "Installing the command center (system service)"
sudo install -m 644 "$REPO/software/pi/systemd/sonic-command-center.service" \
     /etc/systemd/system/sonic-command-center.service
# The unit ships with the author's user and path; make it match this Pi.
sudo sed -i "s|^User=.*|User=$PI_USER|; s|^WorkingDirectory=.*|WorkingDirectory=$REPO/software/pi|" \
     /etc/systemd/system/sonic-command-center.service
sudo systemctl daemon-reload
sudo systemctl enable --now sonic-command-center
sudo systemctl restart sonic-command-center

say "Installing the eyes kiosk (user service)"
mkdir -p "$HOME/.config/systemd/user"
install -m 644 "$REPO/software/pi/systemd/sonic-eyes-kiosk.service" \
        "$HOME/.config/systemd/user/sonic-eyes-kiosk.service"
sed -i "s|^ExecStart=.*|ExecStart=$REPO/scripts/sonic-kiosk.sh|" \
    "$HOME/.config/systemd/user/sonic-eyes-kiosk.service"
systemctl --user daemon-reload 2>/dev/null || true

# ------------------------------------------------------- desktop autostart --
# The kiosk must start *inside* the graphical session, and each Raspberry Pi OS
# desktop has its own way of saying so. Detect rather than assume.
say "Wiring the kiosk into the desktop session"
AUTOSTART_LINES='systemctl --user import-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR XDG_SESSION_TYPE DISPLAY
systemctl --user restart sonic-eyes-kiosk.service'

add_once() {  # add_once <file> ; appends stdin unless already present
  local file="$1"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  if grep -q "sonic-eyes-kiosk" "$file"; then
    echo "   already wired into $file"
  else
    cat >> "$file"
    echo "   wired into $file"
  fi
}

if command -v labwc >/dev/null 2>&1; then
  printf '%s\n' "$AUTOSTART_LINES" | add_once "$HOME/.config/labwc/autostart"
elif command -v wayfire >/dev/null 2>&1; then
  # wayfire has no autostart file by default; it takes an ini section instead.
  WF="$HOME/.config/wayfire.ini"
  touch "$WF"
  if grep -q "sonic-eyes-kiosk" "$WF"; then
    echo "   already wired into $WF"
  else
    grep -q '^\[autostart\]' "$WF" || printf '\n[autostart]\n' >> "$WF"
    printf 'sonic_eyes = %s/scripts/sonic-kiosk.sh\n' "$REPO" >> "$WF"
    echo "   wired into $WF"
  fi
elif [ -d "$HOME/.config/lxsession" ] || command -v lxsession >/dev/null 2>&1; then
  printf '%s\n' "$AUTOSTART_LINES" | \
    add_once "$HOME/.config/lxsession/LXDE-pi/autostart"
else
  echo "   !! unknown desktop; start the kiosk yourself with:" >&2
  echo "      systemctl --user restart sonic-eyes-kiosk.service" >&2
fi

# ------------------------------------------------------------------ checks --
say "Checking the server answers"
ok=0
for _ in $(seq 1 20); do
  if curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:8080/eyes; then ok=1; break; fi
  sleep 1
done
if [ "$ok" = 1 ]; then
  echo "   /eyes responds"
  curl -fsS http://127.0.0.1:8080/status; echo
else
  echo "   !! the command center is not answering; see the log below" >&2
  sudo journalctl -u sonic-command-center -n 30 --no-pager >&2
  exit 1
fi

say "Done"
echo "   Remote:  http://$(hostname -I | awk '{print $1}'):8080"
echo "   Eyes:    http://$(hostname -I | awk '{print $1}'):8080/eyes"
echo
echo "   If the LCD is still blank, log in on the Pi's desktop once (or reboot)"
echo "   so the compositor runs the autostart line above."
