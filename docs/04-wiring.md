# 04 · Wiring & pin maps

> ⚠ **This document still describes the Minecraft build.** The Sonic ESP32 work
> (a dual-wheel robot plus switchable lights) has not started; when it does, this
> page gets rewritten. The Pi, the eyes and the phone remote are already Sonic —
> see [01-architecture.md](01-architecture.md).

Exact pins for each character, matching the firmware. If you wire to different pins, change
the `#define`s at the top of the matching `software/esp32/src/node_<character>.h` (or
`software/pi/wolf/mouth.py` for the Wolf) and re-flash.

## Golden rules (read once)

- **Common ground.** Every power supply (ESP32, servo battery, motor supply, LED supply)
  must share a **GND** connection with the ESP32. Without it, nothing works reliably.
- **Don't power servos/motors/long LED strips from the ESP32's 3.3 V pin.** Use a separate
  5 V supply (or the 5 V/`VIN` rail from a USB power bank), grounds tied together.
- **ESP32 logic is 3.3 V.** Servos, NeoPixels and most relays accept a 3.3 V data/signal line
  fine in practice. If a long NeoPixel strip looks flaky, add a 3.3→5 V level shifter on the
  data line and a ~330 Ω resistor in series, plus a 1000 µF cap across the strip's 5 V/GND.
- **GPIO 34** (used by the Portal reed switch) is **input-only** — fine for a switch, can't
  drive anything.

---

## 🟩 Creeper — ESP32

Effect: accelerating white flash → servo drives a pin into the central balloon → relay fires
confetti. Listens on `creeper/explode`.

| Function | ESP32 pin | Connect to |
|----------|-----------|-----------|
| White flash LED(s) | **GPIO 5** | LED(s) + series resistor (~220–330 Ω) → GND. For several LEDs or higher brightness, drive them via a transistor/MOSFET from 5 V. |
| Pin servo (signal) | **GPIO 13** | servo signal wire |
| Pin servo (power) | — | servo **V+ → 5 V**, **GND → common GND** |
| Confetti relay (signal) | **GPIO 12** | relay **IN** |
| Confetti relay (power) | — | relay **VCC → 5 V**, **GND → common GND**; relay contacts switch the popper's trigger |

Tuning: `PIN_REST` / `PIN_STAB` angles in `node_creeper.h`. **Dry-run the servo sweep with no
balloon mounted first**, then arm a balloon.

---

## 🟪 Enderman — ESP32

Effect: belly ring lights a solid, portal-chosen color + eyes light while "on".
Listens on `enderman/activate` (`on`/`off`) and `enderman/color` (`#RRGGBB`, retained).

| Function | ESP32 pin | Connect to |
|----------|-----------|-----------|
| Belly: NeoPixel 16-ring (data) | **GPIO 4** | ring **DIN** (add ~330 Ω in series) |
| Belly ring (power) | — | ring **5 V** (external supply, ~1 A) + **GND → common GND**; ~1000 µF cap across 5 V/GND |
| Eyes: 2 white LEDs | **GPIO 5** | LEDs + resistor → GND (both eyes can share this pin) |

The physical chest key hangs in the lit belly so the kids can grab it.

---

## 🟫 Portal — ESP32 + H-bridge + DC motor

Effect: frame glows purple, then a DC motor winds a string that pulls the door latch open.
Listens on `portal/open`.

**Motor via the H-bridge** (one channel — e.g. an L298N-style board):

| Function | ESP32 pin | H-bridge |
|----------|-----------|----------|
| Direction A | **GPIO 25** | IN1 |
| Direction B | **GPIO 26** | IN2 |
| Speed/enable (PWM) | **GPIO 27** | ENA |
| — | — | motor supply → H-bridge VS/12V in; **H-bridge GND → common GND**; motor leads → OUT1/OUT2 |

**Frame edge-glow** (flexible NeoPixel strip, ~20 px):

| Function | ESP32 pin | Connect to |
|----------|-----------|-----------|
| Strip (data) | **GPIO 4** | strip **DIN** |
| Strip (power) | — | strip **5 V** + **GND → common GND** |

**Optional cube sensor** (reed switch — currently read but not acted on):

| Function | ESP32 pin | Connect to |
|----------|-----------|-----------|
| Reed switch | **GPIO 34** (input-only) | switch between GPIO 34 and GND; firmware uses `INPUT_PULLUP`; magnet in the obsidian cube |

Tuning: `PULL_MS` in `node_portal.h` controls how long the motor runs to pull the latch.
**Tune with the latch string disconnected first**, then connect and adjust so it reliably
releases without over-winding.

---

## 🐉 Ender Dragon — ESP32

Effect: glowing core flares to white then dies; a servo catch drops the obsidian cube.
Listens on `dragon/destroy`.

| Function | ESP32 pin | Connect to |
|----------|-----------|-----------|
| Core: NeoPixel 8-ring (data) | **GPIO 4** | ring **DIN** |
| Core ring (power) | — | ring **5 V** + **GND → common GND** |
| Catch servo (signal) | **GPIO 13** | servo signal |
| Catch servo (power) | — | servo **V+ → 5 V**, **GND → common GND** |

Tuning: `CATCH_CLOSED` holds the cube, `CATCH_OPEN` releases it (`node_dragon.h`). The dragon
hangs from the ceiling on a string so it can circle.

---

## 🐺 Wolf — Raspberry Pi (not an ESP32)

The Wolf is driven directly by the brain Pi: the LCD is its eyes, the amplifier/speaker is
its voice, and one servo is its mouth.

| Function | Pi pin | Connect to |
|----------|--------|-----------|
| Mouth servo (signal) | **GPIO 18** (BCM) | servo signal |
| Mouth servo (power) | — | servo **V+ → 5 V**, **GND → common GND with the Pi** |
| Eyes | — | LCD via HDMI (the pygame app draws on it) |
| Voice | — | amplifier + speakers via the Pi's audio out |

The servo uses hardware PWM through `pigpio` (`pigpiod` must be running — see
[02-raspberry-pi-setup.md](02-raspberry-pi-setup.md)). Change the pin in
`software/pi/wolf/mouth.py` if needed.

---

## Pin reuse across boards — is that a bug?

No. The Creeper, Enderman, Portal and Dragon are **separate ESP32 boards**, so reusing
GPIO 4 / 5 / 13 across them is fine — each board only runs its own character's firmware.

## Per-character power summary

| Character | Compute | Extra supply needed |
|-----------|---------|---------------------|
| Creeper | ESP32 (USB power bank) | 5 V for servo + relay/popper |
| Enderman | ESP32 (USB power bank) | 5 V for the 16-ring (~1 A) |
| Portal | ESP32 (USB power bank) | motor supply for the H-bridge + 5 V for the strip |
| Dragon | ESP32 (USB power bank) | 5 V for the 8-ring + servo |
| Wolf | Raspberry Pi | 5 V for the mouth servo |

Charge every power bank the night before (it's on the party-day checklist in
[05-operation-runbook.md](05-operation-runbook.md)).
