"""Scores ReviewBench reviews with the benchmark's own judge: writes each review's reported comments in the judge's input format, then reads the judge's verdicts back as scores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.layout import PR
from core.model import Review, load_reviews, load_subjects


def candidate(pr: dict, review: Review) -> dict:
    return {
        "pr": pr,
        "agent": review.name,
        "findings": [
            {"producer": review.name, "file": f.path, "start_line": f.line, "end_line": f.line, "message": f.text.strip()}
            for f in review.findings
            if f.reported
        ],
        "usage": {"time_in_ms": int(review.seconds * 1000), "total_tokens": review.tokens},
    }


def judged(reviews: list[Review], subjects: Path) -> list[Review]:
    names = {k for k, s in load_subjects(subjects).items() if s.dataset == "reviewbench"}
    return [r for r in reviews if r.subject in names and r.outcome not in ("error", "leaked")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["candidates", "scores"])
    parser.add_argument("--subjects", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="candidates: one directory per review, named as the review; scores: the scores file")
    parser.add_argument("--verdicts", type=Path, help="scores: the directory the judge wrote into, one results.details.json per review")
    parser.add_argument("--golden", type=Path, help="scores: the benchmark's golden directory, which says which golden findings are accepted")
    args = parser.parse_args()
    reviews = judged(load_reviews(args.reviews), args.subjects)
    if args.step == "candidates":
        for r in reviews:
            dest = args.out / r.name / f"{r.subject}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(candidate(json.loads((args.subjects / r.subject / PR).read_text()), r), indent=2) + "\n")
        print(len(reviews), "reviews written", flush=True)
        return
    with args.out.open("w") as out:
        for r in reviews:
            verdicts = {d["pr_key"]: d["candidate_findings"] for d in json.loads((args.verdicts / r.name / "results.details.json").read_text())}[r.subject]
            golden = json.loads((args.golden / f"{r.subject}.json").read_text())["findings"]
            defects = {str(i): g["category"] for i, g in enumerate(golden) if g["tp_fp"] == "tp"}
            reported = [f for f in r.findings if f.reported]
            covered = {str(i) for v in verdicts for i in v["covered_golden_indices"]}
            valid = [f.id for f, v in zip(reported, verdicts, strict=True) if v["status"] in ("matched_tp", "novel_tp")]
            out.write(json.dumps({"review": r.key, "defects": defects, "found": sorted(covered & defects.keys()), "valid": valid}) + "\n")


if __name__ == "__main__":
    main()
