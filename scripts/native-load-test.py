#!/usr/bin/env python3
import json
import statistics
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse

BASE = "http://192.168.1.200"
ENDPOINTS = [
    "/sensor/main_ph",
    "/sensor/a1_ph_voltage__v_",
    "/sensor/dallas_temp__c_",
    "/text_sensor/kh_status",
    "/diag/metrics",
]


def http_get(path: str, timeout: float = 5.0):
    start = time.perf_counter()
    req = urllib.request.Request(BASE + path, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return elapsed_ms, body


def worker(iterations: int, out: list, lock: threading.Lock):
    for i in range(iterations):
        path = ENDPOINTS[i % len(ENDPOINTS)]
        try:
            ms, _ = http_get(path)
            with lock:
                out.append(("ok", path, ms))
        except Exception:
            with lock:
                out.append(("err", path, 0.0))


def http_post(path: str, timeout: float = 5.0):
    start = time.perf_counter()
    req = urllib.request.Request(
        BASE + path,
        method="POST",
        data=urllib.parse.urlencode({"x": ""}).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return elapsed_ms, body


def percentile(values, p):
    if not values:
        return 0.0
    idx = int((len(values) - 1) * p)
    return sorted(values)[idx]


def main():
    try:
        http_post("/button/kh_stop/press")
        time.sleep(0.25)
    except Exception:
        pass

    print("Warmup...")
    for _ in range(6):
        ok = False
        for _retry in range(3):
            try:
                http_get("/diag/metrics")
                ok = True
                break
            except Exception:
                time.sleep(0.2)
        if not ok:
            print("Warmup warning: /diag/metrics timeout")
        time.sleep(0.1)

    total_threads = 6
    per_thread = 70
    results = []
    lock = threading.Lock()

    print(f"Running load: threads={total_threads}, per_thread={per_thread}, total={total_threads*per_thread}")
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=total_threads) as ex:
        futures = [ex.submit(worker, per_thread, results, lock) for _ in range(total_threads)]
        for _ in as_completed(futures):
            pass
    t1 = time.perf_counter()

    oks = [r for r in results if r[0] == "ok"]
    errs = [r for r in results if r[0] == "err"]
    lat = [r[2] for r in oks]

    print("")
    print(f"Requests OK={len(oks)} ERR={len(errs)} duration_s={(t1-t0):.2f}")
    if lat:
        print(
            "Latency ms: min={:.2f} avg={:.2f} p95={:.2f} p99={:.2f} max={:.2f}".format(
                min(lat), statistics.mean(lat), percentile(lat, 0.95), percentile(lat, 0.99), max(lat)
            )
        )

    by_path = {}
    for ok, path, ms in oks:
        by_path.setdefault(path, []).append(ms)

    print("")
    print("Per endpoint:")
    for p in ENDPOINTS:
        vals = by_path.get(p, [])
        if not vals:
            print(f"  {p}: no data")
            continue
        print(
            "  {} -> n={} avg={:.2f} p95={:.2f} max={:.2f}".format(
                p, len(vals), statistics.mean(vals), percentile(vals, 0.95), max(vals)
            )
        )

    print("")
    try:
        _, body = http_get("/diag/metrics")
        print("Device /diag/metrics:")
        print(body.decode("utf-8", "ignore"))
    except Exception as e:
        print(f"Cannot read /diag/metrics after load: {e}")


if __name__ == "__main__":
    main()
