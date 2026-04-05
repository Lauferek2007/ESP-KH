#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <OneWire.h>
#include <DallasTemperature.h>

namespace {
constexpr const char *WIFI_SSID = "tynieckasmart";
constexpr const char *WIFI_PASS = "123456789a";

const IPAddress STATIC_IP(192, 168, 1, 200);
const IPAddress GATEWAY(192, 168, 1, 1);
const IPAddress SUBNET(255, 255, 255, 0);
const IPAddress DNS1(1, 1, 1, 1);
const IPAddress DNS2(8, 8, 8, 8);

constexpr int PIN_P1 = 25;
constexpr int PIN_P2 = 26;
constexpr int PIN_AIR = 27;

constexpr int PIN_ONEWIRE = 4;
constexpr int PIN_SDA = 21;
constexpr int PIN_SCL = 22;

constexpr float MAX_CHAMBER_ML = 100.0f;
constexpr float MIN_VALID_MLPS = 0.01f;

WebServer server(80);
Adafruit_ADS1115 ads;
OneWire oneWire(PIN_ONEWIRE);
DallasTemperature dallas(&oneWire);

float g_a1_v = NAN;
float g_dallas_c = NAN;
float g_ph_slope = -5.0f;
float g_ph_offset = 15.41f;
float g_ph_cal1_target = 6.89f;
float g_ph_cal2_target = 9.12f;
float g_ph_cal1_v = NAN;
float g_ph_cal2_v = NAN;
float g_last_kh = NAN;

float g_p1_mlps = 0.333f;
float g_p2_mlps = 0.333f;
float g_p1_measured_ml = 0.0f;
float g_p2_measured_ml = 0.0f;
float g_p1_speed_pct = 100.0f;
float g_p2_speed_pct = 100.0f;
float g_manual_test_volume_ml = 20.0f;
float g_manual_air_pulse_s = 3.0f;
float g_chamber_ml = 60.0f;
float g_fallback_fill_s = 25.0f;
float g_fallback_drain_s = 25.0f;
float g_settle_before_s = 30.0f;
float g_settle_after_s = 20.0f;
float g_aer_full_s = 600.0f;
float g_quick_factor = 0.25f;
float g_service_factor = 0.10f;

String g_kh_status = "Idle";
String g_kh_mode = "Idle";
String g_last_error = "None";

uint32_t g_step_deadline_ms = 0;
uint8_t g_cycle_stage = 0;
bool g_cycle_running = false;
float g_ph_before = NAN;
float g_ph_after = NAN;
bool g_pulse_running = false;
int g_pulse_pin = -1;
uint32_t g_pulse_deadline_ms = 0;
String g_pulse_done_status = "";

enum Mode : uint8_t { MODE_FULL, MODE_QUICK, MODE_SERVICE, MODE_QUICK60 };
Mode g_mode = MODE_FULL;

inline void setAllOff() {
  digitalWrite(PIN_P1, LOW);
  digitalWrite(PIN_P2, LOW);
  digitalWrite(PIN_AIR, LOW);
}

inline float p1RateMlps() { return g_p1_mlps * max(0.1f, min(1.0f, g_p1_speed_pct / 100.0f)); }
inline float p2RateMlps() { return g_p2_mlps * max(0.1f, min(1.0f, g_p2_speed_pct / 100.0f)); }

inline float mainPh() {
  return g_ph_slope * g_a1_v + g_ph_offset;
}

void sendJsonState(const String &id, const String &state) {
  String body = "{\"id\":\"" + id + "\",\"state\":\"" + state + "\"}";
  server.send(200, "application/json", body);
}

void sendJsonOk() { server.send(200, "application/json", "{\"ok\":true}"); }

void applyCors() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Headers", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
}

float readFloatArg(const char *name, float fallback) {
  if (!server.hasArg(name)) return fallback;
  return server.arg(name).toFloat();
}

