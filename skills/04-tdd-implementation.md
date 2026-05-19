# Skill 04: TDD Implementation

Use this skill **inside the product repository** (Claude Code, not Claude Web) once the plan (Skill 03) is committed.

**Recommended model:** modelo barato (Qwen / DeepSeek / Devstral vía OpenCode/Crush). Razón: este paso quema tokens en loop; Opus es desperdicio acá.

**Role:** Developer — see `roles/developer.md`

---

## Context loading

1. `roles/developer.md`
2. The approved spec at `specs/NNN-<slug>.md` (in the product repo)
3. `todo.md` at the repo root
4. `stacks/python-lambda/rules.md` (from this repo via filesystem or pasted into the conversation)

---

## Objective

Execute the `todo.md` task by task. Each task is a TDD cycle:

1. **RED** — write the failing test. Commit: `chore: <behavior> (failing)`.
2. **GREEN** — minimal implementation. Commit: `feat: <behavior> (passing)`.
3. **REFACTOR** (if needed) — cleanup. Commit: `refactor: <what>`.

The commit sequence is enforced by commitlint in CI. Skipping RED breaks the build.

---

## Procedure per task

1. Read the next unchecked task in `todo.md`.

2. **Si la tarea es Slice 0 — Scaffold** (única excepción al TDD strict):
   - No hay RED. Setup de proyecto no es behavior testable.
   - Ejecutar los sub-pasos del Slice 0 tal como están en el `todo.md` (crear `pyproject.toml`, layout `src/`, `handler.py` stub, `tests/__init__.py`).
   - Correr `pytest` final — debe retornar exit 0 (incluso con 0 tests).
   - **Commit único:** `chore: scaffold python lambda project`.
   - Marcar Slice 0 como `[x]` y pasar a Slice 1.
   - Si algo falla en el scaffold → BLOCKED. No improvisar.

3. **Para las Slices 1+ (TDD strict):**
   - RED:
     - Write the test in `tests/test_<module>.py`.
     - Run `pytest` — confirm it FAILS for the expected reason.
     - Commit: `chore: <behavior> (failing)`.
   - GREEN:
     - Implement the minimum code in `src/<module>.py` to make the test pass.
     - Run `pytest` — confirm GREEN.
     - Run `ruff check && mypy src` — fix any issues.
     - Commit: `feat: <behavior> (passing)`.
   - REFACTOR (only if there's cleanup):
     - Improve code quality without changing tests.
     - Run `pytest` again — must stay green.
     - Commit: `refactor: <what>`.
   - Mark task `[x]` in `todo.md`.

---

## Failure handling

- After 3 failed attempts on RED → GREEN, stop and report **BLOCKED: <reason>**. Do not improvise.
- If a test seems wrong, do NOT rewrite it. Report BLOCKED and ask the user.
- If the spec is ambiguous mid-task, stop and ask. Do not invent.

---

## Limits of autonomy

The agent MUST NOT do any of these without explicit user approval:

- Push directly to `main`.
- Merge a PR.
- Install a new dependency.
- Modify CI workflows.
- Modify branch protection.
- Disable a hook or scanner.
- Use `--no-verify`, `--force`, `--force-with-lease`.
- Edit a test to make it pass (must fix the implementation instead).
- Decide scope or behavior beyond what the spec says.

---

## Output

When `todo.md` is fully checked:

1. Run `pytest --cov=src --cov-report=term`.
2. Run `ruff check && mypy src`.
3. Report: tests passed, coverage %, lint clean, ready for Skill 05.

### PR creation

Cuando el branch está listo:

- **Descripción del PR:** usar `templates/PR_DESCRIPTION.md` como plantilla. Completar todos los checkboxes y placeholders antes de pedir review humano.
- **Transition Jira:** mover el ticket de `Spec ready` → `In Review` (o equivalente del workflow). Si hay Atlassian connector con escritura, ejecutar con confirmación; sino, entregar al usuario los pasos manuales.

**Siguiente paso:** Skill 05 — Review + evals.

If coverage < 80%, add missing tests and re-run before declaring done. **No abrir PR sin coverage gate verde.**
