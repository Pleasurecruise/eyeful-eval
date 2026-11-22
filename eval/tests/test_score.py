from __future__ import annotations

import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.model import Finding, Review
from score.relay import relay
from score.reviewbench import candidate


class Relay(unittest.TestCase):
    def test_forwards_with_added_headers(self) -> None:
        seen: dict[str, str] = {}

        class Upstream(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                seen.update((k.lower(), v) for k, v in self.headers.items())
                seen["path"], seen["body"] = self.path, self.rfile.read(int(self.headers["Content-Length"])).decode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')

            def log_message(self, *_: object) -> None:
                pass

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        try:
            with relay(f"http://127.0.0.1:{upstream.server_address[1]}/v1", {"x-opencode-session": "s1"}) as base:
                request = urllib.request.Request(
                    base + "/chat/completions", data=b'{"m": 1}', headers={"Authorization": "Bearer k", "Content-Type": "application/json"}, method="POST"
                )
                with urllib.request.urlopen(request) as answer:
                    self.assertEqual(answer.read(), b'{"ok": true}')
        finally:
            upstream.shutdown()
        self.assertEqual(
            (seen["path"], seen["body"], seen["authorization"], seen["x-opencode-session"]), ("/v1/chat/completions", '{"m": 1}', "Bearer k", "s1")
        )


class ReviewBench(unittest.TestCase):
    def test_candidate(self) -> None:
        pr = {"repo": "https://github.com/owner/repo", "pr_number": 12, "base": "b" * 40, "head": "a" * 40}
        shown, hidden = (
            Finding(i, "src/pool.ts", line, "error", title, body, "concurrency", "test", "", "", "", "", False, reported)
            for i, line, title, body, reported in (
                ("0/concurrency/0", 42, "conns is read without the mutex.", "Two requests can lose a write.", True),
                ("0/style/0", 7, "Name the constant.", "", False),
            )
        )
        review = Review("owner_repo_12-aaaaaaaa", "eyeful", "panel", 1, "read_only", "complete", (shown, hidden), 1000, 10, 1.5)
        made = candidate(pr, review)
        self.assertEqual(made["pr"], pr)
        self.assertEqual(
            made["findings"],
            [
                {
                    "producer": "eyeful-panel-1-read_only",
                    "file": "src/pool.ts",
                    "start_line": 42,
                    "end_line": 42,
                    "message": "conns is read without the mutex.\n\nTwo requests can lose a write.",
                }
            ],
        )
        self.assertEqual(made["usage"], {"time_in_ms": 1500, "total_tokens": 1000})


if __name__ == "__main__":
    unittest.main()
