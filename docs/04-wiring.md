# 04 · Wiring — Eggman's robot

One ESP32 drives everything: two wheels through a DRV8800 each, a 16-LED
NeoPixel ring, and a servo that releases the lock on the chest.

> ⚠ **Wire grounds first and check them twice.** Almost every strange symptom on
> a build like this — motors twitching, LEDs flickering the wrong colour, the
> ESP32 rebooting when a wheel starts — is a ground that is not actually shared.

---

## Pin map

These are set in one block at the top of `software/esp32/src/node_robot.h`.
Change them there if your board is already built differently; nothing else in
the firmware hard-codes a pin.

| ESP32 pin | Goes to | Why this pin |
|-----------|---------|--------------|
| 25 | DRV8800 #1 **PHASE** — left wheel direction | free, output-capable |
| 26 | DRV8800 #1 **ENABLE** — left wheel PWM | free, output-capable |
| 32 | DRV8800 #2 **PHASE** — right wheel direction | free, output-capable |
| 33 | DRV8800 #2 **ENABLE** — right wheel PWM | free, output-capable |
| 27 | both drivers' **nSLEEP** | one pin powers both H-bridges down |
| 4 | NeoPixel ring **DIN** | free, no boot role |
| 14 | lock servo **signal** | free, output-capable |

**Pins deliberately avoided.** GPIO 6–11 are wired to the flash chip and using
them bricks the board until you reflash. GPIO 34–39 are input only, with no
pull-ups and no output drivers at all. GPIO 0, 2, 12 and 15 are strapping pins
that decide how the ESP32 boots; a motor driver holding one at the wrong level
at power-up stops the board starting.

---

## The wheels (DRV8800 × 2)

The DRV8800 takes direction and speed as two separate signals, which is why
each motor needs two ESP32 pins.

| DRV8800 pin | Connect to |
|-------------|-----------|
| PHASE | ESP32 25 (left) / 32 (right) — HIGH is one way, LOW the other |
| ENABLE | ESP32 26 (left) / 33 (right) — the PWM that sets speed |
| nSLEEP | ESP32 27, both drivers together |
| VM, GND | the **motor battery**, not the ESP32's 5 V |
| OUT+, OUT− | the motor |
| nFAULT | leave unconnected, or to a spare input if you want fault reporting |

**Power.** Motors must have their own supply. Running them off the same
regulator as the ESP32 browns it out the moment a wheel stalls, and the board
resets mid-party. Join the two grounds at exactly one point, near the drivers.

Put a **100 µF or larger electrolytic across VM and GND** at each driver, close
to the chip, and a small ceramic across each motor's own terminals. Brushed
motors are electrically noisy and this is what stops that noise reaching the
NeoPixels and the WiFi.

**If a wheel turns the wrong way**, swap that motor's two wires. Do not
compensate in software; the code assumes PHASE HIGH is forward on both sides.

---

## The NeoPixel ring (16 LEDs)

| Ring pin | Connect to |
|----------|-----------|
| DIN | ESP32 4, through a **330 Ω resistor** in series, as close to the ring as possible |
| 5 V | the 5 V supply |
| GND | common ground |

Add a **1000 µF capacitor across the ring's 5 V and GND**. Without it the
inrush when all sixteen LEDs jump to white can glitch the first pixel or reset
the board.

**Brightness is capped in firmware at 60 of 255** (`RING_BRIGHTNESS`). Sixteen
LEDs at full white draw close to an amp by themselves, which is more than most
USB supplies will give and enough to brown out the ESP32. A quarter brightness
still reads as bright white on a costume. Raise it only if you have measured
your supply.

The ESP32's 3.3 V data line is marginally below what a 5 V NeoPixel expects. It
usually works, and the 330 Ω resistor helps. If the first LED misbehaves, either
run the ring from 4.5 V or add a level shifter on the data line.

---

## The lock servo

| Servo wire | Connect to |
|------------|-----------|
| signal (usually orange or white) | ESP32 14 |
| + (red) | 5 V supply — **not** the ESP32's 3.3 V pin |
| − (brown or black) | common ground |

The firmware drives it to `LOCK_CLOSED_DEG` (0°) at boot and to
`LOCK_OPEN_DEG` (90°) on **OPEN**. If your latch needs more or less travel,
change those two constants; if it moves the wrong way, swap the two values
rather than remounting the horn.

Fit the horn with the latch **closed** and the servo already at 0°, or the
first command will slam it against its end stop.

---

## Order to build and test in

Test each stage before adding the next. Debugging all three at once is what
costs a day.

1. **ESP32 alone.** Flash it, watch the serial monitor at 115200, confirm it
   joins WiFi and its pill goes green on the phone.
2. **Servo only.** Press OPEN and Re-arm. Check the travel before it is
   attached to anything that can jam.
3. **Ring only.** Lights on, lights off.
4. **Wheels, robot on a stand with the wheels off the ground.** Check each
   direction before it can drive into anything. Forward should move both wheels
   the same way; left and right should spin them opposite ways.
5. **On the floor**, with the speed slider low, then raise it.
