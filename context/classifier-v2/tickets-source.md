# Tickets Source — Classifier v2

La lista canónica de tickets de implementación vive en el repo de specs del clasificador (fuera de este repo). Esta nota indica **cómo leerlos** desde dentro del flujo.

---

## Ubicación

**Repositorio local del usuario:** `/Users/harias25/kriptos-classifier-v2-spec/`

Archivos relevantes:

- `v2/tickets-implementacion.md` — **fuente principal de tickets** (uno por Lambda / EMR job, con AC y lógica).
- `v2/tareas-por-fase.md` — tareas imperativas por fase × área.
- `v2/plan-trabajo.md` — vista cruzada por área × fase con HUs candidatas.
- `v2/orquestacion-backend.md` — tickets para DevOps (infra).
- `v2/epicas-jira.md` — épicas del proyecto en Jira.
- `v2/new-backend/phase1/`, `v2/new-backend/phase2/` — specs detalladas por componente.

---

## Cómo leer un ticket desde una skill

1. El usuario menciona el ticket por número (ej. "Ticket 1") o por nombre del componente (ej. `tree-url-generator`).
2. La skill abre `v2/tickets-implementacion.md` y busca la sección.
3. Si el ticket no está completo, también lee la spec detallada del componente:
   - Fase 1: `v2/new-backend/phase1/{componente}.md`
   - Fase 2: `v2/new-backend/phase2/{componente}.md`

---

## Tickets actualmente identificados

### Fase 1 (POC validado, pendientes de productización)

| # | Componente | Trigger | Tecnología |
|---|------------|---------|------------|
| 1 | `tree-url-generator` | API Gateway POST `/v2/tree/init` | Python Lambda |
| 2 | `tree-uncompressor` | EventBridge sobre `compressed_trees/` | Python Lambda |
| 3 | `emr-job-trigger` | EventBridge sobre `decompressed_trees/` | Python Lambda |
| 4 | `joyas-priorizer` | EMR Serverless invocado por #3 | PySpark |

### Fase 2

| # | Componente | Trigger | Tecnología |
|---|------------|---------|------------|
| 5 | `gse-cycle-init` | SQS FIFO `gse-crown-cycle-queue` | Python Lambda |
| 6 | `gse-sample-reception-notifier` | SQS `gse-sample-reception-queue` | Python Lambda |
| 7 | `gse-sample-anonymizer-notifier` | SQS `gse-sample-anonymizer-queue` | Python Lambda |
| 8 | `gse-station-status` | DDB Stream sobre STATION | Python Lambda |
| 9 | `gse-enterprise-status` | DDB Stream sobre CYCLE | Python Lambda |
| 10 | `gse-request-complete` | API Gateway POST `/v2/gse/request-complete` | Python Lambda |

---

## Para la demo

**Caso piloto:** Ticket 1 — `tree-url-generator`.

Por qué: autocontenido (sin cajas negras), 5 AC bien definidos, threat surface real (API pública con firma S3), pequeño pero no trivial. Si funciona acá, el patrón replica para todos los demás Lambdas.
