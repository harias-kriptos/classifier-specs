# Template — PR Review Report (pre-human)

Plantilla para el **reporte de review automático** que Skill 05 deja como comentario en el PR antes de pedir review humano. Si el reporte dice BLOCKED, el PR queda en draft y vuelve a Skill 04.

> Reemplazar `{...}`. Si una sección sale READY, dejar el checkbox `[x]`. Si sale BLOCKED, dejar el checkbox vacío y agregar detalle.

---

```markdown
## 🤖 Review report — Skill 05

Ejecutado: **{YYYY-MM-DD HH:MM UTC}** · Rol: **Reviewer** · Modelo: **Sonnet 4.6**

Spec: `specs/{NNN}-{slug}.md` · Branch: `{branch-name}` · Commit: `{SHA corto}`

---

### Spec compliance

Cada AC de la spec tiene al menos un test que lo asegura:

- [{x|/}] AC01 — {nombre} — test `{test_name}` — {status: ✅ pass / ❌ fail / ⚠️ no test found}
- [{x|/}] AC02 — ...
- [{x|/}] AC03 — ...

{Si algún AC no tiene test, listarlo acá explícitamente como "MISSING — escribir antes de pedir review humano".}

### TDD trace

- [{x|/}] Cada `feat: <behavior> (passing)` tiene un `chore: <behavior> (failing)` precedente para la misma behavior.
- [{x|/}] Ningún test fue **editado** para hacerlo pasar (verificación contra `git log -p tests/`).

{Si hay violaciones, listarlas con el commit SHA.}

### Quality gates

| Gate | Status | Detalle |
|------|--------|---------|
| pytest | {✅ / ❌} | {N} tests run, {N} passed, {N} failed |
| Coverage | {✅ / ❌} | {X}% (gate ≥ 80%) |
| ruff check | {✅ / ❌} | {detalle si hay issues} |
| ruff format --check | {✅ / ❌} | {detalle} |
| mypy --strict src | {✅ / ❌} | {detalle} |
| pip-audit / Snyk | {✅ / ❌} | {N} high, {N} medium, {N} low |
| SonarCloud | {✅ / ❌ / ⏳ pending} | quality gate {passed / failed} |

### Threat model verificado

{N/A si la spec no tiene threat model, o tabla:}

| # | STRIDE | Mitigación citada por spec | Verificado en código/test |
|---|--------|----------------------------|---------------------------|
| T1 | {category} | {qué} | {`test_name` o `src/{file}.py:LN` — o ⚠️ NOT FOUND} |

### Evals

- {N/A si la spec no tiene componente no-determinístico}
- {O: detalle del run de evals}

```
runner: {runner_name}
model: {model_name}
baseline.json:  precision={X}  recall={X}  f1={X}
this PR:        precision={X}  recall={X}  f1={X}
delta:          {+/-}{X}
```

{Si delta es negativo, marcar como BLOCKED. La baseline solo sube en un PR dedicado `eval: raise baseline to {metric}`.}

### Limits of autonomy check

- [{x|/}] Sin edits a `.github/workflows/`
- [{x|/}] Sin nuevas dependencias sin justificación en `pyproject.toml`
- [{x|/}] Sin `# type: ignore` o `# noqa` sin comentario justificando
- [{x|/}] Sin uso de `--no-verify`, `--force`, `--force-with-lease` en la historia
- [{x|/}] Tests no fueron editados para pasar (verificación por commit log)

### Recomendación

- [ ] **READY** — todos los checkboxes ✅. Listo para review humano.
- [ ] **BLOCKED** — al menos un checkbox fallido. Vuelve a Skill 04 antes de pedir review humano.

#### Detalle BLOCKED (si aplica)

{Lista concreta de qué falló y qué hay que hacer para pasar a READY.}

- {ej. "AC04 no tiene test correspondiente — escribir `test_handler_rejects_unknown_fields` antes de pedir review."}
- {...}

### Siguiente paso

- Si READY → pedir review humano + cambiar PR de draft a "Ready for review" + transition de Jira: `In Review` → `Ready to merge` cuando se aprueba.
- Si BLOCKED → invocar Skill 04 para corregir los items listados.
```

---

## Notas para el agente que lo aplica

- Este reporte va como **comentario en el PR**, no en Jira. Jira recibe solo el `JIRA_MERGE_COMMENT.md` cuando todo está verde.
- Si el reporte es BLOCKED, el agente **NO** debe "arreglar" los issues silenciosamente — debe reportarlos y dejar que Skill 04 los resuelva. Esa separación de responsabilidades es lo que mantiene el TDD honesto.
- Para que el reporte sea verificable, todos los `✅` deben citar el comando exacto que se corrió o el archivo donde está la evidencia.
