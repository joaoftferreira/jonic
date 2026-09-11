# Minecraft Birthday Treasure Hunt — Design Spec

**Date:** 2026-06-16
**Event:** Birthday party treasure hunt for a 6-year-old, Minecraft-themed
**Deadline:** ~10 days (event ≈ 2026-06-26)
**Roles:** User builds physical characters + wiring and is comfortable with HW/SW. Claude owns software + planning.

---

## 1. Goal & guiding principles

A guided treasure hunt where Minecraft characters give clues across the house until the kids reach a chest of gifts. Each character does something interactive (lights, sound, motion, "explosions").

**Principles**
- **Reliability over autonomy.** Every story beat is triggered by the operator (parent) from a phone command center. Sensors/automation are optional polish layered on top, never on the critical path.
- **Wizard-of-Oz first.** The operator watches the kids and presses the next button at the right moment.
- **Build physical first, animate last.** Characters must look right even if a given animation isn't finished.
- **Degrade gracefully.** Any electronic effect has a manual fallback so the party never stalls.
- **Bad-weather alt locations.** Steps note an indoor alternative where relevant.

---

## 2. System architecture

Centralized brain + distributed character nodes, all on the home WiFi.

```
        Operator phone (browser)
              │  WiFi
              ▼
   ┌─────────────────────────────┐
   │  Raspberry Pi (in/near Wolf) │
   │   • Command Center web app   │  (Flask + mobile page)
   │   • MQTT broker (Mosquitto)  │
   │   • Wolf app (Pygame):       │
   │       eyes + sound + mouth   │
   │       servo (GPIO)           │
   └─────────┬────────────────────┘
             │  MQTT over WiFi
   ┌─────────┼───────────┬───────────┬────────────┐
   ▼         ▼           ▼           ▼             
 Creeper   Enderman    Portal      Ender-Dragon   (Bee = Jetson+drone,
 ESP32     ESP32       ESP32       ESP32           separate track)
```

- **Raspberry Pi** is the brain: hosts the MQTT broker, the command-center web page, and the Wolf app. Lives with the Wolf because the LCD is the Wolf's face.
- **One ESP32 per active character** (creeper, enderman, portal, ender-dragon). Each connects to WiFi + MQTT and performs its action on command.
- **Bee/drone** is a separate track (Jetson + quadcopter). Manual fallback guaranteed; autonomous flight is a stretch attempted only if days 9–10 allow.

**Why this shape:** the operator's phone talks to one place (the Pi); the Pi fans commands out over MQTT; each character is independently testable and can fail without taking down the others.

---

## 3. Story flow → triggers

Locations given as `primary / bad-weather-alt` where relevant.

| # | Beat | Location | Effect | Trigger |
|---|------|----------|--------|---------|
| 1 | First clue → go to hive | outside / kitchen | hand kids clue 1 | manual |
| 2 | Bee brings clue → find bone | basement | bee delivers clue 2 | drone or manual |
| 3–4 | Give bone to Wolf | living room | Wolf: hungry→loving eyes, mouth opens, happy bark | **CC button** |
| 5 | Wolf gives clue → creeper | living room | reveal clue 3 (wolf "spits" / operator hands) | CC button / manual |
| 6 | Creeper explodes → clue | living room | flash white → balloon pop → confetti, leaves clue 4 | **CC button** |
| 7 | Ender dragon destroyed → obsidian | bedroom | dragon releases obsidian cube | **CC button** (kids may "hit" it) |
| 8 | Obsidian completes portal → opens | top floor | cube inserted → motor pulls latch → door opens | **CC button** (reed-switch auto = stretch) |
| 9 | Behind portal: chest + enderman | parents' room | enderman eyes + belly glow | **CC button** |
| 10 | Key from enderman → opens chest | parents' room | physical key opens padlock | manual |

The command center shows the current step so the operator never loses their place.

---

## 4. Software components (Claude's responsibility)

### 4.1 MQTT contract
Single broker on the Pi. Topics (retained where state matters):

| Topic | Payload | Direction | Meaning |
|-------|---------|-----------|---------|
| `wolf/state` | `idle` \| `hungry` \| `loving` | CC → Wolf app | wolf mood |
| `wolf/bark` | `1` | CC → Wolf app | one-shot bark |
| `creeper/explode` | `1` | CC → Creeper | run flash→pop→confetti sequence |
| `dragon/destroy` | `1` | CC → Dragon | release obsidian |
| `portal/open` | `1` | CC → Portal | run motor to pull latch |
| `portal/sensor` | `inserted` | Portal → CC | (stretch) cube detected |
| `enderman/activate` | `on` \| `off` | CC → Enderman | belly + eyes glow |
| `system/heartbeat/<node>` | `ts` | nodes → CC | liveness for status board |

Topic names/payloads are intentionally trivial strings to keep ESP32 parsing dead simple.

### 4.2 Command Center (Pi, Flask + mobile web page)
- Single mobile-friendly page, large touch tiles, one per story beat, laid out in story order.
- Each tile publishes the relevant MQTT message; tiles light up when fired.
- A **current-step indicator** and a **reset** control.
- A **status strip** showing each node's heartbeat (online/offline) so the operator knows before the party if a character is dead.
- Served on the Pi over the home WiFi; opened on the operator's phone.

