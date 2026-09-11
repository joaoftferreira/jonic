# Minecraft Treasure Hunt — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Minecraft-themed birthday treasure hunt where Minecraft characters give clues across the house, each doing an interactive light/sound/motion effect, ending at a gift chest — operated reliably from a phone command center.

**Architecture:** A Raspberry Pi 3 ("brain") runs an MQTT broker, a phone-facing command-center web app, and the Wolf app (animated eyes + sound + mouth servo). Four ESP32 nodes (creeper, enderman, portal, dragon) subscribe to MQTT topics and perform their effects on command. Every story beat is an operator button press (Wizard-of-Oz); sensors/automation are optional polish. The bee/drone is a separate stretch track with a manual fallback.

**Tech Stack:** Python 3 (paho-mqtt, Flask, pygame, gpiozero/pigpio), Mosquitto on the Pi; Arduino/PlatformIO + PubSubClient + Adafruit NeoPixel + ESP32Servo on the ESP32s.

**Task tags:** `[CLAUDE-SW]` = software I build · `[USER-HW]` = physical build/wiring you do · `[BOTH]` = joint.

---

## File Structure

```
dani6/
├── software/
│   ├── pi/
│   │   ├── common/
│   │   │   ├── mqtt_contract.py        # topic/payload constants — single source of truth
│   │   │   └── tests/test_contract.py
│   │   ├── command_center/
│   │   │   ├── app.py                  # Flask server + MQTT publisher
│   │   │   ├── commands.py             # button-id → (topic, payload) mapping + story order
│   │   │   ├── templates/index.html    # mobile button grid + status strip
│   │   │   ├── static/app.js           # button clicks → POST, heartbeat polling
│   │   │   └── tests/test_commands.py
│   │   ├── wolf/
│   │   │   ├── wolf_app.py             # pygame main loop: render eyes, play sound, drive mouth
│   │   │   ├── states.py               # WolfState machine (pure logic, unit-tested)
│   │   │   ├── mouth.py                # servo wrapper (gpiozero), with --no-servo dev mode
│   │   │   ├── assets/                 # bark.wav, whine.wav, happybark.wav
│   │   │   └── tests/test_states.py
│   │   ├── requirements.txt
│   │   └── systemd/                    # unit files for autostart at the party
│   │       ├── treasure-broker.note
│   │       ├── treasure-command-center.service
│   │       └── treasure-wolf.service
│   └── esp32/
│       ├── platformio.ini             # 4 envs (creeper/enderman/portal/dragon) via -D flags
│       ├── include/config.h           # WiFi + MQTT broker settings
│       └── src/
│           ├── main.cpp               # base: WiFi+MQTT+heartbeat+dispatch
│           ├── node_creeper.h
│           ├── node_enderman.h
│           ├── node_portal.h
│           └── node_dragon.h
├── clues/                              # printable clue cards (markdown → print)
│   └── clues.md
└── docs/superpowers/...                # spec + this plan
```

---

# PHASE 0 — Foundation (Days 1–2)

Goal: prove the whole pipeline end-to-end (phone button → MQTT → ESP32 blinks an LED) before building anything physical.

### Task 1: Repo scaffold + version control  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/requirements.txt`
- Create: `.gitignore`

- [ ] **Step 1: Initialize git**

```bash
cd /home/kam/EProjects/dani6
git init
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.pio/
software/pi/wolf/assets/*.wav
*.log
```

- [ ] **Step 3: Create `software/pi/requirements.txt`**

```
paho-mqtt==2.1.0
Flask==3.0.3
pygame==2.6.0
gpiozero==2.0.1
pigpio==1.78
pytest==8.2.0
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore software/pi/requirements.txt
git commit -m "chore: scaffold repo and python deps"
```

---

### Task 2: MQTT contract (single source of truth)  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/common/mqtt_contract.py`
- Test: `software/pi/common/tests/test_contract.py`

- [ ] **Step 1: Write the failing test**

```python
# software/pi/common/tests/test_contract.py
from common import mqtt_contract as c

def test_topics_are_unique_and_namespaced():
    topics = [c.WOLF_STATE, c.WOLF_BARK, c.CREEPER_EXPLODE,
              c.DRAGON_DESTROY, c.PORTAL_OPEN, c.ENDERMAN_ACTIVATE]
    assert len(topics) == len(set(topics))
    assert all("/" in t for t in topics)

def test_wolf_states_enumerated():
    assert c.WOLF_STATES == ("idle", "hungry", "loving")

def test_heartbeat_topic_builder():
    assert c.heartbeat_topic("creeper") == "system/heartbeat/creeper"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd software/pi && python -m pytest common/tests/test_contract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'common.mqtt_contract'`

- [ ] **Step 3: Write minimal implementation**

```python
# software/pi/common/mqtt_contract.py
"""Single source of truth for MQTT topics and payloads.
Keep payloads as trivial strings so ESP32 parsing stays dead simple."""

WOLF_STATE = "wolf/state"          # payload: idle | hungry | loving
WOLF_BARK = "wolf/bark"            # payload: "1"
CREEPER_EXPLODE = "creeper/explode"  # payload: "1"
DRAGON_DESTROY = "dragon/destroy"    # payload: "1"
PORTAL_OPEN = "portal/open"          # payload: "1"
PORTAL_SENSOR = "portal/sensor"      # payload: "inserted"  (stretch, node->CC)
ENDERMAN_ACTIVATE = "enderman/activate"  # payload: on | off

WOLF_STATES = ("idle", "hungry", "loving")

def heartbeat_topic(node: str) -> str:
    return f"system/heartbeat/{node}"
```

- [ ] **Step 4: Add `conftest.py` so `common` imports cleanly**

```python
# software/pi/conftest.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd software/pi && python -m pytest common/tests/test_contract.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add software/pi/common software/pi/conftest.py
git commit -m "feat: define MQTT contract with tests"
```

