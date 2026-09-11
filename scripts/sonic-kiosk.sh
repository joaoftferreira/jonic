#!/usr/bin/env bash
# Launches Chromium fullscreen on Sonic's eyes page. Started by the
# sonic-eyes-kiosk user service; see docs/02-raspberry-pi-setup.md.
#
# This exists because the browser's package name moved between Raspberry Pi OS
# releases: "chromium-browser" on bookworm, plain "chromium" on trixie. Finding
# it here keeps the flags in version control and the systemd unit identical on
# every Pi.
set -euo pipefail

URL="${SONIC_EYES_URL:-http://127.0.0.1:8080/eyes}"

# Find the compositor ourselves rather than trusting that something exported it.
# The desktop's autostart hands its environment to `systemd --user`, but that
# import is easy to miss: the user manager may have restarted since, or the
# service may be started by hand over SSH. Without WAYLAND_DISPLAY, Chromium
# still starts and still loads the page -- it just has no window, so the panel
# shows the desktop and the fault looks like a rendering bug instead of a
# missing variable.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  for sock in "$XDG_RUNTIME_DIR"/wayland-[0-9]*; do
    case "$sock" in *.lock) continue ;; esac
    [ -S "$sock" ] || continue
    export WAYLAND_DISPLAY="$(basename "$sock")"
    break
  done
fi
if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  echo "sonic-kiosk: no wayland socket in $XDG_RUNTIME_DIR;" \
       "is the desktop session up?" >&2
  exit 1
fi
echo "sonic-kiosk: using WAYLAND_DISPLAY=$WAYLAND_DISPLAY"

for candidate in chromium-browser chromium; do
  if BROWSER="$(command -v "$candidate")"; then
    break
  fi
done
if [ -z "${BROWSER:-}" ]; then
  echo "sonic-kiosk: no chromium found (tried chromium-browser, chromium)" >&2
  exit 1
fi

# Wait for the server rather than crash-looping against it: on a cold boot the
# graphical session is usually up before Flask has finished binding the port.
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null --max-time 2 "$URL"; then break; fi
  sleep 1
done

# A profile of our own. Without it, launching Chromium while any other
# Chromium already owns the default profile makes the new process hand its URL
# to the running one and exit 0 immediately. Under Restart=always that reads as
# "it stopped, start it again" and the service spins, opening a fresh page --
# and a fresh WebSocket -- every few seconds.
PROFILE="${SONIC_KIOSK_PROFILE:-$HOME/.cache/sonic-kiosk}"
mkdir -p "$PROFILE"

# Clear out a previous kiosk still holding that profile, so a restart is
# deterministic. Matching on the profile path leaves any browser the operator
# opened by hand untouched.
pkill -f -- "--user-data-dir=$PROFILE" 2>/dev/null || true
sleep 1

# --no-sandbox                REQUIRED on this Pi. Without it Chromium starts,
#                             runs the page's JavaScript and even opens its
#                             WebSocket, but never maps a window -- so the
#                             service looks healthy while the panel shows the
#                             desktop. Costs little here: the only page ever
#                             loaded is our own, served from localhost.
# --test-type                 hides the yellow "unsupported command-line flag"
#                             infobar that --no-sandbox otherwise puts across
#                             the top of the character's face
# --ozone-platform=wayland    explicit, not "hint=auto". On Raspberry Pi OS
#                             trixie the auto hint resolves to X11 even with a
#                             Wayland socket present, and Chromium then dies
#                             with "Missing X server or $DISPLAY" -- but only
#                             after the service already looks healthy, so the
#                             panel just shows the desktop
# --kiosk                     fullscreen, no browser chrome at all
# --noerrdialogs / --disable-session-crashed-bubble
#                             never put a dialog over the character's face
#                             after a power cut, which is how a Pi gets
#                             switched off in practice
# --check-for-update-interval no update nag mid-party
# --disable-pinch / --overscroll-history-navigation=0
#                             the panel is a touchscreen; a stray hand must not
#                             zoom the eyes or swipe the page away
# --autoplay-policy           sound later, without needing a click first
exec "$BROWSER" \
  --user-data-dir="$PROFILE" \
  --no-sandbox \
  --test-type \
  --ozone-platform=wayland \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=Translate \
  --check-for-update-interval=31536000 \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --autoplay-policy=no-user-gesture-required \
  "$URL"
