"""Read-only zero-dependency Render free preview. No background jobs or persistent writes."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            status, payload = 200, {"status": "ok", "service": "schumann-saa012-free-preview"}
        elif self.path == "/":
            status, payload = 200, {"service": "schumann-saa012-free-preview", "mode": "read-only", "research": "disabled", "persistence": "none", "note": "SAA-012 research remains offline."}
        else:
            status, payload = 404, {"error": "not found"}
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
