# Template — Jira Comment (Merge / Done)

Plantilla para el **comentario final** en el ticket Jira cuando el PR pasó review y está listo para merge (o ya mergeado). La usa Skill 05.

> Pegar este markdown como comentario. Reemplazar `{...}`. Cambiar transition del ticket cuando aplique.

---

```markdown
## ✅ Listo para merge / Mergeado (Skill 05)

Review ejecutado: **{YYYY-MM-DD}** · Rol: **Reviewer** · Modelo: **Sonnet 4.6**

---

### Implementación

- **PR/MR:** {link} — `{branch-name}`
- **Commit final:** {SHA corto}
- **Repo:** `{kriptos-io/...}`

### Quality gates

| Gate | Resultado |
|------|-----------|
| pytest | ✅ {N} tests, todos pasando |
| Coverage | ✅ {X}% (gate ≥ 80%) |
| ruff check | ✅ clean |
| ruff format --check | ✅ clean |
| mypy --strict src | ✅ clean |
| Snyk / pip-audit | ✅ 0 high, {N} low |
| SonarCloud | ✅ quality gate passed |

### Spec compliance

- ✅ AC01: cubierto por `{test_name}`
- ✅ AC02: cubierto por `{test_name}`
- ✅ AC03: cubierto por `{test_name}`
- ✅ AC04: cubierto por `{test_name}`
- ✅ AC05: cubierto por `{test_name}`
- ✅ AC06: cubierto por `{test_name}`

### TDD trace

- ✅ Cada `feat: <behavior> (passing)` tiene un `chore: <behavior> (failing)` precedente.
- ✅ Ningún test fue editado para pasar después de fallar.

### Threat model verificado

| # | Mitigación | Verificado en |
|---|------------|---------------|
| T1 | {qué la enforza} | {`test_name` o `src/file.py:LN`} |
| T2 | {...} | {...} |

### Evals

- {N/A si no aplica}
- {O: "baseline F1 = 0.92 → current F1 = 0.93. No degradación."}

### Bloqueantes residuales para producción

- {ej. Q1 (auth) — no se cierra en este PR, requiere ticket aparte antes de deploy a prod}
- {O: "Ninguno — listo para deploy"}

### Próximos pasos

1. Merge del PR a `{rama base}`.
2. {Deploy automático / manual / espera siguiente release}.
3. {Si aplica: monitorear `{métrica}` durante {N} horas post-deploy.}
4. Cerrar ticket Jira (transition: `Ready to merge` → `Done`).
```

---

## Notas para el agente que lo aplica

- Si el review encontró BLOCKED en cualquier sección, **no usar este template** — usar el reporte de review pre-humano (`PR_REVIEW_REPORT.md`). Este template es solo para cuando todo está verde.
- "Bloqueantes residuales para producción" no impide el merge a `main`; solo es nota para el deploy operativo (cuándo se promociona la build a entornos productivos).
