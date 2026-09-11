# Enderman — 16-LED NeoPixel ring with portal color picker

**Date:** 2026-07-10
**Status:** Proposed — awaiting user review
**Node:** Enderman (ESP32)

## Goal

Drive a 16-LED WS2812 NeoPixel ring from the enderman ESP32. The ring lights all
16 LEDs in a single color chosen from a color picker in the command-center portal.
The color is remembered; every time the enderman is turned ON the ring defaults to
that color. The ring can be turned on/off from the portal.

## Assumptions (defaults chosen while user was away — confirm on review)

1. **On behavior = solid color.** When ON, all 16 LEDs light steadily in the picked
   color. The current breathing-purple animation is removed.
2. **Color update = live.** Picking a new color repaints the ring immediately if it
   is on, and is used for the next ON. Implemented naturally via a retained MQTT topic.
3. **Eyes kept.** The 2 white eye LEDs on GPIO 5 keep turning on/off with the ring.
   The color picker only affects the 16-LED ring.

## Pin choice

**Data pin: GPIO 4 (unchanged).** Already the enderman ring pin, output-capable, and
not a strapping/flash pin — ideal for WS2812. No rewiring vs. the current 8-ring.

Wiring:

| Function | ESP32 pin | Connect to |
|----------|-----------|-----------|
| Ring data (DIN) | **GPIO 4** | ring **DIN**, via ~330 Ω series resistor |
| Ring power | — | ring **5 V → external 5 V supply**, **GND → common GND** |
| Eyes (2 white LEDs) | **GPIO 5** | LEDs + resistor → GND (unchanged) |

Power note: 16 px at full white ≈ 1 A. Use a real 5 V supply (USB power bank 5 V
rail), never the ESP32 3.3 V pin. Add a ~1000 µF cap across the ring's 5 V/GND.

## MQTT contract

Add one topic to `software/pi/common/mqtt_contract.py`:

```python
ENDERMAN_COLOR = "enderman/color"   # payload: "#RRGGBB", retained
```

`ENDERMAN_ACTIVATE = "enderman/activate"` (payload `on`/`off`, retained) is unchanged.

Both topics are published **retained**. The color topic being retained is what makes
"defaults to that color every time it's ON" work with zero Pi-side state: on boot or
reconnect the ESP32 receives the last-picked color before/around the activate message.

## Firmware — `software/esp32/src/node_enderman.h`

- `RING_N` 8 → 16.
- Add `static uint32_t currentColor` initialized to the current purple
  (`ring.Color(128, 0, 160)` ≈ `#8000A0`) so behavior is sane before any color is picked.
- Remove the `phase` breathing state and the animation in `nodeLoop()`; `nodeLoop()`
  becomes empty.
- `nodeSubscribe()` subscribes to both `enderman/activate` and `enderman/color`.
- `nodeOnMessage()`:
  - `enderman/color`: parse `#RRGGBB` → `currentColor`. If `endermanOn`, repaint the
    ring immediately (fill all 16 with `currentColor`, `show()`).
  - `enderman/activate`:
    - `on`: fill all 16 with `currentColor`, `show()`; eyes HIGH; set `endermanOn = true`.
    - `off`: `ring.clear(); ring.show()`; eyes LOW; set `endermanOn = false`.

Hex parsing: accept a leading `#` optionally, take 6 hex chars, `strtol` into R/G/B.
Malformed payloads are ignored (color unchanged).

## Portal — command center

`software/pi/command_center/app.py`: add a route

```
POST /enderman/color   body: color=#RRGGBB (form field)
```

that validates the value matches `^#[0-9A-Fa-f]{6}$` and publishes it to
`enderman/color` with `qos=1, retain=True`. Reject invalid input with HTTP 400.

`templates/index.html`: add a small "Enderman color" control — an
`<input type="color" id="ender-color" value="#8000a0">` — near the enderman on/off
buttons. The existing `enderman_on` / `enderman_off` buttons are kept as-is.

`static/app.js`: add a handler that, on the color input's `change` event, POSTs the
selected value to `/enderman/color`.

## Docs

`docs/04-wiring.md`: update the Enderman section — "8-ring" → "16-ring", note the
~1 A power draw, and mention the `enderman/color` topic. Effect line becomes:
"belly ring lights a solid, portal-chosen color + eyes light while on."

## Testing

- `software/pi/common/tests/test_contract.py`: assert `ENDERMAN_COLOR == "enderman/color"`.
- Add a test for the color route: valid hex → publishes retained to `enderman/color`;
  invalid input → 400 and no publish (mock the MQTT client).
- Manual: flash the `enderman` PlatformIO env, open the portal, pick a color, toggle
  on/off, confirm all 16 LEDs show the picked color and that a new pick repaints live.

## Out of scope

- Per-pixel effects, gradients, animations, brightness slider.
- Changing any other node.
