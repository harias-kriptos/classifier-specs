#!/usr/bin/env bash
# scripts/bootstrap.sh — initialize this repo's working structure.
#
# Preferred path: superpowers is installed → this script tells the user to
# run /superpowers:brainstorming inside Claude Code and exits. That is the
# team's standard workflow.
#
# Fallback path: superpowers is missing or the user passed --no-superpowers
# → this script generates a minimal but functional Rust structure (specs/,
# src/, tests/, evals/, docs/) so RED-GREEN-REFACTOR can start immediately.
# Generated files are stubs marked as such so they don't get mistaken for
# real specs.
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

# ----- detect crate name from Cargo.toml ------------------------------------
# Falls back to the directory name if Cargo.toml is missing or doesn't declare one.

CRATE_NAME=""
if [ -f Cargo.toml ]; then
  CRATE_NAME=$(grep -E '^[[:space:]]*name[[:space:]]*=' Cargo.toml | head -n 1 | sed -E 's/.*"([^"]+)".*/\1/')
fi
if [ -z "$CRATE_NAME" ]; then
  CRATE_NAME=$(basename "$ROOT")
fi
# crate -> module: hyphens become underscores
CRATE_MOD=${CRATE_NAME//-/_}

# ----- state detection ------------------------------------------------------

has_specs="no"
if find specs -maxdepth 1 -name '*.md' -not -name 'SPEC_TEMPLATE.md' \
     -not -empty 2>/dev/null | grep -q .; then
  has_specs="yes"
fi

has_src="no"
if find src -name '*.rs' -type f 2>/dev/null | grep -q .; then
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
  printf '%-22s %s\n' "crate name:"         "$CRATE_NAME"
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
  echo "    nothing to do. To verify state: ./scripts/bootstrap.sh --check"
  exit 0
fi

# ----- happy path: defer to superpowers -------------------------------------

if [ "$mode" = "auto" ] && [ "$superpowers" = "installed" ]; then
  cat <<'EOF'
==> superpowers is installed — this is the team's standard workflow.

    Bootstrap is meant to run inside Claude Code, not from the shell.
    Open this repo in Claude Code and run, in order:

      1. /superpowers:brainstorming
         Use CLAUDE.md as context.

      2. /superpowers:writing-plans
         Produces specs/001-*.md and todo.md.

      3. RED → GREEN → REFACTOR against specs/001-*.md.

    If you need to bootstrap WITHOUT superpowers (CI, fresh laptop, plugin
    outage), re-run this script with --no-superpowers.
EOF
  exit 0
fi

# ----- fallback path: generate minimal Rust structure -----------------------

echo "==> running fallback bootstrap (crate=$CRATE_NAME, superpowers=$superpowers, mode=$mode)"

mkdir -p specs docs/architecture docs/security \
         src/domain src/application/ports src/application/usecases src/adapters \
         tests evals/corpus evals/tasks evals/runners evals/scorers evals/results

# --- specs/001-stub.md
if [ ! -f specs/001-scaffold-stub.md ]; then
  cat > specs/001-scaffold-stub.md <<EOF
# Spec 001: scaffold stub

> Status: stub — REPLACE BEFORE ANY REAL WORK
> Created by: ./scripts/bootstrap.sh fallback path

## ⚠️ This is a placeholder

This spec exists only so that CLAUDE.md's "no code without a spec" rule has
something to point at while the team works on the real first spec.

Replace this file (or supersede it with specs/002-*.md) before merging any
production code to main. The eval baseline gate will not protect you here
because there is no real behavior to score yet.

## 1. Goal

Make \`cargo check\` pass against an empty hexagonal skeleton so the rest of
the workflow (clippy, fmt, tarpaulin, audit, deny) has something to operate
on.

## 2. Non-goals

- Any production behavior.
- Any external integrations.

## 3. Test plan

- [ ] \`cargo check\` passes
- [ ] \`cargo test\` passes with the smoke test
- [ ] \`cargo clippy -- -D warnings\` passes

## 4. Replacement criteria

This spec is replaced when:

- Someone runs \`/superpowers:brainstorming\` and produces a real specs/NNN-*.md
- OR someone writes the real first spec by hand following SPEC_TEMPLATE.md.

Then this file should be deleted in the same PR.
EOF
  echo "    created specs/001-scaffold-stub.md"
fi

# --- src/lib.rs and module stubs
if [ ! -f src/lib.rs ]; then
  cat > src/lib.rs <<EOF
//! ${CRATE_NAME}
//!
//! Generated by ./scripts/bootstrap.sh fallback path. Replace this skeleton
//! once the first real spec exists.

pub mod domain;
pub mod application;
pub mod adapters;
EOF
  echo "    created src/lib.rs"
fi

for mod in domain application adapters; do
  if [ ! -f "src/$mod/mod.rs" ]; then
    printf '//! %s layer — see CLAUDE.md architecture section.\n' "$mod" > "src/$mod/mod.rs"
    echo "    created src/$mod/mod.rs"
  fi
done

if [ ! -f src/application/ports/mod.rs ]; then
  echo "//! ports — traits that adapters implement." > src/application/ports/mod.rs
  echo "    created src/application/ports/mod.rs"
fi

if [ ! -f src/application/usecases/mod.rs ]; then
  echo "//! use cases — orchestration of domain + ports." > src/application/usecases/mod.rs
  echo "    created src/application/usecases/mod.rs"
fi

# Wire submodules into application/mod.rs (idempotent)
if [ -f src/application/mod.rs ] && ! grep -q 'pub mod ports' src/application/mod.rs; then
  cat >> src/application/mod.rs <<'EOF'

pub mod ports;
pub mod usecases;
EOF
fi

# --- main.rs (so cargo can build a binary if Cargo.toml declares one)
if [ ! -f src/main.rs ]; then
  cat > src/main.rs <<EOF
//! ${CRATE_NAME} CLI entry point.
//!
//! Generated by ./scripts/bootstrap.sh. Wires adapters to use cases.

fn main() {
    println!("${CRATE_NAME}: stub binary. Implement against specs/001-*.md.");
}
EOF
  echo "    created src/main.rs"
fi

# --- one trivial passing test so tarpaulin has something to chew on
if [ ! -f tests/smoke_test.rs ]; then
  cat > tests/smoke_test.rs <<EOF
//! Smoke test generated by bootstrap fallback. Delete when real tests exist.

#[test]
fn library_loads() {
    // If this fails, the workspace isn't building. That's the only signal
    // this test is meant to give. Replace with real behavior tests against
    // the first real spec.
    let _ = ${CRATE_MOD}::domain;
}
EOF
  echo "    created tests/smoke_test.rs"
fi

# --- evals baseline so CI's regression gate has a starting bar
if [ ! -f evals/results/baseline.json ]; then
  cat > evals/results/baseline.json <<'EOF'
{
  "_comment": "Generated by bootstrap fallback. Raise this with a dedicated PR titled 'eval: raise baseline to <metric>' once real evals run. If this project has no non-deterministic behavior to evaluate, delete the evals/ directory entirely.",
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

# --- threat model skeleton (empty, with guidance)
if [ ! -f docs/security/threat-model.md ]; then
  cat > docs/security/threat-model.md <<'EOF'
# Threat model

> Generated by bootstrap fallback. Fill in before any release.
>
> If this project has no security-sensitive surfaces, delete this file and
> remove the reference from CLAUDE.md.

## Surfaces

List every component that crosses a trust boundary: reads untrusted input,
writes outside its own process, talks to the network, or holds credentials.

| Surface | Trust boundary | STRIDE focus |
|---|---|---|
| (fill in) | | |

## Mitigations

For each surface above, state what stops a hostile input from causing harm.
Cite the line of code or test that enforces each mitigation.

- [ ] (fill in)

## Out of scope

State explicitly what this threat model does NOT cover, so reviewers don't
assume something is mitigated when it isn't.
EOF
  echo "    created docs/security/threat-model.md"
fi

# --- todo.md
if [ ! -f todo.md ]; then
  cat > todo.md <<'EOF'
# todo

> Working list for the current spec. Replace contents whenever specs/NNN-*.md changes.

Generated by bootstrap fallback. The first real task is to replace
specs/001-scaffold-stub.md with a real specification.

- [ ] Replace specs/001-scaffold-stub.md with the first real vertical slice
  - [ ] Run /superpowers:brainstorming (if available) OR draft by hand from SPEC_TEMPLATE.md
  - [ ] Pick the first behavior small enough to RED-GREEN-REFACTOR in one PR
- [ ] Delete tests/smoke_test.rs once real tests cover the same modules
- [ ] Raise evals/results/baseline.json once the first eval run produces real numbers (or delete evals/ if not applicable to this project)
EOF
  echo "    created todo.md"
fi

cat <<EOF

==> fallback bootstrap done.

    Generated structure:
      specs/001-scaffold-stub.md    REPLACE before merging real code
      src/                          hexagonal skeleton (domain / application / adapters)
      tests/smoke_test.rs           trivial; delete when real tests exist
      evals/results/baseline.json   F1=0; raise via dedicated PR (or delete if N/A)
      docs/security/threat-model.md fill in before release
      todo.md

    Verify with:    cargo check && cargo test
    Next step:      open Claude Code and continue against specs/001-scaffold-stub.md
                    (or, preferred, install superpowers and replace the stub
                    spec via /superpowers:brainstorming)
EOF
