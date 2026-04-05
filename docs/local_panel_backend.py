#!/usr/bin/env python3
import argparse
import json
import math
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


DOCS_DIR = Path(__file__).resolve().parent


class DeviceState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.boot = time.time()
        self.wifi_ssid = "tynieckasmart"
        self.wifi_rssi = -56.0
        self.last_kh = float("nan")
        self.a1_v = 1.680
        self.ph_slope = -5.0
        self.ph_offset = 15.41
        self.dallas_c = 24.0
        self.ph_cal1_target = 6.89
        self.ph_cal2_target = 9.12
        self.ph_cal1_v = 1.680
        self.ph_cal2_v = 1.630
        self.p1_ml = 0.0
        self.p2_ml = 0.0
        self.p1_speed = 100.0
        self.p2_speed = 100.0
        self.manual_vol = 20.0
        self.switches = {
            "manual_hold_p1": False,
            "manual_hold_p2": False,
            "manual_hold_air": False,
            "p1_intake": False,
            "p2_return": False,
            "air_pump": False,
        }
        self.kh_status = "Idle"
        self.kh_mode = "Idle"
        self.last_error = "None"

    def tick(self) -> None:
        t = time.time() - self.boot
        with self.lock:
            self.a1_v = 1.68 + 0.01 * math.sin(t / 7.0)
            self.wifi_rssi = -56 + 2.5 * math.sin(t / 11.0)
            self.dallas_c = 24.0 + 0.4 * math.sin(t / 20.0)

    def main_ph(self) -> float:
        with self.lock:
            return self.ph_slope * self.a1_v + self.ph_offset

    def uptime_s(self) -> int:
        return int(time.time() - self.boot)


STATE = DeviceState()