---

### Task 3: Install + configure Mosquitto broker on the brain Pi  `[CLAUDE-SW]` (on-device)

**Files:**
- Create: `software/pi/systemd/treasure-broker.note`

- [ ] **Step 1: Install Mosquitto**

```bash
sudo apt update && sudo apt install -y mosquitto mosquitto-clients
```

- [ ] **Step 2: Allow LAN clients (no auth — closed home network, party scope)**

Create `/etc/mosquitto/conf.d/treasure.conf`:
```
listener 1883 0.0.0.0
allow_anonymous true
```

- [ ] **Step 3: Restart and enable on boot**

```bash
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto
```

- [ ] **Step 4: Verify pub/sub works locally**

Terminal A: `mosquitto_sub -t 'test/#' -v`
Terminal B: `mosquitto_pub -t 'test/hello' -m '1'`
Expected: Terminal A prints `test/hello 1`

- [ ] **Step 5: Record the Pi's LAN IP for ESP32 config**

Run: `hostname -I`
Write the first IP into `software/pi/systemd/treasure-broker.note` (e.g. `BROKER_IP=192.168.1.50`). The ESP32 `config.h` will use this.

- [ ] **Step 6: Commit the note**

```bash
git add software/pi/systemd/treasure-broker.note
git commit -m "docs: record broker IP and mosquitto config steps"
```

---

### Task 4: Command center — button→message mapping (TDD)  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/command_center/commands.py`
- Test: `software/pi/command_center/tests/test_commands.py`

- [ ] **Step 1: Write the failing test**

```python
# software/pi/command_center/tests/test_commands.py
from command_center.commands import BUTTONS, button_message

def test_every_button_has_label_topic_payload_and_step():
    for b in BUTTONS:
        assert b["id"] and b["label"] and b["topic"] and b["payload"]
        assert isinstance(b["step"], int)

def test_buttons_in_story_order():
    steps = [b["step"] for b in BUTTONS]
    assert steps == sorted(steps)

def test_button_message_resolves_topic_payload():
    topic, payload = button_message("creeper_explode")
    assert topic == "creeper/explode"
    assert payload == "1"

def test_unknown_button_raises():
    import pytest
    with pytest.raises(KeyError):
        button_message("does_not_exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd software/pi && python -m pytest command_center/tests/test_commands.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'command_center.commands'`

- [ ] **Step 3: Write minimal implementation**

```python
# software/pi/command_center/commands.py
from common import mqtt_contract as c

# Story-ordered operator buttons. step = position in the 11-step hunt.
BUTTONS = [
    {"id": "wolf_hungry",    "label": "Wolf: Hungry",        "topic": c.WOLF_STATE,        "payload": "hungry", "step": 3},
    {"id": "wolf_loving",    "label": "Wolf: Bone given ❤",  "topic": c.WOLF_STATE,        "payload": "loving", "step": 4},
    {"id": "wolf_bark",      "label": "Wolf: Bark",          "topic": c.WOLF_BARK,         "payload": "1",      "step": 5},
    {"id": "creeper_explode","label": "Creeper: EXPLODE",    "topic": c.CREEPER_EXPLODE,   "payload": "1",      "step": 6},
    {"id": "dragon_destroy", "label": "Dragon: Destroy",     "topic": c.DRAGON_DESTROY,    "payload": "1",      "step": 7},
    {"id": "portal_open",    "label": "Portal: Open",        "topic": c.PORTAL_OPEN,       "payload": "1",      "step": 8},
    {"id": "enderman_on",    "label": "Enderman: Glow on",   "topic": c.ENDERMAN_ACTIVATE, "payload": "on",     "step": 9},
    {"id": "wolf_idle",      "label": "Wolf: reset to idle", "topic": c.WOLF_STATE,        "payload": "idle",   "step": 99},
    {"id": "enderman_off",   "label": "Enderman: off",       "topic": c.ENDERMAN_ACTIVATE, "payload": "off",    "step": 99},
]

_BY_ID = {b["id"]: b for b in BUTTONS}

def button_message(button_id: str):
    b = _BY_ID[button_id]
    return b["topic"], b["payload"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd software/pi && python -m pytest command_center/tests/test_commands.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add software/pi/command_center/commands.py software/pi/command_center/tests
git commit -m "feat: command-center button-to-message mapping with tests"
```

---

### Task 5: Command center — Flask app + web UI  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/command_center/app.py`
- Create: `software/pi/command_center/templates/index.html`
- Create: `software/pi/command_center/static/app.js`

- [ ] **Step 1: Write the Flask server**

