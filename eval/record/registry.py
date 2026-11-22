"""Registers a run for the record: the setup it ran with, and each invocation with its subjects, the scripts' digest and commit, its times and the outcomes. The manifest sits in the run's directory and, committed, in registry/; a directory never mixes setups, and a change to the scripts shows as a new digest."""

from __future__ import annotations

import hashlib
import json
import platform
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from core.model import Review, Subject
from core.shell import sh

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "manifest.json"


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def digest(paths: list[Path], root: Path | None = None) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(str(p.relative_to(root) if root else p.name).encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def setup(binary: Path, subjects: dict[str, Subject], pi: str) -> dict:
    return {
        "dataset": sorted({s.dataset for s in subjects.values()}),
        "eyeful": {"binary": binary.name, "sha256": digest([binary])},
        "agent": {"pi": sh(["pi", "--version"]).strip(), "model": pi or "pi's own settings"},
        "host": platform.platform(),
    }


def begin(out: Path, fixed: dict, invocation: dict) -> None:
    path = out / MANIFEST
    manifest = json.loads(path.read_text()) if path.exists() else {"setup": fixed, "invocations": [], "outcomes": {}}
    if manifest["setup"] != fixed:
        raise SystemExit(f"{out} holds reviews from another setup; see {path}")
    commit = sh(["git", "rev-parse", "HEAD"], cwd=ROOT).strip()
    scripts = digest([p for p in (ROOT / "eval").rglob("*.py") if "tests" not in p.parts], ROOT)
    manifest["invocations"].append(invocation | {"commit": commit, "scripts": scripts, "started": now(), "finished": None})
    save(out, manifest)


def finish(out: Path, reviews: list[Review]) -> None:
    manifest = json.loads((out / MANIFEST).read_text())
    manifest["invocations"][-1]["finished"] = now()
    manifest["outcomes"] = dict(Counter(r.outcome for r in reviews))
    save(out, manifest)


def save(out: Path, manifest: dict) -> None:
    text = json.dumps(manifest, indent=2) + "\n"
    (out / MANIFEST).write_text(text)
    record = ROOT / "registry" / "-".join(manifest["setup"]["dataset"]) / f"{out.name}.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(text)
