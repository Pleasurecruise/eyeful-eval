"""Forwards requests to a model provider with headers the provider requires and a benchmark's judge does not send."""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOP = {"host", "content-length", "connection", "accept-encoding"}


@contextmanager
def relay(upstream: str, headers: dict[str, str]) -> Iterator[str]:
    """Serves on a local port until the block ends, and yields its base URL."""

    class Forward(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            sent = {k: v for k, v in self.headers.items() if k.lower() not in HOP} | headers
            request = urllib.request.Request(upstream.rstrip("/") + self.path, data=body, headers=sent, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=600) as answer:
                    status, data, kind = answer.status, answer.read(), answer.headers.get("Content-Type", "application/json")
            except urllib.error.HTTPError as err:
                status, data, kind = err.code, err.read(), err.headers.get("Content-Type", "application/json")
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Forward)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
