#!/usr/bin/env bash
# Copy this repo to the Pi and (re)install everything. Run from your laptop:
#
#     scripts/deploy-to-pi.sh              # uses the default target below
#     scripts/deploy-to-pi.sh kam@1.2.3.4  # or name one
#     scripts/deploy-to-pi.sh --code-only  # skip apt/pip, just push the code
#
# Deliberately credential-free: the code travels over your existing SSH key, so
# the Pi never holds a GitHub key, a token or a password. Nothing secret is
# written into the repo either.
set -euo pipefail

TARGET="${SONIC_PI:-kam@raspberrypi.local}"
CODE_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --code-only) CODE_ONLY=1 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) TARGET="$arg" ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="EProjects/jonic"      # relative to the Pi user's home

echo ">> Deploying $REPO to $TARGET:~/$DEST"
ssh "$TARGET" "mkdir -p ~/$DEST"

# --delete keeps the Pi an exact mirror, so a file deleted here disappears
# there too and no stale module is left to be imported.
rsync -az --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'eyes_calibration.json' \
  "$REPO/" "$TARGET:$DEST/"

if [ "$CODE_ONLY" = 1 ]; then
  echo ">> Code pushed; restarting the server only"
  ssh "$TARGET" "sudo systemctl restart sonic-command-center && \
                 systemctl --user restart sonic-eyes-kiosk.service 2>/dev/null || true"
else
  # -t only when this shell actually has a terminal, so the script works the
  # same when run by hand and when run from a pipeline.
  TTY_FLAG=(); [ -t 0 ] && TTY_FLAG=(-t)
  ssh "${TTY_FLAG[@]}" "$TARGET" "bash ~/$DEST/scripts/pi-provision.sh"
fi
