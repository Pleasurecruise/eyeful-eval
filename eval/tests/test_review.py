from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.layout import owners
from core.model import Subject
from review.result import read, stopped


class Gates(unittest.TestCase):
    def test_stopped(self) -> None:
        ran = {"status": "unverified", "repro": {}}
        failed = ["FAILED"] * 5
        for verdict, gate in (
            ({"status": "confirmed"}, ""),
            (ran, "runs"),
            (ran | {"change": ["FAILED", "PASSED"]}, "not_flaky"),
            (ran | {"change": ["ERROR"] * 5}, "fails_as_claimed"),
            (ran | {"status": "not_reproduced", "change": ["PASSED"] * 5}, "fails_as_claimed"),
            (ran | {"status": "pre_existing", "change": failed, "base": "FAILED"}, "introduced"),
            (ran | {"status": "reproduced", "change": failed, "base": "ERROR", "fixed": "FAILED"}, "fail_to_pass"),
            (ran | {"status": "reproduced", "change": failed, "base": "PASSED", "fixed": "PASSED"}, "pass_to_pass"),
            (ran | {"status": "fix_verified", "change": failed, "base": "PASSED", "fixed": "PASSED"}, ""),
        ):
            self.assertEqual(stopped(verdict), gate, verdict)


class Retries(unittest.TestCase):
    def test_exhausted_retries_are_failed(self) -> None:
        subject = Subject("s", "crb", "", "/repo", "b", "h", "")
        with tempfile.TemporaryDirectory() as root:
            run = Path(root)
            (run / "outside.json").write_text("[]")
            runs = [{"usage": {"tokens": 5, "micro_usd": 1}, "error": "the agent ran for too long"}]
            (run / "result.json").write_text(json.dumps({"verifications": [], "findings": [], "comments": [], "runs": runs, "outcome": "partial"}))
            self.assertEqual(read(subject, "single", 1, "execution", run, 1.0).outcome, "error")
            (run / "failed").touch()
            self.assertEqual(read(subject, "single", 1, "execution", run, 1.0).outcome, "failed")


class Merged(unittest.TestCase):
    def test_a_comment_takes_its_merged_findings_verdict(self) -> None:
        subject = Subject("s", "swebench", "", "/repo", "b", "h", "")
        repro = {"run": "t.py::test_a", "oracle": "derived"}
        raw = {
            "findings": [
                {"id": "0/correctness/0", "evidence": "analysis"},
                {"id": "0/skeptic/0", "evidence": "test"},
                {"id": "0/skeptic/1", "evidence": "test"},
            ],
            "comments": [
                {
                    "finding": "0/correctness/0",
                    "path": "a.py",
                    "line": 1,
                    "severity": "error",
                    "subject": "s",
                    "discussion": "",
                    "experts": ["correctness", "skeptic"],
                    "decorations": [],
                    "kind": "review",
                    "repro": repro,
                },
                {
                    "finding": "0/skeptic/1",
                    "path": "b.py",
                    "line": 2,
                    "severity": "warning",
                    "subject": "t",
                    "discussion": "",
                    "experts": ["skeptic"],
                    "decorations": [],
                    "kind": "review",
                },
            ],
            "verifications": [
                {"finding": "0/skeptic/0", "status": "fix_verified", "repro": repro, "change": ["FAILED"] * 5, "base": "PASSED", "fixed": "PASSED"},
                {"finding": "0/skeptic/1", "status": "confirmed"},
            ],
            "runs": [],
            "outcome": "complete",
        }
        with tempfile.TemporaryDirectory() as root:
            run = Path(root)
            (run / "stages").mkdir()
            (run / "stages" / "match.json").write_text(
                json.dumps({"root": {"0/correctness/0": "0/correctness/0", "0/skeptic/0": "0/correctness/0", "0/skeptic/1": "0/skeptic/1"}})
            )
            (run / "outside.json").write_text("[]")
            (run / "result.json").write_text(json.dumps(raw))
            self.assertEqual(owners(run, raw), {"0/correctness/0": "0/correctness/0", "0/skeptic/0": "0/correctness/0", "0/skeptic/1": "0/skeptic/1"})
            merged, alone = read(subject, "panel", 1, "execution", run, 1.0).findings
            self.assertEqual((merged.id, merged.status, merged.evidence, merged.oracle), ("0/correctness/0", "fix_verified", "test", "derived"))
            self.assertEqual((alone.id, alone.status), ("0/skeptic/1", "confirmed"))


class Leaks(unittest.TestCase):
    def test_a_condition_inherits_its_finders_leak(self) -> None:
        subject = Subject("s", "swebench", "", "/repo", "b", "h", "")
        raw = {"findings": [], "comments": [], "verifications": [], "runs": [], "outcome": "complete"}
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            for condition in ("execution", "read_only"):
                (home / condition / "agents").mkdir(parents=True)
                (home / condition / "outside.json").write_text("[]")
                (home / condition / "result.json").write_text(json.dumps(raw))
            (home / "execution" / "agents" / "expert-correctness-1.jsonl").write_text("")
            (home / "execution" / "agents" / "judge-1.jsonl").write_text("")
            with mock.patch("review.result.outside", side_effect=lambda t, _: ["/elsewhere"] if t.name.startswith("judge") else []):
                self.assertEqual(read(subject, "panel", 1, "read_only", home / "read_only", 1.0).outcome, "complete")
            with mock.patch("review.result.outside", side_effect=lambda t, _: ["/elsewhere"] if t.name.startswith("expert") else []):
                self.assertEqual(read(subject, "panel", 1, "read_only", home / "read_only", 1.0).outcome, "leaked")
                self.assertEqual(read(subject, "panel", 1, "execution", home / "execution", 1.0).outcome, "complete")


if __name__ == "__main__":
    unittest.main()
