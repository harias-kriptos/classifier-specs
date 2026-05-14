#!/usr/bin/env bash
# .claude/hooks/enforce-tdd-trace.sh
# Runs at the end of a turn. Verifies that if Rust source under src/ was added or
# modified, there is at least one corresponding test change in the same working tree.
# Non-blocking: emits a warning the user can act on.

set -euo pipefail

cd "$CLAUDE_PROJECT_DIR" || exit 0

# Only meaningful inside a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# Skip if branch is main/master — block-main-branch handles that case
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
case "$BRANCH" in
  main|master) exit 0 ;;
esac

# Files changed since the last commit on this branch (staged + unstaged)
CHANGED=$(git status --porcelain | awk '{print $2}')

SRC_CHANGED=$(echo "$CHANGED" | grep -E '^src/.*\.rs$' || true)
TEST_CHANGED=$(echo "$CHANGED" | grep -E '^(tests/|evals/)' || true)
INLINE_TEST_CHANGED=$(echo "$CHANGED" | xargs -I{} grep -l '#\[cfg(test)\]' {} 2>/dev/null || true)

if [ -n "$SRC_CHANGED" ] && [ -z "$TEST_CHANGED" ] && [ -z "$INLINE_TEST_CHANGED" ]; then
  cat >&2 <<EOF
[tdd-trace] Source under src/ changed without a corresponding test change.
            Per CLAUDE.md section 2, every code change must trace to a failing
            test that preceded it. If you are mid-refactor, commit your tests
            and source separately so the audit trail stays clean.

            Changed source files:
$(echo "$SRC_CHANGED" | sed 's/^/              - /')
EOF
fi

exit 0
