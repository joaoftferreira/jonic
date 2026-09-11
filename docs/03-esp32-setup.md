# 03 · ESP32 setup (Eggman's robot)

One ESP32 runs the robot: two wheels, a NeoPixel ring and the lock servo. Wiring
is in [04-wiring.md](04-wiring.md); this page is about getting firmware onto it.

---

## 1. Credentials

```bash
cd software/esp32
cp include/config.h.example include/config.h
```

Edit `include/config.h` with your 2.4 GHz WiFi (the ESP32 cannot use 5 GHz) and
the Pi's address. **`config.h` is gitignored**, so your credentials never enter
the repository.

```c
#define WIFI_SSID     "your-network"
#define WIFI_PASSWORD "your-password"
#define MQTT_BROKER   "192.168.2.106"   // the Pi
#define MQTT_PORT     1883
```

Give the Pi a fixed address first, or this number goes stale and the robot goes
deaf.

---

## 2. Build and flash

With [PlatformIO](https://platformio.org/) installed:

```bash
cd software/esp32
pio run -e robot                 # compile only
pio run -e robot -t upload       # compile and flash over USB
pio device monitor               # watch it, 115200 baud
```

On the monitor you should see the WiFi dots, then `[robot] setup done`. Every
command it receives is logged, which is the quickest way to tell a wiring fault
from a message that never arrived.

---

## 3. The broker

The robot needs the MQTT broker on the Pi. The eyes do not, and never wait for
it, so it is easy to forget it is missing.

```bash
ssh kam@raspberrypi.local systemctl is-active mosquitto
```

If that is not `active`, re-run the deploy **from a terminal** so it can ask for
the Pi's sudo password:

```bash
scripts/deploy-to-pi.sh kam@raspberrypi.local
```

---

## 4. Check it

The `robot` pill on the phone page goes green within a few seconds of the ESP32
joining WiFi; it publishes a heartbeat every three seconds. A red pill means it
is not powered, not on WiFi, or pointed at the wrong broker address.

Then work through the staged test in [04-wiring.md](04-wiring.md) — servo, ring,
wheels on a stand, wheels on the floor — rather than trying everything at once.

---

## What the firmware listens to

| Topic | Payload | Effect |
|-------|---------|--------|
| `robot/drive` | `forward` \| `back` \| `left` \| `right` \| `stop` | drives, until it stops hearing this |
| `robot/speed` | `0`–`100` | motor power, retained |
| `robot/lights` | `on` \| `off` | the ring, white, retained |
| `robot/lock` | `open` \| `reset` | the lock servo, retained |

**The robot stops itself.** `robot/drive` is repeated about five times a second
while you hold a button, and the firmware brakes if half a second passes with
nothing arriving. Letting go, locking the phone, closing the tab, losing WiFi
and the broker dying all end the same way: the robot stops. This is also why
`robot/drive` is the one topic that is never retained — a retained drive would
be replayed the instant the ESP32 reconnected, and the robot would set off with
nobody holding anything.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `robot` pill stays red | Not powered, wrong WiFi (must be 2.4 GHz), or `MQTT_BROKER` does not match the Pi's current address. Check the serial monitor. |
| Pill green, nothing moves | Broker is running and messages arrive (they appear on the monitor), so it is wiring: check nSLEEP is high and the motor supply is connected. |
| One wheel turns the wrong way | Swap that motor's two wires. Do not fix it in software. |
| Board resets when a wheel starts | Motors are sharing the ESP32's supply, or the grounds meet in the wrong place. See the power note in the wiring guide. |
| Robot creeps without a button held | Should be impossible — report it. The deadman timeout in `nodeLoop()` is the guard. |
| LEDs flicker or the first pixel is wrong | Missing 330 Ω series resistor or the 1000 µF capacitor; possibly 3.3 V data needing a level shifter. |
| Servo buzzes at rest | It is holding against a mechanical stop. Adjust `LOCK_CLOSED_DEG` / `LOCK_OPEN_DEG` or remount the horn. |
