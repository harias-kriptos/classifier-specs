Ejecutá Skill 04 (TDD Implementation) dentro del repo del producto. Tarea(s) objetivo: $ARGUMENTS

Pre-requisitos:
- Estás en el repo del producto (no en classifier-specs).
- `specs/NNN-<slug>.md` existe y está commiteado.
- `todo.md` existe en la raíz.

Pasos:
1. Leé `skills/04-tdd-implementation.md` desde classifier-specs (path absoluto si está clonado en `~/`).
2. Leé `roles/developer.md` y `templates/TDD_TRACE_TEMPLATE.md`.
3. Leé la spec y `todo.md` del repo del producto.
4. **Si `tdd-trace.md` no existe en raíz del repo, crearlo desde el template.**
5. Para cada tarea unchecked en `todo.md`:
   a. **Append a `tdd-trace.md`** un header de slice nuevo con timestamp.
   b. RED — escribí test, corré pytest. **Append output literal a `tdd-trace.md` bajo `### RED`**.
   c. GREEN — implementación mínima, corré pytest + ruff + mypy. **Append output literal a `tdd-trace.md` bajo `### GREEN`**.
   d. REFACTOR (opcional) — cleanup, pytest verde. **Append a `tdd-trace.md` bajo `### REFACTOR`** (o "skipped" si no aplica).
   e. **Append `**Slice complete:** <timestamp> (<duration>)`** y separador `---`.
   f. Marcá la tarea `[x]` en `todo.md`.
   g. (Opcional) commit — squash al final, por slice, o granular. Decisión del dev.
6. Si 3 intentos fallan en una tarea, parar y reportar BLOCKED en `tdd-trace.md`.
7. Al terminar todas las slices, append el bloque "Resumen final" del template (coverage, gates, total duration).

**Source of truth del TDD: `tdd-trace.md`**, no los commits. Skill 05 lo audita.

Limits of autonomy: respetá los listados en `skills/04-tdd-implementation.md`. No pushees a main, no instales deps, no toques workflows.
