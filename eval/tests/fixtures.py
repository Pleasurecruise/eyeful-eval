"""Records shared by the tests."""

from __future__ import annotations

from core.model import Finding, Review


def review(subject: str, rep: int, config: str = "panel") -> Review:
    finding = Finding("0/correctness/0", "a.py", 1, "error", "t", "b", "correctness", "test", "", "", "", "", False, True)
    return Review(subject, "eyeful", config, rep, "none", "complete", (finding,), 1000, 10, 1.0)
