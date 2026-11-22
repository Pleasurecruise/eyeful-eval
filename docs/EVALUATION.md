# Evaluation

[中文](zh/EVALUATION.md)

The protocol for evaluating eyeful. It follows eyeful's
[proposal](https://github.com/Pleasurecruise/eyeful/blob/main/docs/reports/proposal.pdf); departures
are dated in [`registry/amendments.md`](../registry/amendments.md). Every change to the design was
made before any review was scored; later entries change no result. The results are in
[RESULTS.md](RESULTS.md).

## 1. Research questions

The research questions are the proposal's, which is frozen. RQ1 and RQ2 ask how to build the planner
and the verifier; the evaluation answers RQ3 and tests each design by an ablation.

| Question              | Proposal                                                                                                             | Measured by                                                                      |
| --------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| RQ1, planning         | How can a change be divided among expert agents so that every changed file is reviewed by the experts its intent needs? | The planner ablation: two fixed experts replace the planner                      |
| RQ2, verification     | How can a candidate finding be confirmed by execution when the expected behaviour may not be stated in the code?       | The share of findings passing the six gates; the oracle-rule ablation: every reproduction may block |
| RQ3, evaluation       | Does the panel find more known defects than a single agent with the same model and skills, does verification leave fewer invalid findings, and at what cost? | Detection (recall), noise (precision by condition) and cost                       |

## 2. Benchmarks and sampling

Defects must be known in advance, so that no output is labelled by hand, and one benchmark must have
executable tests. No subject was used in developing eyeful's prompts.

| Benchmark          | Source                                                                                                    | Known defects                          | Subjects | Measures                       |
| ------------------ | --------------------------------------------------------------------------------------------------------- | -------------------------------------- | -------- | ------------------------------ |
| SWE-bench Verified | [SWE-bench/SWE-bench_Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)              | The issue, judged by its hidden tests  | 30       | Detection, verifiability, cost |
| Code Review Bench  | [withmartian/code-review-benchmark](https://github.com/withmartian/code-review-benchmark), offline set    | Core golden comments, human-confirmed  | 10       | Detection, noise, cost         |
| ReviewBench        | [review-bench/ReviewBench](https://github.com/review-bench/ReviewBench)                                    | Accepted golden findings               | 50       | Confirmatory, February 2027    |

**SWE-bench.** The frame is the 293 tasks from the seven projects the apparatus can test. Sixteen
subjects come from a purposive set of 20, four of which failed the validity criteria (§3); 14 more are
drawn in SHA-256 order of their identifiers ([`selection.md`](../registry/swebench/selection.md)).
**Code Review Bench.** Ten Keycloak pull requests from the offline set; the seven pull requests eyeful's
prompts were developed on are from other projects. **ReviewBench.** 50 pull requests drawn from
the 219 less the 25 used in development, run after the main results as a confirmatory set
([`plan.md`](../registry/reviewbench/plan.md)).

## 3. Subjects

A subject is a git repository with a base and a head commit; eyeful reviews the head.

- **SWE-bench (reverted fix).** From the task's image, the base commits the reference fix and the head
  removes it, so the change under review introduces the issue. Two test commands, one test and a
  suite of passing PASS_TO_PASS tests, run in the task's image without network.
- **Code Review Bench and ReviewBench.** The pull request's head against the merge base of its base
  and head.
- **Blinding.** Defect descriptions are stored apart from repositories, names are hashes, and hidden
  tests never enter a repository.
- **Validity.** A SWE-bench subject is kept if its hidden tests pass on the base and fail on the head
  offline and its suite is non-empty; this tests the environment, not any review.

## 4. Design

Within-subject, with two factors.

| Configuration | Invocation                           | Replications | Finds                                  |
| ------------- | ------------------------------------ | ------------ | -------------------------------------- |
| panel         | `eyeful review`                      | 1            | Experts assigned by the planner        |
| single        | `eyeful review generalist`           | 3            | One agent with every skill             |
| fixed         | `eyeful review correctness security` | 1            | Two experts, no planner (ablation)     |

| Verification | Reports                                          | SWE-bench               | Code Review Bench       |
| ------------ | ------------------------------------------------ | ----------------------- | ----------------------- |
| execution    | Findings reproduced, or not disputed if untested | yes                     | yes, equal to read_only |
| read_only    | Findings a judge agent does not dispute          | no: noise not measurable | yes                    |
| none         | All findings                                     | yes                     | yes                     |

The panel is compared with the union of the single agent's three replications, which cost about as
much as one panel run, and with its first. Execution produces the findings and the other conditions verify the same set, so
differences between conditions are due to verification. Build, model, reasoning level, skills,
prompts, budgets and test commands are held fixed. The unit of analysis is the subject.

## 5. Apparatus

[`eval/`](../eval) has one package per stage. A stage depends only on `core`, whose `layout` defines
the files stages exchange, and on the files the previous stage wrote; `review` also writes its run's
manifest through `record`. Each package's tests are in `eval/tests/test_<package>.py`.

| Package    | Responsibility                                                                     |
| ---------- | ---------------------------------------------------------------------------------- |
| `build`    | Construct subjects, check their validity (§3), draw SWE-bench and ReviewBench subjects |
| `review`   | Conduct each review in a sandbox with retries; audit access; read findings and verdicts |
| `record`   | Manifests of each run; the progress table                                          |
| `score`    | Each benchmark's own scorer: SWE-bench's harness, the review benchmarks' judges    |
| `analysis` | Measures and intervals                                                             |
| `core`     | Shared records; the files stages exchange; running commands                        |

[`eval/schedule.sh`](../eval/schedule.sh) runs the experiment in a fixed order.

## 6. Procedure

- **Model.** DeepSeek V4.1 Flash on OpenCode Go through pi, reasoning `medium`, for every agent and
  judge.
- **Order.** One review at a time: the provider admits 20 concurrent calls and a review issues up to
  eight.
- **Containment.** Agents read only the repository. A review with any other access is excluded, as are
  the conditions verifying its experts' findings.
- **Failures.** A failed review is repeated up to three times, then kept as failed, detecting nothing.
- **Provenance.** A manifest records the setup and each invocation, including the scripts' digest.

## 7. Measures

| Benchmark         | Defect detected when                                                   | Finding valid when             | Scorer       |
| ----------------- | ---------------------------------------------------------------------- | ------------------------------ | ------------ |
| SWE-bench         | the official harness resolves the task with a reported finding's fix   | its fix resolves the task      | `resolve.py` |
| Code Review Bench | the benchmark's judge matches a finding to a Core golden comment       | the judge does not reject it   | `match.py`   |
| ReviewBench       | the benchmark's judge covers an accepted golden finding                | the judge counts it as a true positive | `score/reviewbench.py` |

RQ3: recall and categories, McNemar's exact test; precision per condition, paired bootstrap; tokens,
cost and time, bootstrap. RQ2: the share of executed findings passing all six gates, resolving
findings execution does not confirm, and blocking findings with and without the oracle rule. RQ1:
the planner ablation's recall, McNemar's exact test. Intervals are 95%, from 10,000 resamples of
subjects, drawn in a fixed order so that the seed fixes them.

## 8. Threats to validity

- **Construct.** Golden sets are incomplete, so precision is a lower bound. On SWE-bench the change
  is the defect, so noise is not measurable, and a finding is valid only if execution reproduced it,
  so verification loss is zero by construction. Code Review Bench's subjects have no runnable tests,
  so execution equals read_only there: whether execution reduces noise is not measured, only whether
  a read-only judge does.
- **Internal.** One model reviews, judges and scores; judges may be lenient and vary between runs;
  retries keep the successful attempt. Recording scripts changed during the runs, never the reviewing
  build; each change is in the manifests.
- **Development.** eyeful's prompts were tuned on seven Code Review Bench pull requests outside the
  sample. Two phrases written while reading their golden comments are not in the evaluated build.
  Pilot reviews of seven sampled Code Review Bench subjects and two SWE-bench subjects were read
  before the plan was amended.
- **External.** Python subjects, mostly Django; ten Keycloak pull requests; the model may have seen
  the SWE-bench issues.
- **Conclusion.** The proposal planned about 130 subjects and 860 reviews; time allowed 40 subjects and
  456 reviews, with the panel run once. Power is limited, and no difference is not equivalence.
  ReviewBench, held out from development, is run in February 2027 as a confirmatory set.
