# Components — Classifier v2

Índice de specs detalladas por componente del producto Classifier de Kriptos. Cargado por Skills 01–02 cuando un ticket toca un componente específico.

> **Origen:** copia consolidada del repo de specs original. Mantenida en este repo para que el Project de Claude Web la lea como Project File.

---

## Backend — Phase 1 (Scan & File Discovery)

Desde el escaneo del disco del agente hasta `suspicious_crown_jewels/{ent}/{sta}/crown_jewels.jsonl` listo para Fase 2.

| Componente | Spec | Trigger | Lenguaje |
|---|---|---|---|
| Overview de Fase 1 | [phase-1/overview.md](phase-1/overview.md) | — | — |
| `tree-url-generator` | [phase-1/tree-url-generator.md](phase-1/tree-url-generator.md) | API Gateway `POST /v2/tree/init` | Python Lambda |
| `tree-uncompressor` | [phase-1/tree-uncompressor.md](phase-1/tree-uncompressor.md) | EventBridge sobre PutObject en `compressed_trees/` | Python Lambda |
| `emr-job-trigger` | [phase-1/emr-job-trigger.md](phase-1/emr-job-trigger.md) | EventBridge sobre PutObject en `decompressed_trees/` | Python Lambda |
| `joyas-priorizer` | [phase-1/joyas-priorizer.md](phase-1/joyas-priorizer.md) | EMR Serverless | PySpark |

---

## Backend — Phase 2 (GSE · Priority Sample Collection)

Para cada `crown_jewels.jsonl`, dentro de tiempo razonable el LLM downstream recibe notificación con cycle cerrado + prefix S3 de samples anonimizados.

| Componente | Spec | Trigger | Lenguaje |
|---|---|---|---|
| Overview de Fase 2 | [phase-2/overview.md](phase-2/overview.md) | — | — |
| `gse-cycle-init` | [phase-2/gse-cycle-init.md](phase-2/gse-cycle-init.md) | SQS FIFO `gse-crown-cycle-queue` | Python Lambda |
| `gse-sample-reception-notifier` | [phase-2/gse-sample-reception-notifier.md](phase-2/gse-sample-reception-notifier.md) | SQS `gse-sample-reception-queue` | Python Lambda |
| `gse-sample-anonymizer-notifier` | [phase-2/gse-sample-anonymizer-notifier.md](phase-2/gse-sample-anonymizer-notifier.md) | SQS `gse-sample-anonymizer-queue` | Python Lambda |
| `gse-station-status` | [phase-2/gse-station-status.md](phase-2/gse-station-status.md) | DDB Stream STATION | Python Lambda |
| `gse-enterprise-status` | [phase-2/gse-enterprise-status.md](phase-2/gse-enterprise-status.md) | DDB Stream CYCLE | Python Lambda |
| `gse-request-complete` | [phase-2/gse-request-complete.md](phase-2/gse-request-complete.md) | API Gateway `POST /v2/gse/request-complete` | Python Lambda |

Infra de soporte:

| Recurso | Spec |
|---|---|
| Buckets S3 | [phase-2/buckets.md](phase-2/buckets.md) |
| Colas SQS | [phase-2/queues.md](phase-2/queues.md) |
| Tabla DDB `gse-cycles-samples` | [phase-2/gse-cycles-samples.md](phase-2/gse-cycles-samples.md) |
| Contratos con cajas negras | [phase-2/external-contracts.md](phase-2/external-contracts.md) |

---

## Agente (Multiplataforma y Cloud)

Specs del agente que corre en máquinas/cloud del cliente.

| Componente | Spec |
|---|---|
| README general del agente | [agent/README.md](agent/README.md) |
| Flujo general | [agent/flujo-general.md](agent/flujo-general.md) |
| Definiciones (terminología, IDs, contratos) | [agent/definiciones.md](agent/definiciones.md) |
| Scanner | [agent/scanner.md](agent/scanner.md) |
| Processing (extracción de chunks, anonimización) | [agent/processing.md](agent/processing.md) |
| Classifier (clasificación de documentos) | [agent/classifier.md](agent/classifier.md) |
| Tagging | [agent/tagging.md](agent/tagging.md) |
| GSE (Group Sample Engine) | [agent/gse.md](agent/gse.md) |
| Sistema KEM | [agent/sistema-kem.md](agent/sistema-kem.md) |
| Real-time | [agent/real-time.md](agent/real-time.md) |
| Parametrizaciones (config del agente) | [agent/parametrizaciones.md](agent/parametrizaciones.md) |
| Plataforma web | [agent/plataforma-web.md](agent/plataforma-web.md) |

---

## Cómo cargar este contexto en las skills

**Skill 01 (Brainstorm)** carga: `ecosystem.md` + el componente específico del ticket.

Ejemplo: si el ticket es sobre `gse-cycle-init`, la skill lee:
- `ecosystem.md` (overview general)
- `components/phase-2/overview.md`
- `components/phase-2/gse-cycle-init.md`
- `components/phase-2/gse-cycles-samples.md` (si se mencionan operaciones DDB)
- `components/phase-2/external-contracts.md` (si menciona cajas negras)

**Skill 02 (Spec)** carga lo mismo + `current-decisions.md` + `stacks/python-lambda/rules.md`.

La regla es **carga on-demand**: solo lo necesario para el ticket. No leer todos los archivos cada vez (rompe el context budget < 20%).
