# 02 · Raspberry Pi setup (the brain and the face)

The Pi runs two things: the **command center** (Flask, serving the phone remote and the eyes
page) and **Chromium in kiosk mode** showing the eyes fullscreen on the 7" LCD. The MQTT
broker is optional until the ESP32 robot exists.

Once SSH is on, the whole install is one command from your laptop.

---

## 0. Prerequisites

- A Raspberry Pi running Raspberry Pi OS **with desktop** — the eyes need a graphical
  session.
- The Pi on the same WiFi as your laptop and your phone.
- **SSH enabled on the Pi.** A fresh image ships with it off. At the Pi, once:

  ```bash
  sudo systemctl enable --now ssh
  ```

  Or `sudo raspi-config` → *Interface Options → SSH → Enable*.

- Your laptop's SSH key authorized on the Pi. From your laptop, once:

  ```bash
  ssh-copy-id kam@raspberrypi.local
  ```

  It asks for the Pi's password once and copies your **public** key. Nothing secret is
  stored afterwards and nothing goes into this repo.

> Your private key stays in `~/.ssh` on your laptop. Public keys are not secrets — there is
> one committed in `scripts/pi-enable-ssh.sh` on purpose.

---

## 1. Find (and ideally fix) the Pi's address

```bash
ssh kam@raspberrypi.local hostname -I      # e.g. 192.168.2.106
```

This is the address you open on your phone. **Strongly recommended:** give the Pi a DHCP
reservation so it does not move between reboots, then write it on a sticker and put it on
the back of Sonic's head.

---

## 2. Install everything

From your laptop, in the repo:

```bash
scripts/deploy-to-pi.sh                  # defaults to kam@raspberrypi.local
scripts/deploy-to-pi.sh kam@192.168.2.106   # or name the target
```

It copies the repo to `~/EProjects/jonic` on the Pi over your existing SSH key and then runs
`scripts/pi-provision.sh` there, which:

- installs `python3-flask`, `python3-paho-mqtt`, `curl` and Chromium via apt;
- installs `flask-sock` via pip, since Raspberry Pi OS does not package it;
- installs and starts the **command center** as a system service, rewriting its `User=` and
  `WorkingDirectory=` to match this Pi;
- installs the **eyes kiosk** as a *user* service and wires it into whichever desktop this
  release uses (labwc, wayfire or LXDE);
- waits for the server and prints the addresses.

Both scripts are idempotent, so re-run the deploy as often as you like. After a code change
you usually only want:

```bash
scripts/deploy-to-pi.sh --code-only      # push code, restart, skip apt/pip
```

The Pi holds **no credentials**: the code arrives by rsync from your laptop, so it never
needs a GitHub key, a token or a stored password.

> **Why a user service for the kiosk.** Chromium must start *inside* the desktop's Wayland
> session. A system service starts before the compositor exists and the screen stays blank.
> The provision script adds a line to the desktop's autostart that hands the session
> environment to `systemd --user` and starts the kiosk.

**Finish with a reboot** so the desktop runs that autostart line for the first time, and set
`sudo raspi-config` → *System Options → Boot / Auto Login → **Desktop Autologin***, and
*Display Options → Screen Blanking → **off***.

---

## 3. Check it

```bash
ssh kam@raspberrypi.local systemctl status sonic-command-center
ssh kam@raspberrypi.local 'systemctl --user status sonic-eyes-kiosk'
ssh kam@raspberrypi.local 'journalctl -u sonic-command-center -e --no-pager'
```

Open `http://<pi-ip>:8080/eyes` in any browser to see the face, and `http://<pi-ip>:8080` on
your phone for the remote. The `eyes` pill goes green once the LCD page is connected.

On the eyes page itself you can test without a phone: **B** or **space** blinks, **←** and
**→** look, **↓** looks ahead.

Run the test suite on the Pi if you want to be thorough:

```bash
ssh kam@raspberrypi.local 'cd EProjects/jonic/software/pi && python3 -m pytest -q'
```

---

