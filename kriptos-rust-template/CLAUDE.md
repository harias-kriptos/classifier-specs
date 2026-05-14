# Project Charter for Claude

This file is the contract between you (Claude Code) and this repository. **Read it before every task.**

Replace this paragraph with a one-sentence description of what this project does, the ticket prefix that owns it (e.g. `KT-XXXXX`), and the branch convention (e.g. `KT-XXXXX-<short-slug>`).

---

## 1. How this project is bootstrapped

This is a **template-based repo**. When you first open it, `specs/` will only contain `SPEC_TEMPLATE.md` and `src/` may be empty. That is the expected starting state. There is a `SessionStart` hook that detects this and tells you what to do — read its output before doing anything else.

The team's standard workflow is **superpowers-first, with a deterministic fallback**:

### Happy path (every developer on the team)

The team standard is to have `superpowers` installed. When you detect that the repo is pre-bootstrap and superpowers is available, your first three actions are, in this order:

1. `/superpowers:brainstorming` — use the relevant sections of this file as context. Output is a design conversation with the user, not files.
2. `/superpowers:writing-plans` — turns the brainstorm into `specs/001-<slug>.md` and `todo.md`.
3. RED → GREEN → REFACTOR against `specs/001-<slug>.md`.

You may not skip to implementation, even if the user asks. Push back and explain: this repo's CI gates depend on a real spec existing.

### Fallback path (superpowers unavailable)

If the `SessionStart` hook reports that superpowers is missing, ask the user which they prefer:

**Option 1 (preferred):** install superpowers — `claude plugin install superpowers@claude-plugins-official` — and restart the session. This is the team standard for a reason: the brainstorming and plan-writing flows produce better specs than hand-drafting.

**Option 2:** run `./scripts/bootstrap.sh --no-superpowers`. This generates a minimal but functional scaffold: a `specs/001-scaffold-stub.md` marked as stub, a hexagonal `src/` skeleton, a trivial passing test, an `evals/results/baseline.json` with F1=0, and a threat-model skeleton. The stub spec must be replaced before merging real code.

The fallback exists so a fresh laptop on Monday morning, a CI runner, or a session during a plugin outage are not blocked. It is not the preferred path.

### Once bootstrapped

Once `specs/NNN-*.md` exist (real ones, not the stub) and `src/` has real code, the `SessionStart` hook stops asking and you operate normally against the latest spec. The hook also catches the half-state where specs exist but src is empty — pick up at the RED phase of the next pending task in `todo.md`.

---

## 2. The development loop

```
1. spec        →  specs/NNN-<slug>.md committed
2. plan        →  todo.md at repo root with one task per assertion
3. red         →  failing test committed:  chore(failing): <behavior>
4. green       →  minimal impl:            feat(passing):  <behavior>
5. refactor    →  cleanup:                 refactor:       <what>
6. evaluate    →  harness run + score recorded in evals/results/  (if applicable)
```

`commitlint` enforces the `chore(failing):` prefix in CI. You do not get to skip the red commit. If you produced source code without a matching test commit, the `enforce-tdd-trace.sh` Stop hook will warn you at end-of-turn — fix it before the user notices.

---

## 3. Architecture

Clean / hexagonal in Rust. Three layers under `src/`:

```
src/
├── domain/         pure types, no I/O, no async, no deps beyond std + serde
├── application/    use cases + ports (traits). depends on domain only.
│   ├── ports/      traits that adapters implement
│   └── usecases/   orchestration of domain + ports
└── adapters/       concrete impls. depends on application.
```

**Dependency rule:** `domain` imports nothing from the workspace. `application` imports `domain` only. `adapters` import `application`. Anything that breaks this is a `BLOCKED` and gets reported back to the user.

`src/main.rs` is a thin CLI binary that wires adapters → use cases. It is **not** tested directly; the use cases are.

---

## 4. Testing standard

| Layer | Test location | Framework | Real I/O? |
|---|---|---|---|
| `domain` | inline `#[cfg(test)] mod tests` | built-in | never |
| `application` | inline `#[cfg(test)] mod tests` | built-in + `mockall` | never — mock all ports |
| `adapters` | `tests/<adapter>_test.rs` | built-in | yes, against `tempfile::tempdir()` and local fakes |
| end-to-end | `tests/e2e_*.rs` | built-in | yes, against a fixture corpus under `tests/fixtures/` |

