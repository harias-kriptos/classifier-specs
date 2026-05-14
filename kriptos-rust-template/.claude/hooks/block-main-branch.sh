#!/usr/bin/env bash
# .claude/hooks/block-main-branch.sh
# Blocks any file edits when on the main branch.

set -euo pipefail

BRANCH=$(git branch --show-current 2>/dev/null || echo "")

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  echo '{"decision":"block","reason":"Cannot edit files directly on main/master. Create a feature branch first: git checkout -b feat/<name>"}' >&2
  exit 2
fi

exit 0
