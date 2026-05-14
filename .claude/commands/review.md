Ejecutá Skill 05 (Review + evals) sobre la branch actual del repo del producto. Contexto: $ARGUMENTS

Pasos:
1. Leé `skills/05-review-evals.md`.
2. Leé `roles/reviewer.md`.
3. Leé la spec correspondiente y `todo.md`.
4. Verificá:
   - Cada AC tiene test
   - Cada `feat:` tiene `chore: (failing)` precedente para la misma behavior
   - pytest verde con coverage ≥ 80%
   - ruff + mypy clean
   - Snyk / pip-audit sin vulnerabilidades high
   - Threat model: mitigaciones citadas existen
   - Evals (si aplican): no degradaron
5. Salida: report markdown completo con recomendación READY o BLOCKED.

Si encontrás un problema: REPORTÁLO, no lo fixees. El fix vuelve a Skill 04.
