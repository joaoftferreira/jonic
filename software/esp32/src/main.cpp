#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"

#if   defined(NODE_ROBOT)
  #define NODE_NAME "robot"
  #include "node_robot.h"
#elif defined(NODE_CREEPER)
  #define NODE_NAME "creeper"
  #include "node_creeper.h"
#elif defined(NODE_ENDERMAN)
  #define NODE_NAME "enderman"
  #include "node_enderman.h"
#elif defined(NODE_PORTAL)
  #define NODE_NAME "portal"
  #include "node_portal.h"
#elif defined(NODE_DRAGON)
  #define NODE_NAME "dragon"
  #include "node_dragon.h"
#else
  #error "Define a NODE_* build flag"
#endif

WiFiClient espClient;
PubSubClient mqtt(espClient);
unsigned long lastBeat = 0;

void onMessage(char* topic, byte* payload, unsigned int len) {
  String msg; for (unsigned i = 0; i < len; i++) msg += (char)payload[i];
  nodeOnMessage(String(topic), msg);
}

void reconnect() {
  while (!mqtt.connected()) {
    if (mqtt.connect(NODE_NAME)) {
      nodeSubscribe(mqtt);
    } else { delay(1000); }
  }
}

void setup() {
  Serial.begin(115200);
  nodeSetup();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (!mqtt.connected()) reconnect();
  mqtt.loop();
  nodeLoop();
  if (millis() - lastBeat > 3000) {
    lastBeat = millis();
    mqtt.publish((String("system/heartbeat/") + NODE_NAME).c_str(),
                 String(millis()).c_str());
  }
}