### 4.3 Wolf app (Pi, Pygame fullscreen)
- Fullscreen 2D eyes on the LCD. States:
  - **idle/look-around:** eyes drift randomly.
  - **hungry:** periodic hungry look (sync with whine sound).
  - **loving:** heart-eyes when bone is given.
- **Sound:** mostly quiet; occasional bark/whine; happy bark on bone. Synced to eye state via `pygame.mixer`.
- **Mouth:** physical PWM servo on a Pi GPIO — closed at rest, opens when bone is given (on `wolf/state=loving`).
- Subscribes to `wolf/state` and `wolf/bark`.

### 4.4 ESP32 firmware (one PlatformIO project, per-node build flags)
Shared skeleton: WiFi connect → MQTT connect → subscribe → act → publish heartbeat. Per-node action code:
- **Creeper:** flash LED bright white (telegraph), short delay, drive servo-pin into central balloon, fire confetti popper (servo pulls trigger).
- **Ender-dragon:** release mechanism (servo/solenoid) drops the obsidian cube on `dragon/destroy`.
- **Portal:** drive DC motor via H-bridge to pull the latch wire for a timed pulse, then stop; optional reed switch publishes `portal/sensor`.
- **Enderman:** light eyes + belly LEDs (NeoPixel or plain LEDs) on `enderman/activate`.

### 4.5 Bee / drone track (Jetson, separate)
- **Fallback (must-have):** non-autonomous bee — handed over, on a string, or hidden — that "delivers" clue 2.
- **Stretch:** Jetson-guided autonomous flight using the quad's WiFi camera. Only attempted after the core hunt is fully working.

**Stack:** Pi — Python (paho-mqtt, Flask, Pygame), Mosquitto. ESP32 — Arduino/PlatformIO + PubSubClient. Drone — Jetson (separate). All offline-capable on the home WiFi.

---

## 5. Hardware mechanisms (decided)

- **Creeper pop:** servo-driven pin into the central balloon (loud pop, no heat), driven by the creeper ESP32. Confetti popper fired by a 5V relay (one-shot) on the same node.
- **Portal latch:** DC motor pulling a wire attached to the door latch, driven by an Arduino H-bridge (e.g., L298N-class), controlled by the portal ESP32. Timed pulse to pull, then stop.
- **Wolf mouth:** small PWM servo on the Pi.
- **Ender dragon obsidian drop:** servo or small solenoid release (mechanism TBD with build) holding the cube until `dragon/destroy`.

---

## 6. 10-day schedule

- **Days 1–2 — Foundation.** Confirm inventory; Claude stands up broker + command center + one ESP32 proven end-to-end (`creeper/explode` → LED blink). Pipeline proven early.
- **Days 3–6 — Parallel build.** User: wolf box, creeper balloon rig, portal door, enderman, skeleton/bone, chest; wires each node. Claude: finishes firmware per node + Wolf app eyes/sound/mouth.
- **Days 7–8 — Integration & dry-run.** Full 11-step rehearsal; tune timing, sound levels, clue wording; status board check.
- **Day 9 — Stretch + buffer.** Drone autonomous attempt; catch-up on anything that slipped.
- **Day 10 — Dress rehearsal & freeze.** Final run, print clues, charge batteries/power banks, label everything.

---

## 7. Bill of materials (confirm against actual inventory)

User reports "most parts procured." Confirm quantities:
- ESP32 boards ×5 (creeper, enderman, portal, dragon + 1 spare) — confirmed
- Raspberry Pi 3 ×2 (brain + hot spare), Orange Pi ×1 (spare/Jetson helper), Arduino Mega ×1 — confirmed
- LCD screen for wolf face (have)
- Jetson + quadcopter w/ WiFi camera (have)
- PWM servos ×3 → **wolf mouth, creeper pin, dragon release** (confetti moves to relay; see below) — confirmed
- DC motors (several) + H-bridge ×1 for portal latch — confirmed
- LEDs on hand (confirmed): NeoPixel **8-ring**, NeoPixel **8-LED bar/stick**, flexible **~20-pixel** NeoPixel strip, assorted **discrete white LEDs**, a couple of **5V relays**.
- **Proposed LED allocation:**
  - Enderman belly → NeoPixel 8-ring #1 (pulse). Enderman eyes → 2 white LEDs (or 2 pixels off flex strip).
  - Ender dragon → NeoPixel 8-ring #2 as a "power core" that flares then dies on destroy.
  - Creeper flash → discrete white LEDs (instant bright telegraph before pop).
  - 8-LED bar → spare. Flexible ~20-pixel strip → portal frame edge-glow (or creeper accent).
  - 5V relays → **confetti popper trigger** (one-shot) on creeper node; spare relay for portal motor power switching if needed.
- Small amplifier + speakers for wolf barking — confirmed
- Confetti popper(s) — **confirm type** (electric/relay-triggerable vs. manual pull)
- Servos ×~4 (creeper pin, confetti, wolf mouth, dragon release) — **confirm count**
- Balloons (creeper body + central pop balloon)
- White faux-fur / carpet (wolf), cardboard/foam, purple sheer curtain (portal), foam cubes, padlock + key (chest)
- Batteries / USB power banks for each node; jumper wires, transistors/MOSFETs/resistors as needed

---

## 8. Open items / assumptions
- Exact parts inventory to be confirmed by user at spec review.
- Ender-dragon drop mechanism finalized during physical build.
- Drone autonomy explicitly out of the critical path.
- Number of kids / how clue-handoff is staged (single group assumed).
