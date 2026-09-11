# 03 · ESP32 setup (the four characters)

> ⚠ **This document still describes the Minecraft build.** The Sonic ESP32 work
> (a dual-wheel robot plus switchable lights) has not started; when it does, this
> page gets rewritten. The Pi, the eyes and the phone remote are already Sonic —
> see [01-architecture.md](01-architecture.md).

Each of the Creeper, Enderman, Portal, and Dragon runs on its own ESP32 board. They share
**one** firmware project; a build flag picks which character a board becomes. You flash the
same project four times with four different "environments."

> Do the [Pi setup](02-raspberry-pi-setup.md) first — the boards need the broker's IP, and
> you'll want the command center running to confirm each board checks in.

---

## 0. Install PlatformIO

PlatformIO is the build/flash toolchain. Either:

- **VS Code extension:** install "PlatformIO IDE" from the marketplace, **or**
- **CLI:**
  ```bash
  pip3 install platformio
  ```

Confirm: `pio --version`.

---

## 1. Set your WiFi + broker IP

Edit `software/esp32/include/config.h` and fill in your real values:

```cpp
#pragma once
#define WIFI_SSID     "YOUR_HOME_SSID"      // your WiFi name
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"  // your WiFi password
#define MQTT_BROKER   "192.168.1.50"        // the Pi's IP from doc 02, step 1
#define MQTT_PORT     1883
```

Use the **2.4 GHz** band — ESP32 boards don't do 5 GHz.

> ⚠️ **Secrets note:** `config.h` is currently tracked in git, so your WiFi password would be
> committed. If that matters to you, ask and we'll gitignore `config.h` and add a
> `config.h.example` template instead. For a private repo + a party rig it's usually fine.

---

## 2. Flash each board

Connect **one** ESP32 over USB and flash it as a specific character. The environment names
are `creeper`, `enderman`, `portal`, `dragon`.

```bash
cd software/esp32

# Creeper
pio run -e creeper -t upload

# Enderman
pio run -e enderman -t upload

# Portal
pio run -e portal -t upload

# Dragon
pio run -e dragon -t upload
```

**Tip:** physically label each board (sticker/tape) the moment you flash it — they're
identical and easy to mix up.

**If `upload` can't find the port**, specify it:
```bash
pio run -e creeper -t upload --upload-port /dev/ttyUSB0
```
(On Linux you may need to be in the `dialout` group: `sudo usermod -aG dialout $USER`, then
log out/in.)

---

## 3. Watch a board boot (serial monitor)

```bash
pio device monitor          # 115200 baud
```

You'll see dots while it joins WiFi, then it connects to the broker. Within a few seconds the
matching pill on the command center page (`http://<pi-ip>:8080`) turns **green** — that's the
board's heartbeat arriving. Green pill = that character is alive and reachable.

---

## 4. Test each effect from your phone

With a board powered and on the bench (do this **before** final assembly, and run mechanical
effects with nothing fragile attached):

| Board | Press this button | Expected |
|-------|-------------------|----------|
| Creeper | **Creeper: EXPLODE** | white LED flashes accelerate, servo sweeps the pin out and back, relay clicks (confetti) |
| Enderman | **Enderman: Glow on** / **off** | belly ring breathes purple + eyes light / everything off |
| Portal | **Portal: Open** | frame strip brightens, motor runs ~0.9 s then stops |
| Dragon | **Dragon: Destroy** | core ramps to white then goes dark, servo opens the catch then closes |

You can also trigger effects without the phone:
```bash
mosquitto_pub -t creeper/explode  -m 1
mosquitto_pub -t enderman/activate -m on
mosquitto_pub -t portal/open      -m 1
mosquitto_pub -t dragon/destroy   -m 1
```

---

## 5. Tuning (edit, re-flash)

A few constants you'll likely tweak after seeing the real mechanism. Edit the file, then
re-run `pio run -e <board> -t upload`.

| What | File | Constant | Notes |
|------|------|----------|-------|
| Portal latch pull time | `src/node_portal.h` | `PULL_MS` (900) | increase if the motor doesn't pull the latch fully; decrease to avoid over-winding |
| Creeper pin throw | `src/node_creeper.h` | `PIN_REST` / `PIN_STAB` | angles for retracted vs. stabbing the balloon |
| Dragon catch angles | `src/node_dragon.h` | `CATCH_CLOSED` / `CATCH_OPEN` | closed = holds the cube, open = drops it |

Pin assignments per board are documented in **[04-wiring.md](04-wiring.md)** — change them
there too if your wiring differs.

---

## How the one-project-four-characters trick works

`platformio.ini` defines four environments, each passing a `-D NODE_*` flag:

```ini
[env:creeper]   build_flags = -D NODE_CREEPER
[env:enderman]  build_flags = -D NODE_ENDERMAN
[env:portal]    build_flags = -D NODE_PORTAL
[env:dragon]    build_flags = -D NODE_DRAGON
```

`src/main.cpp` contains the shared plumbing (WiFi, MQTT connect, heartbeat every 3 s) and,
based on the flag, includes exactly one `node_<character>.h`. Each `node_*.h` provides four
hooks: `nodeSetup()`, `nodeSubscribe()`, `nodeLoop()`, `nodeOnMessage()`. That's the entire
per-character logic — everything else is reused.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Pill never turns green | Wrong `MQTT_BROKER` IP in `config.h`; or board on 5 GHz WiFi; check serial monitor for connect errors. |
| Connects then drops repeatedly | WiFi signal weak at that location; or the Pi's IP changed (use a DHCP reservation). |
| `upload` fails / no port | Bad USB cable (must be data, not charge-only); wrong port; not in `dialout` group. |
| Effect runs but motor/servo doesn't move | Power: servos/motors need their own 5 V supply with **common ground** to the ESP32 — see wiring doc. |
| Compile error about `analogWrite` | Very old ESP32 core. Update the platform (`pio pkg update`) — the project targets a current core. |
