"""Runs commands for the evaluation: a failing command raises with its output."""

from __future__ import annotations

import subprocess
from pathlib import Path

IDENTITY = ["-c", "user.name=eyeful", "-c", "user.email=eyeful@localhost", "-c", "commit.gpgsign=false"]


def sh(args: list[str], cwd: Path | None = None, stdin: str | None = None) -> str:
    done = subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:6])}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def git(repo: Path, *args: str, stdin: str | None = None) -> str:
    return sh(["git", *IDENTITY, *args], cwd=repo, stdin=stdin)
