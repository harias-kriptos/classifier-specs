# Template — PR / MR Description

Plantilla para la **descripción del Pull/Merge Request** cuando se abre tras implementar una spec. La usa Skill 04 al final del loop TDD.

> Reemplazar `{...}`. No borrar secciones — la CI puede chequear que estén presentes.

---

```markdown
## Tipo de cambio

- [ ] feat — nueva funcionalidad
- [ ] fix — bug fix
- [ ] refactor — sin cambio de comportamiento
- [ ] docs — solo documentación
- [ ] test — solo tests
- [ ] chore — infra, configuración
- [ ] perf — mejora de performance
- [ ] eval — cambio de baseline de evals

## Resumen

{2-3 frases describiendo qué hace este PR. Lo que un reviewer debería saber antes de mirar el diff.}

## Spec implementada

- **Archivo:** `specs/{NNN}-{slug}.md`
- **Ticket Jira:** {KR-XXXXX}
- **Brainstorm:** {link al archivo en classifier-specs/brainstorms/ — opcional}

## Acceptance Criteria cubiertos

- [x] AC01 — {nombre} — test `{test_name}`
- [x] AC02 — {nombre} — test `{test_name}`
- [x] AC03 — {nombre} — test `{test_name}`
- ...

## TDD trace

Cada AC tiene su par de commits RED → GREEN. Verificable con `git log --oneline`:

```
chore: spec for {feature} ({KR-XXXXX})
chore: {AC01 behavior} (failing)
feat: {AC01 behavior} (passing)
chore: {AC02 behavior} (failing)
feat: {AC02 behavior} (passing)
refactor: {what} (opcional)
...
```

## Quality gates (deben estar verdes antes de pedir review humano)

- [ ] `pytest --cov=src` — todos verdes, coverage ≥ 80%
- [ ] `ruff check` — clean
- [ ] `ruff format --check` — clean
- [ ] `mypy --strict src` — clean
- [ ] `pip-audit` o Snyk — 0 vulnerabilidades high/critical
- [ ] SonarCloud — quality gate passed
- [ ] Threat model verificado (si aplica) — cada mitigación con test/código que la enforza

## Threat model verificado

{N/A si no hay surface, sino tabla:}

| # | STRIDE | Mitigación | Test / código |
|---|--------|------------|----------------|
| T1 | {S/T/R/I/D/E} | {qué} | `{test_name}` o `src/{file}.py:{LN}` |

## Notas para el reviewer

{Lo que NO es obvio del diff. Decisiones tomadas, alternativas evaluadas, partes con las que hay que tener cuidado.}

## Breaking changes

- [ ] No introduce breaking changes
- [ ] Sí — {descripción + plan de migración}

## Deployment notes

{Si requiere variables de entorno nuevas, migraciones, configuración en consola AWS, etc. Si nada → "Sin acciones manuales requeridas."}

## Bloqueantes residuales para producción

- {ej. Q1 (auth) — no se cierra acá, requiere ticket aparte antes de deploy a prod}
- {O: "Ninguno — mergear a `main` habilita el flujo de deploy controlado por CI."}

## Checklist (autor)

- [ ] El PR linkea a la spec (`specs/{NNN}-*.md`).
- [ ] El PR linkea al ticket Jira (`{KR-XXXXX}`).
- [ ] Conventional commits en toda la historia del branch.
- [ ] CI verde en este commit (no en commits anteriores).
- [ ] Si hubo cambios en `pyproject.toml` (deps), `pip-audit` corrió limpio.
- [ ] Si hubo gaps de contexto detectados por Skill 02, el PR a `classifier-specs/` ya está mergeado.
```

---

## Notas para el agente que lo aplica

- Si Skill 05 corre antes del PR (cosa que hace), las quality gates ya están todas verdes. Skill 04 marca todos los checkboxes con `[x]` confiando en el output de Skill 05.
- Si algún checkbox queda en `[ ]`, el PR queda en **draft** y no se pide review humano hasta resolverlo.
