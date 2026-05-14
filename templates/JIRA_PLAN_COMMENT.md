# Template — Jira Comment (Plan output)

Plantilla para el **comentario en el ticket Jira** que contiene el output de Skill 03 (Plan). Sucede después de que la spec ya está commiteada en el repo del producto.

> Pegar este markdown como comentario. Reemplazar `{...}`.

---

```markdown
## 📋 Plan de implementación (Skill 03)

Plan generado: **{YYYY-MM-DD}** · Rol: **Tech Lead** · Modelo: **Sonnet 4.6**

---

### Spec base

- **Archivo:** `specs/{NNN}-{slug}.md` en `{repo del producto}`
- **PR de la spec:** {link al PR — opcional si la spec fue mergeada a `main` sin PR separado}

### Resumen del plan

{1-3 frases describiendo cómo se va a partir el trabajo en slices.}

### Slices verticales (TDD)

Cada slice = una tarea atómica con RED → GREEN → REFACTOR.

| # | Slice | Tests planificados | Archivos impactados |
|---|-------|--------------------|--------------------|
| 1 | {nombre} | `{test_name_1}`, `{test_name_2}` | `src/{path}.py`, `tests/{path}.py` |
| 2 | {nombre} | `{test_name}` | `src/{path}.py` |
| ... | | | |

### Estimación

- **Slices totales:** {N}
- **Esfuerzo estimado:** {horas/días}
- **Confianza:** {alta / media / baja — alta solo si todos los AC tienen tests claros}

### Dependencias bloqueantes

- {Q1 del brainstorm si aplica — ej. "Auth pendiente, no bloquea desarrollo solo deploy"}
- {dependencia externa — ej. "Bedrock keywords subidas — requerido para slice N"}

### Riesgos técnicos detectados

- {ej. "AC05 requiere log_does_not_include_raw_body — implementación cuidadosa para no romper observabilidad"}
- {...}

### Archivo

`todo.md` commiteado en `{repo del producto}` con el detalle por slice.

### Siguiente paso

**Skill 04 — TDD Implementation.** Modelo recomendado: Sonnet 4.6 (o modelo barato vía OpenCode/Crush para el loop).

Para invocar Skill 04 en Claude Code:

> `/implement` desde la raíz del repo del producto.

La skill leerá `specs/{NNN}-*.md` y `todo.md` automáticamente.
```

---

## Notas para el agente que lo aplica

- El plan NO es la spec — el plan dice "cómo lo voy a hacer en pasos atómicos", la spec dice "qué debe hacer". No duplicar contenido entre ambos.
- Si el plan tiene > 10 slices, la spec es demasiado grande. Volver a Skill 02 para partirla en specs más chicas.
