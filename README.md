# 💙 Sonic Birthday

An animatronic Sonic the Hedgehog for a 9-year-old's birthday party. A 7" LCD inside the
head is Sonic's eyes; you puppeteer them from your phone. The eyes are the real
`sonic-eyes.svg` artwork, animated live in the browser, so they stay crisp at any size and
can be stretched to fit whatever the mechanical frame ends up being.

> **TL;DR:** A Raspberry Pi is the server. It serves a remote page to your phone and a
> fullscreen eyes page to the LCD, and pushes animations from one to the other over a
> WebSocket. Press **Blink** on your phone and the face blinks.

---

## What works today

| | |
|---|---|
| 👀 **Eyes on the LCD** | SVG contour, irises and shines, fitted and centred on the panel |
| 😉 **Blink** | a Sonic-blue eyelid drops over both eyes, holds shut, and lifts, 500 ms |
| 👈 👉 **Look left / right / ahead** | the irises turn and hold until you change them |
| 📱 **Phone remote** | four buttons, plus a live status pill for the face |
| 💎 **Emeralds** | nine Chaos Emeralds snake into each eye, form an octagon around the blue one, and keep turning |
| 🔧 **Live calibration** | width, height and position sliders that update the LCD as you drag, then save |

| 🤖 **Eggman's robot** | hold-to-drive on two wheels, a white LED ring, and a servo that unlocks the chest |

**Hardware still to build:** the robot itself. The firmware compiles and the controls are
live; see [docs/04-wiring.md](docs/04-wiring.md).

---

## How it works

```
        Your phone ──tap──┐
                          ▼
        ┌──────────────────────────────────┐
        │  Raspberry Pi                    │
        │    Flask server        :8080     │
        │      /      remote (your phone)  │
        │      /eyes  the face (this Pi)   │
        │      /ws    WebSocket between    │
        │                                  │
        │    Chromium --kiosk  →  7" LCD   │
        └───────────────┬──────────────────┘
                        │ MQTT (not built yet)
                        ▼
                   ESP32: robot + lights
```

A tap on the phone POSTs to the Pi, which broadcasts the animation name over the WebSocket.
The eyes page owns all the timing; the server never animates anything itself. Full detail in
**[docs/01-architecture.md](docs/01-architecture.md)**.

---

## Repository layout

```
jonic/
├── README.md                  ← you are here
├── art/
│   └── sonic-eyes.svg             the traced eye artwork — the source of truth
├── scripts/
│   ├── extract_eye_geometry.py    regenerates eyes/geometry.py from that SVG
│   ├── deploy-to-pi.sh            push the repo to the Pi and install it
│   ├── pi-provision.sh            the install itself, runs on the Pi
│   └── sonic-kiosk.sh             launches Chromium on the eyes page
├── docs/
│   ├── 01-architecture.md         system overview + the animation contract
│   ├── 02-raspberry-pi-setup.md   install, autostart, and calibration
│   ├── 03-esp32-setup.md          flash the robot's ESP32
│   ├── 04-wiring.md               robot wiring + pin map
│   └── 05-operation-runbook.md    party-day checklist
└── software/
    ├── pi/
    │   ├── eyes/                  geometry, animation constants, calibration store
    │   ├── command_center/        Flask app, WebSocket hub, both web pages
    │   ├── common/                MQTT contract for the ESP32
    │   └── systemd/               autostart units
    └── esp32/                 robot firmware (node_robot.h) + old Minecraft nodes
```

---

## Quick start

```bash
cd software/pi
python3 -m pytest -q              # 80 tests
python3 -m command_center.app
```

Then open `http://localhost:8080/eyes` for the face and `http://<your-ip>:8080` on your
phone for the remote. On the eyes page you can also press **B** to blink and the **arrow
keys** to look around, which saves reaching for a phone while you work.

Deploying to the real Pi, once SSH is on and your key is authorized:

```bash
scripts/deploy-to-pi.sh kam@raspberrypi.local
```

Full setup → **[docs/02-raspberry-pi-setup.md](docs/02-raspberry-pi-setup.md)**. The Pi
holds no credentials: code travels over your own SSH key, so it never needs a GitHub key or
a stored password.

---

## Changing the eye artwork

Edit `art/sonic-eyes.svg` in Inkscape, keeping the same five shapes (one contour path, two
iris ellipses, two shine ellipses), then:

```bash
python3 scripts/extract_eye_geometry.py
cd software/pi && python3 -m pytest -q
```

The script bakes Inkscape's transforms into plain coordinates and rewrites
`software/pi/eyes/geometry.py`. The tests then check the shapes still make sense and that
the gaze distance still keeps both irises and both shines visible against the new outline.

---

## Heritage

This started as a Minecraft treasure hunt for a 6-year-old. The Pi command center, the MQTT
contract and the deployment pattern are carried over from it; the wolf's pygame face has
been replaced by the SVG eyes. The ESP32 firmware and the wiring and clue documents are
still the Minecraft ones and are due a rework alongside the robot.
