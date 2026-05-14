# Template — Jira Comment (Brainstorm output)

Plantilla para el **comentario en el ticket Jira** que contiene el output completo de Skill 01. La usa Skill 01 al cerrar Casos B y C.

> Pegar este markdown como comentario. Reemplazar `{...}`. No borrar secciones — todas son parte del contrato de Skill 01.

---

```markdown
## 🧠 Brainstorm output (Skill 01)

Refinamiento ejecutado: **{YYYY-MM-DD}** · Rol: **Product Manager** · Modelo: **Opus 4.7**

---

### 1. Resumen

{2-3 frases con el ticket reformulado tras el refinamiento.}

### 2. Acceptance Criteria refinados

- **AC01 — {nombre}:** {testable}. Tests: `{test_name_1}`, `{test_name_2}`.
- **AC02 — ...**
- **AC03 — ...**

### 3. Edge Cases identificados

- {edge case 1}
- {edge case 2}
- {...}

### 4. Out of Scope

- {qué queda explícitamente fuera}
- {...}

### 5. Threat Surface

| # | STRIDE | Threat | Mitigación |
|---|--------|--------|------------|
| T1 | {S/T/R/I/D/E} | {qué} | {mitigación o "🔴 deferred — bloqueante para prod"} |

(O "Ninguna superficie identificada" si aplica.)

### 6. Open Questions deferidas

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | {...} | {...} | {...} | {...} |

### 7. Persistencia ejecutada

- **Caso:** {A / B / C / D}
- **Acciones:**
  - {ej. Descripción del ticket actualizada con Resumen + AC}
  - {ej. Página Confluence creada en `<link>`}
  - {ej. Copia en `classifier-specs/brainstorms/KR-XXXXX-<slug>.md`}

### 8. Siguiente paso

**Skill 02 — Spec + Threat Model.** Modelo recomendado: Opus 4.7.

Para invocar Skill 02 en una conversación nueva:

> "Ejecutá Skill 02 sobre el brainstorm de {KR-XXXXX}. Repo del producto: {kriptos-io/...}"

La skill leerá este comentario y el archivo en `classifier-specs/brainstorms/` automáticamente.
```

---

## Notas para el agente que lo aplica

- Este comentario **no reemplaza** la descripción del ticket — la complementa. La descripción tiene `JIRA_STORY.md` (resumen ejecutivo + AC); el comentario tiene el brainstorm completo (con threat model, edge cases, todo).
- Si no hay connector con permisos de escritura: entregar este markdown al usuario para que pegue manualmente.