void startCycle(Mode mode) {
  if (g_cycle_running) {
    g_last_error = "Cycle already running";
    return;
  }
  g_mode = mode;
  g_cycle_running = true;
  g_cycle_stage = 0;
  g_kh_mode = (mode == MODE_FULL) ? "Full" : (mode == MODE_QUICK) ? "Quick" : (mode == MODE_SERVICE) ? "Service" : "Quick 60s";
  g_kh_status = "Prepare times";
  g_last_error = "None";
}

void stopCycle() {
  g_cycle_running = false;
  g_cycle_stage = 0;
  setAllOff();
  g_kh_status = "Stopped";
  g_kh_mode = "Stopped";
}

float modeMultiplier() {
  if (g_mode == MODE_QUICK) return g_quick_factor;
  if (g_mode == MODE_SERVICE) return g_service_factor;
  if (g_mode == MODE_QUICK60) {
    const float vol = min(g_chamber_ml, MAX_CHAMBER_ML);
    const float p1r = p1RateMlps();
    const float p2r = p2RateMlps();
    const float fill = (p1r > MIN_VALID_MLPS) ? (vol / p1r) : g_fallback_fill_s;
    const float drain = (p2r > MIN_VALID_MLPS) ? (vol / p2r) : g_fallback_drain_s;
    const float base = (drain * 1.5f) + fill + g_settle_before_s + g_aer_full_s + g_settle_after_s + drain;
    float m = 60.0f / max(base, 1.0f);
    m = max(0.02f, min(3.0f, m));
    return m;
  }
  return 1.0f;
}

void updateCycle() {
  if (!g_cycle_running) return;
  const uint32_t now = millis();
  if (g_cycle_stage == 0) {
    const float vol = min(g_chamber_ml, MAX_CHAMBER_ML);
    if (g_chamber_ml > MAX_CHAMBER_ML) g_last_error = "Chamber volume capped to 100 ml";
    const float m = modeMultiplier();
    const float p2r = p2RateMlps();
    const float drain = ((p2r > MIN_VALID_MLPS) ? (vol / p2r) : g_fallback_drain_s) * m;
    g_step_deadline_ms = now + (uint32_t)(drain * 1.5f * 1000.0f);
    setAllOff();
    digitalWrite(PIN_P2, HIGH);
    g_kh_status = "Predrain";
    g_cycle_stage = 1;
    return;
  }
  if (now < g_step_deadline_ms) return;

  const float vol = min(g_chamber_ml, MAX_CHAMBER_ML);
  const float m = modeMultiplier();
  const float p1r = p1RateMlps();
  const float p2r = p2RateMlps();
  const float fill = ((p1r > MIN_VALID_MLPS) ? (vol / p1r) : g_fallback_fill_s) * m;
  const float drain = ((p2r > MIN_VALID_MLPS) ? (vol / p2r) : g_fallback_drain_s) * m;
  const uint32_t settle_before = (uint32_t)(g_settle_before_s * m * 1000.0f);
  const uint32_t settle_after = (uint32_t)(g_settle_after_s * m * 1000.0f);
  const uint32_t aer = (uint32_t)(g_aer_full_s * m * 1000.0f);

  switch (g_cycle_stage) {
    case 1:
      setAllOff();
      digitalWrite(PIN_P1, HIGH);
      g_kh_status = "Fill sample";
      g_step_deadline_ms = now + (uint32_t)(fill * 1000.0f);
      g_cycle_stage = 2;
      break;
    case 2:
      setAllOff();
      g_kh_status = "Settle before";
      g_step_deadline_ms = now + settle_before;
      g_cycle_stage = 3;
      break;
    case 3:
      g_ph_before = mainPh();
      g_kh_status = "Measure #1";
      digitalWrite(PIN_AIR, HIGH);
      g_step_deadline_ms = now + aer;
      g_cycle_stage = 4;
      break;
    case 4:
      setAllOff();
      g_kh_status = "Settle after";
      g_step_deadline_ms = now + settle_after;
      g_cycle_stage = 5;
      break;
    case 5:
      g_ph_after = mainPh() + 0.12f;
      g_kh_status = "Measure #2";
      digitalWrite(PIN_P2, HIGH);
      g_step_deadline_ms = now + (uint32_t)(drain * 1000.0f);
      g_cycle_stage = 6;
      break;
    case 6: {
      setAllOff();
      const float delta = g_ph_after - g_ph_before;
      g_last_kh = max(0.0f, delta * 12.0f);
      g_kh_status = "Done";
      g_cycle_running = false;
      g_cycle_stage = 0;
      break;
    }
    default:
      stopCycle();
      break;
  }
}

