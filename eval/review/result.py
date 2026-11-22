"""Reads a finished eyeful review: its comments as findings, each with the verdict of the finding behind it, and whether its agents stayed in the repository."""

from __future__ import annotations

import json
from pathlib import Path

from core.layout import owners
from core.model import Condition, Finding, Review, Subject
from review.audit import outside

STRENGTH = ("fix_verified", "reproduced", "pre_existing", "confirmed", "unverified", "not_reproduced", "rejected")


def stopped(verdict: dict) -> str:
    change, base, fixed = verdict.get("change", []), verdict.get("base", ""), verdict.get("fixed", "")
    if "repro" not in verdict or verdict["status"] == "fix_verified":
        return ""
    if not change:
        return "runs"
    if len(set(change)) > 1:
        return "not_flaky"
    if change[0] != "FAILED":
        return "fails_as_claimed"
    if base in ("", "FAILED"):
        return "introduced"
    return "pass_to_pass" if fixed == "PASSED" else "fail_to_pass"


def lead(c: dict, members: list[str], verdicts: dict) -> str:
    """The merged finding whose verdict stands for the comment: the one that gave it its reproduction, else the strongest."""
    judged = [m for m in members if m in verdicts]
    if c.get("repro"):
        return next((m for m in judged if verdicts[m].get("repro") == c["repro"]), c["finding"])

    def rank(m: str) -> int:
        return STRENGTH.index(verdicts[m]["status"]) if verdicts[m]["status"] in STRENGTH else len(STRENGTH)

    return min(judged, key=rank, default=c["finding"])


def finders_leaked(execution: Path, repo: Path) -> bool:
    """Whether the planner or an expert of the execution run read outside the repository: the other conditions verify their findings."""
    agents = execution / "agents"
    return any(outside(t, (repo,)) for t in [*agents.glob("planner-*.jsonl"), *agents.glob("expert-*.jsonl")])


def read(subject: Subject, config: str, rep: int, condition: Condition, run: Path, seconds: float) -> Review:
    result = run / "result.json"
    gave_up = (run / "failed").exists()
    if not result.exists():
        return Review(subject.id, "eyeful", config, rep, condition, "failed" if gave_up else "error", (), 0, 0, seconds)
    raw = json.loads(result.read_text())
    verdicts = {v["finding"]: v for v in raw["verifications"]}
    claims = {f["id"]: f for f in raw["findings"]}
    own = owners(run, raw)
    leads = {c["finding"]: lead(c, [f for f, o in own.items() if o == c["finding"]] or [c["finding"]], verdicts) for c in raw["comments"]}
    findings = tuple(
        Finding(
            id=c["finding"],
            path=c["path"],
            line=c["line"],
            severity=c["severity"],
            title=c["subject"],
            body=c["discussion"],
            source=",".join(c["experts"]),
            evidence=claims[leads[c["finding"]]]["evidence"],
            cwe=claims[c["finding"]].get("cwe", ""),
            status=verdicts.get(leads[c["finding"]], {}).get("status", ""),
            gate=stopped(verdicts.get(leads[c["finding"]], {})),
            oracle=(verdicts.get(leads[c["finding"]], {}).get("repro") or {}).get("oracle", ""),
            blocking="blocking" in c["decorations"],
            reported=c["kind"] != "open",
        )
        for c in raw["comments"]
    )
    tokens = sum(r["usage"]["tokens"] for r in raw["runs"])
    cost = sum(r["usage"]["micro_usd"] for r in raw["runs"])
    outcome = "error" if any(r.get("error") for r in raw["runs"]) else raw["outcome"]
    if outcome == "error" and gave_up:
        outcome = "failed"
    if json.loads((run / "outside.json").read_text()) or (condition != "execution" and finders_leaked(run.parent / "execution", Path(subject.repo))):
        outcome = "leaked"
    return Review(subject.id, "eyeful", config, rep, condition, outcome, findings, tokens, cost, seconds)
