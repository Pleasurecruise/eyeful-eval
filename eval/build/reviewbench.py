"""Prepares ReviewBench pull requests as review subjects: a sample held out from development, each checked out at the benchmark's head."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

from build.subjects import HISTORY
from core.layout import PR
from core.model import Subject

MIRROR = "https://github.com/review-bench"
DEPTHS = (HISTORY, 3000)
POINTERS = ["-c", "filter.lfs.process=", "-c", "filter.lfs.smudge=", "-c", "filter.lfs.clean=", "-c", "filter.lfs.required=false"]
SAMPLE = 50


def key(row: dict) -> str:
    return f"{row['repo'].removeprefix('https://github.com/').replace('/', '_')}_{row['pr_number']}-{row['head'][:8]}"


def fetch(repo: Path, row: dict) -> str:
    remotes = (f"{MIRROR}/{row['repo'].removeprefix('https://github.com/').replace('/', '_')}.git", f"{row['repo']}.git")
    env = os.environ | {"GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"}
    for depth in DEPTHS:
        for remote in remotes:
            done = subprocess.run(
                ["git", "-C", str(repo), "fetch", "--quiet", f"--depth={depth}", remote, row["base"], row["head"]], capture_output=True, env=env
            )
            if done.returncode == 0:
                break
        base = subprocess.run(["git", "-C", str(repo), "merge-base", row["base"], row["head"]], capture_output=True, text=True)
        if base.returncode == 0:
            (repo / ".git" / "FETCH_HEAD").unlink(missing_ok=True)
            return base.stdout.strip()
    raise RuntimeError("the base and the head share no history that could be fetched")


def subject(row: dict, out: Path, repos: Path) -> Subject:
    name = key(row)
    home = out / name
    home.mkdir(parents=True, exist_ok=True)
    (home / "description.md").write_text(f"{row['title']}\n\n{row.get('body') or ''}".strip() + "\n")
    (home / PR).write_text(json.dumps({k: row[k] for k in ("repo", "pr_number", "base", "head")}, indent=2) + "\n")
    if (home / "subject.json").exists():
        return Subject.load(home / "subject.json")
    repo = repos / hashlib.sha256(name.encode()).hexdigest()[:12]
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    base = fetch(repo, row)
    subprocess.run(
        ["git", "-C", str(repo), *POINTERS, "-c", "advice.detachedHead=false", "checkout", "--quiet", "--force", "--detach", row["head"]], check=True
    )
    made = Subject(name, "reviewbench", "", str(repo.resolve()), base, row["head"], "")
    made.save(home / "subject.json")
    return made


def sample(rows: dict[str, dict], without: set[str], count: int) -> dict[str, dict]:
    rest = sorted((name for name in rows if name not in without), key=lambda name: hashlib.sha256(name.encode()).hexdigest())
    languages: dict[str, list[str]] = {}
    for name in rest:
        languages.setdefault(rows[name]["language"], []).append(name)
    quota = {lang: count * len(names) / len(rest) for lang, names in languages.items()}
    seats = {lang: math.floor(q) for lang, q in quota.items()}
    for lang in sorted(quota, key=lambda lang: (seats[lang] - quota[lang], lang))[: count - sum(seats.values())]:
        seats[lang] += 1
    return {name: rows[name] for lang, names in languages.items() for name in names[: seats[lang]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["ids", "subjects", "check"], help="ids prints the sample's ids, comma-separated")
    parser.add_argument("--set", type=Path, required=True, help="the benchmark's corpus/manifest.json, all 219 pull requests")
    parser.add_argument(
        "--without", type=Path, required=True, help="the benchmark's corpus/test/test.json: the 25 pull requests eyeful was developed on, never sampled"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=SAMPLE,
        help="how many pull requests to keep, allotted to each language by its share of the rest, the same ones every time",
    )
    parser.add_argument("--subjects", type=Path, help="subjects and check: where each subject's description is")
    parser.add_argument("--repos", type=Path, help="subjects: where the repositories the reviewers work in go, under names that say nothing about the subject")
    args = parser.parse_args()
    rows = sample({key(r): r for r in json.loads(args.set.read_text())}, {key(r) for r in json.loads(args.without.read_text())}, args.sample)
    if args.step == "ids":
        print(",".join(sorted(rows)))
        return
    if args.step == "subjects":
        for row in rows.values():
            try:
                made = subject(row, args.subjects, args.repos)
            except (RuntimeError, subprocess.CalledProcessError) as err:
                print(key(row), "skipped:", err, flush=True)
                continue
            print(made.id, made.base[:12], made.head[:12], flush=True)
        return
    if args.step == "check":
        wrong = 0
        for name, row in rows.items():
            path = args.subjects / name / "subject.json"
            problem = "no subject"
            if path.exists():
                made = Subject.load(path)
                head = subprocess.run(["git", "-C", made.repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
                base = subprocess.run(["git", "-C", made.repo, "merge-base", row["base"], row["head"]], capture_output=True, text=True).stdout.strip()
                dirty = subprocess.run(["git", "-C", made.repo, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
                problem = next(
                    (
                        p
                        for p, bad in (
                            ("the checkout is not the benchmark's head", head != row["head"] or made.head != row["head"]),
                            ("the base is not the merge base of the benchmark's base and head", base != made.base),
                            ("the checkout has changes", bool(dirty)),
                        )
                        if bad
                    ),
                    "",
                )
            if problem:
                wrong += 1
                print(name, problem, flush=True)
        print(f"{len(rows) - wrong} of {len(rows)} subjects match the benchmark", flush=True)
        raise SystemExit(wrong > 0)


if __name__ == "__main__":
    main()
