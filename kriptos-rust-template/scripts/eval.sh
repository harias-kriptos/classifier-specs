#!/usr/bin/env bash
# scripts/eval.sh — run the regression harness for non-deterministic behavior.
# Run via: ./scripts/eval.sh run [runner] [model]
#
# If this project is fully deterministic, delete this script and the evals/
# directory; the harness is unused.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Default model: empty string means "let the runner decide based on its config".
# Override with the second positional argument, e.g.:
#   ./scripts/eval.sh run <runner> <model>
DEFAULT_MODEL=""

run() {
  local runner="${1:-all}"
  local model="${2:-$DEFAULT_MODEL}"
  local date_tag
  date_tag="$(date +%Y-%m-%d)"

  mkdir -p evals/results

  # Discover available runners from evals/tasks/*.jsonl
  local available
  available=$(find evals/tasks -maxdepth 1 -name '*.jsonl' 2>/dev/null \
                | sed -E 's|.*/([^/]+)\.jsonl|\1|' || true)

  if [ -z "$available" ]; then
    echo "==> no task files found under evals/tasks/. Nothing to eval."
    echo "    Add tasks/<runner>.jsonl and a matching eval-<runner> binary."
    exit 0
  fi

  run_one() {
    local name="$1"
    local model_tag="${model:-default}"
    local safe_model="${model_tag//[:\/]/-}"
    echo "==> eval runner=$name model=${model:-<default>}"
    cargo run --release --bin "eval-$name" -- \
      --tasks "evals/tasks/${name}.jsonl" \
      ${model:+--model "$model"} \
      --out   "evals/results/${date_tag}_${name}_${safe_model}.json"
  }

  case "$runner" in
    all)
      for r in $available; do run_one "$r"; done
      ;;
    *)
      if echo "$available" | grep -qx "$runner"; then
        run_one "$runner"
      else
        echo "unknown runner: $runner" >&2
        echo "available: $available" >&2
        exit 1
      fi
      ;;
  esac

  if [ -x ./scripts/eval-gate.sh ]; then
    echo "==> comparing against baseline"
    ./scripts/eval-gate.sh "$date_tag" "$runner" "${model:-default}" || {
      echo "==> regression detected. Review the result file before merging." >&2
      exit 1
    }
  else
    echo "==> note: scripts/eval-gate.sh not found — skipping baseline comparison."
    echo "    Add it to enforce regression gates in CI."
  fi

  echo "==> done"
}

help() {
  cat <<'EOF'
eval.sh — run the regression harness

Usage:
  ./scripts/eval.sh run [runner] [model]
      runner: name matching a file under evals/tasks/<runner>.jsonl
              (default: "all" — runs every runner found)
      model:  optional model identifier passed to the runner

Results are written to evals/results/ and gated against evals/results/baseline.json.
EOF
}

case "${1:-help}" in
  run)  shift; run "$@" ;;
  help) help ;;
  *)    help; exit 1 ;;
esac
