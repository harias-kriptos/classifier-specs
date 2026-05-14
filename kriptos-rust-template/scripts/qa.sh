#!/usr/bin/env bash
# scripts/qa.sh — quality gate
# Run via: ./scripts/qa.sh run | ./scripts/qa.sh help

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

run() {
  echo "==> cargo fmt --check"
  cargo fmt --all -- --check

  echo "==> cargo clippy (deny warnings)"
  cargo clippy --all-targets --all-features -- -D warnings

  echo "==> cargo test"
  cargo test --workspace --all-features

  echo "==> cargo tarpaulin (coverage gate 80%)"
  if command -v cargo-tarpaulin >/dev/null 2>&1; then
    cargo tarpaulin --out Xml --workspace --skip-clean --fail-under 80
  else
    echo "  (tarpaulin not installed — skipping. Install: cargo install cargo-tarpaulin)"
  fi

  echo "==> done"
}

help() {
  cat <<'EOF'
qa.sh — quality gate

Usage:
  ./scripts/qa.sh run    Run fmt + clippy + test + coverage gate
  ./scripts/qa.sh help   Show this message

Exits non-zero on any failure. Intended for both local pre-push and CI.
EOF
}

case "${1:-help}" in
  run)  run ;;
  help) help ;;
  *)    help; exit 1 ;;
esac
