# SWE-bench: adding subjects

Written before the added subjects were built or reviewed. The 20 subjects in `subjects/` were
picked by hand while the scripts were written; 16 of them are valid (`baseline.json`). These
rules add 14 more, to reach about the 30 the plan names, without choosing them.

1. The pool is every task of SWE-bench Verified in a project `build.subjects` has a runner for, less
   the 20 already built.
2. Tasks are tried in the order of the SHA-256 of their instance id.
3. A task is built with `build.subjects` from its arm64 image, or from its x86_64 image when there is
   no arm64 one, into `subjects-2/`.
4. A task is kept when its hidden FAIL_TO_PASS tests, added by its test patch in a throwaway
   checkout, pass on the base and fail on the head with no network, and its suite of passing
   PASS_TO_PASS tests is not empty. These test the environment only, not any review.
5. Tasks are tried until 14 are kept. Each task tried, kept or not, and why, is in
   `.eval/swebench/selection.jsonl`; a task not kept has its repository, subject and image removed.

The added subjects join the same run, reviewed with the same eyeful build, model, configurations and
conditions as the first 16, and are analysed with them.

The rules are carried out by `eval/build/select.py`, which checks validity with `eval/build/baseline.py`.