```python
# software/pi/command_center/app.py
import time
import threading
from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
from common import mqtt_contract as c
from command_center.commands import BUTTONS, button_message

BROKER = "127.0.0.1"   # command center runs on the broker Pi
NODES = ["creeper", "enderman", "portal", "dragon"]

app = Flask(__name__)
_last_seen = {}        # node -> epoch seconds of last heartbeat

_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def _on_connect(client, userdata, flags, reason_code, properties):
    for node in NODES:
        client.subscribe(c.heartbeat_topic(node))

def _on_message(client, userdata, msg):
    parts = msg.topic.split("/")
    if len(parts) == 3 and parts[0] == "system" and parts[1] == "heartbeat":
        _last_seen[parts[2]] = time.time()

_client.on_connect = _on_connect
_client.on_message = _on_message
_client.connect(BROKER, 1883, 60)
threading.Thread(target=_client.loop_forever, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html", buttons=BUTTONS)

@app.route("/fire/<button_id>", methods=["POST"])
def fire(button_id):
    topic, payload = button_message(button_id)
    _client.publish(topic, payload, qos=1, retain=(topic == c.WOLF_STATE or topic == c.ENDERMAN_ACTIVATE))
    return jsonify(ok=True, topic=topic, payload=payload)

@app.route("/status")
def status():
    now = time.time()
    return jsonify({n: (now - _last_seen[n] < 10) if n in _last_seen else False for n in NODES})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

- [ ] **Step 2: Write the mobile page**

```html
<!-- software/pi/command_center/templates/index.html -->
<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>🎮 Treasure Hunt Control</title>
<style>
 body{font-family:system-ui;margin:0;background:#1d1f21;color:#eee}
 h1{font-size:18px;text-align:center;padding:10px;margin:0;background:#2b2b2b}
 #status{display:flex;gap:6px;justify-content:center;padding:8px;flex-wrap:wrap}
 .pill{padding:4px 10px;border-radius:12px;font-size:12px;background:#555}
 .pill.up{background:#2e7d32}.pill.down{background:#b71c1c}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px}
 button{font-size:20px;padding:22px 8px;border:0;border-radius:14px;color:#fff;background:#3a6ea5;touch-action:manipulation}
 button:active{transform:scale(.97);background:#2c5580}
 .big{grid-column:1/3;background:#c0392b;font-weight:700}
</style></head><body>
<h1>🟩 Treasure Hunt Control</h1>
<div id="status"></div>
<div class="grid">
 {% for b in buttons %}
   <button class="{{ 'big' if 'EXPLODE' in b.label else '' }}" onclick="fire('{{ b.id }}', this)">{{ b.label }}</button>
 {% endfor %}
</div>
<script src="/static/app.js"></script>
</body></html>
```

- [ ] **Step 3: Write the client JS**

```javascript
// software/pi/command_center/static/app.js
async function fire(id, el) {
  el.style.background = '#27ae60';
  try { await fetch('/fire/' + id, {method: 'POST'}); }
  finally { setTimeout(() => el.style.background = '', 400); }
}
async function poll() {
  try {
    const s = await (await fetch('/status')).json();
    document.getElementById('status').innerHTML =
      Object.entries(s).map(([n,up]) =>
        `<span class="pill ${up?'up':'down'}">${n} ${up?'●':'○'}</span>`).join('');
  } catch(e) {}
}
setInterval(poll, 3000); poll();
```

- [ ] **Step 4: Run it locally and smoke-test (broker must be running)**

Run: `cd software/pi && python -m command_center.app`
On the same machine open `http://localhost:8080`. In another terminal: `mosquitto_sub -t '#' -v`.
Tap **Creeper: EXPLODE**. Expected: subscriber prints `creeper/explode 1`.

- [ ] **Step 5: Commit**

```bash
git add software/pi/command_center
git commit -m "feat: command-center flask app, mobile UI, heartbeat status"
```

---

### Task 6: ESP32 base firmware + prove the pipeline  `[CLAUDE-SW]`

**Files:**
- Create: `software/esp32/platformio.ini`
- Create: `software/esp32/include/config.h`
- Create: `software/esp32/src/main.cpp`
- Create: `software/esp32/src/node_creeper.h` (stub: just blink the onboard LED on explode)

- [ ] **Step 1: Write `platformio.ini` (4 node environments)**

```ini
; software/esp32/platformio.ini
[env]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
    knolleary/PubSubClient@^2.8
    adafruit/Adafruit NeoPixel@^1.12.0
    madhephaestus/ESP32Servo@^3.0.5

[env:creeper]
build_flags = -D NODE_CREEPER
[env:enderman]
build_flags = -D NODE_ENDERMAN
[env:portal]
build_flags = -D NODE_PORTAL
[env:dragon]
build_flags = -D NODE_DRAGON
```

- [ ] **Step 2: Write `include/config.h`**

```cpp
// software/esp32/include/config.h
#pragma once
#define WIFI_SSID     "YOUR_HOME_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define MQTT_BROKER   "192.168.1.50"   // <- from Task 3 Step 5
#define MQTT_PORT     1883
```

- [ ] **Step 3: Write the base `main.cpp` (WiFi + MQTT + heartbeat + dispatch)**

```cpp
// software/esp32/src/main.cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"

#if   defined(NODE_CREEPER)
  #define NODE_NAME "creeper"
  #include "node_creeper.h"
#elif defined(NODE_ENDERMAN)
  #define NODE_NAME "enderman"
  #include "node_enderman.h"
#elif defined(NODE_PORTAL)
  #define NODE_NAME "portal"
  #include "node_portal.h"
#elif defined(NODE_DRAGON)
  #define NODE_NAME "dragon"
  #include "node_dragon.h"
#else
  #error "Define a NODE_* build flag"
#endif

WiFiClient espClient;
PubSubClient mqtt(espClient);
unsigned long lastBeat = 0;

void onMessage(char* topic, byte* payload, unsigned int len) {
  String msg; for (unsigned i = 0; i < len; i++) msg += (char)payload[i];
  nodeOnMessage(String(topic), msg);   // defined in node_*.h
}

void reconnect() {
  while (!mqtt.connected()) {
    if (mqtt.connect(NODE_NAME)) {
      nodeSubscribe(mqtt);             // defined in node_*.h
    } else { delay(1000); }
  }
}

void setup() {
  Serial.begin(115200);
  nodeSetup();                         // defined in node_*.h
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (!mqtt.connected()) reconnect();
  mqtt.loop();
  nodeLoop();                          // defined in node_*.h
  if (millis() - lastBeat > 3000) {
    lastBeat = millis();
    mqtt.publish((String("system/heartbeat/") + NODE_NAME).c_str(),
                 String(millis()).c_str());
  }
}
```

- [ ] **Step 4: Write `node_creeper.h` as a minimal LED-blink stub (real effect comes in Task 12)**

```cpp
// software/esp32/src/node_creeper.h
#pragma once
#include <PubSubClient.h>
#define LED_BUILTIN 2

inline void nodeSetup() { pinMode(LED_BUILTIN, OUTPUT); }
inline void nodeSubscribe(PubSubClient& mqtt) { mqtt.subscribe("creeper/explode"); }
inline void nodeLoop() {}
inline void nodeOnMessage(String topic, String msg) {
  if (topic == "creeper/explode") {
    for (int i = 0; i < 6; i++) { digitalWrite(LED_BUILTIN, HIGH); delay(80);
                                  digitalWrite(LED_BUILTIN, LOW); delay(80); }
  }
}
```

- [ ] **Step 5: Flash and verify end-to-end**

```bash
cd software/esp32 && pio run -e creeper -t upload && pio device monitor
```
Expected monitor output: dots then a successful connect. With the command center open on your phone, tap **Creeper: EXPLODE** → the ESP32 onboard LED blinks 6×, and the command-center status pill for `creeper` turns green.

- [ ] **Step 6: Commit**

```bash
git add software/esp32
git commit -m "feat: esp32 base firmware + creeper stub; pipeline proven end-to-end"
```

> ✅ **Milestone:** phone → MQTT → ESP32 works. The rest is filling in real effects and physical builds.

---

# PHASE 1 — Characters (Days 3–6, parallel tracks)

Each character is one `[USER-HW]` build task and one `[CLAUDE-SW]` software task. They can proceed in any order; hardware and software for the same character meet at its verification step.

## Wolf

### Task 7: Wolf body + screen + speaker + mouth servo  `[USER-HW]`

**Materials:** cardboard box, white faux-fur/carpet, hot glue, LCD screen + cable, Raspberry Pi 3 (brain), amplifier + speakers, 1 PWM servo, 5V supply/power bank, lightweight flap/jaw for the mouth.

- [ ] **Step 1:** Build the cardboard wolf head/body; cut a rectangular window for the LCD where the eyes go; cover with fur, leaving the screen and a mouth opening clear.
- [ ] **Step 2:** Mount the LCD behind the eye window; mount the Pi inside with ventilation; route HDMI/power.
- [ ] **Step 3:** Mount the amplifier + speakers facing out (muffle-free); connect to the Pi's 3.5mm/USB audio.
- [ ] **Step 4:** Mount the mouth servo so its horn opens/closes the jaw flap ~30°. Signal wire → Pi **GPIO18**, servo V+ → 5V, GND common with Pi GND.
- [ ] **Step 5 (verify):** Power the Pi; confirm the screen lights, speakers play `speaker-test -t wav`, and the servo physically moves the jaw when tested (`software/pi/wolf/mouth.py` self-test in Task 9).

### Task 8: Wolf state machine (pure logic, TDD)  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/wolf/states.py`
- Test: `software/pi/wolf/tests/test_states.py`

- [ ] **Step 1: Write the failing test**

```python
# software/pi/wolf/tests/test_states.py
from wolf.states import WolfMachine

def test_starts_idle_mouth_closed():
    w = WolfMachine()
    assert w.state == "idle"
    assert w.mouth_open is False

def test_loving_opens_mouth_and_shows_hearts():
    w = WolfMachine()
    w.set_state("loving")
    assert w.state == "loving"
    assert w.mouth_open is True
    assert w.eye_mode == "hearts"

def test_hungry_mode_eyes_and_closed_mouth():
    w = WolfMachine()
    w.set_state("hungry")
    assert w.eye_mode == "hungry"
    assert w.mouth_open is False

def test_invalid_state_ignored():
    w = WolfMachine()
    w.set_state("loving")
    w.set_state("banana")          # ignored, keeps last valid
    assert w.state == "loving"

def test_bark_is_transient_event_not_state():
    w = WolfMachine()
    w.set_state("idle")
    assert w.consume_bark() is False
    w.trigger_bark()
    assert w.consume_bark() is True
    assert w.consume_bark() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd software/pi && python -m pytest wolf/tests/test_states.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'wolf.states'`

- [ ] **Step 3: Write minimal implementation**

```python
# software/pi/wolf/states.py
from common.mqtt_contract import WOLF_STATES

_EYE = {"idle": "wander", "hungry": "hungry", "loving": "hearts"}

class WolfMachine:
    def __init__(self):
        self.state = "idle"
        self._bark = False

    def set_state(self, state: str):
        if state in WOLF_STATES:
            self.state = state

    @property
    def eye_mode(self) -> str:
        return _EYE[self.state]

    @property
    def mouth_open(self) -> bool:
        return self.state == "loving"

    def trigger_bark(self):
        self._bark = True

    def consume_bark(self) -> bool:
        b, self._bark = self._bark, False
        return b
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd software/pi && python -m pytest wolf/tests/test_states.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add software/pi/wolf/states.py software/pi/wolf/tests
git commit -m "feat: wolf state machine with tests"
```

### Task 9: Wolf mouth servo wrapper  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/wolf/mouth.py`

- [ ] **Step 1: Write the servo wrapper with a dev fallback**

```python
# software/pi/wolf/mouth.py
"""Mouth servo on GPIO18. Use --no-servo / Mouth(enabled=False) off-Pi."""
class Mouth:
    def __init__(self, pin=18, enabled=True):
        self._servo = None
        if enabled:
            from gpiozero import AngularServo
            from gpiozero.pins.pigpio import PiGPIOFactory
            self._servo = AngularServo(pin, min_angle=0, max_angle=40,
                                       pin_factory=PiGPIOFactory())
        self.close()

    def open(self):
        if self._servo: self._servo.angle = 40
    def close(self):
        if self._servo: self._servo.angle = 0

if __name__ == "__main__":   # self-test on the Pi: python -m wolf.mouth
    import time
    m = Mouth()
    for _ in range(3):
        m.open(); time.sleep(0.5); m.close(); time.sleep(0.5)
```

- [ ] **Step 2: Verify on the Pi (requires `sudo pigpiod` running)**

```bash
sudo pigpiod
cd software/pi && python -m wolf.mouth
```
Expected: the jaw opens and closes 3 times.

- [ ] **Step 3: Commit**

```bash
git add software/pi/wolf/mouth.py
git commit -m "feat: wolf mouth servo wrapper with dev fallback"
```

### Task 10: Wolf app — render eyes, play sound, drive mouth  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/wolf/wolf_app.py`
- Create (assets): `software/pi/wolf/assets/bark.wav`, `whine.wav`, `happybark.wav`

- [ ] **Step 1: Obtain three short royalty-free WAVs**

Download three short dog sounds (bark, whine, happy bark) from a CC0 source (e.g. freesound.org) and save them as the three filenames above. Keep each < 2s.

- [ ] **Step 2: Write the pygame app**

```python
# software/pi/wolf/wolf_app.py
import os, random, argparse
import pygame
import paho.mqtt.client as mqtt
from common import mqtt_contract as c
from wolf.states import WolfMachine
from wolf.mouth import Mouth

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
BLACK, WHITE, RED, GREEN = (0,0,0), (240,240,240), (220,40,40), (60,200,90)

def draw_eyes(screen, machine, t):
    screen.fill(BLACK)
    w, h = screen.get_size()
    cx1, cx2, cy = w//3, 2*w//3, h//2
    if machine.eye_mode == "hearts":
        for cx in (cx1, cx2):
            pygame.draw.circle(screen, RED, (cx-25, cy-10), 30)
            pygame.draw.circle(screen, RED, (cx+25, cy-10), 30)
            pygame.draw.polygon(screen, RED, [(cx-55,cy),(cx+55,cy),(cx,cy+60)])
    else:
        dx = int(20*random.uniform(-1,1)) if machine.eye_mode=="wander" else 0
        droop = 18 if machine.eye_mode=="hungry" else 0
        for cx in (cx1, cx2):
            pygame.draw.circle(screen, WHITE, (cx, cy), 70)
            pygame.draw.circle(screen, BLACK, (cx+dx, cy+droop), 28)
    pygame.display.flip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-servo", action="store_true")
    ap.add_argument("--windowed", action="store_true")
    ap.add_argument("--broker", default="127.0.0.1")
    args = ap.parse_args()

    pygame.init(); pygame.mixer.init()
    flags = 0 if args.windowed else pygame.FULLSCREEN
    screen = pygame.display.set_mode((800, 480), flags)
    snd = {n: pygame.mixer.Sound(os.path.join(ASSETS, f"{n}.wav"))
           for n in ("bark", "whine", "happybark")}

    machine = WolfMachine()
    mouth = Mouth(enabled=not args.no_servo)

    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    def on_msg(c_, u, m):
        p = m.payload.decode()
        if m.topic == c.WOLF_STATE:
            machine.set_state(p)
            (mouth.open if machine.mouth_open else mouth.close)()
            if p == "loving": snd["happybark"].play()
        elif m.topic == c.WOLF_BARK:
            machine.trigger_bark()
    cli.on_message = on_msg
    cli.connect(args.broker, 1883, 60)
    cli.subscribe(c.WOLF_STATE); cli.subscribe(c.WOLF_BARK)
    cli.loop_start()

    clock = pygame.time.Clock(); t = 0; idle_timer = 0
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE):
                running = False
        if machine.consume_bark():
            snd["bark"].play()
        # ambient: occasional whine when hungry/idle
        idle_timer += 1
        if idle_timer > 300 and machine.state != "loving":
            idle_timer = 0
            if random.random() < 0.5: snd["whine"].play()
        draw_eyes(screen, machine, t); t += 1
        clock.tick(20)
    cli.loop_stop(); pygame.quit()

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify off-Pi (windowed, no servo)**

Run: `cd software/pi && python -m wolf.wolf_app --windowed --no-servo`
With `mosquitto` running locally: `mosquitto_pub -t wolf/state -m loving` → eyes become hearts + happy bark; `-m hungry` → drooping eyes; `mosquitto_pub -t wolf/bark -m 1` → bark plays.

- [ ] **Step 4: Verify on the Pi (fullscreen + servo)**

Run on the brain Pi (with `pigpiod` running): `python -m wolf.wolf_app`
Use the command center buttons. Expected: eyes render fullscreen on the LCD, mouth servo opens on "Bone given", sounds play through the amplifier.

- [ ] **Step 5: Commit**

```bash
git add software/pi/wolf/wolf_app.py
git commit -m "feat: wolf pygame app — eyes, sound, mouth driven by MQTT"
```

## Creeper

### Task 11: Creeper balloon rig + pin servo + LEDs + confetti  `[USER-HW]`

**Materials:** green balloons (small + 1 central), a central "pillar" support, 1 PWM servo + needle/pin, discrete white LEDs + resistors, ESP32, 5V relay + electric confetti popper (or relay-fired popper), power bank.

- [ ] **Step 1:** Build the creeper: central pillar balloon with small green water balloons glued around it; creeper face on the front.
- [ ] **Step 2:** Mount the servo so its horn drives a pin toward the **central** balloon (the pop scatters the rest).
- [ ] **Step 3:** Mount white LEDs behind the face for the flash; wire LED+resistor to an ESP32 GPIO (e.g. GPIO5) and GND.
- [ ] **Step 4:** Wire the servo signal to GPIO13, V+ 5V, common GND. Wire the relay IN to GPIO12, relay switches the confetti popper trigger.
- [ ] **Step 5 (verify):** With Task 12 firmware flashed, fire **Creeper: EXPLODE** from the command center → LEDs flash, servo drives the pin (do a dry run **without** the balloon first, then armed), relay clicks/fires confetti.

### Task 12: Creeper firmware — flash → pop → confetti  `[CLAUDE-SW]`

**Files:**
- Modify: `software/esp32/src/node_creeper.h` (replace the Task 6 stub)

- [ ] **Step 1: Replace the stub with the real effect**

```cpp
// software/esp32/src/node_creeper.h
#pragma once
#include <PubSubClient.h>
#include <ESP32Servo.h>

#define LED_PIN    5
#define SERVO_PIN  13
#define RELAY_PIN  12
#define PIN_REST   20      // servo angle: pin retracted
#define PIN_STAB   110     // servo angle: pin driven into balloon

static Servo creeperServo;

inline void nodeSetup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT); digitalWrite(RELAY_PIN, LOW);
  creeperServo.attach(SERVO_PIN);
  creeperServo.write(PIN_REST);
}
inline void nodeSubscribe(PubSubClient& mqtt) { mqtt.subscribe("creeper/explode"); }
inline void nodeLoop() {}

inline void nodeOnMessage(String topic, String msg) {
  if (topic != "creeper/explode") return;
  // 1) telegraph: white flash, accelerating
  for (int d = 300; d > 60; d -= 40) {
    digitalWrite(LED_PIN, HIGH); delay(d/2);
    digitalWrite(LED_PIN, LOW);  delay(d/2);
  }
  digitalWrite(LED_PIN, HIGH);            // hold bright
  // 2) POP the central balloon
  creeperServo.write(PIN_STAB); delay(250);
  creeperServo.write(PIN_REST);
  // 3) confetti
  digitalWrite(RELAY_PIN, HIGH); delay(300); digitalWrite(RELAY_PIN, LOW);
  delay(200); digitalWrite(LED_PIN, LOW);
}
```

- [ ] **Step 2: Flash and dry-run (no balloon armed)**

```bash
cd software/esp32 && pio run -e creeper -t upload
```
Fire **Creeper: EXPLODE**. Expected: flash accelerates, servo sweeps to stab and back, relay pulses. Verify motion clears the balloon position before arming a real balloon.

- [ ] **Step 3: Commit**

```bash
git add software/esp32/src/node_creeper.h
git commit -m "feat: creeper firmware — flash, balloon pop, confetti"
```

## Enderman

### Task 13: Enderman body + belly ring + eyes + key  `[USER-HW]`

**Materials:** tall black body (cardboard/fabric), NeoPixel 8-ring (belly), 2 white LEDs (eyes), the chest key mounted visibly in the belly, ESP32, 5V power.

- [ ] **Step 1:** Build the tall enderman; cut a belly opening; mount the 8-ring behind a diffuser so the belly glows.
- [ ] **Step 2:** Mount 2 white LEDs as eyes near the top.
- [ ] **Step 3:** Hang/clip the physical chest key in the lit belly so it's visible and grabbable.
- [ ] **Step 4:** Wire ring DIN → GPIO4 (+5V, GND); eyes → GPIO5 via resistor.
- [ ] **Step 5 (verify):** With Task 14 firmware, **Enderman: Glow on** lights belly (purple pulse) + eyes; **off** turns them off.

### Task 14: Enderman firmware — eyes + belly glow  `[CLAUDE-SW]`

**Files:**
- Create: `software/esp32/src/node_enderman.h`

- [ ] **Step 1: Write the firmware**

```cpp
// software/esp32/src/node_enderman.h
#pragma once
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

#define RING_PIN  4
#define EYES_PIN  5
#define RING_N    8

static Adafruit_NeoPixel ring(RING_N, RING_PIN, NEO_GRB + NEO_KHZ800);
static bool endermanOn = false;
static uint8_t phase = 0;

inline void nodeSetup() {
  pinMode(EYES_PIN, OUTPUT); digitalWrite(EYES_PIN, LOW);
  ring.begin(); ring.clear(); ring.show();
}
inline void nodeSubscribe(PubSubClient& mqtt) { mqtt.subscribe("enderman/activate"); }

inline void nodeLoop() {            // purple breathing when on
  if (!endermanOn) return;
  phase += 2;
  uint8_t b = 40 + (uint8_t)(40 * (1 + sinf(phase * 0.05f)));
  for (int i = 0; i < RING_N; i++) ring.setPixelColor(i, ring.Color(b, 0, b));
  ring.show(); delay(20);
}
inline void nodeOnMessage(String topic, String msg) {
  if (topic != "enderman/activate") return;
  endermanOn = (msg == "on");
  digitalWrite(EYES_PIN, endermanOn ? HIGH : LOW);
  if (!endermanOn) { ring.clear(); ring.show(); }
}
```

- [ ] **Step 2: Flash and verify**

```bash
cd software/esp32 && pio run -e enderman -t upload
```
Fire **Enderman: Glow on** → eyes on, belly breathes purple. **off** → dark.

- [ ] **Step 3: Commit**

```bash
git add software/esp32/src/node_enderman.h
git commit -m "feat: enderman firmware — eyes + breathing belly ring"
```

## Portal

### Task 15: Portal door + curtain + cubes + motor latch  `[USER-HW]`

**Materials:** a real doorway, purple sheer curtain, foam/cardboard cubes (one removable obsidian cube), DC motor + H-bridge, wire/string tied to the door latch, flexible NeoPixel strip for frame edge-glow, ESP32, 5V + motor supply. Optional reed switch + magnet for cube detection.

- [ ] **Step 1:** Hang the purple curtain in the doorway; arrange cubes around the frame; leave one cube slot empty for the obsidian.
- [ ] **Step 2:** Tie a string from the door latch/bolt to the DC motor spindle so winding the motor pulls the latch open.
- [ ] **Step 3:** Wire the motor to the H-bridge outputs; H-bridge IN1→GPIO25, IN2→GPIO26, ENA→GPIO27 (or tie ENA high); motor supply per the H-bridge spec, GND common with ESP32.
- [ ] **Step 4:** Mount the flex NeoPixel strip around the frame; DIN→GPIO4.
- [ ] **Step 5 (optional):** Mount a reed switch where the obsidian cube seats, with a magnet in the cube; wire to GPIO34.
- [ ] **Step 6 (verify):** With Task 16 firmware, **Portal: Open** runs the motor for a timed pulse and pulls the latch; the frame glows purple. Tune the pulse duration in firmware to fully release the latch without over-winding.

### Task 16: Portal firmware — motor latch pulse + frame glow  `[CLAUDE-SW]`

**Files:**
- Create: `software/esp32/src/node_portal.h`

- [ ] **Step 1: Write the firmware**

```cpp
// software/esp32/src/node_portal.h
#pragma once
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

#define IN1 25
#define IN2 26
#define ENA 27
#define STRIP_PIN 4
#define STRIP_N 20
#define PULL_MS 900        // TUNE: how long to run the motor to pull the latch
#define REED_PIN 34        // optional cube sensor

static Adafruit_NeoPixel frame(STRIP_N, STRIP_PIN, NEO_GRB + NEO_KHZ800);

static void motorPull() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW); analogWrite(ENA, 255);
  delay(PULL_MS);
  digitalWrite(IN1, LOW);  digitalWrite(IN2, LOW); analogWrite(ENA, 0);   // stop/coast
}
inline void nodeSetup() {
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT); pinMode(ENA, OUTPUT);
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  pinMode(REED_PIN, INPUT_PULLUP);
  frame.begin();
  for (int i=0;i<STRIP_N;i++) frame.setPixelColor(i, frame.Color(80,0,120));
  frame.show();
}
inline void nodeSubscribe(PubSubClient& mqtt) { mqtt.subscribe("portal/open"); }

static bool lastReed = true;
inline void nodeLoop() {            // stretch: report cube insertion
  bool reed = digitalRead(REED_PIN);
  if (lastReed && !reed) { /* edge: cube seated */ }
  lastReed = reed;
}
inline void nodeOnMessage(String topic, String msg) {
  if (topic == "portal/open") {
    for (int i=0;i<STRIP_N;i++) frame.setPixelColor(i, frame.Color(160,40,220));
    frame.show();
    motorPull();
  }
}
```

> Note: `analogWrite` is available on ESP32 Arduino core ≥3.0. If on an older core, replace ENA control with `ledcAttach`/`ledcWrite`.

- [ ] **Step 2: Flash and verify (door latch disconnected first)**

```bash
cd software/esp32 && pio run -e portal -t upload
```
Fire **Portal: Open** → motor runs ~0.9s then stops; frame brightens. Connect the latch string and tune `PULL_MS` until the latch reliably releases.

- [ ] **Step 3: Commit**

```bash
git add software/esp32/src/node_portal.h
git commit -m "feat: portal firmware — motor latch pulse + frame glow"
```

## Ender Dragon

### Task 17: Paper dragon + ceiling rig + release + power core  `[USER-HW]`

**Materials:** lightweight paper/card dragon, string to ceiling so it circles, a servo-held trapdoor/catch holding the obsidian cube, NeoPixel 8-ring as a glowing "core", ESP32, 5V power.

- [ ] **Step 1:** Build the paper dragon; rig it to the ceiling on a string so it can swing/circle.
- [ ] **Step 2:** Build a small belly catch held closed by a servo horn; the obsidian cube sits in the catch.
- [ ] **Step 3:** Mount the 8-ring as the dragon's glowing core (diffused).
- [ ] **Step 4:** Wire servo signal→GPIO13 (5V, GND); ring DIN→GPIO4.
- [ ] **Step 5 (verify):** With Task 18 firmware, **Dragon: Destroy** flares the core then drops the cube via the servo catch.

### Task 18: Dragon firmware — power-core flare + obsidian drop  `[CLAUDE-SW]`

**Files:**
- Create: `software/esp32/src/node_dragon.h`

- [ ] **Step 1: Write the firmware**

```cpp
// software/esp32/src/node_dragon.h
#pragma once
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Servo.h>

#define RING_PIN 4
#define RING_N   8
#define SERVO_PIN 13
#define CATCH_CLOSED 20
#define CATCH_OPEN   110

static Adafruit_NeoPixel core(RING_N, RING_PIN, NEO_GRB + NEO_KHZ800);
static Servo catchServo;

inline void nodeSetup() {
  core.begin();
  for (int i=0;i<RING_N;i++) core.setPixelColor(i, core.Color(120,0,160));
  core.show();
  catchServo.attach(SERVO_PIN); catchServo.write(CATCH_CLOSED);
}
inline void nodeSubscribe(PubSubClient& mqtt) { mqtt.subscribe("dragon/destroy"); }
inline void nodeLoop() {}

inline void nodeOnMessage(String topic, String msg) {
  if (topic != "dragon/destroy") return;
  // flare: ramp to white-hot
  for (int b = 0; b <= 255; b += 15) {
    for (int i=0;i<RING_N;i++) core.setPixelColor(i, core.Color(b,b,b));
    core.show(); delay(40);
  }
  // die: drop to black
  core.clear(); core.show();
  // release the obsidian
  catchServo.write(CATCH_OPEN); delay(600); catchServo.write(CATCH_CLOSED);
}
```

- [ ] **Step 2: Flash and verify**

```bash
cd software/esp32 && pio run -e dragon -t upload
```
Fire **Dragon: Destroy** → core ramps bright then goes dark, servo opens the catch (cube drops) and re-closes.

- [ ] **Step 3: Commit**

```bash
git add software/esp32/src/node_dragon.h
git commit -m "feat: dragon firmware — power-core flare + obsidian drop"
```

---

# PHASE 2 — Integration & dry run (Days 7–8)

### Task 19: Autostart services on the brain Pi  `[CLAUDE-SW]`

**Files:**
- Create: `software/pi/systemd/treasure-command-center.service`
- Create: `software/pi/systemd/treasure-wolf.service`

- [ ] **Step 1: Command-center service**

```ini
# software/pi/systemd/treasure-command-center.service
[Unit]
Description=Treasure Hunt Command Center
After=network-online.target mosquitto.service
[Service]
WorkingDirectory=/home/kam/EProjects/dani6/software/pi
ExecStart=/usr/bin/python3 -m command_center.app
Restart=always
[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Wolf service (needs display + pigpiod)**

```ini
# software/pi/systemd/treasure-wolf.service
[Unit]
Description=Treasure Hunt Wolf App
After=graphical.target mosquitto.service
[Service]
Environment=DISPLAY=:0
WorkingDirectory=/home/kam/EProjects/dani6/software/pi
ExecStartPre=/usr/bin/pigpiod
ExecStart=/usr/bin/python3 -m wolf.wolf_app
Restart=always
[Install]
WantedBy=graphical.target
```

- [ ] **Step 3: Install, enable, reboot, verify**

```bash
sudo cp software/pi/systemd/treasure-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable treasure-command-center treasure-wolf
sudo reboot
```
After reboot: command center reachable from your phone, wolf eyes on the LCD — with nothing manually started.

- [ ] **Step 4: Commit**

```bash
git add software/pi/systemd
git commit -m "feat: systemd autostart for command center and wolf"
```

### Task 20: Write the clue cards  `[BOTH]`

**Files:**
- Create: `clues/clues.md`

- [ ] **Step 1: Write 4 rhyming, age-6 clues matching the flow**

```markdown
# Treasure Hunt Clues (print these)

**Clue 1 (start):** Buzzy friends are working hard / find the HIVE out in the yard!
  _(bad weather: ...the hive that hums inside — go check the KITCHEN!)_

**Clue 2 (bee delivers):** A rattly friend has lost a bone / down in the BASEMENT, all alone.

**Clue 3 (wolf, after bone):** Woof! I'm happy, off you go / the CREEPER's waiting — don't be slow!

**Clue 4 (after creeper pop):** BOOM! That blast was quite a thing / now find the DRAGON, on the wing! _(bedroom)_

**Final (after dragon → obsidian):** Place the cube to mend the gate / the PORTAL opens — meet your fate!
```

- [ ] **Step 2: Commit**

```bash
git add clues/clues.md
git commit -m "docs: treasure hunt clue cards"
```

### Task 21: Full 11-step dry run  `[BOTH]`

- [ ] **Step 1:** Power everything; confirm all 4 status pills green in the command center.
- [ ] **Step 2:** Walk the full sequence end-to-end with a stand-in "player", pressing each button at the right beat:
  - hand Clue 1 → bee/clue 2 → bone to wolf (**Hungry** then **Bone given**) → **Bark** + Clue 3 → **Creeper EXPLODE** + Clue 4 → **Dragon Destroy** (obsidian drops) → place cube + **Portal Open** → **Enderman Glow on** → key opens chest.
- [ ] **Step 3:** Note any timing/volume/range issues; fix firmware constants (`PULL_MS`, servo angles, flash timing) and re-flash affected nodes.
- [ ] **Step 4:** Re-run until two clean passes in a row. Commit any tuning changes.

```bash
git commit -am "tune: timing/angles from dry run"
```

---

# PHASE 3 — Stretch & buffer (Day 9)

### Task 22: Bee delivery — fallback first, autonomy if time  `[USER-HW]` + `[CLAUDE-SW]`

- [ ] **Step 1 (fallback, must work):** Prepare a non-autonomous bee that delivers Clue 2 — bee body on a string/pole, or simply handed over by an adult "beekeeper". This guarantees step 2 regardless of the drone.
- [ ] **Step 2 (stretch):** Set up the Jetson + quadcopter; verify manual flight + the WiFi camera feed.
- [ ] **Step 3 (stretch):** Attempt simple autonomous behavior (hover + short guided hop toward the basement waypoint). **Time-box to Day 9.** If not rock-solid, use the fallback for the party — do not risk the hunt on the drone.
- [ ] **Step 4:** Decide fallback-vs-drone and document the choice; commit any helper scripts under `software/jetson/`.

### Task 23: Buffer  `[BOTH]`

- [ ] Catch up on any character that slipped; re-run Task 21 dry run after fixes.

---

# PHASE 4 — Dress rehearsal & freeze (Day 10)

### Task 24: Final rehearsal & party-day checklist  `[BOTH]`

- [ ] **Step 1:** Charge every power bank / battery; label each with its character.
- [ ] **Step 2:** Cold-boot test: power the Pi and all nodes from off → confirm autostart brings up command center + wolf + all green pills with zero manual steps.
- [ ] **Step 3:** Full dress rehearsal of all 11 steps, in costume/decoration, at real locations (and the bad-weather alternates).
- [ ] **Step 4:** Print clue cards; place obsidian cube and key; stage each character at its location.
- [ ] **Step 5:** Freeze code. Tag the release.

```bash
git tag party-ready
git commit -am "chore: party-day freeze" --allow-empty
```

- [ ] **Step 6 (party day):** Power on, verify pills green, hand kids Clue 1, and drive the hunt from your phone. 🎉

---

## Self-review notes
- **Spec coverage:** command center (T4–5,19), MQTT contract (T2), broker (T3), wolf eyes/sound/mouth (T8–10, hardware T7), creeper (T11–12), enderman (T13–14), portal motor+H-bridge (T15–16), dragon (T17–18), bee fallback+stretch (T22), clues + bad-weather alts (T20), heartbeat status board (T5), 10-day schedule (phases), reliability/Wizard-of-Oz (every beat is a button). All spec sections mapped.
- **LED allocation** matches spec: enderman belly = ring (T14), dragon core = ring (T18), creeper flash = white LEDs (T12), portal frame = flex strip (T16).
- **Servo allocation** matches spec (3 servos: wolf mouth T9, creeper pin T12, dragon catch T18); confetti on a relay (T12). No 4th servo required.
- **Pin assignments** are consistent within each node file; cross-node reuse of GPIO numbers is fine (separate boards).
- **Open item:** confetti popper type only affects T11 Step 4 wiring (relay-fired vs manual) — does not change firmware.
