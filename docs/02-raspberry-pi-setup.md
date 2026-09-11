# 02 · Raspberry Pi setup (the brain and the face)

The Pi runs two things: the **command center** (Flask, serves the phone remote and the eyes
page) and **Chromium in kiosk mode** showing the eyes fullscreen on the 7" LCD. The MQTT
broker is optional until the ESP32 robot exists.

> Estimated time: ~30 min, with a screen and keyboard on the Pi or over SSH.

---

## 0. Prerequisites

- Raspberry Pi with Raspberry Pi OS **with desktop** — the eyes need a graphical session.
- The Pi on your home WiFi, the same network your phone uses.
- This repo cloned to `/home/kam/EProjects/jonic` on the Pi.

> If your Pi username or path differs from `kam`, update `WorkingDirectory=` and `User=` in
> `software/pi/systemd/sonic-command-center.service` before installing it in step 4.

---

## 1. Find (and ideally fix) the Pi's IP address

```bash
hostname -I        # e.g. 192.168.1.50
```

This is the address you open on your phone. **Strongly recommended:** give the Pi a static
or DHCP-reserved address so it does not move between reboots.

---

## 2. Install the dependencies

```bash
sudo apt update
sudo apt install -y python3-flask python3-paho-mqtt chromium-browser
sudo pip install --break-system-packages flask-sock
```

- **python3-flask** — the web server.
- **python3-paho-mqtt** — the link to the ESP32, later.
- **chromium-browser** — draws the eyes.
- **flask-sock** — the WebSocket. It is not packaged for Raspberry Pi OS, so it comes from
  pip. On Debian trixie `pip` is "externally managed", hence `--break-system-packages`; it
  pulls in `simple-websocket` with it.

Install the broker too if the ESP32 work has started:

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo tee /etc/mosquitto/conf.d/sonic.conf >/dev/null <<'CONF'
listener 1883 0.0.0.0
allow_anonymous true
CONF
sudo systemctl enable --now mosquitto
```

This is an unauthenticated broker on your private home network. Fine for a party, not for
the public internet.

---

## 3. Quick manual test (before autostart)

```bash
cd /home/kam/EProjects/jonic/software/pi
python3 -m command_center.app
```

Open `http://<pi-ip>:8080/eyes` in any browser: you should see Sonic's eyes fill the window.
Open `http://<pi-ip>:8080` on your phone and press the buttons; the eyes respond instantly.
The `eyes` pill at the top of the remote goes green once the face page is connected.

You can also drive the eyes page straight from its own keyboard, which is handy on the
bench: **B** or **space** blinks, **←** and **→** look, **↓** looks ahead.

Run the test suite from the same directory:

```bash
python3 -m pytest -q
```

---

## 4. Autostart on boot

Power the Pi, everything comes up, no laptop needed.

The **command center** is a plain network daemon, so it is a normal **system** service. The
**kiosk** draws on the LCD, so it must start *inside* the desktop's Wayland session — a
system service would start before the compositor exists and the screen would stay blank. So
Chromium runs as a **user** service that labwc launches once it is up.

**1. Command center (system service):**

```bash
sudo cp /home/kam/EProjects/jonic/software/pi/systemd/sonic-command-center.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sonic-command-center
```

**2. Eyes kiosk (user service, launched by the compositor):**

```bash
mkdir -p ~/.config/systemd/user
cp /home/kam/EProjects/jonic/software/pi/systemd/sonic-eyes-kiosk.service ~/.config/systemd/user/
systemctl --user daemon-reload

mkdir -p ~/.config/labwc
cat >> ~/.config/labwc/autostart <<'AUTOSTART'
systemctl --user import-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR XDG_SESSION_TYPE DISPLAY
systemctl --user restart sonic-eyes-kiosk.service
AUTOSTART
```

**3. Boot to the desktop and stop the screen blanking.** `sudo raspi-config` →
*System Options → Boot / Auto Login → **Desktop Autologin***, and
*Display Options → Screen Blanking → **off***. Then `sudo reboot`.

After the reboot, with nothing attached: the eyes are on the LCD and the remote is at
`http://<pi-ip>:8080`.

```bash
systemctl status sonic-command-center      # system service
systemctl --user status sonic-eyes-kiosk   # user service, as the desktop user
journalctl -u sonic-command-center -e
```

---

## 5. Calibrate the eyes to the frame

Do this once the LCD is actually mounted in Sonic's head, because the point is to match the
mechanical opening.

1. Open the remote on your phone and expand **🔧 Eye calibration**.
2. Drag **Width** and **Height** until the white of the eyes fills the frame's opening. The
   LCD updates as you drag.
3. Use **Move ↔** and **Move ↕** if the opening is not centred on the glass.
4. Press **Save**. The values persist across reboots, and the eyes page picks them up again
   whenever it reconnects.

**Reset** returns the sliders to a plain centred fit without saving.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Phone can't reach `:8080` | Phone on a different WiFi band, or the service is not running (`systemctl status sonic-command-center`). |
| LCD is black | The Pi is not booting to the desktop (enable Desktop Autologin), or the kiosk unit was installed as a *system* service instead of a user one. Check `systemctl --user status sonic-eyes-kiosk`. |
| Eyes appear but ignore the buttons | The WebSocket is down: a small red dot shows in the corner of the LCD, and the `eyes` pill on the phone is red. Restart the command center. |
| `No module named flask_sock` | The pip install in step 2 was skipped, or ran as a different user. |
| Eyes come back the wrong size after a reboot | The calibration was adjusted but never **Save**d. |
| `robot` pill is red | Expected until the ESP32 exists. Nothing else depends on it. |
| Screen dims mid-party | Screen blanking is still on; see step 4.3. |
