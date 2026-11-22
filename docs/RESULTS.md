# Results

[中文](zh/RESULTS.md)

Results of the protocol in [EVALUATION.md](EVALUATION.md), eyeful build `61c1b8b`, DeepSeek V4.1 Flash.
Intervals are 95% bootstrap intervals over subjects; p values are McNemar's exact test.

## 1. Conduct

| Benchmark          | Subjects | Runs      | Reviews | Excluded: read outside the repository | Failed after three attempts |
| ------------------ | -------- | --------- | ------- | -------------------------------------- | --------------------------- |
| SWE-bench Verified | 30       | 150 / 150 | 300     | 5                                      | 6                           |
| Code Review Bench  | 10       | 50 / 50   | 150     | 1                                      | 6                           |

Every excluded review read library sources outside the repository; none read evaluation data. Six
read-only reviews made on SWE-bench before that condition was dropped are kept and not analysed.
Failed reviews count as detecting nothing. SWE-bench fixes were scored by the official harness
(`swebench==5.0.2`) and Code Review Bench by its own judge, which returned every review without
error. Departures from the protocol are in [amendments.md](../registry/amendments.md).

## 2. RQ3: detection, with the planner ablation (RQ1)

| Configuration                        | SWE-bench recall (30 defects) | Code Review Bench recall (25 Core defects) |
| ------------------------------------ | ----------------------------- | ------------------------------------------ |
| panel, one run                       | 0.73 [0.57, 0.87]             | 0.72 [0.52, 0.90]                          |
| single, first run                    | 0.70 [0.53, 0.87]             | 0.72 [0.60, 0.86]                          |
| single, any of three runs            | 0.83 [0.70, 0.97]             | 0.80 [0.67, 0.92]                          |
| fixed (planner ablation), one run    | 0.77 [0.60, 0.90]             | 0.76 [0.62, 0.89]                          |

| Pair (defects found only by the first : only by the second) | SWE-bench     | Code Review Bench |
| ----------------------------------------------------------- | ------------- | ----------------- |
| panel vs single, first run                                  | 2 : 1, p=1.00 | 2 : 2, p=1.00     |
| panel vs single, any of three                               | 0 : 3, p=0.25 | 1 : 3, p=0.63     |
| panel vs fixed                                              | 2 : 3, p=1.00 | 2 : 3, p=1.00     |

No difference is significant. The panel found no more defects than one agent with the same model and
skills, and the planner no more than two fixed experts. Three runs of the single agent, which cost
about as much as one panel run, had the highest recall on both benchmarks, also not significantly.
On Code Review Bench the panel and the single agent found defects in five of the eight Core
categories, the fixed experts in six.

## 3. RQ3: noise (Code Review Bench)

| Configuration | Findings per review, none | Precision, none   | Precision, read_only | read_only − none     |
| ------------- | ------------------------- | ----------------- | -------------------- | -------------------- |
| panel         | 16.0 [12.9, 19.1]         | 0.14 [0.09, 0.19] | 0.16 [0.12, 0.21]    | +0.02 [0.01, 0.04]   |
| single        | 5.7 [4.5, 6.9]            | 0.37 [0.26, 0.48] | 0.36 [0.25, 0.47]    | −0.01 [−0.05, 0.03]  |
| fixed         | 6.1 [4.9, 7.3]            | 0.39 [0.26, 0.54] | 0.41 [0.26, 0.55]    | +0.01 [−0.02, 0.04]  |

The read-only judge withheld about one finding in ten and raised precision by at most two points. The
configurations differ more: the panel reported nearly three times as many findings as the single
agent, at well under half its precision. Execution could not run on these Java
subjects, so it equals read_only here; whether execution reduces noise was not measured.

## 4. RQ2: verifiability, with the oracle-rule ablation (SWE-bench)

| Measure                                                        | Value                                                                  |
| -------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Findings executed                                              | 154                                                                    |
| Passed all six gates                                           | 0.76 [0.61, 0.88]                                                      |
| Where the others stopped                                       | pass_to_pass 19, introduced 11, fail_to_pass 4, fails_as_claimed 2, not_flaky 1 |
| Oracles of the reproduced findings                             | derived 129, implicit 9, specified 2                                   |
| Blocking under the oracle rule; share whose fix resolves       | 11; 0.27                                                               |
| Ablation: blocking if any reproduction may block; share whose fix resolves | 140; 0.64                                                  |
| Verification loss                                              | 0 by construction (§8 of the protocol)                                 |

Three findings in four came with a test that fails on the change, passes with the fix and leaves the
suite passing. Almost every oracle was derived from the code, so the oracle rule let few findings
block; letting every reproduction block raises that to 140, of which 64% resolve the task.

## 5. RQ3: cost

Mean per review, execution condition (none in brackets).

| Configuration | SWE-bench tokens (k) | SWE-bench US$ | Code Review Bench tokens (k) | Code Review Bench US$ |
| ------------- | -------------------- | ------------- | ---------------------------- | --------------------- |
| panel         | 401 (272)            | 0.12 (0.09)   | 1177 (869)                   | 0.37 (0.28)           |
| single        | 181 (113)            | 0.05 (0.03)   | 354 (260)                    | 0.12 (0.09)           |
| fixed         | 307 (210)            | 0.09 (0.07)   | 597 (428)                    | 0.20 (0.15)           |

The panel costs 2.2 to 3.3 times a single run. Execution adds 45–60% to a review on SWE-bench and about
36% on Code Review Bench, where the read-only judge costs as much.

## 6. Conclusions

1. **Planning did not improve detection (RQ1, RQ3).** The planned panel found no more defects than a
   single agent, and the planner no more than two fixed experts. Repeating the single agent did
   better than either, though not significantly.
2. **Read-only verification did not reduce noise (RQ3).** A judge with the reviewer's model withheld
   few findings and barely changed precision; the panel's precision was well under half the single
   agent's. Verification cannot raise recall, since it only removes findings.
3. **Execution's contribution is evidence (RQ2).** Three quarters of executed findings carry a
   reproducing test and a verified fix, but the expected behaviour rarely came from outside the code,
   so only 11 findings could block a change.

These are internal comparisons with one model, on 30 and 10 subjects: absence of a significant
difference is not equivalence, and the threats in §8 of the protocol apply. Whether execution, as
opposed to a read-only judge, reduces noise was not measured. ReviewBench, held out from development,
is run in February 2027 to test whether these results hold ([plan](../registry/reviewbench/plan.md)).
