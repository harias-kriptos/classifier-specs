#!/usr/bin/env bash
# scripts/bootstrap.sh — initialize a Python Lambda repo for the Classifier.
#
# Preferred path: superpowers is installed → tells the user to run
# /superpowers:brainstorming inside Claude Code and exits.
#
# Fallback path: superpowers is missing or --no-superpowers was passed → generates
# a minimal but functional Python Lambda structure (specs/, src/, tests/, evals/,
# docs/, handler.py, pyproject.toml).
#
# Idempotent: re-running is safe; existing files are not overwritten.
#
# Usage:
#   ./scripts/bootstrap.sh                  # auto-detect, prefer superpowers
#   ./scripts/bootstrap.sh --no-superpowers # force fallback
#   ./scripts/bootstrap.sh --check          # report state, change nothing

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mode="auto"
case "${1:-}" in
  --no-superpowers) mode="fallback" ;;
  --check)          mode="check" ;;
  "")               mode="auto" ;;
  *) echo "unknown flag: $1" >&2; exit 2 ;;
esac

# ----- detect project name --------------------------------------------------

PROJECT_NAME=""
if [ -f pyproject.toml ]; then
  PROJECT_NAME=$(grep -E '^\s*name\s*=' pyproject.toml | head -n 1 | sed -E 's/.*"([^"]+)".*/\1/')
fi
if [ -z "$PROJECT_NAME" ]; then
  PROJECT_NAME=$(basename "$ROOT")
