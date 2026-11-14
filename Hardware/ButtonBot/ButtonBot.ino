#include <WiFi.h>

#define USE_WEBSOCKET true     // true = WebSocket (main). false = HTTP fallback.

#if USE_WEBSOCKET
  #include <WebSocketsClient.h>
#else
  #include <HTTPClient.h>
#endif

// ---- Network ----
const char*    WIFI_SSID = "MESPanel";
const char*    WIFI_PASS = "PASSWORD";      // your real hotspot password
const char*    PI_HOST   = "10.42.0.1";     // the Pi on its own hotspot
const uint16_t PI_PORT   = 5000;
const char*    PANEL_ID  = "station-1";

// ---- Pins ----
const int PIN_LISTEN_LED = 25;  // blue
const int PIN_LABOR      = 26;  // white
const int RGB_R          = 14;  // RGB red leg
const int RGB_G          = 27;  // RGB green leg
const int BTN_POWER      = 33;
const int BTN_LISTEN     = 32;

// ---- RGB settings ----
const int  AMBER_G      = 60;     // higher = yellower, lower = more orange
const bool COMMON_ANODE = false;  // true if RGB shared leg goes to 3.3V

// ---- Long press ----
const unsigned long LONG_PRESS_MS = 1500;   // hold power this long to turn the dashboard off

// ---- Light state (from the Pi) ----
bool listening = false, labor = false, inspector = false, alertOpen = false;
unsigned long lastRx = 0;
unsigned long listenHoldUntil = 0;              // blue trusts the button until this time
const unsigned long HEARTBEAT_TIMEOUT = 3000;   // ms

// ---- Power button hold tracking ----
bool powerHeld = false;
bool powerLongSent = false;
unsigned long powerDownAt = 0;

// ---- Buttons (50 ms debounce) ----
struct Button {
  int pin;
  const char* id;
  bool lastReading;
  bool stable;
  unsigned long lastChange;
};
Button buttons[] = {
  {BTN_POWER,  "power",         HIGH, HIGH, 0},
  {BTN_LISTEN, "listen_toggle", HIGH, HIGH, 0},
};

#if USE_WEBSOCKET
WebSocketsClient ws;
#endif

// ---------- helpers ----------
void setRGB(uint8_t r, uint8_t g) {
  if (COMMON_ANODE) { r = 255 - r; g = 255 - g; }
  ledcWrite(RGB_R, r);
  ledcWrite(RGB_G, g);
}

// Reads "key": true/false, with or without a space after the colon
bool jsonBool(const String& s, const char* key) {
  int k = s.indexOf(String("\"") + key + "\"");
  if (k < 0) return false;
  int c = s.indexOf(':', k);
  if (c < 0) return false;
  c++;
  while (c < (int)s.length() && s[c] == ' ') c++;
  return s.startsWith("true", c);
}

void applyLights(const String& s) {
  if (s.indexOf("\"lights\"") < 0) return;       // ignore other message types
  // Blue: ignore the Pi for 1.5 s after a button press so it doesn't flicker back
  if (millis() > listenHoldUntil) listening = jsonBool(s, "listening");
  labor     = jsonBool(s, "labor");
  inspector = jsonBool(s, "inspector");
  alertOpen = jsonBool(s, "alert");
  lastRx = millis();
}

String buttonJson(const char* id) {
  return String("{\"type\":\"button\",\"id\":\"") + id + "\"}";
}

void sendButton(const char* id) {
  Serial.print("Button: ");
  Serial.println(id);
#if USE_WEBSOCKET
  String msg = buttonJson(id);
  Serial.print("TX -> ");
  Serial.println(msg);
  ws.sendTXT(msg);
#else
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setConnectTimeout(300);
  http.setTimeout(300);
  http.begin(String("http://") + PI_HOST + ":" + String(PI_PORT) + "/api/panel/button");
  http.addHeader("Content-Type", "application/json");
  http.POST(buttonJson(id));
  http.end();
#endif
}

// Called once each time a debounced button goes down or up
void onButtonEdge(const char* id, bool pressed) {
  if (strcmp(id, "listen_toggle") == 0) {
    if (pressed) {
      listening = !listening;               // instant local toggle
      listenHoldUntil = millis() + 1500;    // trust the button for 1.5 s
      sendButton(id);
    }
  } else if (strcmp(id, "power") == 0) {
    if (pressed) {
      powerHeld = true;
      powerLongSent = false;
      powerDownAt = millis();
    } else {
      if (powerHeld && !powerLongSent) sendButton("power");   // short press
      powerHeld = false;
    }
  }
}

