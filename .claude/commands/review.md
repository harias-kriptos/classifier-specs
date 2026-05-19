Ejecutá Skill 05 (Review + evals) sobre la branch actual del repo del producto. Contexto: $ARGUMENTS

Pasos:
1. Leé `skills/05-review-evals.md` desde classifier-specs.
2. Leé `roles/reviewer.md` y `templates/PR_REVIEW_REPORT.md`.
3. Leé del repo del producto:
   - La spec correspondiente (`specs/NNN-*.md`)
   - `todo.md` (todas las tareas deben estar `[x]`)
   - **`tdd-trace.md` — source of truth del TDD**
   - Threat model si aplica
4. Verificá:
   - **Cada slice del `todo.md` tiene su entrada completa en `tdd-trace.md`** (Slice 0 con Setup/Verification; Slices 1+ con RED/GREEN/REFACTOR).
   - Cada AC del spec tiene al menos un test que la cubre.
   - pytest verde con coverage ≥ 80%.
   - ruff + mypy clean.
   - pip-audit sin vulnerabilidades high.
   - Threat model: mitigaciones citadas existen en código o test.
   - Evals (si aplican): no degradaron.
   - Sin `# type: ignore` o `# noqa` sin comentario justificando.
5. Salida: report markdown completo (formato `PR_REVIEW_REPORT.md`) con recomendación READY o BLOCKED.

**`tdd-trace.md` ausente o incompleto → BLOCKED automático.** Commits son informativos, no source of truth.

Si encontrás un problema: REPORTÁLO, no lo fixees. El fix vuelve a Skill 04.
