"""Serve the QuickPay frontend and forward /api/* to the Django backend.

The backend has no CORS configuration, so the browser must reach the API from the
same origin as the page. This server does that without any change to the backend.

    python serve.py                     # http://127.0.0.1:8080, API at http://127.0.0.1:8000
    QUICKPAY_API=http://127.0.0.1:9000 PORT=3000 python serve.py
"""

import http.server
import os
import urllib.error
import urllib.request

BACKEND = os.environ.get("QUICKPAY_API", "http://127.0.0.1:8000").rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))
ROOT = os.path.dirname(os.path.abspath(__file__))
FORWARDED_HEADERS = ("Content-Type", "Authorization", "Accept")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def _proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        request = urllib.request.Request(BACKEND + self.path, data=body, method=self.command)
        for name in FORWARDED_HEADERS:
            if self.headers.get(name):
                request.add_header(name, self.headers[name])
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, content_type, data = response.status, response.headers.get("Content-Type"), response.read()
        except urllib.error.HTTPError as error:
            status, content_type, data = error.code, error.headers.get("Content-Type"), error.read()
        except urllib.error.URLError:
            status, content_type = 502, "application/json"
            data = b'{"detail": "The QuickPay API is not reachable. Start the Django server and try again."}'

        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405)


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"QuickPay frontend on http://127.0.0.1:{PORT}  (API -> {BACKEND})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