fi
PROJECT_MOD=${PROJECT_NAME//-/_}

# ----- state detection ------------------------------------------------------

has_specs="no"
if find specs -maxdepth 1 -name '*.md' -not -name 'SPEC_TEMPLATE.md' \
     -not -empty 2>/dev/null | grep -q .; then
  has_specs="yes"
fi

has_src="no"
if find src -name '*.py' -type f 2>/dev/null | grep -q .; then
  has_src="yes"
fi

superpowers="missing"
if command -v claude >/dev/null 2>&1; then
  if claude plugin list 2>/dev/null | grep -qi 'superpowers'; then
    superpowers="installed"
  fi
fi

# ----- check mode -----------------------------------------------------------

if [ "$mode" = "check" ]; then
  printf '%-22s %s\n' "project name:"       "$PROJECT_NAME"
  printf '%-22s %s\n' "specs present:"      "$has_specs"
  printf '%-22s %s\n' "src present:"        "$has_src"
  printf '%-22s %s\n' "superpowers plugin:" "$superpowers"
  if [ "$has_specs" = "yes" ] && [ "$has_src" = "yes" ]; then
    echo "verdict: bootstrapped"
  elif [ "$has_specs" = "no" ] && [ "$superpowers" = "installed" ]; then
    echo "verdict: ready for /superpowers:brainstorming"
  else
    echo "verdict: needs bootstrap (run without --check)"
  fi
  exit 0
fi

# ----- already bootstrapped -------------------------------------------------

if [ "$has_specs" = "yes" ] && [ "$has_src" = "yes" ]; then
  echo "==> repo is already bootstrapped (specs/ and src/ both populated)"
  exit 0
fi

# ----- happy path: defer to superpowers -------------------------------------

if [ "$mode" = "auto" ] && [ "$superpowers" = "installed" ]; then
  cat <<'EOF'
==> superpowers is installed — the team standard.

    Bootstrap is meant to run inside Claude Code, not from the shell.
    Open this repo in Claude Code and run, in order:

      1. /brainstorm <ticket-ref>          (Skill 01)
      2. /spec <brainstorm-output>         (Skill 02)
      3. /plan <spec-path>                 (Skill 03)
      4. /implement                        (Skill 04 — TDD loop)
      5. /review                           (Skill 05)

    Or, if you prefer the upstream Superpowers commands:
      /superpowers:brainstorming
      /superpowers:writing-plans
      /superpowers:executing-plans

    To bootstrap WITHOUT superpowers (CI, fresh laptop, plugin outage),
    re-run with --no-superpowers.
EOF
  exit 0
fi

# ----- fallback path: generate minimal Python Lambda structure --------------

echo "==> running fallback bootstrap (project=$PROJECT_NAME, superpowers=$superpowers, mode=$mode)"

mkdir -p specs docs/architecture docs/security \
         src/domain src/application/ports src/application/usecases src/adapters \
         tests/unit tests/integration \
         evals/corpus evals/tasks evals/runners evals/scorers evals/results

# --- specs/001-stub.md
if [ ! -f specs/001-scaffold-stub.md ]; then
  cat > specs/001-scaffold-stub.md <<EOF
# Spec 001: scaffold stub

> Status: stub — REPLACE BEFORE ANY REAL WORK
> Created by: ./scripts/bootstrap.sh fallback path

This spec exists only so the "no code without a spec" rule has something to
point at while the team works on the real first spec.

Replace this file (or supersede it with specs/002-*.md) before merging any
production code to main.

## 1. Goal

Make \`pytest\` pass against an empty Python skeleton so the workflow (ruff,
mypy, pytest, coverage) has something to operate on.

## 2. Non-goals

- Any production behavior.
- Any external integrations.

## 3. Test plan

- [ ] \`pytest\` passes with the smoke test
- [ ] \`ruff check\` clean
- [ ] \`mypy src\` clean

## 4. Replacement criteria

Delete this stub when the first real spec exists in \`specs/002-*.md\`.
EOF
  echo "    created specs/001-scaffold-stub.md"
fi

# --- src layout
for dir in domain application/ports application/usecases adapters; do
  mkdir -p "src/$dir"
  if [ ! -f "src/${dir%%/*}/__init__.py" ]; then
    touch "src/${dir%%/*}/__init__.py"
  fi
  if [ ! -f "src/$dir/__init__.py" ]; then
    touch "src/$dir/__init__.py"
  fi
done
if [ ! -f src/__init__.py ]; then touch src/__init__.py; fi

# --- handler.py
if [ ! -f handler.py ]; then
  cat > handler.py <<EOF
"""${PROJECT_NAME} — Lambda entrypoint.

Generated by ./scripts/bootstrap.sh. Wire adapters to use cases here.
"""
from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint. Replace with real use-case orchestration."""
    return {"statusCode": 200, "body": '{"message": "stub"}'}
EOF
  echo "    created handler.py"
fi

# --- pyproject.toml (only if missing)
if [ ! -f pyproject.toml ]; then
  cat > pyproject.toml <<EOF
[project]
name = "${PROJECT_NAME}"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
  "aws-lambda-powertools[tracer]>=2",
  "boto3>=1.34",
  "pydantic>=2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-cov>=4",
  "moto[s3,dynamodb,sqs]>=5",
  "ruff>=0.5",
  "mypy>=1.10",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "S", "A", "C4", "RET", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=80"
EOF
  echo "    created pyproject.toml"
fi

# --- smoke test
if [ ! -f tests/__init__.py ]; then touch tests/__init__.py; fi
if [ ! -f tests/unit/__init__.py ]; then touch tests/unit/__init__.py; fi
if [ ! -f tests/unit/test_smoke.py ]; then
  cat > tests/unit/test_smoke.py <<EOF
"""Smoke test generated by bootstrap. Delete when real tests exist."""


def test_imports() -> None:
    """If this fails, the package isn't set up correctly."""
    import src  # noqa: F401
EOF
  echo "    created tests/unit/test_smoke.py"
fi

# --- evals baseline
if [ ! -f evals/results/baseline.json ]; then
  cat > evals/results/baseline.json <<'EOF'
{
  "_comment": "Generated by bootstrap fallback. Raise this with a dedicated PR titled 'eval: raise baseline to <metric>' once real evals run. If this Lambda has no non-deterministic behavior, delete evals/ entirely.",
  "runner": "placeholder",
  "model": "placeholder",
  "f1": 0.0,
  "precision": 0.0,
  "recall": 0.0,
  "tasks_evaluated": 0,
  "generated_at": "bootstrap"
}
EOF
  echo "    created evals/results/baseline.json"
fi

# --- threat model skeleton
if [ ! -f docs/security/threat-model.md ]; then
  cat > docs/security/threat-model.md <<'EOF'
# Threat model

> Generated by bootstrap fallback. Fill in before any release, or delete if
> this Lambda has no security-sensitive surfaces.

## Surfaces

| Surface | Trust boundary | STRIDE focus |
|---|---|---|
| (fill in) | | |

## Mitigations

- [ ] (fill in, cite test or line of code)

## Out of scope

Explicitly list what this threat model does NOT cover.
EOF
  echo "    created docs/security/threat-model.md"
fi

# --- todo.md
if [ ! -f todo.md ]; then
  cat > todo.md <<'EOF'
# todo

> Working list for the current spec. Replace whenever specs/NNN-*.md changes.

- [ ] Replace specs/001-scaffold-stub.md with the first real vertical slice
- [ ] Delete tests/unit/test_smoke.py once real tests cover the same modules
- [ ] Raise evals/results/baseline.json once the first eval run produces real numbers (or delete evals/ if not applicable)
EOF
  echo "    created todo.md"
fi

cat <<EOF

==> fallback bootstrap done.

    Generated structure:
      specs/001-scaffold-stub.md    REPLACE before merging real code
      src/                          hexagonal skeleton
      tests/unit/test_smoke.py      delete when real tests exist
      handler.py                    Lambda entrypoint stub
      pyproject.toml                deps + ruff + mypy + pytest config
      evals/results/baseline.json   F1=0; raise via dedicated PR (or delete if N/A)
      docs/security/threat-model.md fill in or delete

    Verify with:    pytest && ruff check && mypy src
    Next step:      open Claude Code and run /brainstorm against the first ticket.
EOF
