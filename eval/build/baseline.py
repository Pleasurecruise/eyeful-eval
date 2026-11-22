"""Checks SWE-bench subjects: in a throwaway checkout with the task's test patch, its hidden FAIL_TO_PASS tests pass on the base and fail on the head, without network."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from build.subjects import RUNNERS, labels
from core.model import Subject, load_subjects


def passes(subject: Subject, commit: str, patch: str, tests: list[str]) -> bool:
    with tempfile.TemporaryDirectory() as tree:
        subprocess.run(["git", "-C", subject.repo, "worktree", "add", "--quiet", "--detach", tree, commit], check=True)
        try:
            subprocess.run(["git", "apply", "--whitespace=nowarn"], cwd=tree, input=patch, text=True, check=True)
            return subprocess.run(["sh", ".eyeful/run.sh", *tests], cwd=tree, capture_output=True, text=True).returncode == 0
        finally:
            subprocess.run(["git", "-C", subject.repo, "worktree", "remove", "--force", tree], check=True)


def check(subject: Subject, row: dict) -> dict:
    tests = labels(json.loads(row["FAIL_TO_PASS"]), RUNNERS[row["repo"]].label)
    return {
        "tests": len(tests),
        "base_passes": passes(subject, subject.base, row["test_patch"], tests),
        "head_fails": not passes(subject, subject.head, row["test_patch"], tests),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True, help="the SWE-bench rows, with their test patches")
    parser.add_argument("--out", type=Path, required=True, help="the checks, as JSON")
    args = parser.parse_args()
    rows = {r["instance_id"]: r for r in json.loads(args.data.read_text())}
    results = {}
    for subject in load_subjects(args.subjects).values():
        results[subject.id] = check(subject, rows[subject.id])
        print(subject.id, results[subject.id], flush=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
