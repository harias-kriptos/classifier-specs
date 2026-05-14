# Demo — Ticket 1: `tree-url-generator`

Esta carpeta contiene los outputs del flujo de 5 pasos aplicado al **Ticket 1** del Classifier v2, como caso piloto del framework de IA de Kriptos.

---

## Por qué este ticket

- **Autocontenido** — cero dependencias de cajas negras (Signal Handler, Anonymizer, LLM, KEM).
- **5 AC bien definidos** ya escritos a mano en `v2/tickets-implementacion.md`. Sirve de "before" para comparar contra la spec generada por agentes.
- **Threat surface real** — expone API pública, firma pre-signed URLs S3, valida input no confiable. Permite ejercitar el threat model del Paso 2.
- **Pequeño pero no trivial** — una Lambda con parseo de body, sanitización, generación UUID, firma S3 con headers, manejo de errores. Suficiente para que el flujo *muestre* algo sin gastar horas.
- **Python Lambda** — patrón replicable inmediatamente a los Tickets 2, 3, 5, 6, 7…

---

## Estructura esperada de outputs

```
ticket-1-tree-url-generator/
├── README.md                       (este archivo)
├── 01-brainstorm-output.md         (output de Skill 01 — Paso 1)
├── 02-spec.md                      (output de Skill 02 — Paso 2, va a `specs/001-*.md` del repo del producto)
├── 02-threat-model.md              (output de Skill 02 si aplica)
├── 03-plan.md                      (output de Skill 03 — Paso 3, va a `todo.md` del repo del producto)
└── 04-05-implementation-log.md     (resumen de Pasos 4 y 5 si se ejecutan)
```

Los Pasos 1-2 son los que ejecutamos esta noche para tener algo presentable al equipo. Pasos 3-5 son bonus.

---

## Cómo se ejecuta la demo

### Paso 1 — Brainstorm (Claude Web, Opus 4.7)

1. Abrir el Proyecto de Claude Web configurado con `CLAUDE_PROJECT.md`.
2. Prompt:
   > "Quiero hacer brainstorm sobre el Ticket 1 del Classifier v2 — `tree-url-generator`. Lee el ticket desde `context/classifier-v2/tickets-source.md` y el body completo en `/Users/harias25/kriptos-classifier-v2-spec/v2/tickets-implementacion.md` sección Ticket 1. Ejecutá Skill 01 — brainstorm."
3. Conversar hasta que el exit checklist de Skill 01 sea verdadero.
4. Pedir el resumen estructurado.
5. Guardar el resumen como `01-brainstorm-output.md` en esta carpeta.

### Paso 2 — Spec + threat model (Claude Web, Opus 4.7)

1. **Misma conversación NO** — abrir una conversación nueva (regla: una skill por conversación).
2. Prompt:
   > "Genera la spec para Ticket 1 — `tree-url-generator`. Ejecutá Skill 02. Acá está el output del brainstorm: [pegar contenido de `01-brainstorm-output.md`]"
3. Recibir spec markdown completa (estructura de `templates/SPEC_TEMPLATE.md`).
4. Recibir threat model si Skill 01 identificó surface.
5. Guardar como `02-spec.md` y `02-threat-model.md`.

### Pasos 3-5 — Plan, TDD, Review (opcional para esta noche)

Vienen después. Requieren:
- Repo nuevo del producto con `kriptos-python-template` aplicado.
- Claude Code corriendo en ese repo.
- Hooks Python equivalentes a los del `kriptos-rust-template`.

---

## Qué medimos para validar el piloto

| Métrica | Valor objetivo | Resultado |
|---|---|---|
| Tiempo total Pasos 1-2 | < 60 minutos | TBD |
| Spec generada cubre todos los AC del ticket original | 5/5 | TBD |
| Threat model identifica al menos S, T, I de STRIDE | sí | TBD |
| Equipo entiende el flujo sin explicación adicional | sí | TBD |
| Pasos del flujo replicables sin Haroldo presente | sí | TBD |

---

## Referencias

- Skill 01 ejecutada: `skills/01-brainstorm.md`
- Skill 02 ejecutada: `skills/02-spec-threat-model.md`
- Ticket fuente: `/Users/harias25/kriptos-classifier-v2-spec/v2/tickets-implementacion.md` (sección Ticket 1)
- Flujo completo de 5 pasos: `docs/references/flow-5-steps.png`
- Guía de TDD + IA: `docs/references/guia-desarrolladores-tdd-ia.pdf`
