# Skill 04: TDD Implementation

Use this skill **inside the product repository** (Claude Code, not Claude Web) once the plan (Skill 03) is committed.

**Recommended model:** modelo barato (Qwen / DeepSeek / Devstral vía OpenCode/Crush). Razón: este paso quema tokens en loop; Opus es desperdicio acá.

**Role:** Developer — see `roles/developer.md`

---

## Context loading

1. `roles/developer.md`
2. The approved spec at `specs/NNN-<slug>.md` (in the product repo)
3. `todo.md` at the repo root
4. `stacks/python-lambda/rules.md` (desde classifier-specs via filesystem)
5. `templates/TDD_TRACE_TEMPLATE.md` (estructura del trace a generar)
6. `tdd-trace.md` en raíz del repo del producto (si no existe, crearlo desde el template; si existe, append)

---

## Objective

Execute the `todo.md` task by task. Each task is a TDD cycle: RED → GREEN → REFACTOR.

**Source of truth del TDD: `tdd-trace.md` en la raíz del repo del producto.** Por cada slice, el agente registra en este archivo:

1. El test que escribió (RED) + output literal del pytest fallando.
2. La implementación mínima (GREEN) + output del pytest pasando + ruff + mypy clean.
3. El refactor (si aplica) + output verde.

**Commits son opcionales.** El dev decide cómo separa: 1 commit por slice, 1 commit por par RED/GREEN, o un único squash al final. Lo que importa es que `tdd-trace.md` quede completo y honesto — eso es lo que Skill 05 audita.

**Por qué `tdd-trace.md` y no git history:**
- Lo escribe el agente mientras ejecuta, no se reconstruye después.
- Captura el output literal del pytest (failing vs passing).
- Es legible por humanos en una pasada.
- No depende de la disciplina del dev en separar commits.

---

## Procedure per task

**Antes de empezar:** si `tdd-trace.md` no existe en raíz del repo del producto, crearlo copiando `templates/TDD_TRACE_TEMPLATE.md` y llenando el bloque "Resumen" (ticket, spec, modelo, started timestamp).

Por cada slice del `todo.md`:

1. Leer la próxima tarea unchecked en `todo.md`.

2. **Append a `tdd-trace.md`** un header de slice nuevo:
   ```
   ## Slice N: <behavior>
   **Started:** <timestamp>
   ```

3. **Si la tarea es Slice 0 — Scaffold** (única excepción al TDD strict):
   - No hay RED. Setup de proyecto no es behavior testable.
   - Ejecutar los sub-pasos del Slice 0 (crear `pyproject.toml`, layout `src/`, `handler.py` stub, `tests/__init__.py`).
   - Correr `pytest` final — debe retornar exit 0.
   - **Append a `tdd-trace.md`:**
     ```
     ### Setup
     - Listed files created
     ### Verification
     - pytest output (exit 0)
     ### Slice complete: <timestamp> (<duration>)
     ```
   - Marcar Slice 0 como `[x]` en `todo.md`.
   - (Opcional) commit: `chore: scaffold python lambda project`.
   - Si algo falla → BLOCKED.

4. **Para Slices 1+ (TDD strict):**

   **RED:**
   - Escribir el test en `tests/test_<module>.py`.
   - Correr `pytest --tb=short`.
   - Confirmar que FALLA por la razón esperada.
   - **Append a `tdd-trace.md`:**
     ```
     ### RED
     - **Test added:** `tests/<file>::<test_name>`
     - **pytest output (failing as expected):**
     ```
     <output literal del pytest>
     ```
     - **✅ El test falla por la razón correcta.**
     ```
   - (Opcional) commit: `chore: <behavior> (failing)`.

   **GREEN:**
   - Implementar el mínimo código en `src/<module>.py` para que pase.
   - Correr `pytest`, confirmar GREEN.
   - Correr `ruff check && mypy --strict src` — fix any issues.
   - **Append a `tdd-trace.md`:**
     ```
     ### GREEN
     - **Implementation:** `src/<path>`
     - **pytest output:** <X passed in Y.YYs>
     - **ruff check:** clean
     - **mypy --strict src:** clean
     ```
   - (Opcional) commit: `feat: <behavior> (passing)`.

   **REFACTOR (solo si hay cleanup):**
   - Mejorar calidad sin cambiar tests.
   - Correr `pytest` — debe seguir verde.
   - **Append a `tdd-trace.md`:**
     ```
     ### REFACTOR
     - **Cleanup:** <descripción>
     - **pytest output (still passing):** <output>
     ```
   - (Opcional) commit: `refactor: <what>`.

   **Si no hay refactor:** append `### REFACTOR\nskipped`.

5. **Append a `tdd-trace.md`:**
   ```
   **Slice complete:** <timestamp> (<duration>)
   ---
   ```

6. Marcar la tarea `[x]` en `todo.md`.

**Después de la última slice:** append el bloque "Resumen final" del template — coverage, gates, slices ejecutadas, duration total.

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