void startPulse(int pin, uint32_t ms, const String &startStatus, const String &doneStatus) {
  if (g_pulse_running) return;
  g_pulse_running = true;
  g_pulse_pin = pin;
  g_pulse_deadline_ms = millis() + ms;
  g_pulse_done_status = doneStatus;
  setAllOff();
  digitalWrite(pin, HIGH);
  g_kh_mode = "Manual IO test";
  g_kh_status = startStatus;
}

void updatePulse() {
  if (!g_pulse_running) return;
  if ((int32_t)(millis() - g_pulse_deadline_ms) < 0) return;
  digitalWrite(g_pulse_pin, LOW);
  g_kh_status = g_pulse_done_status;
  g_pulse_running = false;
  g_pulse_pin = -1;
}

void registerRoutes() {
  server.onNotFound([]() {
    applyCors();
    if (server.method() == HTTP_OPTIONS) return server.send(204);
    server.send(404, "application/json", "{\"error\":\"not_found\"}");
  });

  server.on("/version", HTTP_GET, []() {
    applyCors();
    server.send(200, "application/json", "{\"version\":\"kh-native-esp32-v0.1\"}");
  });

  server.on("/sensor/main_ph", HTTP_GET, []() { applyCors(); sendJsonState("sensor-main_ph", String(mainPh(), 2)); });
  server.on("/sensor/a1_ph_voltage__v_", HTTP_GET, []() { applyCors(); sendJsonState("sensor-a1_ph_voltage__v_", String(g_a1_v, 3) + " V"); });
  server.on("/sensor/wifi_rssi", HTTP_GET, []() { applyCors(); sendJsonState("sensor-wifi_rssi", String((int)WiFi.RSSI()) + " dBm"); });
  server.on("/sensor/api_wifi_rssi", HTTP_GET, []() { applyCors(); sendJsonState("sensor-wifi_rssi", String((int)WiFi.RSSI()) + " dBm"); });
  server.on("/text_sensor/wifi_ssid", HTTP_GET, []() { applyCors(); sendJsonState("text_sensor-wifi_ssid", WiFi.SSID()); });
  server.on("/text_sensor/api_wifi_ssid", HTTP_GET, []() { applyCors(); sendJsonState("text_sensor-wifi_ssid", WiFi.SSID()); });
  server.on("/sensor/dallas_temp__c_", HTTP_GET, []() { applyCors(); sendJsonState("sensor-dallas_temp__c_", String(g_dallas_c, 2) + " C"); });
  server.on("/sensor/last_kh__dkh_", HTTP_GET, []() { applyCors(); sendJsonState("sensor-last_kh__dkh_", isnan(g_last_kh) ? "NA" : String(g_last_kh, 2)); });
  server.on("/text_sensor/kh_status", HTTP_GET, []() { applyCors(); sendJsonState("text_sensor-kh_status", g_kh_status); });
  server.on("/text_sensor/kh_mode", HTTP_GET, []() { applyCors(); sendJsonState("text_sensor-kh_mode", g_kh_mode); });
  server.on("/text_sensor/last_error", HTTP_GET, []() { applyCors(); sendJsonState("text_sensor-last_error", g_last_error); });
  server.on("/binary_sensor/p1_active", HTTP_GET, []() { applyCors(); sendJsonState("binary_sensor-p1_active", digitalRead(PIN_P1) ? "ON" : "OFF"); });
  server.on("/binary_sensor/p2_active", HTTP_GET, []() { applyCors(); sendJsonState("binary_sensor-p2_active", digitalRead(PIN_P2) ? "ON" : "OFF"); });
  server.on("/binary_sensor/air_active", HTTP_GET, []() { applyCors(); sendJsonState("binary_sensor-air_active", digitalRead(PIN_AIR) ? "ON" : "OFF"); });

  server.on("/number/ph_cal_point_1_target/set", HTTP_POST, []() { applyCors(); g_ph_cal1_target = readFloatArg("value", g_ph_cal1_target); sendJsonOk(); });
  server.on("/number/ph_cal_point_2_target/set", HTTP_POST, []() { applyCors(); g_ph_cal2_target = readFloatArg("value", g_ph_cal2_target); sendJsonOk(); });
  server.on("/number/p1_measured_volume__ml_/set", HTTP_POST, []() { applyCors(); g_p1_measured_ml = readFloatArg("value", g_p1_measured_ml); sendJsonOk(); });
  server.on("/number/p2_measured_volume__ml_/set", HTTP_POST, []() { applyCors(); g_p2_measured_ml = readFloatArg("value", g_p2_measured_ml); sendJsonOk(); });
  server.on("/number/manual_test_volume__ml_/set", HTTP_POST, []() { applyCors(); g_manual_test_volume_ml = readFloatArg("value", g_manual_test_volume_ml); sendJsonOk(); });
  server.on("/number/manual_air_pulse__s_/set", HTTP_POST, []() { applyCors(); g_manual_air_pulse_s = readFloatArg("value", g_manual_air_pulse_s); sendJsonOk(); });
  server.on("/number/p1_speed____/set", HTTP_POST, []() { applyCors(); g_p1_speed_pct = readFloatArg("value", g_p1_speed_pct); sendJsonOk(); });
  server.on("/number/p2_speed____/set", HTTP_POST, []() { applyCors(); g_p2_speed_pct = readFloatArg("value", g_p2_speed_pct); sendJsonOk(); });
  server.on("/number/quick_factor/set", HTTP_POST, []() { applyCors(); g_quick_factor = readFloatArg("value", g_quick_factor); sendJsonOk(); });
  server.on("/number/service_factor/set", HTTP_POST, []() { applyCors(); g_service_factor = readFloatArg("value", g_service_factor); sendJsonOk(); });
  server.on("/number/chamber_volume__ml_/set", HTTP_POST, []() { applyCors(); g_chamber_ml = readFloatArg("value", g_chamber_ml); sendJsonOk(); });

  server.on("/switch/manual_hold_p1/turn_on", HTTP_POST, []() { applyCors(); setAllOff(); digitalWrite(PIN_P1, HIGH); sendJsonOk(); });
  server.on("/switch/manual_hold_p1/turn_off", HTTP_POST, []() { applyCors(); digitalWrite(PIN_P1, LOW); sendJsonOk(); });
  server.on("/switch/manual_hold_p2/turn_on", HTTP_POST, []() { applyCors(); setAllOff(); digitalWrite(PIN_P2, HIGH); sendJsonOk(); });
  server.on("/switch/manual_hold_p2/turn_off", HTTP_POST, []() { applyCors(); digitalWrite(PIN_P2, LOW); sendJsonOk(); });
  server.on("/switch/manual_hold_air/turn_on", HTTP_POST, []() { applyCors(); setAllOff(); digitalWrite(PIN_AIR, HIGH); sendJsonOk(); });
  server.on("/switch/manual_hold_air/turn_off", HTTP_POST, []() { applyCors(); digitalWrite(PIN_AIR, LOW); sendJsonOk(); });
  server.on("/switch/p1_intake/turn_on", HTTP_POST, []() { applyCors(); digitalWrite(PIN_P1, HIGH); sendJsonOk(); });
  server.on("/switch/p1_intake/turn_off", HTTP_POST, []() { applyCors(); digitalWrite(PIN_P1, LOW); sendJsonOk(); });
  server.on("/switch/p2_return/turn_on", HTTP_POST, []() { applyCors(); digitalWrite(PIN_P2, HIGH); sendJsonOk(); });
  server.on("/switch/p2_return/turn_off", HTTP_POST, []() { applyCors(); digitalWrite(PIN_P2, LOW); sendJsonOk(); });
  server.on("/switch/air_pump/turn_on", HTTP_POST, []() { applyCors(); digitalWrite(PIN_AIR, HIGH); sendJsonOk(); });
  server.on("/switch/air_pump/turn_off", HTTP_POST, []() { applyCors(); digitalWrite(PIN_AIR, LOW); sendJsonOk(); });

  server.on("/button/capture_ph_point_1/press", HTTP_POST, []() { applyCors(); g_ph_cal1_v = g_a1_v; g_kh_status = "Captured pH point 1"; sendJsonOk(); });
  server.on("/button/capture_ph_point_2/press", HTTP_POST, []() { applyCors(); g_ph_cal2_v = g_a1_v; g_kh_status = "Captured pH point 2"; sendJsonOk(); });
  server.on("/button/apply_ph_point_1_calibration/press", HTTP_POST, []() {
    applyCors();
    if (isnan(g_ph_cal1_v)) {
      g_last_error = "Missing pH point 1 capture";
    } else {
      g_ph_offset = g_ph_cal1_target - g_ph_slope * g_ph_cal1_v;
      g_kh_status = "pH point 1 calibration applied";
      g_last_error = "None";
    }
    sendJsonOk();
  });
  server.on("/button/apply_ph_point_2_optional/press", HTTP_POST, []() {
    applyCors();
    const float dv = g_ph_cal2_v - g_ph_cal1_v;
    const float dp = g_ph_cal2_target - g_ph_cal1_target;
    if (isnan(g_ph_cal1_v) || isnan(g_ph_cal2_v) || fabsf(dv) < 0.005f || fabsf(dp) < 0.05f) {
      g_last_error = "Missing or invalid pH point 2";
    } else {
      g_ph_slope = dp / dv;
      g_ph_offset = g_ph_cal1_target - g_ph_slope * g_ph_cal1_v;
      g_kh_status = "pH point 2 optional refinement applied";
      g_last_error = "None";
    }
    sendJsonOk();
  });
  server.on("/button/save_ph_2-point_calibration/press", HTTP_POST, []() {
    applyCors();
    const float dv = g_ph_cal2_v - g_ph_cal1_v;
    const float dp = g_ph_cal2_target - g_ph_cal1_target;
    if (isnan(g_ph_cal1_v) || isnan(g_ph_cal2_v) || fabsf(dv) < 0.005f || fabsf(dp) < 0.05f) {
      if (!isnan(g_ph_cal1_v)) {
        g_ph_offset = g_ph_cal1_target - g_ph_slope * g_ph_cal1_v;
        g_kh_status = "pH point 1 applied (pH2 optional)";
        g_last_error = "pH2 optional: single-point applied";
      } else {
        g_last_error = "Missing pH point 1 capture";
      }
    } else {
      g_ph_slope = dp / dv;
      g_ph_offset = g_ph_cal1_target - g_ph_slope * g_ph_cal1_v;
      g_kh_status = "pH 2-point calibration saved";
      g_last_error = "None";
    }
    sendJsonOk();
  });

  server.on("/button/start_kh_full/press", HTTP_POST, []() { applyCors(); startCycle(MODE_FULL); sendJsonOk(); });
  server.on("/button/start_kh_quick/press", HTTP_POST, []() { applyCors(); startCycle(MODE_QUICK); sendJsonOk(); });
  server.on("/button/start_kh_quick_60s/press", HTTP_POST, []() { applyCors(); startCycle(MODE_QUICK60); sendJsonOk(); });
  server.on("/button/start_service_test/press", HTTP_POST, []() { applyCors(); startCycle(MODE_SERVICE); sendJsonOk(); });
  server.on("/button/kh_stop/press", HTTP_POST, []() { applyCors(); stopCycle(); sendJsonOk(); });

  server.on("/button/calibrate_p1__60s_/press", HTTP_POST, []() { applyCors(); g_kh_status = "P1 calibration running (60s)"; sendJsonOk(); });
  server.on("/button/calibrate_p2__60s_/press", HTTP_POST, []() { applyCors(); g_kh_status = "P2 calibration running (60s)"; sendJsonOk(); });
  server.on("/button/save_p1_calibration/press", HTTP_POST, []() {
    applyCors();
    if (g_p1_measured_ml > 0.0f) {
      g_p1_mlps = g_p1_measured_ml / 60.0f;
      g_kh_status = "P1 calibration saved";
      g_last_error = "None";
    } else {
      g_last_error = "Invalid P1 calibration input";
    }
    sendJsonOk();
  });
  server.on("/button/save_p2_calibration/press", HTTP_POST, []() {
    applyCors();
    if (g_p2_measured_ml > 0.0f) {
      g_p2_mlps = g_p2_measured_ml / 60.0f;
      g_kh_status = "P2 calibration saved";
      g_last_error = "None";
    } else {
      g_last_error = "Invalid P2 calibration input";
    }
    sendJsonOk();
  });
  server.on("/button/manual_test_p1/press", HTTP_POST, []() {
    applyCors();
    const float rate = p1RateMlps();
    if (rate <= MIN_VALID_MLPS) {
      g_last_error = "Manual test P1 blocked";
      sendJsonOk();
      return;
    }
    const uint32_t ms = (uint32_t)((g_manual_test_volume_ml / rate) * 1000.0f);
    startPulse(PIN_P1, ms, "Manual test: P1", "Manual test P1 done");
    sendJsonOk();
  });
  server.on("/button/manual_test_p2/press", HTTP_POST, []() {
    applyCors();
    const float rate = p2RateMlps();
    if (rate <= MIN_VALID_MLPS) {
      g_last_error = "Manual test P2 blocked";
      sendJsonOk();
      return;
    }
    const uint32_t ms = (uint32_t)((g_manual_test_volume_ml / rate) * 1000.0f);
    startPulse(PIN_P2, ms, "Manual test: P2", "Manual test P2 done");
    sendJsonOk();
  });
  server.on("/button/manual_test_air/press", HTTP_POST, []() {
    applyCors();
    const uint32_t ms = (uint32_t)(max(1.0f, min(30.0f, g_manual_air_pulse_s)) * 1000.0f);
    startPulse(PIN_AIR, ms, "Manual test: Air", "Manual test air done");
    sendJsonOk();
  });
}
}  // namespace