def as_state(entity_id: str, state, value=None):
    payload = {"id": entity_id, "state": state}
    if value is not None:
        payload["value"] = value
    return payload


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def log_message(self, format, *args):
        return

    def _json(self, payload, code=HTTPStatus.OK):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _not_found(self):
        self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def _ok(self):
        self._json({"ok": True})

    def do_GET(self):
        if self.path.startswith("/api/"):
            STATE.tick()
            return self.handle_api_get()
        if self.path == "/":
            self.path = "/webgui-prototype.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.handle_api_post()
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.end_headers()

    def handle_api_get(self):
        p = unquote(urlparse(self.path).path[len("/api"):])

        with STATE.lock:
            if p in ("/sensor/main_ph", "/sensor-main_ph"):
                return self._json(as_state("sensor-main_ph", f"{STATE.main_ph():.2f}"))
            if p in ("/sensor/a1_ph_voltage__v_", "/sensor-a1_ph_voltage__v_"):
                return self._json(as_state("sensor-a1_ph_voltage__v_", f"{STATE.a1_v:.3f} V"))
            if p in ("/sensor/last_kh__dkh_", "/sensor-last_kh__dkh_", "/sensor/kh_last"):
                s = "NA" if math.isnan(STATE.last_kh) else f"{STATE.last_kh:.2f}"
                return self._json(as_state("sensor-last_kh__dkh_", s))
            if p in ("/sensor/wifi_rssi", "/sensor-wifi_rssi", "/sensor/api_wifi_rssi"):
                return self._json(as_state("sensor-wifi_rssi", f"{STATE.wifi_rssi:.0f} dBm"))
            if p in ("/text_sensor/wifi_ssid", "/text_sensor-wifi_ssid", "/text_sensor/api_wifi_ssid"):
                return self._json(as_state("text_sensor-wifi_ssid", STATE.wifi_ssid))
            if p in ("/sensor/dallas_temp__c_", "/sensor-dallas_temp__c_", "/sensor/dallas_temp_c"):
                return self._json(as_state("sensor-dallas_temp__c_", f"{STATE.dallas_c:.2f} C"))
            if p == "/text_sensor/kh_status":
                return self._json(as_state("text_sensor-kh_status", STATE.kh_status))
            if p == "/text_sensor/last_error":
                return self._json(as_state("text_sensor-last_error", STATE.last_error))
            if p == "/version":
                return self._json({"version": "python-local-prototype"})

        return self._not_found()

    def handle_api_post(self):
        parsed = urlparse(self.path)
        p = unquote(parsed.path[len("/api"):])
        query = parse_qs(parsed.query)

        length = int(self.headers.get("Content-Length", "0"))
        if length > 0:
            self.rfile.read(length)

        with STATE.lock:
            if p.startswith("/number/") and p.endswith("/set"):
                object_id = p[len("/number/"):-len("/set")]
                raw_value = query.get("value", ["0"])[0]
                try:
                    value = float(raw_value)
                except ValueError:
                    value = 0.0
                return self.apply_number(object_id, value)

            if p.startswith("/switch/"):
                parts = [x for x in p.split("/") if x]
                if len(parts) == 3 and parts[0] == "switch":
                    object_id, action = parts[1], parts[2]
                    if object_id in STATE.switches:
                        STATE.switches[object_id] = action == "turn_on"
                        STATE.kh_status = f"{object_id} -> {action}"
                        return self._ok()
                return self._not_found()

            if p.startswith("/button/") and p.endswith("/press"):
                object_id = p[len("/button/"):-len("/press")]
                return self.apply_button(object_id)

        return self._not_found()

    def apply_number(self, object_id: str, value: float):
        mapping = {
            "ph_cal_point_1_target": "ph_cal1_target",
            "ph_cal_point_2_target": "ph_cal2_target",
            "p1_measured_volume__ml_": "p1_ml",
            "p2_measured_volume__ml_": "p2_ml",
            "manual_test_volume__ml_": "manual_vol",
            "p1_speed____": "p1_speed",
            "p2_speed____": "p2_speed",
        }
        if object_id not in mapping:
            return self._not_found()
        setattr(STATE, mapping[object_id], value)
        return self._ok()

    def apply_button(self, object_id: str):
        if object_id == "capture_ph_point_1":
            STATE.ph_cal1_v = STATE.a1_v
            STATE.kh_status = "Captured pH point 1"
            return self._ok()
        if object_id == "capture_ph_point_2":
            STATE.ph_cal2_v = STATE.a1_v
            STATE.kh_status = "Captured pH point 2"
            return self._ok()
        if object_id == "apply_ph_point_1_calibration":
            STATE.ph_offset = STATE.ph_cal1_target - STATE.ph_slope * STATE.ph_cal1_v
            STATE.kh_status = "pH point 1 calibration applied"
            STATE.last_error = "None"
            return self._ok()
        if object_id in ("apply_ph_point_2_optional", "save_ph_2-point_calibration"):
            dv = STATE.ph_cal2_v - STATE.ph_cal1_v
            dp = STATE.ph_cal2_target - STATE.ph_cal1_target
            if abs(dv) < 0.005 or abs(dp) < 0.05:
                STATE.ph_offset = STATE.ph_cal1_target - STATE.ph_slope * STATE.ph_cal1_v
                STATE.kh_status = "pH point 1 applied (pH2 optional)"
                STATE.last_error = "pH2 optional: single-point applied"
                return self._ok()
            STATE.ph_slope = dp / dv
            STATE.ph_offset = STATE.ph_cal1_target - STATE.ph_slope * STATE.ph_cal1_v
            STATE.kh_status = "pH 2-point calibration saved"
            STATE.last_error = "None"
            return self._ok()
        if object_id == "start_kh_quick_60s":
            STATE.kh_mode = "Quick 60s"
            STATE.kh_status = "KH quick 60s running"
            # Fake result after quick run trigger
            STATE.last_kh = max(0.0, (7.00 - STATE.main_ph()) * 0.65)
            return self._ok()
        if object_id == "start_service_test":
            STATE.kh_mode = "Service"
            STATE.kh_status = "Service test running"
            return self._ok()
        if object_id == "kh_stop":
            STATE.kh_mode = "Stopped"
            STATE.kh_status = "Stopped"
            for k in STATE.switches:
                STATE.switches[k] = False
            return self._ok()
        if object_id in (
            "calibrate_p1__60s_",
            "calibrate_p2__60s_",
            "save_p1_calibration",
            "save_p2_calibration",
            "manual_test_p1",
            "manual_test_p2",
        ):
            STATE.kh_status = object_id
            return self._ok()
        return self._not_found()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8091)
    args = parser.parse_args()

    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"Local panel backend: http://127.0.0.1:{args.port}/webgui-prototype.html")
        print("API base in UI should be /api (auto on localhost).")
        server.serve_forever()


if __name__ == "__main__":
    main()

