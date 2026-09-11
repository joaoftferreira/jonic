# Enderman 16-LED NeoPixel Color Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive a 16-LED WS2812 ring on the enderman ESP32 that lights all LEDs in a solid color chosen from a color picker in the command-center portal, remembered across on/off toggles.

**Architecture:** A new retained MQTT topic `enderman/color` carries a `#RRGGBB` hex string. The portal publishes it from an `<input type="color">`; the ESP32 stores it and fills all 16 pixels solid whenever it is on. Because the topic is retained, every ON uses the last-picked color with no Pi-side state.

**Tech Stack:** ESP32 / Arduino / Adafruit_NeoPixel (firmware), Python Flask + paho-mqtt (portal), pytest.

## Global Constraints

- MQTT payloads stay as trivial strings (project rule in `mqtt_contract.py`). Color payload is a `#RRGGBB` string.
- Color and activate topics are published **retained** (`qos=1, retain=True`).
- Ring data pin is **GPIO 4** (unchanged). Ring count is **16**.
- Follow existing file patterns; do not restructure unrelated code.
- Python tests run from `software/pi/` with `python -m pytest` (conftest.py adds it to `sys.path`).

---

### Task 1: MQTT contract — add `ENDERMAN_COLOR`

**Files:**
- Modify: `software/pi/common/mqtt_contract.py`
- Test: `software/pi/common/tests/test_contract.py`

**Interfaces:**
- Produces: `mqtt_contract.ENDERMAN_COLOR == "enderman/color"` (module-level `str` constant), consumed by Task 2.

- [ ] **Step 1: Write the failing test**

Add to `software/pi/common/tests/test_contract.py`:

```python
def test_enderman_color_topic():
    assert c.ENDERMAN_COLOR == "enderman/color"
```

Also extend the existing uniqueness test's topic list to include it:

```python
def test_topics_are_unique_and_namespaced():
    topics = [c.WOLF_STATE, c.WOLF_BARK, c.CREEPER_EXPLODE,
              c.DRAGON_DESTROY, c.PORTAL_OPEN, c.ENDERMAN_ACTIVATE,
              c.ENDERMAN_COLOR]
    assert len(topics) == len(set(topics))
    assert all("/" in t for t in topics)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd software/pi && python -m pytest common/tests/test_contract.py -v`
Expected: FAIL with `AttributeError: module 'common.mqtt_contract' has no attribute 'ENDERMAN_COLOR'`

- [ ] **Step 3: Write minimal implementation**

In `software/pi/common/mqtt_contract.py`, add after the `ENDERMAN_ACTIVATE` line:

```python
ENDERMAN_COLOR = "enderman/color"    # payload: "#RRGGBB", retained
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd software/pi && python -m pytest common/tests/test_contract.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add software/pi/common/mqtt_contract.py software/pi/common/tests/test_contract.py
git commit -m "feat(enderman): add enderman/color MQTT topic"
```

---

### Task 2: Portal color route with validation

**Files:**
- Modify: `software/pi/command_center/app.py`
- Create: `software/pi/command_center/tests/test_app.py`

**Interfaces:**
- Consumes: `mqtt_contract.ENDERMAN_COLOR` from Task 1.
- Produces: HTTP route `POST /enderman/color` with form field `color`. On valid `#RRGGBB`: publishes `(ENDERMAN_COLOR, "#rrggbb", qos=1, retain=True)`, returns JSON `{ok: true, color}` (200). On invalid: returns JSON `{ok: false}` (400), no publish. Consumed by Task 3 (the UI POSTs here).

- [ ] **Step 1: Write the failing test**

Create `software/pi/command_center/tests/test_app.py`:

```python
import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def app_and_client():
    # Patch paho's Client so importing app.py does not open a real socket.
    with patch("paho.mqtt.client.Client", return_value=MagicMock()):
        import command_center.app as appmod
        importlib.reload(appmod)  # re-run module body under the patch
        appmod.app.config["TESTING"] = True
        yield appmod.app.test_client(), appmod._client


def test_color_route_publishes_retained(app_and_client):
    client, mq = app_and_client
    resp = client.post("/enderman/color", data={"color": "#00FF88"})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    mq.publish.assert_called_once_with(
        "enderman/color", "#00FF88", qos=1, retain=True)


def test_color_route_rejects_bad_input(app_and_client):
    client, mq = app_and_client
    resp = client.post("/enderman/color", data={"color": "purple"})
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False
    mq.publish.assert_not_called()


def test_color_route_rejects_missing_hash(app_and_client):
    client, mq = app_and_client
    resp = client.post("/enderman/color", data={"color": "00FF88"})
    assert resp.status_code == 400
    mq.publish.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd software/pi && python -m pytest command_center/tests/test_app.py -v`
