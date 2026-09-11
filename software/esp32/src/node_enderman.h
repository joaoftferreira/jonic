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
  Serial.printf("[enderman] setup done: RING_N=%d RING_PIN=%d\n", RING_N, RING_PIN);
}
inline void nodeSubscribe(PubSubClient& mqtt) {
  mqtt.subscribe("enderman/activate");
  mqtt.subscribe("enderman/color");
}
inline void nodeLoop() {}

inline void nodeOnMessage(String topic, String msg) {
  Serial.printf("[enderman] RX topic='%s' msg='%s'\n", topic.c_str(), msg.c_str());
  if (topic == "enderman/color") {
    // Accept "#RRGGBB" or "RRGGBB"; ignore anything else (color unchanged).
    int start = (msg.length() && msg[0] == '#') ? 1 : 0;
    if (msg.length() - start == 6) {
      String hex = msg.substring(start);
      bool valid = true;
      for (int i = 0; i < 6; i++)
        if (!isxdigit((unsigned char)hex[i])) valid = false;
      if (valid) {
        long v = strtol(hex.c_str(), nullptr, 16);
        currentColor = ring.Color((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF);
        Serial.printf("[enderman] color set R=%ld G=%ld B=%ld (on=%d)\n",
                      (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF, endermanOn);
        if (endermanOn) fillRing();  // live repaint
      }
    }
    return;
  }
  if (topic != "enderman/activate") return;
  endermanOn = (msg == "on");
  digitalWrite(EYES_PIN, endermanOn ? HIGH : LOW);
  Serial.printf("[enderman] activate='%s' -> on=%d, painting ring\n", msg.c_str(), endermanOn);
  if (endermanOn) fillRing();
  else { ring.clear(); ring.show(); }
}
