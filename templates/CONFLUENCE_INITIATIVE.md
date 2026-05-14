# Template — Confluence Initiative Page

Plantilla para la **página Confluence** que documenta una iniciativa estratégica. La usa Skill 01 en Caso A (idea cruda traída por CEO/Producto/Comercial) y Caso D (página draft refinada).

> Reemplazar `{...}`. Borrar secciones que no apliquen. Esta página es la **fuente de verdad de negocio** — los Epics Jira que salgan de acá linkean siempre acá.

---

```markdown
# {Título de la iniciativa}

> **Owner:** {nombre + rol}
> **Sponsor:** {nombre + rol}
> **Estado:** Discovery | Refinement | In Delivery | Live | On Hold | Cancelled
> **Creada:** {YYYY-MM-DD}
> **Última actualización:** {YYYY-MM-DD}

---

## TL;DR

{2-3 frases que cualquiera del equipo puede leer en 30 segundos y entender qué es esto, para quién, y por qué ahora.}

---

## Contexto y motivación

{¿Qué situación motivó esta iniciativa? ¿Qué cambió en el negocio, los clientes, el mercado, la tecnología?}

{¿Qué pasa si NO hacemos esto? Costo de oportunidad.}

---

## Problema a resolver

{Descripción concreta del problema. Para quién es problema. Cómo lo viven hoy. Métricas si las hay.}

---

## Propuesta

{Qué proponemos hacer. Alto nivel, no detalle técnico. El "qué", no el "cómo".}

### Principios de diseño

- {ej. "El cliente nunca espera más de 5s por la respuesta"}
- {ej. "Compatible con clientes existentes sin migración"}
- {...}

---

## Alcance

{Qué entra en esta iniciativa.}

### Incluye

- {bloque 1}
- {bloque 2}

### NO incluye (out of scope)

- {qué deliberadamente NO hacemos — anti scope creep estratégico}
- {...}

---

## Métricas de éxito

| Métrica | Baseline | Target | Cómo se mide |
|---------|----------|--------|---------------|
| {ej. tiempo de procesamiento} | {valor actual} | {valor objetivo} | {dashboard / instrumento} |
| {ej. adopción} | {valor} | {valor} | {herramienta} |
| {ej. costo por scan} | {valor USD} | {valor USD} | {cost explorer} |

---

## Stakeholders

| Rol | Persona | Responsabilidad |
|-----|---------|------------------|
| Owner | {nombre} | {qué decide} |
| Sponsor ejecutivo | {nombre} | {qué aprueba} |
| Tech Lead | {nombre} | {arquitectura} |
| Product | {nombre} | {priorización} |
| Equipos colaboradores | {lista} | {qué entregan} |

---

## Plan de delivery (alto nivel)

{Hitos, no tareas individuales. Las tareas viven en Jira.}

| Fase | Entregable | Fecha objetivo | Estado |
|------|------------|----------------|--------|
| 1 — Discovery | {ej. POC validado} | {YYYY-MM-DD} | {} |
| 2 — Refinement | {ej. Specs y tickets listos} | {YYYY-MM-DD} | {} |
| 3 — Build | {ej. MVP funcional} | {YYYY-MM-DD} | {} |
| 4 — Rollout | {ej. Production GA} | {YYYY-MM-DD} | {} |

---

## Decisiones tomadas

| Fecha | Decisión | Por qué | Impacto |
|-------|----------|---------|---------|
| {YYYY-MM-DD} | {decisión} | {motivación} | {qué cambia} |

---

## Open questions

| # | Pregunta | Owner | Bloqueante para |
|---|----------|-------|-----------------|
| Q1 | {...} | {...} | {fase X} |

---

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| {ej. dependencia externa atrasa} | media | alto | {plan B} |

---

## Tickets Jira asociados

> Se actualiza conforme los Epics y Stories se crean.

- **Epic:** {KT-XXXXX} — {título}
- **Stories en flight:** {lista}

---

## Referencias

- **Brainstorm origen:** {link al archivo classifier-specs/brainstorms/<slug>.md}
- **Documentos relacionados:** {Google Docs, presentaciones, papers, otros Confluence}
- **Conversaciones / decisiones grabadas:** {ej. retro, comité estratégico}
```

---

## Notas para el agente que lo aplica

- Esta página es para **stakeholders no técnicos** primero. Lenguaje narrativo, sin jerga. Detalle técnico vive en specs del repo del producto.
- "Estado" se actualiza cada vez que la iniciativa cambia de fase — el agente debe mantener esa línea fresca.
- "Tickets Jira asociados" se va llenando a medida que Skill 01 crea Epics y Skill 02 crea Stories. El link es bidireccional: Epic Jira → esta página, esta página → Epic Jira.
- Si la página ya existía (Caso D), el agente la **actualiza** preservando la historia (sección "Decisiones tomadas" + última fecha de update), no la sobrescribe.
