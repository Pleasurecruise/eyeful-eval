"""Adds SWE-bench subjects by the rules in registry/swebench/selection.md: tasks in hash order, kept when their environment is sound."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from build.baseline import check
from build.subjects import RUNNERS, swebench
from core.layout import flags, official
from core.model import Subject


def arch(name: str) -> str:
    for a in ("arm64", "x86_64"):
        if subprocess.run(["docker", "manifest", "inspect", official(name, a)], capture_output=True).returncode == 0:
            return a
    return ""


def remove(out: Path, name: str, subject: Subject | None, a: str) -> None:
    shutil.rmtree(out / name, ignore_errors=True)
    if subject:
        shutil.rmtree(subject.repo, ignore_errors=True)
        subprocess.run(["docker", "rmi", subject.image], capture_output=True)
    subprocess.run(["docker", "rmi", official(name, a)], capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="SWE-bench Verified rows, as JSON")
    parser.add_argument("--built", type=Path, required=True, help="the subjects already built, which are not drawn")
    parser.add_argument("--out", type=Path, required=True, help="where the drawn subjects go")
    parser.add_argument("--repos", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True, help="every task tried, kept or not, and why, as JSON lines")
    parser.add_argument("--wanted", type=int, default=14)
    args = parser.parse_args()
    rows = json.loads(args.data.read_text())
    built = {p.parent.name for p in args.built.glob("*/subject.json")}
    pool = sorted(
        (r for r in rows if r["repo"] in RUNNERS and r["instance_id"] not in built), key=lambda r: hashlib.sha256(r["instance_id"].encode()).hexdigest()
    )
    tried = [json.loads(line) for line in args.log.read_text().splitlines()] if args.log.exists() else []
    done = {t["id"] for t in tried}
    kept = sum(t["kept"] for t in tried)
    for row in pool:
        if kept >= args.wanted:
            break
        name = row["instance_id"]
        if name in done:
            continue
        a, subject, record = arch(name), None, {"id": name}
        if not a:
            record |= {"kept": False, "reason": "no image"}
        else:
            try:
                subject = swebench(row, args.out, args.repos, a)
            except RuntimeError:
                record |= {"arch": a, "kept": False, "reason": "build failed"}
            else:
                suite = "--test" in flags(Path(subject.repo))
                env = check(subject, row)
                ok = suite and env["base_passes"] and env["head_fails"]
                reason = ", ".join(
                    r
                    for r, bad in (
                        ("no suite", not suite),
                        ("hidden tests fail on the base", not env["base_passes"]),
                        ("hidden tests pass on the head", not env["head_fails"]),
                    )
                    if bad
                )
                record |= {"arch": a, "suite": suite, **env, "kept": ok, "reason": reason}
        if not record["kept"]:
            remove(args.out, name, subject, a)
        kept += record["kept"]
        with args.log.open("a") as log:
            log.write(json.dumps(record) + "\n")
        print(name, record.get("arch", ""), "kept" if record["kept"] else f"not kept: {record['reason']}", f"({kept}/{args.wanted})", flush=True)


if __name__ == "__main__":
    main()
