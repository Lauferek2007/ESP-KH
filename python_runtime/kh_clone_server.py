#!/usr/bin/env python3
import argparse
import json
import math
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"


@dataclass
class Timings:
    predrain_s: float
    fill_s: float
    settle_before_s: float
    aeration_s: float
    settle_after_s: float
    drain_s: float
    total_s: float
    volume_ml: float


class KhClone:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.boot_ts = time.time()

        # Identity/network
        self.wifi_ssid = "tynieckasmart"
        self.wifi_rssi = -56.0

        # Sensors
        self.a1_v = 1.680
        self.ph_slope = -5.0
        self.ph_offset = 15.410
        self.dallas_c = 24.2
        self.ph_before = float("nan")
        self.ph_after = float("nan")
        self.kh_last = float("nan")

        # Safety/config
        self.chamber_ml = 60.0
        self.fallback_fill_s = 25.0
        self.fallback_drain_s = 25.0
        self.t_settle_before_s = 30.0
        self.t_settle_after_s = 20.0
        self.t_aer_full_s = 600.0
        self.quick_factor = 0.25
        self.service_factor = 0.10
        self.co2_eq = 3.0

        # Pump calibration
        self.p1_mlps = 0.333
        self.p2_mlps = 0.333
        self.p1_measured_ml = 0.0
        self.p2_measured_ml = 0.0
        self.p1_speed_pct = 100.0
        self.p2_speed_pct = 100.0

        # pH calibration points
        self.ph_cal1_target = 6.89
        self.ph_cal2_target = 9.12
        self.ph_cal1_v = 1.682
        self.ph_cal2_v = 1.679

        # Manual
        self.manual_test_volume_ml = 20.0
        self.manual_air_pulse_s = 3.0

        # Actuators
        self.switches = {
            "p1_intake": False,
            "p2_return": False,
            "air_pump": False,
            "manual_hold_p1": False,
            "manual_hold_p2": False,
            "manual_hold_air": False,
        }

        # Status
        self.kh_mode = "Idle"
        self.kh_status = "Idle"
        self.last_error = "None"

        # Worker control
        self._stop_evt = threading.Event()
        self._worker: Optional[threading.Thread] = None

    def uptime_s(self) -> int:
        return int(time.time() - self.boot_ts)

    def main_ph(self) -> float:
        return self.ph_slope * self.a1_v + self.ph_offset

    def _safe_volume(self) -> float:
        vol = self.chamber_ml
        if vol > 100.0:
            self.last_error = "Chamber volume capped to 100 ml"
            return 100.0
        return max(1.0, vol)

    def _calc_timings(self, mode: str) -> Timings:
        vol = self._safe_volume()
        fill_s = (vol / self.p1_mlps) if self.p1_mlps > 0.01 else self.fallback_fill_s
        drain_s = (vol / self.p2_mlps) if self.p2_mlps > 0.01 else self.fallback_drain_s
        predrain_s = drain_s * 1.5  # extra emptying safety margin

        settle_before = self.t_settle_before_s
        settle_after = self.t_settle_after_s
        aer = self.t_aer_full_s
        mult = 1.0
        if mode == "Quick":
            mult = self.quick_factor
        elif mode == "Service":
            mult = self.service_factor
        elif mode == "Quick 60s":
            base = predrain_s + fill_s + settle_before + aer + settle_after + drain_s
            mult = 60.0 / max(base, 1.0)
            mult = min(3.0, max(0.02, mult))

        predrain_s *= mult
        fill_s *= mult
        settle_before *= mult
        aer *= mult
        settle_after *= mult
        drain_s *= mult
        total = predrain_s + fill_s + settle_before + aer + settle_after + drain_s
        return Timings(predrain_s, fill_s, settle_before, aer, settle_after, drain_s, total, vol)

    def _set_switches(self, p1=False, p2=False, air=False):
        self.switches["p1_intake"] = p1
        self.switches["p2_return"] = p2
        self.switches["air_pump"] = air

    def _sleep_stage(self, seconds: float) -> bool:
        end = time.time() + max(0.0, seconds)
        while time.time() < end:
            if self._stop_evt.is_set():
                return False
            time.sleep(0.1)
        return True

    def _sample_ph(self, aerated: bool) -> float:
        # Simple model for local tests: aeration slightly increases pH
        base = self.main_ph()
        jitter = 0.03 * math.sin(time.time() / 3.0)
        return base + (0.12 if aerated else 0.0) + jitter

    def _compute_kh(self, ph_before: float, ph_after: float) -> float:
        # Test approximation for backend prototype only.
        # Real algorithm should be aligned with final chemistry model.
        dph = ph_after - ph_before
        return max(0.0, dph * 12.0)

    def stop_all(self):
        self._stop_evt.set()
        self._set_switches(False, False, False)
        self.switches["manual_hold_p1"] = False
        self.switches["manual_hold_p2"] = False
        self.switches["manual_hold_air"] = False
        self.kh_mode = "Stopped"
        self.kh_status = "Stopped"

    def _run_cycle(self, mode: str):
        with self.lock:
            self._stop_evt.clear()
            self.kh_mode = mode
            self.kh_status = "Prepare times"
            self.last_error = "None"
            timings = self._calc_timings(mode)

        # 1) pre-drain
        with self.lock:
            self.kh_status = f"Predrain ({timings.predrain_s:.1f}s)"
            self._set_switches(False, True, False)
        if not self._sleep_stage(timings.predrain_s):
            return

        # 2) fill fresh sample
        with self.lock:
            self.kh_status = f"Fill sample ({timings.fill_s:.1f}s)"
            self._set_switches(True, False, False)
        if not self._sleep_stage(timings.fill_s):
            return

        # 3) settle + first measure
        with self.lock:
            self.kh_status = f"Settle before ({timings.settle_before_s:.1f}s)"
            self._set_switches(False, False, False)
        if not self._sleep_stage(timings.settle_before_s):
            return
        with self.lock:
            self.ph_before = self._sample_ph(aerated=False)
            self.kh_status = f"Measure #1 pH={self.ph_before:.2f}"

        # 4) aeration
        with self.lock:
            self.kh_status = f"Aeration ({timings.aeration_s:.1f}s)"
            self._set_switches(False, False, True)
        if not self._sleep_stage(timings.aeration_s):
            return

        # 5) settle + second measure
        with self.lock:
            self.kh_status = f"Settle after ({timings.settle_after_s:.1f}s)"
            self._set_switches(False, False, False)
        if not self._sleep_stage(timings.settle_after_s):
            return
        with self.lock:
            self.ph_after = self._sample_ph(aerated=True)
            self.kh_status = f"Measure #2 pH={self.ph_after:.2f}"

        # 6) final drain
        with self.lock:
            self.kh_status = f"Drain return ({timings.drain_s:.1f}s)"
            self._set_switches(False, True, False)
        if not self._sleep_stage(timings.drain_s):
            return

        with self.lock:
            self._set_switches(False, False, False)
            self.kh_last = self._compute_kh(self.ph_before, self.ph_after)
            self.kh_status = f"Done. KH={self.kh_last:.2f} dKH"
            self.kh_mode = mode

    def start_cycle(self, mode: str):
        if self._worker and self._worker.is_alive():
            self.last_error = "Cycle already running"
            return False
        self._worker = threading.Thread(target=self._run_cycle, args=(mode,), daemon=True)
        self._worker.start()
        return True

    def periodic_update(self):
        while True:
            with self.lock:
                t = time.time() - self.boot_ts
                self.a1_v = 1.680 + 0.008 * math.sin(t / 6.0)
                self.wifi_rssi = -56.0 + 3.0 * math.sin(t / 11.0)
                self.dallas_c = 24.2 + 0.6 * math.sin(t / 23.0)
            time.sleep(1.0)


