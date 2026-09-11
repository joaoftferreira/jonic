# 01 · Architecture & message contract

If you only read one doc to understand the system, read this one.

## The big idea

The Raspberry Pi is the server. It hosts two web pages and the link between them:

- **`/`** — the **remote**, opened on your phone. Every button is a tap.
- **`/eyes`** — the **face**, opened fullscreen by Chromium on the 7" LCD inside Sonic's
  head. This page draws the eyes and owns every animation.
- **`/ws`** — the **WebSocket** joining the two. A tap on the phone becomes a message
  pushed to the face in a few milliseconds.

```
 PHONE ──tap──▶ COMMAND CENTER ──WebSocket──▶ /eyes page (Chromium, same Pi)
                 (Flask, on the Pi)
                        │
                        └──MQTT──▶ MQTT BROKER ──▶ ESP32  (robot + lights, not built yet)
```

**Why a WebSocket and not MQTT for the eyes.** The face is a browser on the same machine as
the server, and browsers speak WebSocket natively. Routing it through the broker would mean
an MQTT client library in the page and a broker that has to be running before the eyes can
open. This way the eyes come up even with mosquitto stopped and no ESP32 in the house.

## Components

| Component | Runs on | Language | What it does |
|-----------|---------|----------|--------------|
| Command center | Pi | Python (Flask + flask-sock) | serves both pages, broadcasts animations, stores calibration |
| Eyes page | Pi (Chromium kiosk) | SVG + JS | draws the eyes, plays every animation |
| MQTT broker (Mosquitto) | Pi | — | the bus to the ESP32 |
| Robot | ESP32 | C++ (Arduino) | dual-wheel drive + lights — **not built yet** |

## The animation contract

Defined once in `software/pi/eyes/animations.py`, which the server validates against and the
page plays. The server holds no animation state and no timing; it only names the animation.

| Name | What the face does | Duration |
|------|--------------------|----------|
| `blink` | a Sonic-blue eyelid drops over both eyes, holds shut, and lifts | 500 ms |
| `look_left` | both irises slide left and **stay** there | 180 ms |
| `look_right` | both irises slide right and **stay** there | 180 ms |
| `center` | irises return to the resting pose | 180 ms |
| `emeralds` | nine Chaos Emeralds fill each eye, then turn forever | 2.6 s to settle |

The blink holds shut in the middle rather than closing for an instant. The Pi 3 paints
only about eight frames across the whole blink, so a momentary closure is usually never
drawn and the lid appears to stall halfway down. The plateau is worth roughly three frames,
which makes the eyes visibly shut on every press. Measured on the panel: six blinks out of
six. The timing lives in `eyes/animations.py` and is handed to the page, so the two cannot
drift apart.

### The emeralds

Nine gems per eye: eight on the corners of an octagon and the blue one in the middle. They
snake in from the outer edge of each eye, loop around the centre until the octagon closes,
and the blue one zooms in from behind. The ring then turns slowly and indefinitely. The
irises shrink away while it runs and come back when any other animation is played, which is
how the emeralds end.

Every gem flies the same trail at the same speed, one stagger apart. They all stop at the
same instant, so the gem that set off first has been travelling longest and ends up furthest
around the ring, while the last one barely clears the entry point. That ordering is what
makes it read as a snake rather than a fan opening out, and it fixes the angular speed:
gems one stagger apart must land exactly one corner apart, so `DEG_PER_MS` is derived, not
chosen.

The two octagon centres were searched against the traced outline for the levellest, most
mirrored pair that still clears the gems. The largest circle that fits sits at a different
height in each lobe, and using those made the two clusters look lopsided.

Gaze **latches** on purpose: a puppeteer wants to hold a look, so there is an explicit
button to come back to centre rather than an automatic snap-back.

### Messages on the WebSocket

Server to page only. The page never sends anything back.

```json
{"type": "anim",        "name":  "blink"}
{"type": "calibration", "value": {"scale_x": 1.0, "scale_y": 0.92,
                                  "offset_x": 0,  "offset_y": -8}}
```

A page is sent the current calibration the moment it connects, so a mid-party browser
refresh restores the tuning with no button press. If the socket drops, the page retries
every second forever and shows a small red dot in the corner until it is back.

## Where the eye shapes come from

`art/sonic-eyes.svg` is an Inkscape trace: one path for the white contour of both eyes, two
ellipses for the irises, two for their shines. `scripts/extract_eye_geometry.py` bakes every
Inkscape transform into plain coordinates and writes
`software/pi/eyes/geometry.py`. **Edit the art, then re-run the script** — never edit the
generated module by hand.

```bash
python3 scripts/extract_eye_geometry.py
```

### Why the two eyes do not move the same distance

Both irises rest close to the notch that divides the two eyes. The iris moving *away* from
that notch has room to spare; the one moving *toward* it runs out of white almost at once,
and an equal shift buries it and erases its shine, which reads as a rendering fault rather
than a glance. So the inner eye travels a fraction of the outer one's distance
(`GAZE_INNER_RATIO`). The tests measure both against the real flattened outline, so changing
either constant past what the artwork allows fails the suite.

## Fitting the face to the panel

The eyes page sets the SVG's user units equal to panel pixels, then applies one transform:
move the contour's centre to the middle of the screen, scale it to fit, and apply the
operator's calibration on top. Four numbers, all live-adjustable from the phone:

| Field | Meaning |
|-------|---------|
| `scale_x`, `scale_y` | multiplier on the fit, to stretch the face to the mechanical frame |
| `offset_x`, `offset_y` | pixel nudge, for when the frame does not sit centred on the glass |

They are stored in `software/pi/eyes/eyes_calibration.json`, written atomically because the
sliders save on request and the Pi is normally switched off by pulling the plug.

## MQTT (the ESP32 side)

Only heartbeats exist so far. Each node publishes `system/heartbeat/<node>` every 3 seconds
and the remote shows a green pill for anything heard from in the last 10. Topics for the
robot's drive and lights belong in `software/pi/common/mqtt_contract.py` when that work
starts. The command center connects to the broker in the background and never blocks a
request on it, so a missing broker costs nothing.
