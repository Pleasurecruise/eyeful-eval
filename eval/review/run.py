"""Reviews every subject with eyeful: each configuration finds once, and the three verification conditions share those findings. A review is its comments, each one problem."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from core.layout import flags as test_flags
from core.model import Condition, Subject, append_review, load_reviews, load_subjects
from record.registry import begin, finish, setup
from review.audit import outside
from review.confine import environment
from review.result import read

CONFIGS: dict[str, list[str]] = {
    "panel": [],
    "single": ["generalist"],
    "fixed": ["correctness", "security"],
}
CONDITIONS: tuple[Condition, ...] = ("execution", "read_only", "none")
ATTEMPTS = 3


def review(binary: Path, subject: Subject, config: str, condition: Condition, run: Path, flags: list[str], description: Path) -> float:
    run.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp())
    if (run / "stages").exists():
        shutil.copytree(run / "stages", work / "stages")
    command = [
        str(binary),
        "review",
        *CONFIGS[config],
        "--base",
        subject.base,
        "--head",
        subject.head,
        "--verification",
        condition,
        "--yes",
        *(["--description", str(description)] if description.exists() else []),
        "--run",
        str(work),
        "--no-detect",
    ]
    command += test_flags(Path(subject.repo))
    start = time.monotonic()
    with (run / "eyeful.log").open("a") as log:
        subprocess.run(command, cwd=subject.repo, stdout=log, stderr=log, env=environment(Path(subject.repo), (), flags), check=False)
    took = time.monotonic() - start
    opened = sorted({p for t in (work / "agents").glob("*.jsonl") for p in outside(t, (Path(subject.repo),))})
    (work / "outside.json").write_text(json.dumps(opened, indent=2) + "\n")
    shutil.copytree(work, run, dirs_exist_ok=True)
    shutil.rmtree(work)
    return took


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--eyeful", type=Path, required=True, help="the eyeful binary under test")
    parser.add_argument("--configs", default="panel,single")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--conditions", default=",".join(CONDITIONS), help="execution always runs first: it is where the findings come from")
    parser.add_argument("--ids", default="")
    parser.add_argument(
        "--pi", default="", help="the model and thinking level every pi call uses, as provider/model:thinking; pi's own settings decide otherwise"
    )
    args = parser.parse_args()
    args.subjects, args.out, args.eyeful = args.subjects.resolve(), args.out.resolve(), args.eyeful.resolve()
    wanted = {i for i in args.ids.split(",") if i}
    reviews = args.out / "reviews.jsonl"
    args.out.mkdir(parents=True, exist_ok=True)
    flags: list[str] = []
    if args.pi:
        model, thinking = args.pi.rsplit(":", 1)
        flags = ["--model", model, "--thinking", thinking]
    subjects = load_subjects(args.subjects)
    begin(
        args.out,
        setup(args.eyeful, subjects, args.pi),
        {
            "configs": args.configs,
            "reps": args.reps,
            "conditions": args.conditions,
            "ids": args.ids,
            "subjects": {s.id: {"base": s.base, "head": s.head} for s in subjects.values()},
        },
    )
    kept = {r.key: r for r in load_reviews(reviews)} if reviews.exists() else {}
    for subject in subjects.values():
        if wanted and subject.id not in wanted:
            continue
        for config in args.configs.split(","):
            for rep in range(1, args.reps + 1):
                home = args.out / subject.id / f"{config}-{rep}"
                found = 0.0
                for condition in CONDITIONS:
                    if condition not in args.conditions.split(","):
                        continue
                    run = home / condition
                    clock = run / "seconds"
                    if condition != "execution" and (home / "execution" / "failed").exists() and not clock.exists():
                        shutil.copytree(home / "execution", run, dirs_exist_ok=True)
                        clock.write_text("0")
                    if condition != "execution" and not (run / "stages").exists() and (home / "execution" / "stages").exists():
                        shutil.copytree(home / "execution" / "stages", run / "stages")
                    tried = len(list(home.glob(f"{condition}-failed-*")))
                    for attempt in range(tried + 1, ATTEMPTS + 1):
                        if clock.exists():
                            break
                        took = review(args.eyeful, subject, config, condition, run, flags, args.subjects / subject.id / "description.md")
                        errored = read(subject, config, rep, condition, run, took).outcome == "error"
                        if not errored or attempt == ATTEMPTS:
                            if errored:
                                (run / "failed").touch()
                            clock.write_text(str(took))
                            break
                        run.rename(home / f"{condition}-failed-{attempt}")
                        if condition != "execution":
                            shutil.copytree(home / "execution" / "stages", run / "stages")
                    seconds = float(clock.read_text())
                    if condition == "execution":
                        staged = [p.stat().st_mtime for p in (run / "stages" / "expert").rglob("*.json")]
                        first = (run / "snapshot.json").stat().st_mtime if (run / "snapshot.json").exists() else 0.0
                        found = max(staged, default=first) - first
                    else:
                        seconds += found
                    result = read(subject, config, rep, condition, run, seconds)
                    print(result.key, result.outcome, len(result.findings), f"{seconds:.0f}s", flush=True)
                    kept[result.key] = result
                    reviews.write_text("")
                    for one in kept.values():
                        append_review(reviews, one)
    finish(args.out, list(kept.values()))


if __name__ == "__main__":
    main()
