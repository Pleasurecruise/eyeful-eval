from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from build.reviewbench import key, sample
from build.subjects import PATCHED, RUNNERS, commands, labels
from core.layout import flags

PATCH = """diff --git a/app/session.py b/app/session.py
--- a/app/session.py
+++ b/app/session.py
@@ -9,7 +9,8 @@ def is_expired(session, now):
-    return now > session.expires_at
+    return now >= session.expires_at
diff --git a/app/store.py b/app/store.py
--- a/app/store.py
+++ b/app/store.py
@@ -1 +1 @@
-x = 1
+x = 2
"""


class Subjects(unittest.TestCase):
    def test_patched(self) -> None:
        self.assertEqual(PATCHED.findall(PATCH), ["app/session.py", "app/store.py"])

    def test_labels(self) -> None:
        self.assertEqual(labels(["test_a (auth.tests.Login)", "odd name"], True), ["auth.tests.Login.test_a"])
        self.assertEqual(labels(["tests/test_a.py::test_b"], False), ["tests/test_a.py::test_b"])
        self.assertEqual(labels(["t.py::test_a[x y]", "t.py::test_a[x", "t.py::test_b"], False), ["t.py::test_a[x y]", "t.py::test_b"])


class Commands(unittest.TestCase):
    def test_declared_commands_become_flags(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            self.assertEqual(flags(repo), [])
            commands(repo, "eyeful-eval:abc", "linux/arm64", RUNNERS["psf/requests"], [])
            self.assertEqual(flags(repo), ["--test-one", "sh .eyeful/run.sh {test}"])
            commands(repo, "eyeful-eval:abc", "linux/arm64", RUNNERS["psf/requests"], ["t.py::test_a[x y]", "t.py::test_b"])
            self.assertEqual(flags(repo), ["--test-one", "sh .eyeful/run.sh {test}", "--test", "sh .eyeful/run.sh 't.py::test_a[x y]' t.py::test_b"])


class ReviewBench(unittest.TestCase):
    def test_key(self) -> None:
        self.assertEqual(key({"repo": "https://github.com/owner/repo", "pr_number": 12, "head": "a1b2c3d4" + "0" * 32}), "owner_repo_12-a1b2c3d4")

    def test_sample(self) -> None:
        rows = {f"r_{i}-0": {"language": "Go" if i < 6 else "Rust" if i < 9 else "C"} for i in range(10)}
        part = sample(rows, {"r_0-0"}, 4)
        self.assertEqual(len(part), 4)
        self.assertNotIn("r_0-0", part)
        self.assertEqual(sorted(r["language"] for r in part.values()), ["C", "Go", "Go", "Rust"])
        self.assertEqual(part, sample(dict(reversed(list(rows.items()))), {"r_0-0"}, 4))


if __name__ == "__main__":
    unittest.main()
