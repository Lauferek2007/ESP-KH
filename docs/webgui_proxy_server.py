#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import urllib.error
import argparse
from pathlib import Path

ESP_BASE = "http://192.168.1.200"
DOCS_DIR = Path(__file__).resolve().parent
PORT = 8090


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def _proxy(self, method: str):
        target = self.path[len("/api"):]
        if not target.startswith("/"):
            target = "/" + target
        url = ESP_BASE + target

        body = None
        if method in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b""

        req = urllib.request.Request(url=url, data=body, method=method)
        for h in ("Content-Type", "Accept"):
            v = self.headers.get(h)
            if v:
                req.add_header(h, v)

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                payload = resp.read()
                self.send_response(resp.getcode())
                ctype = resp.headers.get("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as e:
            payload = e.read() if hasattr(e, "read") else b""
            self.send_response(e.code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(payload or str(e).encode("utf-8", "ignore"))
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                ('{"error":"proxy_failed","detail":"%s"}' % str(e).replace('"', "'")).encode("utf-8", "ignore")
            )

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy("GET")
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy("POST")
        self.send_response(405)
        self.end_headers()

    def log_message(self, fmt, *args):
        return


def main():
    global ESP_BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--esp", type=str, default=ESP_BASE)
    args = parser.parse_args()

    ESP_BASE = args.esp.rstrip("/")

    with socketserver.ThreadingTCPServer(("127.0.0.1", args.port), Handler) as httpd:
        print(f"Serving docs on http://127.0.0.1:{args.port}/webgui-prototype.html")
        print(f"Proxying /api/* -> {ESP_BASE}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
