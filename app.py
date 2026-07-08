#!/usr/bin/env python3
"""Local HTTP Server for Shortcut Viewer PWA / Chrome App mode.
Serves the self-contained viewer.html, the PWA manifest, sw.js, and icon assets.
"""
import os
import sys
import json
import argparse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_PORT = 8787
PROJ = os.path.dirname(os.path.abspath(__file__))

class H(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # keep console quiet

    def do_GET(self):
        # Prevent DNS rebinding attacks on local server
        host = (self.headers.get("Host") or "").split(":")[0].strip("[]").lower()
        if host not in ("127.0.0.1", "localhost", "::1", ""):
            return self.send_error(403, "forbidden host")

        if self.path == "/" or self.path.startswith("/?") or self.path == "/index.html":
            path = os.path.join(PROJ, "viewer.html")
            if not os.path.exists(path):
                self.send_error(404, "viewer.html not found. Run build.py or render.py first.")
                return
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(content)

        elif self.path == "/manifest.webmanifest":
            man = json.dumps({
                "name": "Shortcut Viewer",
                "short_name": "Shortcuts",
                "start_url": "/?pwa=1",
                "scope": "/",
                "display": "standalone",
                "display_override": ["window-controls-overlay"],
                "background_color": "#0f1115",
                "theme_color": "#2563eb",
                "icons": [
                    {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                    {"src": "/icon-256.png", "sizes": "256x256", "type": "image/png"},
                    {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml"}
                ]
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json; charset=utf-8")
            self.send_header("Content-Length", str(len(man)))
            self.end_headers()
            self.wfile.write(man)

        elif self.path == "/sw.js":
            sw = b"""// Dummy Service Worker to satisfy Chrome PWA install criteria
self.addEventListener('install', function(e) {
  self.skipWaiting();
});
self.addEventListener('activate', function(e) {
  e.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', function(e) {
  // simple pass-through
  e.respondWith(fetch(e.request));
});
"""
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(sw)))
            self.end_headers()
            self.wfile.write(sw)

        elif self.path == "/favicon.svg":
            path = os.path.join(PROJ, "assets", "icon.svg")
            if not os.path.exists(path):
                self.send_error(404)
                return
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        elif self.path in ("/icon-192.png", "/icon-256.png"):
            filename = "icon-192.png" if "192" in self.path else "icon-256.png"
            path = os.path.join(PROJ, "assets", filename)
            if not os.path.exists(path):
                self.send_error(404)
                return
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        else:
            self.send_error(404, "File not found")

def main():
    ap = argparse.ArgumentParser(description="Shortcut Viewer HTTP Server")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port to run on (default {DEFAULT_PORT})")
    ap.add_argument("--open", action="store_true", help="open in default browser")
    args = ap.parse_args()

    port = args.port
    server = None
    while True:
        try:
            server = HTTPServer(("127.0.0.1", port), H)
            break
        except OSError:
            print(f"Port {port} is busy, trying {port + 1}...")
            port += 1

    url = f"http://127.0.0.1:{port}"
    print(f"\nShortcut Viewer running at: {url}")
    print("Press Ctrl+C to stop the server.\n")

    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
