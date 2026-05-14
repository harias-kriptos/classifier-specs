# Eval harness

This directory is the project's regression net for **non-deterministic behavior** — anything where output depends on a model, prompt, heuristic, or other stochastic component. Unit tests cover deterministic logic; this harness covers the rest.

**If this project is fully deterministic, delete this directory.** The harness is dead weight for projects that don't need it.

## Why a harness, not just unit tests

Two things break in non-deterministic systems that unit tests do not catch:

1. **Prompt drift.** A reasonable-looking prompt edit silently lowers precision on a class of inputs.
2. **Model drift.** Bumping a model version changes outputs in ways that pass type checks and fail the user.

A harness fixes this by treating model outputs as data: a fixed corpus in, a scored report out, with a baseline checked into git.

## Layout

```
evals/
├── corpus/        fixture inputs used as test cases
├── tasks/         JSONL, one task per line — fixture + expected output
├── runners/       Rust binaries that load tasks, call the real use case, score
├── scorers/       reusable scoring (exact match, confusion matrix, F1)
└── results/       timestamped JSON outputs, committed to track regression
    └── baseline.json   the bar every PR must clear
```

## Task format

Each `.jsonl` file under `tasks/` has one task per line:

```jsonl
{"id":"<stable-id>","fixture":"corpus/<topic>/<file>","expected":{...}}
{"id":"<stable-id>","fixture":"corpus/<topic>/<file>","expected":{...}}
```

Fields:

| Field | Meaning |
|---|---|
| `id` | stable identifier; never reused, never renamed |
| `fixture` | path relative to `evals/`, must exist in the same commit |
| `expected` | ground truth for whatever metric the runner computes |
| `weight` | optional; default 1.0; raise for tasks that represent common production patterns |

## Running

```
./scripts/eval.sh run                       # default: all runners, default model
./scripts/eval.sh run <runner>              # one runner
./scripts/eval.sh run <runner> <model>      # one runner, one model
```

Each run produces a file under `results/` named `YYYY-MM-DD_<runner>_<model>.json`. The file contains, in order:

1. environment (model name, model digest, host OS, agent version)
2. per-task result (id, expected, actual, pass/fail, latency)
3. aggregate metrics (precision, recall, F1, confusion matrix)

## Baseline and regression gate

`results/baseline.json` is the bar. CI does:

```
last_run = most recent file in results/ matching the PR's runner/model
baseline = results/baseline.json
fail if last_run.f1 < baseline.f1 - 0.01
```

The tolerance (`-0.01`) absorbs natural variance from temperature-0 hosts that still differ across kernels. Tighten it once you have ten clean runs to compute real variance.

To **raise** the baseline, open a PR with the title `eval: raise baseline to <metric>` and only one change: the new `baseline.json`. This forces a human to review and accept the new bar — it cannot happen as a side effect of a code change.

## Adding a new task type

1. Add fixtures under `corpus/<topic>/`.
2. Add tasks to `tasks/<topic>.jsonl`.
3. If the existing runners cannot score this, add a new runner under `runners/` that loads `tasks/<topic>.jsonl` and writes to `results/`.
4. Add the runner to `scripts/eval.sh`.
5. Run it once locally; commit the result; mark it as the new baseline if appropriate.

## What this harness is not

- It is **not** a replacement for unit tests on deterministic code.
- It is **not** a load test. Performance regression has its own scripts.
- It is **not** a security scanner. That is `./scripts/security.sh`.
