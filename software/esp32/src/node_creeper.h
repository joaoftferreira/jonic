#pragma once
#include <PubSubClient.h>
#include <ESP32Servo.h>

#define LED_PIN    5
#define SERVO_PIN  13
#define RELAY_PIN  12
#define PIN_REST   20
#define PIN_STAB   110

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
  for (int d = 300; d > 60; d -= 40) {
    digitalWrite(LED_PIN, HIGH); delay(d/2);
    digitalWrite(LED_PIN, LOW);  delay(d/2);
  }
  digitalWrite(LED_PIN, HIGH);
  creeperServo.write(PIN_STAB); delay(250);
  creeperServo.write(PIN_REST);
  digitalWrite(RELAY_PIN, HIGH); delay(300); digitalWrite(RELAY_PIN, LOW);
  delay(200); digitalWrite(LED_PIN, LOW);
}