## 4. The MQTT broker (only once the ESP32 exists)

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo tee /etc/mosquitto/conf.d/sonic.conf >/dev/null <<'CONF'
listener 1883 0.0.0.0
allow_anonymous true
CONF
sudo systemctl enable --now mosquitto
```

An unauthenticated broker on your private home network. Fine for a party, not for the
public internet. The eyes do not need it and never wait for it.

---

## 5. Calibrate the eyes to the frame

Do this once the LCD is actually mounted in Sonic's head, because the point is to match the
mechanical opening.

1. Open the remote on your phone and expand **🔧 Eye calibration**.
2. Drag **Width** and **Height** until the white of the eyes fills the opening. The LCD
   updates as you drag.
3. Use **Move ↔** and **Move ↕** if the opening is not centred on the glass.
4. Press **Save**. The values persist across reboots, and the eyes page picks them up again
   whenever it reconnects.

**Reset** returns the sliders to a plain centred fit without saving. The saved file is
`software/pi/eyes/eyes_calibration.json` on the Pi; it is gitignored, and the deploy script
will not overwrite it.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `ssh: connect to host ... port 22: Connection refused` | SSH is off on the Pi. Enable it at the Pi (§ 0); it cannot be done remotely. |
| `ssh` asks for a password every time | `ssh-copy-id` was never run, or was run for a different username. |
| Phone can't reach `:8080` | Phone on a different WiFi band, or the service is down (`systemctl status sonic-command-center`). |
| LCD is black | The Pi is not booting to the desktop (enable Desktop Autologin), or the desktop has not run the autostart yet — reboot once after the first deploy. Check `systemctl --user status sonic-eyes-kiosk`. |
| Eyes appear but ignore the buttons | The WebSocket is down: a small red dot shows in the corner of the LCD and the `eyes` pill is red. Restart the command center. |
| `No module named flask_sock` | The pip step failed. Re-run the deploy and read its output. |
| Eyes come back the wrong size after a reboot | The calibration was adjusted but never **Save**d. |
| `robot` pill is red | Expected until the ESP32 exists. Nothing else depends on it. |
| Screen dims mid-party | Screen blanking is still on; see § 2. |
| `sudo: a password is required` during deploy | This Pi does not have passwordless sudo. Run `scripts/deploy-to-pi.sh` from a terminal so it can prompt you once. |
| **LCD shows the desktop, yet the service is "active" and the `eyes` pill is green** | Chromium started, ran the page and opened its WebSocket, but never mapped a window. On this Pi that means `--no-sandbox` is missing from `scripts/sonic-kiosk.sh`. See the note below. |
| `eglCreateContext ES 3.0 failed`, `CollectGraphicsInfo failed` in the log | Harmless noise. The Pi 3 GPU is OpenGL ES 2.0 only and Chromium probes for ES 3.0. It falls back and the eyes render fine. |
| ⚡ **"Low voltage warning" on screen** | The power supply is not keeping up. Confirm with `vcgencmd get_throttled`; anything other than `0x0` means it has browned out. A Pi 3 wants a genuine 5 V 2.5 A supply and a short, thick USB cable. Fix this before the party: under-voltage throttles the CPU and can corrupt the SD card. |

### Why the kiosk runs with `--no-sandbox`

Verified on this exact hardware, Raspberry Pi 3 Model B with Raspberry Pi OS trixie and
labwc. Without the flag, Chromium starts, loads the page and opens its WebSocket to the
server, so everything downstream looks healthy, but it never maps a window and the panel
just shows the desktop. It is the difference between a working face and a blank one.

Two related traps found alongside it:

- **`--ozone-platform=wayland`, not `--ozone-platform-hint=auto`.** The auto hint resolves to
  X11 here even with a Wayland socket present, and Chromium then exits with
  `Missing X server or $DISPLAY`.
- **`Restart=on-failure`, not `Restart=always`.** Chromium exits 0 when it hands its URL to
  an instance that already owns the profile. Restarting on that turns one stray browser into
  an endless respawn loop; it reached 18 processes and 4 duplicate WebSocket connections
  before this was fixed. The kiosk also uses its own profile directory so it can never
  collide with a browser opened by hand.

The security cost is small here: the only page this browser ever loads is our own, served
from localhost on a private network.
