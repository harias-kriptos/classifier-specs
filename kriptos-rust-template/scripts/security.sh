#!/usr/bin/env bash
# scripts/security.sh — security gate
# Run via: ./scripts/security.sh run | ./scripts/security.sh help

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ensure() {
  local bin="$1" install="$2"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "==> installing $bin"
    eval "$install"
  fi
}

run() {
  ensure cargo-audit "cargo install cargo-audit --locked"
  ensure cargo-deny  "cargo install cargo-deny --locked"

  echo "==> cargo audit (RustSec advisory DB)"
  cargo audit

  echo "==> cargo deny check (licenses, sources, duplicates, advisories)"
  if [ -f deny.toml ]; then
    cargo deny check
  else
    echo "  (deny.toml not found — running with defaults)"
    cargo deny check advisories bans licenses sources
  fi

  echo "==> grep for likely secrets in tree"
  # Lightweight secondary check; the real defense is the .claude/hooks/block-secrets.sh
  # and the deny rules in .claude/settings.json. CI should run gitleaks for the full pass.
  if grep -RInE '(AKIA[0-9A-Z]{16}|sk-ant-api03-[A-Za-z0-9_\-]{93}|ghp_[0-9A-Za-z]{36})' \
       --exclude-dir=target --exclude-dir=.git --exclude-dir=node_modules . ; then
    echo "  (matches above — investigate)" >&2
    exit 1
  fi

  echo "==> done"
}

help() {
  cat <<'EOF'
security.sh — security gate

Usage:
  ./scripts/security.sh run    cargo audit + cargo deny + secret grep
  ./scripts/security.sh help   Show this message
EOF
}

case "${1:-help}" in
  run)  run ;;
  help) help ;;
  *)    help; exit 1 ;;
esac
