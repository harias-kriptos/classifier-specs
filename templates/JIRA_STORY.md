# Template — Jira Story / Task

Plantilla para la **descripción** de un Story o Task técnico en Jira. La usan Skill 01 (al crear/actualizar el ticket) y Skill 02 (al cerrar el ticket con la spec).

> Reemplazar todo `{...}` con el valor real. Borrar las secciones que no apliquen.

---

```markdown
## Resumen

{1-3 oraciones describiendo qué cambia para el usuario o el sistema cuando este ticket se termine. Sin jerga interna innecesaria.}

## Acceptance Criteria

- **AC01 — {nombre corto}:** {comportamiento testable}. Test: `{test_name}`.
- **AC02 — {nombre corto}:** {comportamiento testable}. Test: `{test_name}`.
- **AC03 — ...**

## Edge Cases

- {input vacío, límites de tamaño, race conditions, dependencias caídas, etc.}
- {...}

## Out of Scope

- {qué deliberadamente NO se hace en este ticket — anti scope creep}
- {...}

## Threat Surface

- **{T1 — STRIDE category}:** {qué riesgo}. Mitigación: {test/código que lo cubre, o "🔴 deferred → bloqueante para deploy a prod"}.
- {O "ninguna — no hay surface en este ticket" si aplica}

## Open Questions

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | {...} | {persona/equipo} | {asunción temporal} | {merge / deploy / nada} |

## Referencias

- **Brainstorm:** {link al archivo en classifier-specs/brainstorms/ o al comentario Jira con el output completo}
- **Épica:** {KR-XXXXX o "n/a"}
- **Confluence:** {link o "n/a"}
- **Spec técnica:** {link al PR o archivo en el repo del producto — agregado por Skill 02}
- **MR/PR de implementación:** {link — agregado por Skill 04}

## Definition of Done

- [ ] Spec en `specs/NNN-*.md` mergeada al repo del producto
- [ ] Tests cubren cada AC (RED → GREEN → REFACTOR en commits separados)
- [ ] `pytest --cov=src` ≥ 80%
- [ ] `ruff check` + `ruff format --check` clean
- [ ] `mypy --strict src` clean
- [ ] Snyk + SonarCloud verdes en CI
- [ ] Threat model verificado (cada mitigación con test/código que la enforza)
- [ ] PR aprobado por al menos 1 reviewer humano
```

---

## Notas para el agente que lo aplica

- Si la skill que lo invoca no tiene Atlassian connector con permisos de escritura, entregar este markdown listo para que el usuario lo pegue en la descripción del ticket.
- Los placeholders `{...}` deben quedar reemplazados; si una sección no aplica, **borrar la sección completa**, no dejar el placeholder.
- El bloque "Referencias" se va completando entre skills — Skill 01 lo arranca, Skill 02 agrega spec, Skill 04 agrega MR.
