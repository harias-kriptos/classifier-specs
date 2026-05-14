#!/usr/bin/env bash
# .claude/hooks/post-edit-rust.sh
# Runs lightweight syntactic checks after Claude edits Rust files.
# Designed to be quiet on success and informative on failure, without ever blocking.

set -euo pipefail

INPUT=$(cat)
TARGET=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""')

# Only act on Rust files.
case "$TARGET" in
  *.rs) ;;
  Cargo.toml) ;;
  *) exit 0 ;;
esac

cd "$CLAUDE_PROJECT_DIR" || exit 0

# `cargo check` is the cheapest correctness signal.
# Only run if a manifest exists and src/ has at least one file (skip on bare scaffolds).
if [ -f Cargo.toml ] && find src -name '*.rs' -type f 2>/dev/null | grep -q .; then
  if ! cargo check --quiet 2>/tmp/claude-cargo-check.log; then
    {
      echo "{\"decision\":\"approve\",\"reason\":\"Edit applied, but cargo check failed. See errors below.\"}"
      echo "---"
      cat /tmp/claude-cargo-check.log
    } >&2
  fi
fi

# fmt is non-fatal but reported
if [ -f Cargo.toml ]; then
  cargo fmt --all -- --check >/dev/null 2>&1 || \
    echo "[post-edit] cargo fmt would change files. Run: cargo fmt --all" >&2
fi

exit 0