Coverage gate: **80% line coverage** via `cargo tarpaulin --out Xml --workspace --skip-clean`. Anything under that fails CI.

Rules across all layers:

- Never mock domain types — only ports.
- Test names describe behavior: `rejects_paths_outside_scan_root`, not `test_path_check`.
- One logical assertion per test.
- No real external services in unit or integration tests. Use fakes that return canned responses.

---

## 5. Harness for non-deterministic behavior

If this project includes anything non-deterministic — LLM calls, ML inference, heuristic classifiers, retry-with-jitter — ordinary unit tests are not enough. Use the `evals/` directory for regression testing of those parts:

```
evals/
├── corpus/                     fixture inputs for repeatable runs
├── tasks/                      JSONL, one task per line, with expected outputs
├── runners/                    Rust binaries: load tasks → call use case → write report
├── scorers/                    exact match, confusion matrix, F1
└── results/                    timestamped JSON outputs, committed
    └── baseline.json           the bar every PR must clear
```

When you change a model, prompt, or heuristic, **add or update a task in `evals/tasks/` before changing the code**. That is the analog of TDD for non-deterministic behavior. `evals/README.md` has the full spec for task format, scoring, and how baselines get raised (always via a dedicated `eval: raise baseline to <metric>` PR).

**If this project is fully deterministic, delete `evals/` entirely.** The harness is dead weight for projects that don't need it.

---

## 6. Security and sandbox

Update `docs/security/threat-model.md` whenever you introduce a new adapter that crosses a trust boundary (reads untrusted input, writes outside the process, talks to the network, or holds credentials). If this project has no such surfaces, delete the threat model file and remove this section.

Hard rules:

- No `unsafe` Rust outside `adapters/`, and only with a `// SAFETY:` comment.
- No global state, no `lazy_static`, no `static mut`.
- Secrets never live in source. `.env.example` documents the keys; `.env` is in `.gitignore` and `deny`-listed in `.claude/settings.json` so Claude cannot read it.

The Claude Code sandbox is enabled (`.claude/settings.json` → `sandbox.enabled: true`). Writes restricted to working directory + Cargo caches + `/tmp/<project>`. Reads denied from `~/.ssh`, `~/.aws`, `~/.kube`, `~/.gnupg`, Keychain, `.env`. Network limited to crates.io / rust-lang.org / github.com / npm. AWS metadata IPs (`169.254.169.254`, etc.) denied explicitly. Escape hatch `dangerouslyDisableSandbox` is disabled (`allowUnsandboxedCommands: false`).

If you hit a sandbox denial, report it back to the user with the exact command and reason. Do not retry with the escape hatch.

---

## 7. Dependencies

Cargo dependencies require a one-line justification next to the line in `Cargo.toml`:

```toml
example-crate = "1.0"  # short reason this is the right choice for this project
```

After every dependency change, run `cargo audit` and `cargo deny check` locally and paste the output into the PR.

---

## 8. Commands you may run unprompted

Allow-listed in `.claude/settings.json`:

```
cargo check        cargo build       cargo test
cargo clippy -- -D warnings
cargo fmt --all -- --check
cargo audit        cargo nextest run
cargo tarpaulin --out Xml --workspace
./scripts/bootstrap.sh --check
./scripts/qa.sh run
./scripts/security.sh run
./scripts/eval.sh run
```

Require explicit permission:

```
cargo install ...    cargo update         cargo publish
git push             git merge            git rebase
gh pr ...
Edit ./Dockerfile    Edit ./.github/**
```

---

## 9. Naming

- Specs: `specs/NNN-<slug>.md`
- ADRs: `docs/architecture/NNN-<slug>-adr.md`
- Threat model: `docs/security/threat-model.md`
- Eval results: `evals/results/YYYY-MM-DD_<runner>_<model>.json`
- Commits: `chore(failing): …` → `feat(passing): …` → `refactor: …`
- Branch: `<TICKET-PREFIX>-<slug>`
