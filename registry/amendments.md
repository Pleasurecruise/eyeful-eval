# Amendments to the evaluation plan

Changes to the plan in eyeful's `docs/EVALUATION.md`, by date. A change says what it replaces and
why. Those of 2026-11-22 change the design and were made before any review was scored; those of
2026-11-24 were made during or after scoring and change no result. The results are reported under
the plan as amended.

## 2026-11-22

**Runs per subject.** The panel reviews each subject once and the single agent three times; the
fixed configuration once, as before. The plan had the panel and the single agent three times each.
Reason: time. The comparison kept is the plan's own cost-matched one, one panel run against the
union of the single agent's three runs, beside one panel run against the single agent's first. A
known defect counts as found when the run, or any of the three, finds it, so the rule that two of
three runs must find it goes. The panel's second and third runs already made, on 8 Code Review
Bench and 2 SWE-bench subjects, were removed.

**SWE-bench subjects.** 14 subjects are added by the rules in `swebench/selection.md` to the 16
valid ones, toward the plan's 30. 4 built subjects are left out because their hidden tests need
the network, which the reviews' test environment does not have.

**Read-only verification on SWE-bench.** From the 2026-11-22 21:50 UTC invocation, SWE-bench
subjects are reviewed under execution and no verification only. Read-only verification serves the noise
measure, which SWE-bench cannot provide, and took a quarter of each run. The read-only reviews already made are
kept and not analysed.

**Code Review Bench and ReviewBench.** Code Review Bench has the 10 subjects built, not 50.
ReviewBench is not run.

**What was seen first.** Before these changes, reviews of 7 Code Review Bench and 2 SWE-bench
subjects had been read by hand against their known defects; none had been scored.

## 2026-11-24

**Judge concurrency.** Code Review Bench's judge sends 20 calls at once, the provider's whole
allowance, and records a call not answered within 30 seconds as an error. In the first scoring run,
8 of the first 47 reviews judged had such errors. The run was stopped and resumed
with at most 4 calls at once; the judge's own resume judges again every review with an error and
keeps the others. The prompt, model and matching rule are unchanged, and no review was judged
twice to choose between outcomes.

**After scoring.** After every review was scored, the apparatus was reorganised: the
files stages exchange moved into `core.layout`, the unused revmux module was removed, ReviewBench's
module was split into building (`build.reviewbench`) and scoring (`score.reviewbench`), and the
tests were split by package. Re-reading every review and re-scoring from the harness's reports and
the judge's verdicts reproduced `reviews.jsonl` and the scores byte for byte.
The bootstrap resampled subjects in an order that varied between processes; it now sorts them first,
which moved two bounds of Code Review Bench's recall intervals by 0.01 and no estimate.

**ReviewBench as a confirmatory set.** After the main results were seen, ReviewBench
was restored as a confirmatory set, held out from development, to run in February 2027 by the plan in
[`reviewbench/plan.md`](reviewbench/plan.md), fixed before any of its reviews. It does not change
the main analysis.

## Known limits of the measures

- On SWE-bench the change under review is the reverted fix itself, so every finding is on the
  defect's lines; precision there separates findings only by whether their fix resolves the task.
- A finding counts as valid on SWE-bench only when a fix written after reproducing it resolves the
  task, so a finding execution does not reproduce cannot be valid, and verification loss as defined
  is zero by construction. It is reported as such.
