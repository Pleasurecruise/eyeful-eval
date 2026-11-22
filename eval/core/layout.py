"""The files and names one stage writes and another reads: a subject's declared tests, SWE-bench's images, the benchmarks' pull requests and eyeful's merged comments."""

from __future__ import annotations

import json
import re
from pathlib import Path

CONFIG = "config.yml"
PR = "pr.json"  # beside a ReviewBench subject: the benchmark's repository, number, base and head
PLATFORMS = {"arm64": "linux/arm64", "x86_64": "linux/amd64"}
PULL = re.compile(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)")


def flags(repo: Path) -> list[str]:
    """The test commands a subject declares in .eyeful/config.yml, as eyeful's flags."""
    path = repo / ".eyeful" / CONFIG
    declared = dict(line.split(": ", 1) for line in path.read_text().splitlines() if ": " in line) if path.exists() else {}
    return [f for key, flag in (("test_one", "--test-one"), ("test", "--test")) if key in declared for f in (flag, declared[key])]


def official(name: str, arch: str) -> str:
    """SWE-bench's published image for a task."""
    return f"swebench/sweb.eval.{arch}.{name.replace('__', '_1776_')}:latest"


def pull(url: str) -> tuple[str, str, str, str] | None:
    """A Code Review Bench pull request's subject name, owner, project and number."""
    m = PULL.fullmatch(url)
    return ("{}__{}-{}".format(*m.groups()), *m.groups()) if m else None


def owners(run: Path, raw: dict) -> dict[str, str]:
    """The comment each finding was merged into, through the root eyeful's match stage gave it."""
    match = run / "stages" / "match.json"
    root = json.loads(match.read_text())["root"] if match.exists() else {}
    comment = {root.get(c["finding"], c["finding"]): c["finding"] for c in raw["comments"]}
    return {f["id"]: comment[root.get(f["id"], f["id"])] for f in raw["findings"] if root.get(f["id"], f["id"]) in comment}