void checkButtons() {
  for (auto &b : buttons) {
    bool reading = digitalRead(b.pin);
    if (reading != b.lastReading) {
      b.lastChange = millis();
      b.lastReading = reading;
    }
    if (millis() - b.lastChange > 50 && reading != b.stable) {
      b.stable = reading;
      onButtonEdge(b.id, b.stable == LOW);
    }
  }
}

// Fires power_off as soon as the hold time is reached
void checkPowerHold() {
  if (powerHeld && !powerLongSent && millis() - powerDownAt >= LONG_PRESS_MS) {
    powerLongSent = true;
    sendButton("power_off");
  }
}

void updateLights() {
  unsigned long now = millis();
  bool piAlive = (lastRx != 0) && (now - lastRx < HEARTBEAT_TIMEOUT);

  if (!piAlive) {                       // lost the Pi: all lights off
    digitalWrite(PIN_LISTEN_LED, LOW);
    digitalWrite(PIN_LABOR, LOW);
    setRGB(0, 0);
    return;
  }

  digitalWrite(PIN_LISTEN_LED, listening);
  digitalWrite(PIN_LABOR, labor);

  if (alertOpen) {                      // red fast flash, takes priority
    bool on = (now / 125) % 2;
    setRGB(on ? 255 : 0, 0);
  } else if (inspector) {               // amber slow flash
    bool on = (now / 500) % 2;
    setRGB(on ? 255 : 0, on ? AMBER_G : 0);
  } else {
    setRGB(0, 0);
  }
}

// ---------- transport ----------
#if USE_WEBSOCKET

void onWsEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED: {
      Serial.println("WebSocket connected");
      String hello = String("{\"type\":\"hello\",\"panel\":\"") + PANEL_ID + "\"}";
      ws.sendTXT(hello);
      break;
    }
    case WStype_DISCONNECTED: {
      Serial.println("WebSocket disconnected");
      break;
    }
    case WStype_TEXT: {
      String s;
      s.reserve(length);
      for (size_t i = 0; i < length; i++) s += (char)payload[i];

      static String lastMsg = "";       // only print when the lights message changes
      if (s != lastMsg) {
        Serial.print("RX <- ");
        Serial.println(s);
        lastMsg = s;
      }

      applyLights(s);
      break;
    }
    default:
      break;
  }
}

#else

void pollLights() {
  static unsigned long last = 0;
  if (millis() - last < 500) return;
  last = millis();
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.setConnectTimeout(300);
  http.setTimeout(300);
  http.begin(String("http://") + PI_HOST + ":" + String(PI_PORT) + "/api/panel/lights");
  if (http.GET() == 200) applyLights(http.getString());
  http.end();
}

#endif

// ---------- setup / loop ----------
void setup() {
  Serial.begin(115200);

  pinMode(PIN_LISTEN_LED, OUTPUT);
  pinMode(PIN_LABOR, OUTPUT);
  digitalWrite(PIN_LISTEN_LED, LOW);
  digitalWrite(PIN_LABOR, LOW);
  ledcAttach(RGB_R, 5000, 8);           // core 3.x
  ledcAttach(RGB_G, 5000, 8);
  setRGB(0, 0);

  pinMode(BTN_POWER,  INPUT_PULLUP);
  pinMode(BTN_LISTEN, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.setMinSecurity(WIFI_AUTH_WPA_PSK);   // allow older WPA hotspots (fixes reason 211)
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to Wi-Fi");
  unsigned long t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 15000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi not connected yet (will keep trying)");
  }

#if USE_WEBSOCKET
  ws.begin(PI_HOST, PI_PORT, "/ws/panel");
  ws.onEvent(onWsEvent);
  ws.setReconnectInterval(2000);
  ws.enableHeartbeat(10000, 3000, 2);
#endif
}

void loop() {
#if USE_WEBSOCKET
  ws.loop();
#else
  pollLights();
#endif
  checkButtons();
  checkPowerHold();
  updateLights();
}