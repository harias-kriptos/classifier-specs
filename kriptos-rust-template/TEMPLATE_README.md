# Kriptos Rust project template

A starter layout for new Rust projects at Kriptos. Ships with:

- `.claude/` — sandbox-enforced settings, six hooks, the `SessionStart` bootstrap detector.
- `CLAUDE.md` — project charter Claude reads before every task.
- `scripts/` — `bootstrap.sh`, `qa.sh`, `security.sh`, `eval.sh`.
- `specs/SPEC_TEMPLATE.md` — the format every spec follows.
- `evals/README.md` — harness layout for non-deterministic behavior (delete if not needed).

## How to use this template

1. Copy this directory into a new repo. Run `git init` if it isn't already a repo.
2. Add a `Cargo.toml` declaring the crate name. The fallback bootstrap reads the name from there.
3. Edit `CLAUDE.md`: replace the placeholder paragraph in section 0 with a one-sentence project description, the ticket prefix (e.g. `KT-XXXXX`), and the branch convention.
4. Open the repo in Claude Code. The `SessionStart` hook will detect the pre-bootstrap state and tell Claude what to do next — typically `/superpowers:brainstorming`.
5. If superpowers isn't available, run `./scripts/bootstrap.sh --no-superpowers` for a deterministic scaffold.

## What stays, what changes per project

| Keep as-is | Change per project |
|---|---|
| `.claude/hooks/*.sh` | `CLAUDE.md` (project description, sections that don't apply) |
| `.claude/settings.json` (mostly) | Sandbox `allowedDomains` if you need extra origins |
| `scripts/bootstrap.sh` | `Cargo.toml` (crate name, deps with justification) |
| `scripts/qa.sh`, `scripts/security.sh`, `scripts/eval.sh` | Custom CI workflows under `.github/workflows/` |
| `specs/SPEC_TEMPLATE.md` | Delete `evals/` entirely if project is fully deterministic |

## Conventions baked into this template

- **Spec-first.** No code without a spec under `specs/NNN-<slug>.md`. Enforced by `SessionStart` hook + Stop hook.
- **TDD strict.** `chore(failing):` → `feat(passing):` → `refactor:` commit sequence. Enforced by commitlint in CI.
- **Hexagonal Rust.** `src/domain` / `src/application` / `src/adapters`. Dependency rule: inward only.
- **Sandboxed bash.** `.claude/settings.json` enables Seatbelt/bubblewrap. Escape hatch disabled.
- **Coverage gate.** 80% line coverage via `cargo tarpaulin`.
- **Secrets blocked.** `block-secrets.sh` hook + denied paths in `settings.json` + `.env` in `.gitignore`.

## Hooks installed

| Event | Hook | What it does |
|---|---|---|
| `SessionStart` | `session-start-bootstrap-check.sh` | Detects bootstrap state and superpowers availability; injects guidance into Claude's context. |
| `PreToolUse` (Edit/Write) | `block-main-branch.sh` | Refuses edits when on `main` or `master`. |
| `PreToolUse` (Edit/Write) | `block-secrets.sh` | Refuses edits that introduce AWS keys, GitHub PATs, API tokens, PEM private keys, etc. |
| `PreToolUse` (Bash) | `block-dangerous-commands.sh` | Refuses `rm -rf /`, force-push, curl-pipe-bash, fork bomb. |
| `PostToolUse` (Edit/Write) | `post-edit-rust.sh` | Runs `cargo check` and `cargo fmt --check` after Rust edits. Non-blocking. |
| `Stop` | `enforce-tdd-trace.sh` | Warns at end-of-turn if `src/` changed without a corresponding test change. |

## Sandbox boundaries

Set in `.claude/settings.json` → `sandbox`:

- **Writes:** working directory, Cargo caches, `/tmp`. Nothing else.
- **Reads denied:** `~/.ssh`, `~/.aws`, `~/.kube`, `~/.gnupg`, `~/.netrc`, macOS Keychain, `.env`.
- **Network allowed:** crates.io, rust-lang.org, github.com, npm registry. Everything else blocked.
- **Network denied explicitly:** `169.254.169.254`, `metadata.google.internal`, `instance-data.ec2.internal` (cloud metadata SSRF defense).
- **Escape hatch closed:** `allowUnsandboxedCommands: false`. If a command can't run sandboxed, add it to `excludedCommands` or the `ask` list explicitly.

Read more: https://code.claude.com/docs/en/sandboxing
