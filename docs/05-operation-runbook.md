# 05 · Operation runbook (party day)

How to bring the face up and run it. Keep this open on a second device.

---

## The day before

- [ ] **Cold-boot test.** Power the Pi from off, with no laptop attached, and confirm the
      eyes appear on the LCD on their own and the remote answers at `http://<pi-ip>:8080`.
- [ ] **Calibrate** the eyes to the finished head and press **Save**
      (see [02-raspberry-pi-setup.md](02-raspberry-pi-setup.md) § 5). Reboot once and check
      the tuning came back.
- [ ] **Rehearse the animations.** Press each button and watch from where the kids will
      stand, a few metres back, not from arm's length.
- [ ] **Write the Pi's IP on a sticker** and put it on the back of the head.

---

## ~15 minutes before

1. **Power the Pi.** Wait about a minute. The eyes come up by themselves.
2. On your phone, on the same WiFi, open **`http://<pi-ip>:8080`**.
3. **Check the `eyes` pill is green.** Green means the face is connected and listening.
   The `robot` pill stays red until the ESP32 is built; ignore it.
4. Press **Blink** once to confirm the whole chain works.

---

## Driving the face

You are the puppeteer. The four buttons are all there is:

| Button | What happens |
|--------|--------------|
| **😉 Blink** | a blue eyelid drops and lifts, about a third of a second |
| **👈 Look left** | the eyes turn left and **hold** |
| **Look right 👉** | the eyes turn right and **hold** |
| **👀 Look ahead** | back to looking straight at whoever is in front |

Because a look holds until you change it, remember to press **Look ahead** before you walk
away, or Sonic spends the rest of the party staring at a wall.

A blink between two looks sells the movement: look left, blink, look right reads as a
character noticing something, while a bare slide reads as a machine.

---

## If something goes wrong

| Problem | Move |
|---------|------|
| Eyes are frozen and the `eyes` pill is red | The face lost the WebSocket. It retries by itself every second; give it a moment. If it stays red, `sudo systemctl restart sonic-command-center`. |
| LCD is black | `systemctl --user restart sonic-eyes-kiosk` from the Pi's desktop session. |
| Eyes are the wrong size or off-centre | Open the calibration panel and fix it live. It is designed to be safe to touch mid-party. |
| Phone can't reach the remote | Check the phone's WiFi band, then re-open the address on the sticker. |
| Everything is wedged | Pull the Pi's power and put it back. It boots to the eyes on its own in about a minute, calibration included. |

> Principle: **the character carries the party, the animation is the garnish.** If the face
> stops, Sonic is still a big cardboard Sonic. Never let a gadget stall the fun.

---

## After the party

If you tuned anything on the day, commit it so it is not lost:

```bash
git commit -am "tune: party-day adjustments"
```
