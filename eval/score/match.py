"""Scores Code Review Bench reviews with the benchmark's own judge, step 3 of its offline pipeline, and counts recall under its default Core profile."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from core.layout import pull
from core.model import load_reviews
from score.relay import relay

# The judge's own entry point with --no-dedup, sending at most the given number of calls at once; its default, 20, is OpenCode Go's whole
# allowance, so calls queue past the judge's 30-second timeout and are recorded as errors.
JUDGE = "import asyncio, sys; import code_review_benchmark.step3_judge_comments as j; j.process_batch.__defaults__ = ({},); sys.argv = ['step3', '--no-dedup']; asyncio.run(j.main())"
CORE = frozenset({"bug", "security", "concurrency", "data", "api", "perf", "test_gap", "doc_defect"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True, help="the benchmark's offline directory")
    parser.add_argument("--reviews", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--out", type=Path, required=True, help="the judge's working directory and the scores; a review already judged there is not judged again"
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="NAME=VALUE added to every request the judge makes to MARTIAN_BASE_URL, such as x-opencode-session=..., which OpenCode Go requires",
    )
    parser.add_argument(
        "--concurrency", type=int, default=4, help="the most calls the judge makes at once; a review whose calls failed is judged again on the next run"
    )
    args = parser.parse_args()
    headers = dict(h.split("=", 1) for h in args.header)
    golden: dict[str, tuple[str, list[dict[str, str]]]] = {}
    for file in sorted((args.benchmark / "golden_comments").glob("*.json")):
        for row in json.loads(file.read_text()):
            if pr := pull(row["url"]):
                golden[pr[0]] = (row["url"], row["comments"])
    reviews = [r for path in args.reviews for r in load_reviews(path) if r.subject in golden and r.outcome not in ("error", "leaked")]
    data: dict[str, dict] = {}
    candidates: dict[str, dict[str, list[dict]]] = {}
    for r in reviews:
        url, comments = golden[r.subject]
        data.setdefault(url, {"pr_title": "", "golden_comments": comments, "reviews": []})["reviews"].append(
            {"tool": r.name, "repo_name": r.subject, "pr_url": url, "review_comments": []}
        )
        candidates.setdefault(url, {})[r.name] = [{"text": f.text, "path": f.path, "line": f.line, "source": "extracted"} for f in r.findings if f.reported]
    judged = args.out / "results" / os.environ["MARTIAN_MODEL"].strip().replace("/", "_")
    judged.mkdir(parents=True, exist_ok=True)
    (args.out / "results" / "benchmark_data.json").write_text(json.dumps(data, indent=2) + "\n")
    (judged / "candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")
    with relay(os.environ["MARTIAN_BASE_URL"], headers) as base:
        subprocess.run(
            ["uv", "run", "--project", str(args.benchmark.resolve()), "python", "-c", JUDGE.format(args.concurrency)],
            cwd=args.out,
            env=os.environ | {"PYTHONPATH": str(args.benchmark.resolve()), "MARTIAN_BASE_URL": base if headers else os.environ["MARTIAN_BASE_URL"]},
            check=True,
        )
    evaluations = json.loads((judged / "evaluations.json").read_text())
    with (args.out / "scores.jsonl").open("w") as out:
        for r in reviews:
            url, comments = golden[r.subject]
            verdict = evaluations[url][r.name]
            unmatched = {fp["candidate"] for fp in verdict["false_positives"]}
            matched = {tp["golden_comment"] for tp in verdict["true_positives"]}
            defects = {str(i): g["category"] for i, g in enumerate(comments) if g["category"] in CORE}
            out.write(
                json.dumps(
                    {
                        "review": r.key,
                        "defects": defects,
                        "found": [i for i in defects if comments[int(i)]["comment"] in matched],
                        "valid": [f.id for f in r.findings if f.reported and f.text not in unmatched],
                    }
                )
                + "\n"
            )


if __name__ == "__main__":
    main()
