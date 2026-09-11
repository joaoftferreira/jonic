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
  for (int b = 0; b <= 255; b += 15) {
    for (int i=0;i<RING_N;i++) core.setPixelColor(i, core.Color(b,b,b));
    core.show(); delay(40);
  }
  core.clear(); core.show();
  catchServo.write(CATCH_OPEN); delay(600); catchServo.write(CATCH_CLOSED);
}
