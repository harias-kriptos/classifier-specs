# Skill 05: Review + Evals

Use this skill after Skill 04 finishes and before opening the human PR. Runs inside the product repo (Claude Code) or in CI.

**Recommended model:** Sonnet 4.6 (review needs reasoning, not Opus depth).

**Role:** Reviewer — see `roles/reviewer.md`

---

## Context loading

1. `roles/reviewer.md`
2. The approved spec `specs/NNN-<slug>.md`
3. **`tdd-trace.md`** en raíz del repo del producto — **source of truth del TDD**.
4. The current branch diff (`git diff origin/main...HEAD`) — informativo, no source of truth.
5. `todo.md` (todas las tareas deben estar `[x]`)
6. `stacks/python-lambda/rules.md`

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

**Source of truth: `tdd-trace.md`** en raíz del repo del producto. Skill 04 lo escribe mientras ejecuta. Si no existe, el flujo se rompió y es BLOCKED automático.

Para cada slice listada en `todo.md`, verificar en `tdd-trace.md`:

- ¿Tiene sección `## Slice N: <behavior>`?
- ¿Tiene `### RED` con output literal del pytest fallando?
- ¿Tiene `### GREEN` con output literal del pytest pasando + ruff clean + mypy clean?
- ¿Tiene `### REFACTOR` (aunque sea "skipped")?
- ¿Tiene `**Slice complete:** <timestamp>`?

**Slice 0 (Scaffold)** es la única excepción: no tiene RED, solo `### Setup` y `### Verification`.

Si alguna slice del `todo.md` está marcada `[x]` pero falta su entrada en `tdd-trace.md` → **BLOCKED**.

Si una entrada tiene `### GREEN` sin `### RED` previo → **BLOCKED** (excepto Slice 0).

**Commits son informativos, no source of truth.** El dev puede haber hecho squash, commits por slice, o no commitear hasta el final — eso es decisión del dev. Lo que importa es que `tdd-trace.md` esté completo y honesto.

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

Reportar si alguno de estos ocurrió durante implementación:
- Edits a `.github/workflows/` o branch protection.
- Nuevas dependencias agregadas sin justificación en `pyproject.toml`.
- `# type: ignore` o `# noqa` **sin comentario inline justificando**.
- Tests editados para hacerlos pasar (cruzar contra `tdd-trace.md` — si una slice tenía un test escrito en RED y después aparece modificado en GREEN sin que el behavior haya cambiado, es violación).
- Uso de `--no-verify`, `--force`, `--force-with-lease` en git.

---

## Output

Dos artefactos según el resultado:

### Si READY

1. **Comentario en el PR** con el review report — usar `templates/PR_REVIEW_REPORT.md`. Marca todos los checkboxes como `[x]` y recomendación = READY.
2. **Comentario en Jira** — usar `templates/JIRA_MERGE_COMMENT.md`. Lista quality gates verdes, AC cubiertos, bloqueantes residuales para producción.
3. **Transition Jira:** `In Review` → `Ready to merge` (con confirmación del usuario).
4. Cambiar el PR de draft a "Ready for review" si estaba en draft.

### Si BLOCKED

1. **Comentario en el PR** con el review report — usar `templates/PR_REVIEW_REPORT.md`. Recomendación = BLOCKED, con la lista concreta de qué falló y cómo arreglarlo.
2. **NO** actualizar Jira (el ticket queda en `In Review`).
3. **NO** sacar el PR de draft.
4. Indicar al usuario: invocar Skill 04 para corregir los items listados.

---

## Operating rules

- Report problems, do not silently fix them. The agent does not get to "fix" lint or coverage at this stage — that would mean Skill 04 wasn't done.
- If something is borderline (coverage 79.5%), report it as is and let the human decide.
- The PR is not "done" until READY is the recommendation. BLOCKED means back to Skill 04.

**Siguiente paso si READY:** human review + merge.
**Siguiente paso si BLOCKED:** Skill 04 para resolver los items listados.
