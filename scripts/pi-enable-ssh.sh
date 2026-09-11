#!/usr/bin/env bash
# Run this ON THE RASPBERRY PI (as the Pi's normal user, not root).
# It enables the SSH server and authorizes the control machine's key so
# Claude/this laptop can connect passwordless.
#
# Usage on the Pi:
#   bash pi-enable-ssh.sh
set -e

KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILLSbBOYpL8SoCttPe6LLWs5Fi5WEiU56XWJCuZv9i5C joaoftferreira@gmail.com'

echo ">> Enabling and starting the SSH server..."
sudo systemctl enable --now ssh

echo ">> Authorizing the control machine's public key..."
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
touch "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
# add the key only if it isn't already present (idempotent)
grep -qF "$KEY" "$HOME/.ssh/authorized_keys" || echo "$KEY" >> "$HOME/.ssh/authorized_keys"

echo
echo ">> Done."
echo ">> SSH status:"; sudo systemctl is-active ssh
echo ">> This Pi's username is: $(whoami)"
echo ">> This Pi's IP addresses: $(hostname -I)"
echo
echo ">> Tell the assistant the username printed above so it can connect:"
echo "     ssh $(whoami)@$(hostname -I | awk '{print $1}')"
