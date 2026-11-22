"""Writes .eval/progress.md: one row per finished run of a configuration, all three conditions, for each dataset."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from core.model import load_reviews

ROOT = Path(__file__).resolve().parents[2]

PLANNED = {"panel": 1, "single": 3, "fixed": 1}


def section(name: str, run: Path, subjects: int) -> list[str]:
    reviews = load_reviews(run / "reviews.jsonl") if (run / "reviews.jsonl").exists() else []
    runs: dict[tuple[str, str, int], dict[str, object]] = {}
    for r in reviews:
        runs.setdefault((r.subject, r.config, r.rep), {})[r.condition] = r
    done = [k for k, c in runs.items() if {"execution", "none"} <= c.keys()]
    total = subjects * sum(PLANNED.values())
    lines = [
        f"## {name}",
        "",
        f"{len(done)} of {total} runs finished ({len(done) / total:.0%}); outcomes {dict(Counter(r.outcome for r in reviews))}.",
        "",
        "| Subject | Config | Run | Execution | Read-only | None | Findings | Fix verified | Confirmed | Rejected | Retries | Tokens (k) | Minutes (execution) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key in sorted(done, key=lambda k: (k[0], list(PLANNED).index(k[1]), k[2])):
        subject, config, rep = key
        c = runs[key]
        ex = c["execution"]
        serious = [f for f in ex.findings if f.severity != "note"]
        status = Counter(f.status for f in serious)
        retries = len(list((run / subject / f"{config}-{rep}").glob("execution-failed-*")))
        lines.append(
            f"| {subject.split('__')[-1]} | {config} | {rep} | {ex.outcome} | {c['read_only'].outcome if 'read_only' in c else '-'} | {c['none'].outcome} "
            f"| {len(serious)} (+{len(ex.findings) - len(serious)} notes) | {status['fix_verified']} | {status['confirmed']} | {status['rejected']} "
            f"| {retries} | {ex.tokens / 1e3:.0f} | {ex.seconds / 60:.0f} |"
        )
    return [*lines, ""]


def main() -> None:
    swe = ROOT / ".eval" / "swebench"
    valid = {k for k, v in json.loads((swe / "baseline.json").read_text()).items() if v["base_passes"] and v["head_fails"]}
    log = swe / "selection.jsonl"
    added = sum(json.loads(line)["kept"] for line in log.read_text().splitlines()) if log.exists() else 0
    crb = len(list((ROOT / ".eval" / "crb" / "subjects").glob("*/subject.json")))
    out = [
        "# Progress",
        "",
        f"Updated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC. A run is one configuration's review of a subject in its conditions; findings are errors and warnings found in execution.",
        "",
    ]
    out += section(f"SWE-bench ({len(valid)} + {added} added subjects)", swe / "runs" / "61c1b8b", len(valid) + added)
    out += section(f"Code Review Bench ({crb} subjects)", ROOT / ".eval" / "crb" / "runs" / "61c1b8b", crb)
    (ROOT / ".eval" / "progress.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
