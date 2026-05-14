# Classifier v2 — Ecosystem Overview

Resumen del producto Classifier de Kriptos. Esta es la primera lectura para cualquier skill que refine un ticket del clasificador. Es **resumen ejecutivo** — para detalle de cada componente, ver `tickets-source.md` (apunta al repo completo de specs).

---

## Qué es

El Classifier es el sistema que escanea archivos en máquinas/cloud de clientes (enterprises), prioriza candidatos sensibles ("joyas de la corona"), recolecta samples, los anonimiza y los clasifica con un LLM. Resultado: cada documento queda etiquetado (sensibilidad, grupo, agente que lo escaneó).

---

## Áreas

| # | Área | Owner | Tecnología |
|---|------|-------|------------|
| A | Agente Multiplataforma (PC: Windows/Mac/Linux/FileServer/OneDrive/SharePoint/Google) | Equipo agente | TBD |
| B | Agente Cloud (corre dentro AWS del cliente) | Equipo agente | TBD |
| C | Backend Phase 1 — Scan & File Discovery | Equipo backend | Python (Lambda + EMR Serverless / PySpark) |
| D | Backend Phase 2 — GSE (Priority Sample Collection) | Equipo backend | Python (Lambda + DynamoDB + SQS + S3) |
| E | Plataforma Web | Equipo frontend | React (existente) |
| F | Cajas negras / dependencias | Otros equipos (Signal Handler, Anonymizer, LLM, KEM, Bedrock) | n/a |

---

## Fases

### Fase 1 — Scan & File Discovery

Desde el escaneo del disco del agente hasta tener `suspicious_crown_jewels/{ent}/{sta}/crown_jewels.jsonl` listo para Fase 2.

**Backend (Python Lambdas + EMR):**
- `tree-url-generator` — Lambda detrás de API Gateway POST `/v2/tree/init`. Valida body, genera `tree_id`, firma pre-signed URL al bucket `compressed_trees`.
- `tree-uncompressor` — Lambda triggered por EventBridge sobre PutObject en `compressed_trees/`. Streaming gunzip a `decompressed_trees/`, propaga headers `x-amz-meta-*`.
- `emr-job-trigger` — Lambda triggered por PutObject en `decompressed_trees/`. Llama EMR Serverless StartJobRun.
- `joyas-priorizer` (PySpark / EMR) — Carga keywords del enterprise como broadcast, scan del NDJSON, match por nombre, escribe `crown_jewels.jsonl` (incluso vacío para no atascar Fase 2).

**Estado:** POC validado en backend Phase 1. Cambios v3 pendientes en el agente.

### Fase 2 — Priority Sample Collection (GSE)

Para cada `crown_jewels.jsonl` que aterrice, dentro de un tiempo razonable el LLM downstream recibe una notificación con `cycle_id` cerrado + el prefix S3 de los samples anonimizados listos para clasificar.

**Backend:**
- `gse-cycle-init` — Lambda con event source en SQS FIFO `gse-crown-cycle-queue`. Get-or-create CYCLE en DDB, query KEM para `stations_expected`, crea STATION + REQUEST, notifica al Signal Handler.
- `gse-sample-reception-notifier` — Lambda con event source en SQS `gse-sample-reception-queue`. Increment `samples_received` en DDB, notifica al Anonymizer.
- `gse-sample-anonymizer-notifier` — Lambda con event source en SQS `gse-sample-anonymizer-queue`. Increment `samples_anonymized` en DDB.
- `gse-station-status` — Lambda con DDB Stream filter en STATION records. Marca STATION como complete y suma a CYCLE.stations_completed.
- `gse-enterprise-status` — Lambda con DDB Stream filter en CYCLE records. Marca CYCLE complete y notifica al LLM Process Queue.
- `gse-request-complete` — Lambda detrás de API Gateway POST `/v2/gse/request-complete`. Cierra REQUEST y registra skipped.

**Infra:** DDB `gse-cycles-samples` (single-table 3 niveles), 3 SQS + DLQs, buckets `gse-raw` y `gse-anonymized` con EventBridge, EventBridge Pipes desde DDB Streams.

---

## Cajas negras (dependencias externas)

- **Signal Handler** (equipo plataforma agente) — push del payload de cycle al agente. Canal TBD (IoT, polling, SNS).
- **Anonymizer** (equipo seguridad/IA) — lee `gse-raw`, escribe `gse-anonymized`. Idempotente por `sample_id`.
- **LLM Process** (equipo IA) — consume cycle cerrado, clasifica, persiste resultados.
- **KEM** — endpoint para stations activas por enterprise.
- **Bedrock** (equipo data) — genera `keywords/{enterprise_id}.json` con contexto de empresa/sector/país.

---

## Convenciones cruzadas

- **Encoding:** UTF-8 NFC en nombres de archivo y paths.
- **IDs:** regex `^[a-zA-Z0-9\-_]+$` para `enterprise_id` y `station_id` (anti path-traversal).
- **Headers S3 propagados:** `x-amz-meta-enterprise-id`, `-station-id`, `-total-lines`, `-fingerprint`, `-uploaded-at`, `-agent-version`, `-tree-id`. **Cualquier alteración rompe la firma.**
- **Logs:** JSON estructurado con `enterprise_id`, `station_id`, `tree_id`/`cycle_id`, `request_id`.
- **Idempotencia:** conditional writes en DDB. DLQ tras N reintentos.
- **Pipeline status:** `requested` → `uploading` → `complete` para STATION; `collecting` → `complete` para CYCLE.

---

## Referencias

- Specs v1 y v2 completas: `/Users/harias25/kriptos-classifier-v2-spec/`
- Lista canónica de tickets de implementación: ver `tickets-source.md`
- Decisiones técnicas vigentes: ver `current-decisions.md`
