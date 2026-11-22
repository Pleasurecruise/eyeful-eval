"""Builds review subjects: a SWE-bench task reverted so that the change removes its reference fix, with tests that run in the task's container, or a Code Review Bench pull request."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from core.layout import CONFIG, PLATFORMS, official, pull
from core.model import Subject
from core.shell import git, sh

PATCHED = re.compile(r"^--- a/(\S+)", re.MULTILINE)
SUITE = 300
HISTORY = 200
ROUNDS = 4
ENTER = "export PATH=/opt/miniconda3/envs/testbed/bin:$PATH CONDA_DEFAULT_ENV=testbed CONDA_PREFIX=/opt/miniconda3/envs/testbed"


@dataclass(frozen=True)
class Runner:
    command: str
    label: bool


RUNNERS: dict[str, Runner] = {
    "django/django": Runner("./tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1", True),
    "psf/requests": Runner("pytest -rA -p no:cacheprovider", False),
    "pallets/flask": Runner("pytest -rA -p no:cacheprovider", False),
    "pytest-dev/pytest": Runner("pytest -rA -p no:cacheprovider", False),
    "pylint-dev/pylint": Runner("pytest -rA -p no:cacheprovider", False),
    "pydata/xarray": Runner("pytest -rA -p no:cacheprovider", False),
    "mwaskom/seaborn": Runner("pytest --no-header -rA -p no:cacheprovider", False),
}


def labels(tests: list[str], label: bool) -> list[str]:
    if not label:
        return [t for t in tests if t.count("[") == t.count("]")]
    named = [re.fullmatch(r"(\w+) \(([\w.]+)\)", t) for t in tests]
    return [f"{m.group(2)}.{m.group(1)}" for m in named if m]


def passing(repo: Path, candidates: list[str]) -> list[str]:
    for _ in range(ROUNDS):
        if not candidates:
            return []
        done = subprocess.run(["sh", ".eyeful/run.sh", *candidates], cwd=repo, capture_output=True, text=True)
        if done.returncode == 0:
            return candidates
        passed = set(done.stdout.splitlines())
        candidates = [t for t in candidates if f"PASSED {t}" in passed]
    return []


def commands(repo: Path, image: str, platform: str, runner: Runner, suite: list[str]) -> None:
    hidden = repo / ".eyeful"
    hidden.mkdir(exist_ok=True)
    (hidden / "inside.sh").write_text(
        f'set -e\ntar -C /change --exclude=.git --exclude=.eyeful -cf - . | tar -C /testbed -xf -\ncd /testbed\n{ENTER}\nexec {runner.command} "$@"\n'
    )
    (hidden / "run.sh").write_text(
        f'exec docker run --rm --network none --platform {platform} -v "$PWD":/change:ro {image} bash /change/.eyeful/inside.sh "$@"\n'
    )
    declared = {"test_one": "sh .eyeful/run.sh {test}"} | ({"test": f"sh .eyeful/run.sh {' '.join(shlex.quote(t) for t in suite)}"} if suite else {})
    (hidden / CONFIG).write_text("".join(f"{k}: {v}\n" for k, v in declared.items()))


def swebench(row: dict[str, str], out: Path, repos: Path, arch: str) -> Subject:
    name: str = row["instance_id"]
    runner = RUNNERS[row["repo"]]
    home = out / name
    repo = repos / hashlib.sha256(name.encode()).hexdigest()[:12]
    if (home / "subject.json").exists():
        return Subject.load(home / "subject.json")
    home.mkdir(parents=True, exist_ok=True)
    repos.mkdir(parents=True, exist_ok=True)
    source = official(name, arch)
    image = f"eyeful-eval:{hashlib.sha256(name.encode()).hexdigest()[:12]}"
    platform = PLATFORMS[arch]
    sh(["docker", "pull", "--quiet", "--platform", platform, source])
    sh(["docker", "tag", source, image])
    box = sh(["docker", "create", "--platform", platform, image]).strip()
    try:
        sh(["docker", "cp", f"{box}:/testbed", str(repo)])
    finally:
        sh(["docker", "rm", box])
    git(repo, "checkout", "--quiet", "--detach", row["base_commit"])
    git(repo, "clean", "--force", "-d", "--quiet")
    commands(repo, image, platform, runner, [])
    commands(repo, image, platform, runner, passing(repo, labels(json.loads(row["PASS_TO_PASS"])[:SUITE], runner.label)))
    git(repo, "apply", "--whitespace=nowarn", stdin=row["patch"])
    git(repo, "add", "--update")
    git(repo, "add", "--force", ".eyeful")
    git(repo, "commit", "--quiet", "--no-verify", "-m", "Prepare the release branch")
    base = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "apply", "--reverse", "--whitespace=nowarn", stdin=row["patch"])
    touched = ", ".join(dict.fromkeys(PATCHED.findall(row["patch"])))
    git(repo, "commit", "--quiet", "--no-verify", "--all", "-m", f"Rework {touched}")
    head = git(repo, "rev-parse", "HEAD").strip()
    subject = Subject(name, "swebench", row.get("difficulty", ""), str(repo.resolve()), base, head, image)
    subject.save(home / "subject.json")
    return subject


def benchmarked(name: str, owner: str, project: str, number: str, out: Path, repos: Path) -> Subject:
    home = out / name
    repo = repos / hashlib.sha256(name.encode()).hexdigest()[:12]
    if (home / "subject.json").exists():
        return Subject.load(home / "subject.json")
    pr = json.loads(sh(["gh", "api", f"repos/{owner}/{project}/pulls/{number}"]))
    home.mkdir(parents=True, exist_ok=True)
    repo.mkdir(parents=True, exist_ok=True)
    sh(["git", "init", "--quiet"], cwd=repo)
    remote = f"https://github.com/{owner}/{project}.git"
    git(repo, "fetch", "--quiet", f"--depth={pr['commits'] + HISTORY}", remote, pr["base"]["sha"], pr["head"]["sha"])
    base = git(repo, "merge-base", pr["base"]["sha"], pr["head"]["sha"]).strip()
    git(repo, "checkout", "--quiet", "--detach", pr["head"]["sha"])
    subject = Subject(name, "crb", "", str(repo.resolve()), base, pr["head"]["sha"], "")
    subject.save(home / "subject.json")
    return subject


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=["swebench", "crb"])
    parser.add_argument("--data", type=Path, required=True, help="SWE-bench Verified rows or one of Code Review Bench's golden comment files, as JSON")
    parser.add_argument("--out", type=Path, required=True, help="where each subject's description goes; it names the defect, so keep it away from --repos")
    parser.add_argument(
        "--repos",
        type=Path,
        required=True,
        help="where the repositories the reviewers work in go, under names that say nothing about the subject; not a temporary or cache directory, which the system and cleaners empty",
    )
    parser.add_argument("--ids", default="", help="comma-separated ids; empty builds every row the runners cover")
    parser.add_argument("--arch", default="arm64", choices=["arm64", "x86_64"])
    args = parser.parse_args()
    wanted = {i for i in args.ids.split(",") if i}
    for row in json.loads(args.data.read_text()):
        crb = pull(row.get("url", ""))
        name = row.get("instance_id") or crb[0]
        if wanted and name not in wanted:
            continue
        if args.dataset == "swebench" and row["repo"] not in RUNNERS:
            continue
        try:
            subject = swebench(row, args.out, args.repos, args.arch) if args.dataset == "swebench" else benchmarked(*crb, args.out, args.repos)
        except RuntimeError as err:
            print(name, "skipped:", err, flush=True)
            continue
        print(subject.id, subject.base[:12], subject.head[:12], flush=True)


if __name__ == "__main__":
    main()