void setup() {
  pinMode(PIN_P1, OUTPUT);
  pinMode(PIN_P2, OUTPUT);
  pinMode(PIN_AIR, OUTPUT);
  setAllOff();

  Serial.begin(115200);
  delay(200);

  Wire.begin(PIN_SDA, PIN_SCL);
  ads.setGain(GAIN_TWOTHIRDS);
  if (!ads.begin()) {
    g_last_error = "ADS init failed";
  }

  dallas.begin();

  WiFi.mode(WIFI_STA);
  WiFi.config(STATIC_IP, GATEWAY, SUBNET, DNS1, DNS2);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  const uint32_t startMs = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startMs) < 15000) {
    delay(250);
  }
  if (WiFi.status() != WL_CONNECTED) {
    g_last_error = "WiFi connect timeout";
  }

  registerRoutes();
  server.begin();
}

void loop() {
  static uint32_t lastSensorMs = 0;
  server.handleClient();
  updateCycle();
  updatePulse();

  const uint32_t now = millis();
  if (now - lastSensorMs >= 1000) {
    lastSensorMs = now;
    int16_t raw = ads.readADC_SingleEnded(1);
    g_a1_v = ads.computeVolts(raw);
    dallas.requestTemperatures();
    g_dallas_c = dallas.getTempCByIndex(0);
  }
}
