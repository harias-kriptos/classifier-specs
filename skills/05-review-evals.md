# Skill 05: Review + Evals

Use this skill after Skill 04 finishes and before opening the human PR. Runs inside the product repo (Claude Code) or in CI.

**Recommended model:** Sonnet 4.6 (review needs reasoning, not Opus depth).

**Role:** Reviewer — see `roles/reviewer.md`

---

## Context loading

1. `roles/reviewer.md`
2. The approved spec `specs/NNN-<slug>.md`
3. The current branch diff (`git diff origin/main...HEAD`)
4. `todo.md` (all tasks should be checked)
5. `stacks/python-lambda/rules.md`

---

## Objective

Confirm that the implementation matches the spec and passes all gates before the human review starts. Catch issues a human reviewer shouldn't have to flag.

---

## Procedure

### 1. Spec compliance

For each AC in the spec:
- Is there at least one test asserting it?
- Does the test actually exercise the behavior (no tautological asserts)?

Report any AC without a corresponding test.

### 2. TDD trace

Check the commit log for the expected sequence per task:

```
chore: <behavior> (failing)
feat: <behavior> (passing)
refactor: <what>  (optional)
```

If a `feat:` commit has no preceding `chore: (failing)` for the same behavior, that's a violation. Report.

### 3. Quality gates

Run and verify all pass:

- `pytest --cov=src --cov-report=term-missing` — coverage ≥ 80%
- `ruff check` — clean
- `ruff format --check` — clean
- `mypy --strict src` — clean (or `mypy src` if --strict is too restrictive for the project)
- `pip-audit` or `snyk test` — no high/critical vulnerabilities

### 4. Threat model verification

If the spec had a threat model section:
- For each row in the STRIDE table, verify the mitigation cited (line of code or test) actually exists.
- Report any unverified mitigation.

### 5. Evals (if applicable)

If `evals/` exists and the spec changed LLM behavior, classifier output, or any non-deterministic component:
- Run `pytest evals/` or the eval runner.
- Compare score against `evals/results/baseline.json`.
- If score dropped, report BLOCKED — do not raise the baseline silently.
- If score improved, document the delta but do NOT raise the baseline in this PR (separate `eval: raise baseline` PR).

### 6. Limits of autonomy check

Report if any of these happened during implementation:
- Edits to `.github/workflows/`
- New dependencies added without justification in `pyproject.toml`
- Use of `# type: ignore` or `# noqa` (acceptable with comment justifying it)
- Tests edited to pass (compare commit history)

---

## Output

A review report (markdown), ready to paste into the PR description or `demo/.../05-review.md`:

```markdown
## Review report — Spec NNN: <slug>

### Spec compliance
- [x] AC01: test_<...> — pass
- [x] AC02: test_<...> — pass
...

### TDD trace
- [x] All `feat:` commits have a preceding `chore: (failing)`.

### Quality gates
- [x] pytest: <N> tests, <coverage>%
- [x] ruff: clean
- [x] mypy: clean
- [x] vulnerabilities: <N> low, 0 high

### Threat model
- [x] All STRIDE mitigations verified
- [ ] OR: <list unverified>

### Evals
- [ ] N/A
- [ ] OR: baseline <metric>=<value> → current <value>

### Recommendation
- READY for human review
- OR: BLOCKED — <reason>
```

---

## Operating rules

- Report problems, do not silently fix them. The agent does not get to "fix" lint or coverage at this stage — that would mean Skill 04 wasn't done.
- If something is borderline (coverage 79.5%), report it as is and let the human decide.
- The PR is not "done" until READY is the recommendation. BLOCKED means back to Skill 04.

**Siguiente paso:** human review + merge.
