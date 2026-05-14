# Template — Jira Epic

Plantilla para la **descripción** de un Epic en Jira. La usa Skill 01 en Caso A (idea cruda → Epic) y Caso D (Confluence → Epic con link).

> Reemplazar todo `{...}` con el valor real. Borrar secciones que no apliquen.

---

```markdown
## Resumen ejecutivo

{1-2 párrafos. Para quién es esto, qué problema resuelve, por qué ahora. Lenguaje narrativo, no técnico — esta sección la leen sponsors no técnicos.}

## Objetivos

- {objetivo de negocio 1, medible si es posible}
- {objetivo de negocio 2}
- {...}

## Success Metrics

| Métrica | Baseline actual | Target | Cómo se mide |
|---------|-----------------|--------|---------------|
| {ej. tiempo de procesamiento} | {valor} | {valor} | {dashboard/herramienta} |
| {ej. error rate} | {valor} | {valor} | {dashboard/herramienta} |

## Alcance

{Qué incluye este Epic — alto nivel, no tareas individuales.}

- {bloque de funcionalidad 1}
- {bloque de funcionalidad 2}
- {...}

## Out of Scope

- {qué se descarta explícitamente — anti scope creep a nivel iniciativa}
- {...}

## Stakeholders

- **Sponsor:** {nombre + rol}
- **Product owner:** {nombre}
- **Tech lead:** {nombre}
- **Equipos involucrados:** {lista}

## Tickets hijos

{Lista enlazada de Stories/Tasks que componen el Epic. Se va completando a medida que se refinan.}

- KR-XXXXX — {título corto}
- KR-XXXXX — {título corto}
- {...}

## Referencias

- **Confluence:** {link a la página de iniciativa si aplica — Caso A/D}
- **Brainstorm:** {link al archivo en classifier-specs/brainstorms/}
- **Documentos relacionados:** {Google Doc, presentación, etc.}

## Timeline / Hitos (opcional)

| Hito | Fecha objetivo | Estado |
|------|----------------|--------|
| {ej. POC validado} | {YYYY-MM-DD} | {pending / done} |
| {ej. Spec aprobada} | {YYYY-MM-DD} | {pending / done} |
| {ej. Production rollout} | {YYYY-MM-DD} | {pending / done} |
```

---

## Notas para el agente que lo aplica

- El Epic vive en Jira pero **siempre debe linkear a Confluence** si la iniciativa tiene página estratégica (Caso A o D).
- "Success Metrics" no es opcional — si no se puede medir, el Epic no tiene cierre claro. Si no hay métrica obvia, dejarlo como "Open question Q1" y pedirle al sponsor.
- "Tickets hijos" se actualiza conforme los Stories/Tasks se van creando. El agente puede dejar esa sección con "{a definir cuando los Stories se refinen}" inicialmente.