Expected: FAIL — 404 on the POST (route not defined), so the `status_code == 200`/`400` assertions fail.

- [ ] **Step 3: Write minimal implementation**

In `software/pi/command_center/app.py`, add `import re` at the top with the other imports, and add this route after the existing `fire` route (before `status`):

```python
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

@app.route("/enderman/color", methods=["POST"])
def enderman_color():
    color = request.form.get("color", "")
    if not _HEX_RE.match(color):
        return jsonify(ok=False, error="expected #RRGGBB"), 400
    _client.publish(c.ENDERMAN_COLOR, color, qos=1, retain=True)
    return jsonify(ok=True, color=color)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd software/pi && python -m pytest command_center/tests/test_app.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full Python suite to check nothing regressed**

Run: `cd software/pi && python -m pytest -q`
Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add software/pi/command_center/app.py software/pi/command_center/tests/test_app.py
git commit -m "feat(portal): add /enderman/color route publishing retained hex"
```

---

### Task 3: Portal UI — color picker control

**Files:**
- Modify: `software/pi/command_center/templates/index.html`
- Modify: `software/pi/command_center/static/app.js`

**Interfaces:**
- Consumes: `POST /enderman/color` from Task 2.
- Produces: no code interface; a user-facing control. Verified manually (no JS test harness in this repo).

- [ ] **Step 1: Add the color control to the template**

In `software/pi/command_center/templates/index.html`, add these style rules inside the existing `<style>` block (before `</style>`):

```css
 #ender-controls{display:flex;align-items:center;justify-content:center;gap:10px;padding:10px}
 #ender-controls label{font-size:15px}
 #ender-color{width:56px;height:40px;border:0;border-radius:10px;background:#2b2b2b;padding:0}
```

Then add this block immediately after the closing `</div>` of `<div class="grid">` (i.e. after the buttons loop, before `<script>`):

```html
<div id="ender-controls">
  <label for="ender-color">🟪 Enderman color</label>
  <input type="color" id="ender-color" value="#8000a0">
</div>
```

- [ ] **Step 2: Add the change handler to app.js**

In `software/pi/command_center/static/app.js`, add at the end of the file:

```javascript
const enderColor = document.getElementById('ender-color');
if (enderColor) {
  enderColor.addEventListener('change', async () => {
    const color = enderColor.value.toUpperCase();  // "#RRGGBB"
    try {
      await fetch('/enderman/color', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'color=' + encodeURIComponent(color),
      });
    } catch (e) {}
  });
}
```

- [ ] **Step 3: Manually verify the control renders and posts**

Run the portal locally (a real broker is optional — the POST still returns 200/400 regardless):

Run: `cd software/pi && python -m command_center.app` then open `http://localhost:8080`.
Expected: a "🟪 Enderman color" swatch appears under the buttons. Picking a color issues `POST /enderman/color` (visible in the Flask console log as a 200). Stop the server with Ctrl-C.

Note: `command_center.app` opens an MQTT connection to `127.0.0.1:1883` on import. If no broker is running it will raise `ConnectionRefusedError` on startup — either start `mosquitto` first, or skip this manual check and rely on the Task 2 tests plus the on-device check in Task 4.

- [ ] **Step 4: Commit**

```bash
git add software/pi/command_center/templates/index.html software/pi/command_center/static/app.js
git commit -m "feat(portal): add enderman color picker control"
```

---

### Task 4: Firmware — 16-px solid color ring

**Files:**
- Modify: `software/esp32/src/node_enderman.h`

**Interfaces:**
- Consumes: MQTT topics `enderman/activate` (`on`/`off`) and `enderman/color` (`#RRGGBB`).
- Produces: firmware behavior only. Verified by a clean PlatformIO build.

- [ ] **Step 1: Replace the enderman node file**

Overwrite `software/esp32/src/node_enderman.h` with:

```cpp
#pragma once
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

#define RING_PIN  4
#define EYES_PIN  5
#define RING_N    16

static Adafruit_NeoPixel ring(RING_N, RING_PIN, NEO_GRB + NEO_KHZ800);
static bool endermanOn = false;
static uint32_t currentColor = 0x8000A0;  // default purple

inline void fillRing() {
  for (int i = 0; i < RING_N; i++) ring.setPixelColor(i, currentColor);
  ring.show();
}

inline void nodeSetup() {
  pinMode(EYES_PIN, OUTPUT); digitalWrite(EYES_PIN, LOW);
  ring.begin(); ring.clear(); ring.show();
}
inline void nodeSubscribe(PubSubClient& mqtt) {
  mqtt.subscribe("enderman/activate");
  mqtt.subscribe("enderman/color");
}
inline void nodeLoop() {}

inline void nodeOnMessage(String topic, String msg) {
  if (topic == "enderman/color") {
    // Accept "#RRGGBB" or "RRGGBB"; ignore anything else.
    int start = (msg.length() && msg[0] == '#') ? 1 : 0;
    if (msg.length() - start == 6) {
      long v = strtol(msg.substring(start).c_str(), nullptr, 16);
      currentColor = ring.Color((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF);
      if (endermanOn) fillRing();  // live repaint
    }
    return;
  }
  if (topic != "enderman/activate") return;
  endermanOn = (msg == "on");
  digitalWrite(EYES_PIN, endermanOn ? HIGH : LOW);
  if (endermanOn) fillRing();
  else { ring.clear(); ring.show(); }
}
```

- [ ] **Step 2: Build the enderman firmware to verify it compiles**

Run: `cd software/esp32 && pio run -e enderman`
Expected: `SUCCESS` (build completes with no errors).

- [ ] **Step 3: On-device check (hardware, if available)**

Flash and observe: `cd software/esp32 && pio run -e enderman -t upload`. With the portal running, pick a color and press "Enderman: Glow on" — all 16 LEDs should light that solid color; picking a new color while on should repaint live; "Enderman: off" clears the ring and eyes. (Skip if no board is connected; the build in Step 2 is the gating check.)

- [ ] **Step 4: Commit**

```bash
git add software/esp32/src/node_enderman.h
git commit -m "feat(enderman): 16-px solid picked color ring via enderman/color"
```

---

### Task 5: Update wiring docs

**Files:**
- Modify: `docs/04-wiring.md:40-51` (the Enderman section)

**Interfaces:** none (documentation).

- [ ] **Step 1: Update the Enderman section**

In `docs/04-wiring.md`, replace the Enderman effect line and table so it reads:

```markdown
## 🟪 Enderman — ESP32

Effect: belly ring lights a solid, portal-chosen color + eyes light while "on".
Listens on `enderman/activate` (`on`/`off`) and `enderman/color` (`#RRGGBB`, retained).

| Function | ESP32 pin | Connect to |
|----------|-----------|-----------|
| Belly: NeoPixel 16-ring (data) | **GPIO 4** | ring **DIN** (add ~330 Ω in series) |
| Belly ring (power) | — | ring **5 V** (external supply, ~1 A) + **GND → common GND**; ~1000 µF cap across 5 V/GND |
| Eyes: 2 white LEDs | **GPIO 5** | LEDs + resistor → GND (both eyes can share this pin) |
```

Also update the per-character power summary row for Enderman (`docs/04-wiring.md:132`):

```markdown
| Enderman | ESP32 (USB power bank) | 5 V for the 16-ring (~1 A) |
```

- [ ] **Step 2: Commit**

```bash
git add docs/04-wiring.md
git commit -m "docs(wiring): enderman 16-ring + enderman/color topic"
```

---

## Self-Review

**Spec coverage:**
- 16-LED ring → Task 4 (`RING_N 16`). ✓
- Solid picked color, drop animation → Task 4 (`fillRing`, empty `nodeLoop`). ✓
- Color picker in portal → Task 3. ✓
- Default to color every ON → Task 4 (`fillRing` on activate) + retained topic (Task 2). ✓
- On/off from portal → existing buttons, unchanged; ring clears on off (Task 4). ✓
- Live color update → Task 4 (`if (endermanOn) fillRing()`). ✓
- Eyes kept → Task 4 (EYES_PIN logic retained). ✓
- MQTT contract topic → Task 1. ✓
- Pin GPIO 4 → Task 4 + docs Task 5. ✓
- Tests (contract + route) → Tasks 1, 2. ✓
- Docs → Task 5. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code. ✓

**Type consistency:** `ENDERMAN_COLOR` == `"enderman/color"` used identically in Tasks 1/2; route path `/enderman/color` matches between Task 2 (definition) and Task 3 (fetch); `currentColor`/`fillRing` defined and used within Task 4. ✓
