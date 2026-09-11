#pragma once
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

#define IN1 25
#define IN2 26
#define ENA 27
#define STRIP_PIN 4
#define STRIP_N 20
#define PULL_MS 900
#define REED_PIN 34

static Adafruit_NeoPixel frame(STRIP_N, STRIP_PIN, NEO_GRB + NEO_KHZ800);

static void motorPull() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW); analogWrite(ENA, 255);
  delay(PULL_MS);
  digitalWrite(IN1, LOW);  digitalWrite(IN2, LOW); analogWrite(ENA, 0);
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
inline void nodeLoop() {
  bool reed = digitalRead(REED_PIN);
  if (lastReed && !reed) { }
  lastReed = reed;
}
inline void nodeOnMessage(String topic, String msg) {
  if (topic == "portal/open") {
    for (int i=0;i<STRIP_N;i++) frame.setPixelColor(i, frame.Color(160,40,220));
    frame.show();
    motorPull();
  }
}
