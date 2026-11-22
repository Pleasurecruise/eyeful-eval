# eyeful-eval

The evaluation of [eyeful](https://github.com/Pleasurecruise/eyeful): building subjects from public
benchmarks, reviewing them with eyeful, scoring the reviews with each benchmark's own scorer and
analysing the results. The protocol is in [docs/EVALUATION.md](docs/EVALUATION.md)
([中文](docs/zh/EVALUATION.md)); changes to it are in [registry/amendments.md](registry/amendments.md); the results are in
[docs/RESULTS.md](docs/RESULTS.md) ([中文](docs/zh/RESULTS.md)).

## Layout

| Path        | Holds                                                                         | Committed |
| ----------- | ----------------------------------------------------------------------------- | --------- |
| `eval/`     | The apparatus, one package per stage, in Python's standard library            | Yes       |
| `registry/` | Each run's manifest, the amendments, the SWE-bench selection rules and the ReviewBench plan | Yes |
| `docs/`     | The protocol and the results                                                  | Yes       |
| `.eval/`    | Benchmarks, subjects, repositories, eyeful builds, runs and scores            | Never     |

| Package          | Modules                                                       | Stage                                            |
| ---------------- | ------------------------------------------------------------- | ------------------------------------------------ |
| `eval/core`      | `model`, `layout`, `shell`                                    | Shared records; files stages exchange; commands  |
| `eval/build`     | `subjects`, `baseline`, `select`, `reviewbench`               | Build subjects, check their validity, draw more  |
| `eval/review`    | `run`, `confine`, `audit`, `result`                           | Review in a sandbox, audit, read a review         |
| `eval/record`    | `registry`, `progress`                                        | Manifests; the progress table                    |
| `eval/score`     | `resolve`, `match`, `relay`, `reviewbench`                    | Each benchmark's own scorer                      |
| `eval/analysis`  | `analyze`                                                     | Measures and intervals                           |

In `.eval/<benchmark>/`, `subjects/` holds what names each defect and `repos/` the repositories
reviewers read, under hashed names; `runs/` and `scores/` are written by the apparatus. Subjects and
runs record absolute paths, so the clone stays in one place.

## Setup

```sh
mise install     # Python, pi and ruff, at the versions the experiment used
mise run lint    # ruff check and format check
mise run test
```

A run also needs, on macOS: an eyeful build at `.eval/bin/eyeful-<commit>`, built in eyeful's clone
with `go build -o ../eyeful-eval/.eval/bin/eyeful-$(git rev-parse --short HEAD) ./cmd/eyeful`; Docker;
`uv`, which runs SWE-bench's harness; and the Code Review Bench checkout at `.eval/crb/benchmark`.

## Running

`eval/schedule.sh` runs the whole experiment in order and `python3 -m record.progress` tabulates it in
`.eval/progress.md`. Each stage can also be run alone; under mise, `PYTHONPATH` is set:

```sh
python3 -m build.subjects swebench --data .eval/swebench/verified.json --out .eval/swebench/subjects --repos .eval/swebench/repos
python3 -m build.baseline --subjects .eval/swebench/subjects --data .eval/swebench/verified.json --out .eval/swebench/baseline.json
python3 -m review.run --subjects .eval/swebench/subjects --out .eval/swebench/runs/<commit> --eyeful .eval/bin/eyeful-<commit>
python3 -m score.resolve --subjects .eval/swebench/subjects --data .eval/swebench/verified.json --runs .eval/swebench/runs/<commit> --out .eval/swebench/scores/<commit>
python3 -m analysis.analyze --dataset swebench --subjects .eval/swebench/subjects --reviews .eval/swebench/runs/<commit>/reviews.jsonl --scores .eval/swebench/scores/<commit>/scores.jsonl
```

`verified.json` is SWE-bench Verified as published now, whose rows carry the image and evaluation
script the harness runs. Code Review Bench is scored with `score.match`, whose judge reaches
OpenCode Go through `--header x-opencode-session=<id>`. Every module takes `--help`.
