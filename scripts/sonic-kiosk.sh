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
