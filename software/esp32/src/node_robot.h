#pragma once
// Eggman's robot: two wheels driven differentially, a 16-LED NeoPixel ring,
// and a servo that releases the lock on the chest.
//
// Wiring lives in docs/04-wiring.md. Every pin is in the block below; nothing
// else in this file hard-codes one.
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Servo.h>

// ---------------------------------------------------------------- pins -----
// Chosen to avoid GPIO 6-11 (wired to the flash chip), 34-39 (input only, no
// pull-ups) and the strapping pins 0/2/12/15 that decide how the ESP32 boots.
#define L_PHASE   25   // DRV8800 #1 PHASE  - left wheel direction
#define L_ENABLE  26   // DRV8800 #1 ENABLE - left wheel PWM
#define R_PHASE   32   // DRV8800 #2 PHASE  - right wheel direction
#define R_ENABLE  33   // DRV8800 #2 ENABLE - right wheel PWM
#define MOTOR_SLEEP 27 // both drivers' nSLEEP: LOW powers the H-bridges down
#define RING_PIN  4    // NeoPixel ring data in
#define LOCK_PIN  14   // lock servo signal

#define RING_N    16
#define RING_BRIGHTNESS 60   // of 255. See the note in nodeSetup().

#define LOCK_CLOSED_DEG 0
#define LOCK_OPEN_DEG   90

// Stop driving if no command arrives for this long. The phone repeats every
// 200 ms while a button is held, so this rides out a couple of lost packets
// yet still halts quickly when you let go, the phone locks, or WiFi drops.
#define DRIVE_TIMEOUT_MS 500

static Adafruit_NeoPixel ring(RING_N, RING_PIN, NEO_GRB + NEO_KHZ800);
static Servo lockServo;

static uint8_t motorDuty = 166;          // ~65%, replaced by robot/speed
static unsigned long lastDriveMs = 0;
static bool driving = false;

// PHASE picks the direction, ENABLE is the PWM. ENABLE at 0 brakes the motor
// rather than letting it coast, which is what you want on a floor with
// children on it.
static void wheel(int phasePin, int enablePin, int direction) {
  if (direction == 0) {
    analogWrite(enablePin, 0);
    return;
  }
  digitalWrite(phasePin, direction > 0 ? HIGH : LOW);
  analogWrite(enablePin, motorDuty);
}

static void drive(int left, int right) {
  wheel(L_PHASE, L_ENABLE, left);
  wheel(R_PHASE, R_ENABLE, right);
  driving = (left != 0 || right != 0);
}

static void stopMotors() { drive(0, 0); }

inline void nodeSetup() {
  pinMode(L_PHASE, OUTPUT);  pinMode(L_ENABLE, OUTPUT);
  pinMode(R_PHASE, OUTPUT);  pinMode(R_ENABLE, OUTPUT);
  pinMode(MOTOR_SLEEP, OUTPUT);
  digitalWrite(MOTOR_SLEEP, HIGH);       // wake both DRV8800s
  stopMotors();

  // 16 LEDs at full white would pull nearly an amp on their own, which browns
  // out the regulator that is also running the motors. A quarter brightness
  // still reads as bright white on a costume.
  ring.begin();
  ring.setBrightness(RING_BRIGHTNESS);
  ring.clear();
  ring.show();

  lockServo.setPeriodHertz(50);
  lockServo.attach(LOCK_PIN, 500, 2400);
  lockServo.write(LOCK_CLOSED_DEG);

  Serial.printf("[robot] setup done: duty=%d ring=%d lock=%d\n",
                motorDuty, RING_PIN, LOCK_PIN);
}

inline void nodeSubscribe(PubSubClient& mqtt) {
  mqtt.subscribe("robot/drive");
  mqtt.subscribe("robot/speed");
  mqtt.subscribe("robot/lights");
  mqtt.subscribe("robot/lock");
}

inline void nodeLoop() {
  // The deadman. Losing the phone, the WiFi or the broker must leave the robot
  // standing still rather than driving into someone.
  if (driving && millis() - lastDriveMs > DRIVE_TIMEOUT_MS) {
    stopMotors();
    Serial.println("[robot] drive timed out, stopping");
  }
}

inline void nodeOnMessage(String topic, String msg) {
  if (topic == "robot/drive") {
    lastDriveMs = millis();
    if      (msg == "forward") drive(+1, +1);
    else if (msg == "back")    drive(-1, -1);
    else if (msg == "left")    drive(-1, +1);   // wheels oppose: turn on the spot
    else if (msg == "right")   drive(+1, -1);
    else                       stopMotors();    // "stop", and anything unknown
    return;
  }

  if (topic == "robot/speed") {
    long percent = msg.toInt();
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;
    motorDuty = (uint8_t)(percent * 255 / 100);
    Serial.printf("[robot] speed %ld%% -> duty %d\n", percent, motorDuty);
    return;
  }

  if (topic == "robot/lights") {
    bool on = (msg == "on");
    for (int i = 0; i < RING_N; i++)
      ring.setPixelColor(i, on ? ring.Color(255, 255, 255) : 0);
    ring.show();
    return;
  }

  if (topic == "robot/lock") {
    // "open" releases the latch and stays there; "reset" re-arms it.
    lockServo.write(msg == "open" ? LOCK_OPEN_DEG : LOCK_CLOSED_DEG);
    Serial.printf("[robot] lock '%s'\n", msg.c_str());
  }
}
