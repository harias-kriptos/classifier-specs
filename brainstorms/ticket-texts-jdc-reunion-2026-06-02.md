# Ticket texts — Reunión JDC (Validación manual + Reportes + área) 2026-06-02

> Origen: reunión "Validación Manual de Archivos JDC (Joyas de la Corona)".
> Sigue `templates/JIRA_STORY.md`.
> Fecha: 2026-06-02.
>
> ✅ **Creados en Jira (2026-06-02), bajo épica [KT-16369](https://kriptosteam.atlassian.net/browse/KT-16369), estado RFC:**
> - Ticket 1 → [KT-17245](https://kriptosteam.atlassian.net/browse/KT-17245) (Task, asignado a Jefferson Esteban Yaguana Montero)
> - Ticket 2 → [KT-17246](https://kriptosteam.atlassian.net/browse/KT-17246) (Task, asignado a Jefferson Esteban Yaguana Montero)
> - Ticket 3 → [KT-17247](https://kriptosteam.atlassian.net/browse/KT-17247) (Story, sin asignar — equipo backend)
>
> **Contexto de scope:** la arquitectura de Fase 1.5 (validación humana) **aún no está aprobada por el equipo**. De esta reunión, lo único que se ticketea ahora es lo que es defendible sin depender de esa aprobación:
> 1. Las dos tareas de **Esteban** (son insumos / bloqueantes, no trabajo de backend).
> 2. La inclusión de **`area_id`** en el contrato de metadata (cambio chico, independiente del flujo de validación).
>
> El consolidador de reportes Excel y el loop de reprocesamiento **NO se abren todavía** — dependen de los entregables de Esteban (tickets 1 y 2) y de la aprobación de la arquitectura.

---

## 🟦 Ticket 1 (Esteban) — Documento de casuísticas de cambios del cliente

- **Tipo:** Task (documentación / discovery)
- **Asignado:** Esteban
- **Épica:** [KT-16369](https://kriptosteam.atlassian.net/browse/KT-16369) (confirmar)
- **Bloquea a:** futuro ticket de "loop de reprocesamiento JDC" (no abierto aún)

```markdown
## Resumen

Documentar todas las casuísticas posibles de cambios que el cliente puede solicitar
durante la validación manual de archivos JDC, para que el equipo técnico pueda
dimensionar el loop de reprocesamiento y los impactos en la arquitectura. Hoy el
pipeline asume una sola pasada hacia adelante; este documento es el insumo que define
qué casos disparan un reproceso y con qué alcance.

## Casuísticas a cubrir (mínimo)

- **C1 — Rechazo de archivos identificados como JDC:** el cliente marca como no-JDC
  archivos que el pipeline clasificó como joya. Qué se espera que pase con ellos.
- **C2 — Solicitud de patrones nuevos no contemplados:** el cliente pide buscar
  patrones/keywords que no estaban en el set inicial. Qué dispara y quién los genera.
- **C3 — Excepciones por área organizacional:** validaciones acotadas a un área
  específica (ej. "tarjetas de crédito solo de ciertas áreas"). Cómo se expresa la excepción.

## Acceptance Criteria

- **AC01 — Inventario completo:** el documento enumera cada casuística con un ID,
  descripción, ejemplo real, y frecuencia esperada.
- **AC02 — Impacto por casuística:** para cada caso, indica qué tendría que cambiar
  (keywords en S3, re-run de EMR, re-indexación, re-validación) — a nivel de QUÉ, no de CÓMO.
- **AC03 — Disparador:** para cada caso, quién lo inicia (cliente / agente / equipo IA)
  y desde dónde (plataforma web / manual).
- **AC04 — Casos límite:** cubre al menos cambios concurrentes y cambios después de
  haber confirmado una validación.

## Referencias

- **Reunión:** Validación Manual de Archivos JDC (2026-06-02).
- **Épica:** KT-16369.

## Definition of Done

- [ ] Documento revisado por el equipo técnico (backend)
- [ ] Cada casuística con ejemplo concreto del cliente
- [ ] Enlazado desde la épica KT-16369
```

---

## 🟦 Ticket 2 (Esteban) — Formato estándar de Excel consolidado (tipo CESEM)

- **Tipo:** Task (documentación / diseño de formato)
- **Asignado:** Esteban
- **Épica:** [KT-16369](https://kriptosteam.atlassian.net/browse/KT-16369) (confirmar)
- **Bloquea a:** futuro ticket de "consolidador de reportes JDC" (no abierto aún)

```markdown
## Resumen

Definir el formato estándar del Excel consolidado client-facing para el reporte final
de JDC, equivalente al formato usado con CESEM. Hoy EMR genera un JSON por estación
(no un Excel consolidado); este documento es el insumo que define cómo se ve el
entregable final para que después se pueda especificar el componente que lo genera.

## Alcance del formato a definir

- **Consolidación:** todas las estaciones de un enterprise en un solo Excel.
- **Presentación:** colores, organización profesional, formato client-facing.
- **Metadata obligatoria:** incluir `area ID` entre `enterprise ID` y `station ID`
  (jerarquía enterprise → área → estación). Ver Ticket 3 (inclusión de area_id).

## Acceptance Criteria

- **AC01 — Estructura de hojas/columnas:** el documento define las hojas, columnas y
  el orden de cada una, con un ejemplo (plantilla .xlsx o mockup).
- **AC02 — Jerarquía de metadata:** queda explícito dónde aparece enterprise / área /
  estación y cómo se agrupan los archivos.
- **AC03 — Estilo:** colores, encabezados, formato de celdas y cualquier convención
  visual (similar a CESEM) quedan documentados con ejemplo.
- **AC04 — Referencia CESEM:** se adjunta o enlaza el Excel de CESEM como base comparativa.

## Referencias

- **Reunión:** Validación Manual de Archivos JDC (2026-06-02).
- **Épica:** KT-16369.

## Definition of Done

- [ ] Plantilla .xlsx (o mockup) entregada
- [ ] Validado por producto / equipo backend
- [ ] Enlazado desde la épica KT-16369
```

---

## 🟩 Ticket 3 (técnico) — Inclusión de `area_id` en el contrato de metadata

- **Tipo:** Story / Task técnico (monorepo — solo componentes afectados)
- **Asignado:** equipo técnico (backend)
- **Épica:** [KT-16369](https://kriptosteam.atlassian.net/browse/KT-16369) (confirmar)
- **Repos:** `scan-match-backend` (monorepo Fase 1) — agregar el campo en los componentes que lo deben considerar.

```markdown
## Resumen

Introducir `area_id` como nivel de la jerarquía de metadata, **entre `enterprise_id` y
`station_id`** (enterprise → área → estación). Hoy el modelo es solo enterprise → station;
agregar área permite las "validaciones por área específica" (ej. tarjetas de crédito solo
de ciertas áreas) y que el reporte final incluya área en su metadata.

⚠️ `area_id` (unidad organizacional estructural) es distinto de `matched_business_areas`
(categorización del keyword, ej. "estrategia planeacion"). Este ticket agrega el primero.

## Componentes del monorepo que deben considerar area_id

- **Ingesta / scan (tree-url-generator — KT-16612):** origen del `area_id` en la metadata
  del árbol. Es donde entra al pipeline.
- **joyas-priorizer (KT-16616):** propagar `area_id` a cada fila de `matches.jsonl`.
- **DDB `classifier-cycles-state` (KT-17009):** `area_id` como atributo de la STATION.

Downstream (índice OpenSearch `crown_jewel_candidates`, schema GraphQL/AppSync, y el
consolidador de reportes) heredan `area_id` cuando esa capa se confirme — **fuera de
scope de este ticket**, que cierra solo el contrato de origen (scan → matches → DDB).

## Acceptance Criteria

- **AC01 — Origen:** la metadata del árbol scaneado incluye `area_id`. Test: `test_scan_metadata_includes_area_id`.
- **AC02 — Propagación a matches:** cada fila de `matches.jsonl` lleva `area_id`. Test: `test_match_row_carries_area_id`.
- **AC03 — DDB:** la STATION en `classifier-cycles-state` persiste `area_id` como atributo. Test: `test_station_persists_area_id`.
- **AC04 — Retrocompatibilidad:** árboles/metadata sin `area_id` no rompen el pipeline (valor por defecto / `unknown` documentado). Test: `test_missing_area_id_defaults_safe`.

## Edge Cases

- Metadata legacy sin `area_id` (datos previos al cambio) → valor por defecto, no aborta.
- Un mismo `station_id` reportado bajo dos `area_id` distintos → definir política (¿error, último gana, o área es parte de la clave?).
- ¿`area_id` se vuelve segmento del key de S3 (`{ent}/{area}/{sta}/`) o queda solo como campo dentro del archivo? Ver Open Questions.

## Out of Scope

- Índice OpenSearch, schema GraphQL y reporte Excel — heredan area_id en tickets posteriores.
- El flujo de validación humana completo (no aprobado aún).

## Open Questions

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | ¿De dónde sale `area_id`? ¿Lo provee **KEM** (estructura organizacional del enterprise) o lo reporta el **agente** en el scan? | Haroldo + Equipo IA / KEM | Asumir que viene de KEM | Implementación AC01 |
| Q2 | ¿`area_id` es segmento del key S3 (`{ent}/{area}/{sta}/`) o solo campo en metadata/DDB? | Tech Lead | Solo campo (no key) | AC02 / AC03 |

## Referencias

- **Reunión:** Validación Manual de Archivos JDC (2026-06-02).
- **Épica:** KT-16369.

## Definition of Done

- [ ] Tests cubren cada AC (RED → GREEN → REFACTOR)
- [ ] `area_id` documentado en el contrato de metadata (README del monorepo)
- [ ] Q1 (origen del area_id) resuelta antes de mergear
- [ ] PR aprobado por al menos 1 reviewer humano
```

---

## Resumen para liderazgo (los "tickets creados" de esta reunión)

| # | Ticket | Tipo | Dueño | Estado |
|---|--------|------|-------|--------|
| [KT-17245](https://kriptosteam.atlassian.net/browse/KT-17245) | Documento de casuísticas de cambios del cliente | Task | Esteban | ✅ Creado (RFC) |
| [KT-17246](https://kriptosteam.atlassian.net/browse/KT-17246) | Formato estándar de Excel consolidado (tipo CESEM) | Task | Esteban | ✅ Creado (RFC) |
| [KT-17247](https://kriptosteam.atlassian.net/browse/KT-17247) | Inclusión de `area_id` en el contrato de metadata | Story | Backend | ✅ Creado (RFC) |

**No committables para JUN-2** (dependen de 1 y 2 + aprobación de arquitectura): consolidador de reportes Excel, loop de reprocesamiento por cambios del cliente.
