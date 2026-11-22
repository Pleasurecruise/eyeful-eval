#!/bin/sh
# Runs the experiment in order, one review at a time: SWE-bench, with the added subjects merged in
# once they are built, then Code Review Bench. The panel runs once, the single agent three times,
# the fixed configuration once; SWE-bench skips read-only verification, which it cannot measure
# (registry/amendments.md). A step that fails stops the rest.
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/eval"
D=.eval/swebench
C=.eval/crb
E=.eval/bin/eyeful-61c1b8b
P=opencode-go/deepseek-v4.1-flash:medium

merge() {
	pgrep -f "build.select" >/dev/null && return
	for s in "$D"/subjects-2/*/; do
		[ -f "$s/subject.json" ] && mv "$s" "$D/subjects/"
	done
	return 0
}

ids() {
	python3 - <<'PY'
import json, pathlib
d = pathlib.Path(".eval/swebench")
valid = {k for k, v in json.loads((d / "baseline.json").read_text()).items() if v["base_passes"] and v["head_fails"]}
log = d / "selection.jsonl"
valid |= {t["id"] for t in map(json.loads, log.read_text().splitlines()) if t["kept"]} if log.exists() else set()
print(",".join(sorted(i for i in valid if (d / "subjects" / i / "subject.json").exists())))
PY
}

for pass in 1 2; do
	for step in "panel 1" "single 3" "fixed 1"; do
		set -- $step
		merge
		python3 -m review.run --subjects "$D/subjects" --ids "$(ids)" --out "$D/runs/61c1b8b" --eyeful "$E" --pi "$P" \
			--configs "$1" --reps "$2" --conditions execution,none >> "$D/runs/61c1b8b/run.log" 2>&1
	done
done
echo "SWE-BENCH DONE" >> "$D/runs/61c1b8b/run.log"

for step in "panel 1" "single 3" "fixed 1"; do
	set -- $step
	python3 -m review.run --subjects "$C/subjects" --out "$C/runs/61c1b8b" --eyeful "$E" --pi "$P" --configs "$1" --reps "$2" >> "$C/runs/61c1b8b/run.log" 2>&1
done
echo "ALL DONE" | tee -a "$D/runs/61c1b8b/run.log" >> "$C/runs/61c1b8b/run.log"