STATE = KhClone()


def state_json(entity_id: str, state):
    return {"id": entity_id, "state": state}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def log_message(self, format, *args):
        return

    def _send_json(self, payload, code=HTTPStatus.OK):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._api_get()
        if self.path == "/":
            self.path = "/webgui-prototype.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._api_post()
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.end_headers()

    def _api_get(self):
        p = unquote(urlparse(self.path).path[len("/api"):])
        with STATE.lock:
            if p in ("/version",):
                return self._send_json({"version": "kh-python-clone"})
            if p in ("/sensor/main_ph", "/sensor-main_ph"):
                return self._send_json(state_json("sensor-main_ph", f"{STATE.main_ph():.2f}"))
            if p in ("/sensor/a1_ph_voltage__v_", "/sensor-a1_ph_voltage__v_"):
                return self._send_json(state_json("sensor-a1_ph_voltage__v_", f"{STATE.a1_v:.3f} V"))
            if p in ("/sensor/last_kh__dkh_", "/sensor/kh_last", "/sensor-last_kh__dkh_"):
                val = "NA" if math.isnan(STATE.kh_last) else f"{STATE.kh_last:.2f}"
                return self._send_json(state_json("sensor-last_kh__dkh_", val))
            if p in ("/sensor/wifi_rssi", "/sensor/api_wifi_rssi", "/sensor-wifi_rssi"):
                return self._send_json(state_json("sensor-wifi_rssi", f"{STATE.wifi_rssi:.0f} dBm"))
            if p in ("/text_sensor/wifi_ssid", "/text_sensor/api_wifi_ssid", "/text_sensor-wifi_ssid"):
                return self._send_json(state_json("text_sensor-wifi_ssid", STATE.wifi_ssid))
            if p in ("/sensor/dallas_temp__c_", "/sensor/dallas_temp_c", "/sensor-dallas_temp__c_"):
                return self._send_json(state_json("sensor-dallas_temp__c_", f"{STATE.dallas_c:.2f} C"))
            if p == "/text_sensor/kh_status":
                return self._send_json(state_json("text_sensor-kh_status", STATE.kh_status))
            if p == "/text_sensor/last_error":
                return self._send_json(state_json("text_sensor-last_error", STATE.last_error))
            if p == "/sensor/uptime__s_":
                return self._send_json(state_json("sensor-uptime__s_", str(STATE.uptime_s())))
        return self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def _api_post(self):
        parsed = urlparse(self.path)
        p = unquote(parsed.path[len("/api"):])
        query = parse_qs(parsed.query)
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)

        if p.startswith("/number/") and p.endswith("/set"):
            object_id = p[len("/number/"):-len("/set")]
            raw = query.get("value", ["0"])[0]
            try:
                value = float(raw)
            except ValueError:
                value = 0.0
            return self._set_number(object_id, value)

        if p.startswith("/switch/"):
            parts = [x for x in p.split("/") if x]
            if len(parts) == 3 and parts[0] == "switch":
                return self._switch(parts[1], parts[2])

        if p.startswith("/button/") and p.endswith("/press"):
            object_id = p[len("/button/"):-len("/press")]
            return self._button(object_id)

        return self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def _set_number(self, object_id: str, value: float):
        with STATE.lock:
            mapping = {
                "ph_cal_point_1_target": "ph_cal1_target",
                "ph_cal_point_2_target": "ph_cal2_target",
                "p1_measured_volume__ml_": "p1_measured_ml",
                "p2_measured_volume__ml_": "p2_measured_ml",
                "manual_test_volume__ml_": "manual_test_volume_ml",
                "p1_speed____": "p1_speed_pct",
                "p2_speed____": "p2_speed_pct",
                "quick_factor": "quick_factor",
                "service_factor": "service_factor",
                "chamber_volume__ml_": "chamber_ml",
            }
            key = mapping.get(object_id)
            if not key:
                return self._send_json({"error": "unknown_number"}, HTTPStatus.NOT_FOUND)
            setattr(STATE, key, value)
        return self._send_json({"ok": True})

    def _switch(self, object_id: str, action: str):
        with STATE.lock:
            if object_id not in STATE.switches:
                return self._send_json({"error": "unknown_switch"}, HTTPStatus.NOT_FOUND)
            STATE.switches[object_id] = action == "turn_on"
            STATE.kh_status = f"{object_id} -> {action}"
        return self._send_json({"ok": True})

    def _button(self, object_id: str):
        with STATE.lock:
            if object_id == "capture_ph_point_1":
                STATE.ph_cal1_v = STATE.a1_v
                STATE.kh_status = "Captured pH point 1"
                return self._send_json({"ok": True})
            if object_id == "capture_ph_point_2":
                STATE.ph_cal2_v = STATE.a1_v
                STATE.kh_status = "Captured pH point 2"
                return self._send_json({"ok": True})
            if object_id == "apply_ph_point_1_calibration":
                STATE.ph_offset = STATE.ph_cal1_target - STATE.ph_slope * STATE.ph_cal1_v
                STATE.kh_status = "pH point 1 calibration applied"
                STATE.last_error = "None"
                return self._send_json({"ok": True})
            if object_id in ("apply_ph_point_2_optional", "save_ph_2-point_calibration"):
                dv = STATE.ph_cal2_v - STATE.ph_cal1_v
                dp = STATE.ph_cal2_target - STATE.ph_cal1_target
                if abs(dv) < 0.005 or abs(dp) < 0.05:
                    STATE.ph_offset = STATE.ph_cal1_target - STATE.ph_slope * STATE.ph_cal1_v
                    STATE.kh_status = "pH point 1 applied (pH2 optional)"
                    STATE.last_error = "pH2 optional: single-point applied"
                    return self._send_json({"ok": True})
                STATE.ph_slope = dp / dv
                STATE.ph_offset = STATE.ph_cal1_target - STATE.ph_slope * STATE.ph_cal1_v
                STATE.kh_status = "pH 2-point calibration saved"
                STATE.last_error = "None"
                return self._send_json({"ok": True})

            if object_id == "start_kh_full":
                ok = STATE.start_cycle("Full")
                return self._send_json({"ok": ok})
            if object_id == "start_kh_quick":
                ok = STATE.start_cycle("Quick")
                return self._send_json({"ok": ok})
            if object_id == "start_kh_quick_60s":
                ok = STATE.start_cycle("Quick 60s")
                return self._send_json({"ok": ok})
            if object_id == "start_service_test":
                ok = STATE.start_cycle("Service")
                return self._send_json({"ok": ok})
            if object_id == "kh_stop":
                STATE.stop_all()
                return self._send_json({"ok": True})

            if object_id == "calibrate_p1__60s_":
                STATE.kh_status = "P1 calibration running (60s)"
                return self._send_json({"ok": True})
            if object_id == "calibrate_p2__60s_":
                STATE.kh_status = "P2 calibration running (60s)"
                return self._send_json({"ok": True})
            if object_id == "save_p1_calibration":
                if STATE.p1_measured_ml > 0:
                    STATE.p1_mlps = STATE.p1_measured_ml / 60.0
                    STATE.kh_status = "P1 calibration saved"
                    STATE.last_error = "None"
                else:
                    STATE.last_error = "Invalid P1 calibration input"
                return self._send_json({"ok": True})
            if object_id == "save_p2_calibration":
                if STATE.p2_measured_ml > 0:
                    STATE.p2_mlps = STATE.p2_measured_ml / 60.0
                    STATE.kh_status = "P2 calibration saved"
                    STATE.last_error = "None"
                else:
                    STATE.last_error = "Invalid P2 calibration input"
                return self._send_json({"ok": True})

            if object_id in ("manual_test_p1", "manual_test_p2", "manual_test_air"):
                STATE.kh_status = f"{object_id} done"
                return self._send_json({"ok": True})

        return self._send_json({"error": "unknown_button"}, HTTPStatus.NOT_FOUND)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    args = parser.parse_args()

    threading.Thread(target=STATE.periodic_update, daemon=True).start()

    with ThreadingHTTPServer((args.host, args.port), Handler) as server:
        print(f"KH python clone: http://{args.host}:{args.port}/webgui-prototype.html")
        print("This backend emulates ESP API under /api/* for local end-to-end tests.")
        server.serve_forever()


if __name__ == "__main__":
    main()

