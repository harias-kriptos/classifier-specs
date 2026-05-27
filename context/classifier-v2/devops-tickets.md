# Infra Tickets — Inventario para DevOps

> **Última actualización:** 2026-05-19 (post-reconciliación con Jira).
> **Owner del backend:** Haroldo Arias Molina.
> **Para:** equipo DevOps de Kriptos.
>
> Inventario de **toda** la infra que el backend del Classifier necesita (Fase 1 + 1.5 + 2). Indica qué existe, qué está incompleto, qué cambia con el refresh arquitectónico (2026-05-19) y qué hay que crear desde cero. **Cruzado con Jira (épicas KT-16368 y KT-16369) al 2026-05-19.**
>
> Tickets de **código** correlacionados → [dev-tickets.md](dev-tickets.md). Detalle del refresh → [brainstorms/architecture-refresh-phase-1-2-2026-05-19.md](../../brainstorms/architecture-refresh-phase-1-2-2026-05-19.md).

## DevOps tickets ya creados en Jira

| Ticket | Status | Owner | Cubre | Notas |
|---|---|---|---|---|
| [KT-16725](https://kriptosteam.atlassian.net/browse/KT-16725) | 🟡 In Progress | Cristian Armas | tree-url-generator (Lambda + API GW + bucket `compressed_trees`) | Lambda KT-16612 ya está deployed — el ticket sigue abierto, probable cleanup/hardening pendiente. |
| [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) | 🔴 **BLOCKED** | Fabian Buitron | tree-uncompressor (Lambda + bucket `decompressed_trees` + DLQ) **+** emr-job-trigger (Lambda + EMR Serverless + EventBridge) | **Bloquea KT-16613 y KT-16614** (los dos en In Progress en sprint vivo). Urgente destrabar. |
| [KT-16727](https://kriptosteam.atlassian.net/browse/KT-16727) | ❌ Cancelled | Fabian Buitron | emr-job-trigger standalone | Consolidado en KT-16726. Ignorar. |
| [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) | ✅ **DONE** (parcial) | Cristian Armas | joyas-priorizer (EMR Serverless app + buckets `keywords` y `crown_jewels`) | Infra AWS completa. **Pero el repo `kriptos-io/joyas-priorizer` NO se creó** (era parte del AC01 del ticket). Follow-up: [KT-17034](https://kriptosteam.atlassian.net/browse/KT-17034). Ver §1.1 + sección "Decisión pendiente" abajo. |
| [KT-16729](https://kriptosteam.atlassian.net/browse/KT-16729) | 📋 RFC | Cristian Armas | Monitoring base (SNS `kriptos-backend-alerts` + subs) | Pendiente de aprobación. |
| [KT-17034](https://kriptosteam.atlassian.net/browse/KT-17034) | 📋 RFC | (sin asignar) | **Crear repo `kriptos-io/joyas-priorizer`** | Follow-up de KT-16728 — la infra AWS está deployada pero el repo de código no se creó. Bloquea a KT-16616. |

## ✅ Creación de repos de GitHub: responsabilidad DevOps

Verificado 2026-05-23: **cada DevOps ticket de Lambda nuevo (KT-17012/13/14/15/18/19/20/21/22/23) ya incluye la creación del repo `kriptos-io/<nombre>` en su AC01** (mismo patrón que `kriptos-io/s3-tree-uploader`).

| Repo en `kriptos-io/` | Estado GitHub | DevOps ticket que lo crea |
|---|---|---|
| `s3-tree-uploader` | ✅ existe | KT-16725 (done en su parte de repo) |
| `tree-uncompressor` | ✅ existe | KT-16726 (BLOCKED) |
| `emr-job-trigger` | ✅ existe | KT-16726 (BLOCKED) |
| `joyas-priorizer` | ❌ falta | **KT-17034** (follow-up de KT-16728) |
| `crown-candidates-indexer` | ❌ falta | KT-17012 AC01 |
| `phase1-enterprise-barrier` | ❌ falta | KT-17013 AC01 |
| `validation-mutation-handler` | ❌ falta | KT-17014 AC01 |
| `validation-confirm` | ❌ falta | KT-17015 AC01 |
| `gse-cycle-init` | ❌ falta | KT-17018 AC01 |
| `gse-sample-reception-notifier` | ❌ falta | KT-17019 AC01 |
| `gse-sample-anonymizer-notifier` | ❌ falta | KT-17020 AC01 |
| `gse-request-complete` | ❌ falta | KT-17021 AC01 |
| `gse-station-status` | ❌ falta | KT-17022 AC01 |
| `gse-enterprise-status` | ❌ falta | KT-17023 AC01 |
| `unlockstack` (workflows) | ✅ existe | — (shared infra) |

**Resumen:** 4 repos existen (los de Fase 1 base + workflows reusables), 11 repos faltan. Los 11 están cubiertos por DevOps tickets (10 en AC01 de los nuevos + 1 en KT-17034 nuevo).

---

## Decisión pendiente: bucket de candidatos

`KT-16728` (DONE) creó el bucket **`crown_jewels`**. El refresh proponía renombrarlo a `crown_jewel_candidates` para reflejar que son candidatos pre-validación. **No vale la pena renombrar** (S3 no permite rename in-place, requiere migrar). Recomendación: **mantener `crown_jewels` como bucket de candidatos**, documentar la semántica, y crear `validated_crown_jewels` como bucket nuevo del refresh. Esto evita rework de DevOps + un downtime de migración. Actualizá KT-16616 (MOD) reemplazando `crown_jewel_candidates/` por `crown_jewels/` en el AC02.

## Otros tickets que pueden colisionar

| Ticket | Status | Owner | Relación con el refresh |
|---|---|---|---|
| [KT-16920](https://kriptosteam.atlassian.net/browse/KT-16920) | 🟡 In Progress | Nelson Garzón | **Revisión de formato y campos del documento de Joyas de la Corona.** Colisiona con la decisión JSONL + `normalize_category.py`. **Sync con Nelson antes de cerrar Skill 02 de KT-16616.** |
| [KT-16859](https://kriptosteam.atlassian.net/browse/KT-16859) | 📋 RFC | Jefferson Yaguana | Detección de Joyas con **Harness Agentic** — posible enfoque alternativo / paralelo al matcher tradicional. Validar si compite con el refresh o lo complementa. |
| [KT-16389](https://kriptosteam.atlassian.net/browse/KT-16389) | 🔴 Blocked | Haroldo | Feature de detección en el agente — bloqueado, probable que dependa del backend de Fase 1. |

---

## 0. Cómo leer este archivo

| Status | Significado |
|---|---|
| ✅ **EXISTE** | Desplegado y verificado (porque KT-16612 corre en prod, su infra obligatoriamente existe). |
| ❓ **VERIFICAR** | Probablemente existe si DevOps avanzó con KT-16613/14/16, pero hay que confirmar con el equipo. |
| ⚠️ **EXISTE + MOD** | Existe pero el refresh requiere cambios (rename, cambio de filter, etc.). |
| 📋 **NUEVO** | No existe. Hay que crear. |

Naming convention asumida: `kriptos-{env}-{recurso}` (confirmar). Lambda runtime y ECR repo: `lambda-{nombre-componente}`.

**Si tu equipo DevOps quiere chequear estado real:** una pasada con AWS CLI sobre los nombres listados acá da una foto rápida.

---

## 1. Inventario por recurso (agrupado por tipo)

### 1.1 S3 Buckets

| Bucket | Status | Jira | Consumidor (Lambda) | Notas |
|---|---|---|---|---|
| `compressed_trees` | ✅ EXISTE | [KT-16725](https://kriptosteam.atlassian.net/browse/KT-16725) | tree-url-generator (KT-16612 W), tree-uncompressor (KT-16613 R) | Encryption AES-256, public-access block, EventBridge habilitado. KT-16612 ya sube ahí. |
| `decompressed_trees` | 🔴 BLOCKED | [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) | tree-uncompressor (KT-16613 W), emr-job-trigger (KT-16614 R), joyas-priorizer (KT-16616 R) | Encryption + public-access block + EventBridge sobre `.jsonl` → emr-job-trigger. **Bloquea sprint vivo.** |
| `keywords` | ✅ EXISTE | [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) | joyas-priorizer (KT-16616 R) | IAM del Equipo IA configurado para PUT. Sin EventBridge (no se necesita). |
| `crown_jewels` | ✅ EXISTE | [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) | joyas-priorizer (KT-16616 W), crown-candidates-indexer (N1 R) | **Decisión: NO renombrar a `crown_jewel_candidates`.** Mantener `crown_jewels` y documentar semánticamente que contiene **candidatos** pendientes de validación. Hay que **agregar la EventBridge rule** que dispare a la nueva SQS `crown-candidates-indexer-queue` cuando exista N1. |
| `validated_crown_jewels` | 📋 **NUEVO** | (a crear) | validation-confirm (N4 W), gse-cycle-init (N5 R) | Encryption + public-access block + EventBridge sobre `manifest.json` → SQS FIFO `gse-validated-cycle-queue.fifo`. Lifecycle 30 días. |
| `gse-raw` | 📋 **NUEVO** | (a crear) | Agente PC (W via presigned URL), Cloud Agent (W via IAM), gse-sample-reception-notifier (event via SQS), Anonymizer Equipo IA (R) | Encryption + public-access block + EventBridge sobre `.json` → SQS `gse-sample-reception-queue`. Lifecycle 7 días. Confirmar IAM del Cloud Agent + del Anonymizer (Equipo IA). |
| `gse-anonymized` | 📋 **NUEVO** | (a crear) | Anonymizer Equipo IA (W), gse-sample-anonymizer-notifier (event via SQS), LLM Equipo IA (R) | Encryption + public-access block + EventBridge sobre `.json` → SQS `gse-sample-anonymizer-queue`. Lifecycle 30 días. Confirmar IAM del Anonymizer (PUT) y del LLM (GET). |

### 1.2 DynamoDB Tables

| Tabla | Status | Consumidor (Lambda) | Detalle |
|---|---|---|---|
| **`classifier-cycles-state`** | 📋 **NUEVO** ([KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009)) | **Los 10 Lambdas nuevos** (KT-17024 a KT-17033). State machine único de todo el pipeline. | PK String (`enterprise_id`), SK String (multi-prefix: `CYCLE#`, `STATION#`, `REQUEST#`). **Stream `NEW_AND_OLD_IMAGES` activo** (lo leen las 3 state lambdas). Billing PAY_PER_REQUEST. TTL en `ttl`. **Update 2026-05-23: tabla consolidada** — reemplaza a `crown-validation-state` y `gse-cycles-samples` que eran 2 tablas separadas en la versión anterior. |
| ~~`gse-cycles-samples`~~ | ⛔ **SUPERSEDED** ([KT-17016](https://kriptosteam.atlassian.net/browse/KT-17016)) | — | Consolidado en `classifier-cycles-state`. Ver comentario en KT-17016. |

### 1.3 SQS Queues

| Cola | Status | Productor | Consumidor | Notas |
|---|---|---|---|---|
| `crown-candidates-indexer-queue` | 📋 **NUEVO** | EventBridge sobre `crown_jewels` PutObject (suffix `.jsonl`) | N1 crown-candidates-indexer | Standard. DLQ `crown-candidates-indexer-dlq`. Max receives 5. Visibility timeout > Lambda timeout (≥ 360s). Batch size 1 a la Lambda. |
| `tree-uncompressor-dlq` | 🔴 BLOCKED | (max-receives 2 desde EventBridge → Lambda) | DLQ | Parte de [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726). |
| `emr-job-trigger-dlq` | 🔴 BLOCKED | (max-receives 2) | DLQ | Parte de [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726). |
| `gse-validated-cycle-queue.fifo` | 📋 **NUEVO** | EventBridge sobre `validated_crown_jewels` PutObject suffix `manifest.json` | N5 gse-cycle-init | FIFO con `MessageGroupId=enterprise_id` y `MessageDeduplicationId=sha256(bucket+key)`. DLQ FIFO. Max receives 3. |
| `gse-sample-reception-queue` | 📋 **NUEVO** | EventBridge sobre `gse-raw` PutObject | N6 gse-sample-reception-notifier | Standard. DLQ. Batch size 10, batching window 5s. |
| `gse-sample-anonymizer-queue` | 📋 **NUEVO** | EventBridge sobre `gse-anonymized` PutObject | N7 gse-sample-anonymizer-notifier | Standard. DLQ. Batch size 10, batching window 5s. |

### 1.4 EventBridge Rules (S3 → SQS o Lambda)

| Regla | Status | Source | Filter | Target |
|---|---|---|---|---|
| `tree-uncompressor-trigger` | 🔴 BLOCKED ([KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726)) | S3 `compressed_trees` PutObject | suffix `.jsonl.gz` | `lambda-tree-uncompressor` (directo) |
| `emr-job-trigger-trigger` | 🔴 BLOCKED ([KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726)) | S3 `decompressed_trees` PutObject | suffix `.jsonl` | `lambda-emr-job-trigger` (directo) |
| `crown-candidates-indexer-rule` | 📋 **NUEVO** | S3 `crown_jewels` PutObject | suffix `.jsonl` | SQS `crown-candidates-indexer-queue` |
| `gse-validated-cycle-rule` | 📋 **NUEVO** | S3 `validated_crown_jewels` PutObject | suffix `manifest.json` | SQS FIFO `gse-validated-cycle-queue.fifo` |
| `gse-sample-reception-rule` | 📋 **NUEVO** | S3 `gse-raw` PutObject | suffix `.json` | SQS `gse-sample-reception-queue` |
| `gse-sample-anonymizer-rule` | 📋 **NUEVO** | S3 `gse-anonymized` PutObject | suffix `.json` | SQS `gse-sample-anonymizer-queue` |

### 1.5 EventBridge Pipes (DDB Stream → state lambdas)

| Pipe | Status | Source | Filter | Target | DLQ |
|---|---|---|---|---|---|
| `phase1-enterprise-barrier-pipe` | 📋 **NUEVO** | DDB Stream `crown-validation-state` | `eventName IN ["MODIFY","INSERT"] AND NewImage.SK begins_with "PHASE1_STATION#"` | `lambda-phase1-enterprise-barrier` (N2) | Sí, propio + alarma |
| `gse-station-status-pipe` | 📋 **NUEVO** | DDB Stream `gse-cycles-samples` | `eventName IN ["MODIFY","INSERT"] AND NewImage.SK begins_with "STATION#"` | `lambda-gse-station-status` (N9) | Sí + alarma |
| `gse-enterprise-status-pipe` | 📋 **NUEVO** | DDB Stream `gse-cycles-samples` | `eventName = "MODIFY" AND NewImage.SK begins_with "CYCLE#"` | `lambda-gse-enterprise-status` (N10) | Sí + alarma |

Cada Pipe necesita IAM propio:
- `dynamodb:DescribeStream, GetShardIterator, GetRecords, ListStreams` sobre el stream de la tabla.
- `lambda:InvokeFunction` sobre el Lambda target.

Batch size 10, batching window 5s para los 3.

### 1.6 API Gateway routes

| Route | Status | Lambda backend | Auth | Notas |
|---|---|---|---|---|
| `POST /v2/tree/init` | ✅ EXISTE | lambda-s3-tree-uploader (KT-16612) | API key | Ya en prod. |
| `POST /v2/validation/confirm` | 📋 **NUEVO** | lambda-validation-confirm (N4) | API key (+ recomendado WAF para tenant validation upstream en Plataforma Web) | Misma HTTP API que `/v2/tree/init` (agregar route, no nueva API). |
| `POST /v2/gse/request-complete` | 📋 **NUEVO** | lambda-gse-request-complete (N8) | API key | Misma HTTP API. |

### 1.7 OpenSearch

| Recurso | Status | Consumidor | Notas |
|---|---|---|---|
| Cluster / domain | ❓ VERIFICAR | Plataforma Web ya consume — confirmar si es el mismo cluster que usaremos | Si la Plataforma Web ya tiene cluster productivo y económico → reusar (recomendado, decisión del brainstorm). Si no → crear domain dedicado. |
| Índice `crown_jewel_candidates` | 📋 **NUEVO** | crown-candidates-indexer (N1 W bulk), validation-mutation-handler (N3 RW), validation-confirm (N4 R scroll), Plataforma Web (R via GraphQL) | Mappings explícitos para `candidate_id, enterprise_id, station_id, cycle_id, path, path_normalized, folder, name, name_normalized, extension, size, modified_date, matched_patterns, matched_business_areas, validation_status, validation_actor, validation_at, normalize_version, indexed_at, original_category, original_business_area`. Ver sección 2.4 del brainstorm para el JSON exacto. |

### 1.8 Lambda runtimes + ECR repos

Para **cada Lambda** del backend hay que crear: ECR repo, Lambda function (initial con placeholder image), IAM execution role, CloudWatch Log Group, alarma sobre errores. El **deploy del código** lo hace la pipeline reusable de cada repo de código (`kriptos-io/unlockstack/.github/workflows/lambda-docker-automatic-release.yml`).

| Lambda | Status ECR + Function | Status IAM role | Mem | Timeout | Jira |
|---|---|---|---|---|---|
| `lambda-s3-tree-uploader` | ✅ EXISTE | ✅ EXISTE | 256 MB | 30 s | [KT-16725](https://kriptosteam.atlassian.net/browse/KT-16725) |
| `lambda-tree-uncompressor` | 🔴 BLOCKED | 🔴 BLOCKED | 1024 MB | 300 s | [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) |
| `lambda-emr-job-trigger` | 🔴 BLOCKED | 🔴 BLOCKED | 256 MB | 60 s | [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) |
| `lambda-joyas-priorizer` *(EMR job, no Lambda)* | n/a (EMR) | ✅ EMR exec role | n/a | n/a | [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) |
| `lambda-crown-candidates-indexer` (N1) | 📋 **NUEVO** | 📋 **NUEVO** | 512 MB | 300 s |
| `lambda-phase1-enterprise-barrier` (N2) | 📋 **NUEVO** | 📋 **NUEVO** | 256 MB | 30 s |
| `lambda-validation-mutation-handler` (N3) | 📋 **NUEVO** | 📋 **NUEVO** | 512 MB | 60 s |
| `lambda-validation-confirm` (N4) | 📋 **NUEVO** | 📋 **NUEVO** | 1024 MB | 300 s |
| `lambda-gse-cycle-init` (N5) | 📋 **NUEVO** | 📋 **NUEVO** | 512 MB | 60 s |
| `lambda-gse-sample-reception-notifier` (N6) | 📋 **NUEVO** | 📋 **NUEVO** | 256 MB | 30 s |
| `lambda-gse-sample-anonymizer-notifier` (N7) | 📋 **NUEVO** | 📋 **NUEVO** | 256 MB | 30 s |
| `lambda-gse-request-complete` (N8) | 📋 **NUEVO** | 📋 **NUEVO** | 256 MB | 30 s |
| `lambda-gse-station-status` (N9) | 📋 **NUEVO** | 📋 **NUEVO** | 256 MB | 30 s |
| `lambda-gse-enterprise-status` (N10) | 📋 **NUEVO** | 📋 **NUEVO** | 256 MB | 30 s |

### 1.9 IAM — permisos por Lambda (resumen para los nuevos roles)

| Lambda | Permisos clave |
|---|---|
| N1 crown-candidates-indexer | `s3:GetObject` (`crown_jewel_candidates/*`), `ddb:Query/PutItem/UpdateItem/GetItem` (`crown-validation-state`), `es:ESHttpPost/Put`, `secretsmanager:GetSecretValue` (KEM key) |
| N2 phase1-enterprise-barrier | `ddb:UpdateItem/GetItem` (`crown-validation-state`), `sns:Publish` (notify channel — stub) |
| N3 validation-mutation-handler | `es:ESHttpPost/Put`, `ddb:UpdateItem/GetItem` (`crown-validation-state`) |
| N4 validation-confirm | `es:ESHttpPost` (scroll), `s3:PutObject` (`validated_crown_jewels/*`), `ddb:UpdateItem/GetItem` (`crown-validation-state`) |
| N5 gse-cycle-init | `s3:GetObject` (`validated_crown_jewels/*`), `ddb:Query/PutItem/UpdateItem` (`gse-cycles-samples`), `secretsmanager:GetSecretValue` (KEM), publish a Signal Handler (TBD) |
| N6 gse-sample-reception-notifier | `ddb:UpdateItem` (`gse-cycles-samples`), publish a Anonymizer (TBD) |
| N7 gse-sample-anonymizer-notifier | `ddb:UpdateItem` (`gse-cycles-samples`) |
| N8 gse-request-complete | `ddb:UpdateItem/TransactWriteItems/GetItem` (`gse-cycles-samples`) |
| N9 gse-station-status | `ddb:UpdateItem` (`gse-cycles-samples`) |
| N10 gse-enterprise-status | `ddb:UpdateItem` (`gse-cycles-samples`), publish a LLM Process Queue (TBD) |

### 1.10 Secrets Manager

| Secret | Status | Usado por |
|---|---|---|
| `kem-api-key` | 📋 **NUEVO** (o ❓ VERIFICAR si ya existe en otro proyecto) | N1 crown-candidates-indexer, N5 gse-cycle-init |

### 1.11 SNS / canales de notificación

| Topic | Status | Productor | Consumidor | Notas |
|---|---|---|---|---|
| `phase1-ready-for-validation` | 📋 **NUEVO** | N2 phase1-enterprise-barrier | Plataforma Web | **Stub temporal** — canal definitivo lo define Plataforma Web (puede ser GraphQL subscription, webhook, email). Crear como SNS topic con sub vacío para no bloquear backend. |
| Signal Handler channel | 📋 **NUEVO (TBD por Equipo IA)** | N5 gse-cycle-init | Agente vía Signal Handler | Equipo IA define el canal. |
| Anonymizer notify channel | 📋 **NUEVO (TBD por Equipo IA)** | N6 gse-sample-reception-notifier | Anonymizer | Equipo IA define. |
| LLM Process Queue | 📋 **NUEVO (TBD por Equipo IA)** | N10 gse-enterprise-status | LLM clasificador | Equipo IA define. |

### 1.12 CloudWatch — Monitoring base

| Recurso | Status |
|---|---|
| SNS topic `kriptos-backend-alerts` con sub a email backend + Slack | 📋 RFC ([KT-16729](https://kriptosteam.atlassian.net/browse/KT-16729)) — pendiente de aprobación. Bloquea todas las alarmas. |
| CloudWatch Log Groups (`/aws/lambda/{name}`, 30d retention) | Cada nuevo Lambda necesita el suyo |
| Alarmas por Lambda errors > 3 en 5 min | Cada Lambda necesita la suya |
| Alarmas DLQ depth > 0 | Cada cola con DLQ necesita la suya |
| Alarma API GW 5xx > 5 en 5 min | Por cada route con API GW |
| Alarma EMR job FAILED | KT-16616 |

### 1.13 EMR Serverless

| Recurso | Status | Jira | Notas |
|---|---|---|---|
| EMR Serverless application | ✅ EXISTE | [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) | release `emr-7.0.0`, tipo Spark, max capacity 4 vCPU / 8 GB, auto-start, auto-stop 5min idle. |
| IAM execution role para EMR | ✅ EXISTE | [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) | Permisos sobre `decompressed_trees`, `keywords`, `crown_jewels`, `logs:*`. **Sin cambios para el refresh** (mantenemos `crown_jewels` como bucket de candidatos). |
| S3 log destination del EMR | 📋 **NUEVO (sugerido)** | (a crear) | Bucket dedicado para logs persistentes (no creado en KT-16728). |

### 1.14 GraphQL / Plataforma Web

| Recurso | Status | Owner |
|---|---|---|
| Schema extension — query `crownJewelCandidates` | 📋 **NUEVO** | Plataforma Web (Frontend / Backend) |
| Schema extension — mutations `validateCandidateGroup`, `overrideCandidate`, `addExtraPath`, `confirmValidation` | 📋 **NUEVO** | Plataforma Web |
| Resolver / invoker que llama a `lambda-validation-mutation-handler` (N3) | 📋 **NUEVO** | Plataforma Web |
| UI de validación (vista de candidatos, agrupación, bulk-ops) | 📋 **NUEVO** | Plataforma Web |

---

## 2. Tickets DevOps sugeridos (agrupados por entregable)

Sugerencia: 1 ticket DevOps por **Lambda de código** (cubre ECR + Lambda function + IAM role + log group + alarma + recursos de trigger). + 1 ticket por **recurso compartido grande** (DDB, OS index, monitoring base).

### Fase 1 — estado de tickets DevOps en Jira

| Ticket Jira | Entregable | Status | Acción |
|---|---|---|---|
| [KT-16725](https://kriptosteam.atlassian.net/browse/KT-16725) | tree-url-generator (Lambda + API GW + bucket `compressed_trees`) | 🟡 In Progress (Cristian) | Cerrar — código KT-16612 ya deployed; verificar pendientes. |
| [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) | tree-uncompressor + emr-job-trigger (Lambdas + bucket `decompressed_trees` + EMR EventBridge + DLQs) | 🔴 **BLOCKED** (Fabian) | **Urgente.** Identificar el bloqueo y destrabar — bloquea KT-16613 y KT-16614 (sprint vivo). |
| [KT-16727](https://kriptosteam.atlassian.net/browse/KT-16727) | emr-job-trigger standalone | ❌ Cancelled | Ignorar (consolidado en KT-16726). |
| [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) | joyas-priorizer (EMR app + buckets `keywords` y `crown_jewels`) | ✅ DONE (Cristian) | Listo. Pendiente: agregar EventBridge rule de `crown_jewels` cuando exista N1 — ver DV-F1.5-A abajo. |
| [KT-16729](https://kriptosteam.atlassian.net/browse/KT-16729) | Monitoring base (SNS + subs) | 📋 RFC (Cristian) | Aprobar y deployar — bloquea todas las alarmas del backend. |

### Fase 1.5 — 7 tickets creados en Jira (2026-05-19)

| Ticket Jira | Entregable | Bloquea a |
|---|---|---|
| [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | **DDB `classifier-cycles-state` + Stream** (consolidada Fase 1 + Fase 2 — absorbe lo de KT-17016) | Los 15 DevOps de Lambdas (KT-17012 a KT-17023) |
| [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) | Índice OpenSearch `crown_jewel_candidates` + mappings | KT-17012, KT-17014, KT-17015, GraphQL Plataforma Web |
| ~~[KT-17011](https://kriptosteam.atlassian.net/browse/KT-17011)~~ | ⛔ **CANCELLED 2026-05-26** — Secret existe ya; el IAM grant está bakeado en AC de KT-17078 y KT-17082. | — |
| [KT-17012](https://kriptosteam.atlassian.net/browse/KT-17012) | `lambda-crown-candidates-indexer` (N1) + SQS + EventBridge rule sobre `crown_jewels` | KT-17013 |
| [KT-17013](https://kriptosteam.atlassian.net/browse/KT-17013) | `lambda-phase1-enterprise-barrier` (N2) + EventBridge Pipe sobre DDB Stream | Plataforma Web (consume notify) |
| [KT-17014](https://kriptosteam.atlassian.net/browse/KT-17014) | `lambda-validation-mutation-handler` (N3) + invocación desde GraphQL Plataforma Web | Plataforma Web |
| [KT-17015](https://kriptosteam.atlassian.net/browse/KT-17015) | `lambda-validation-confirm` (N4) + API GW route `POST /v2/validation/confirm` + bucket `validated_crown_jewels` + SQS FIFO `gse-validated-cycle-queue.fifo` | KT-17018 (Fase 2) |

### Fase 2 — 8 tickets creados en Jira (2026-05-19)

| Ticket Jira | Entregable | Bloquea a |
|---|---|---|
| ~~[KT-17016](https://kriptosteam.atlassian.net/browse/KT-17016)~~ | ⛔ **SUPERSEDED por KT-17009** (consolidación 2026-05-23) | — |
| [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) | Buckets `gse-raw` + `gse-anonymized` + EventBridge rules + SQS queues | KT-17019, KT-17020, Agente, Anonymizer, LLM |
| [KT-17018](https://kriptosteam.atlassian.net/browse/KT-17018) | `lambda-gse-cycle-init` (N5) + SQS FIFO consumer + multi-trigger desde inicio | KT-17019–KT-17023 |
| [KT-17019](https://kriptosteam.atlassian.net/browse/KT-17019) | `lambda-gse-sample-reception-notifier` (N6) + SQS consumer | — |
| [KT-17020](https://kriptosteam.atlassian.net/browse/KT-17020) | `lambda-gse-sample-anonymizer-notifier` (N7) + SQS consumer | — |
| [KT-17021](https://kriptosteam.atlassian.net/browse/KT-17021) | `lambda-gse-request-complete` (N8) + API GW route `POST /v2/gse/request-complete` | — |
| [KT-17022](https://kriptosteam.atlassian.net/browse/KT-17022) | `lambda-gse-station-status` (N9) + EventBridge Pipe sobre DDB Stream | KT-17023 |
| [KT-17023](https://kriptosteam.atlassian.net/browse/KT-17023) | `lambda-gse-enterprise-status` (N10) + EventBridge Pipe + notify LLM | — |

---

## 3. Lo que NO va en este archivo

- Repos de código y sus pipelines (los hace `repo-provisioning` por repo de Lambda + se trackea en [dev-tickets.md](dev-tickets.md)).
- Canales de notificación definitivos a cajas negras del Equipo IA (Signal Handler, Anonymizer, LLM) — el Equipo IA es responsable; este backend solo deja stubs.
- GraphQL schema exacto + UI de validación — responsabilidad de Plataforma Web (acá solo se lista que existe el bloqueo).
- Threat surface / WAF / auth fina — diferido a próxima iteración del brainstorm.

---

## 4. Orden de ataque sugerido para DevOps

**Sprint 1 (esta semana — bloqueante de Fase 1):**
1. **Destrabar [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726)** (BLOCKED, Fabian) — sin esto KT-16613 y KT-16614 no pueden deployarse.
2. Cerrar [KT-16725](https://kriptosteam.atlassian.net/browse/KT-16725) (loose ends de tree-url-generator).
3. Aprobar y deployar [KT-16729](https://kriptosteam.atlassian.net/browse/KT-16729) (SNS monitoring base).

**Sprint 2 (Fase 1.5 — bloqueante de validación humana):**
4. [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB `crown-validation-state` + Stream) — primero, bloquea las 4 Lambdas.
5. [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) (índice OpenSearch — coordinar con Plataforma Web).
6. ~~KT-17011~~ Cancelado — el grant IAM al Secret existente está bakeado en KT-17078 y KT-17082.
7. [KT-17012](https://kriptosteam.atlassian.net/browse/KT-17012) y [KT-17013](https://kriptosteam.atlassian.net/browse/KT-17013) en paralelo (N1 indexer + N2 barrier).
8. [KT-17015](https://kriptosteam.atlassian.net/browse/KT-17015) (validation-confirm + bucket validated + SQS FIFO + API GW).
9. [KT-17014](https://kriptosteam.atlassian.net/browse/KT-17014) (validation-mutation-handler — depende del schema GraphQL de Plataforma Web).

**Sprint 3+ (Fase 2):**
10. [KT-17016](https://kriptosteam.atlassian.net/browse/KT-17016) (DDB `gse-cycles-samples`) y [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) (buckets + SQS) en paralelo.
11. [KT-17018](https://kriptosteam.atlassian.net/browse/KT-17018) (gse-cycle-init).
12. [KT-17019](https://kriptosteam.atlassian.net/browse/KT-17019), [KT-17020](https://kriptosteam.atlassian.net/browse/KT-17020), [KT-17021](https://kriptosteam.atlassian.net/browse/KT-17021), [KT-17022](https://kriptosteam.atlassian.net/browse/KT-17022), [KT-17023](https://kriptosteam.atlassian.net/browse/KT-17023) — en orden o paralelos según capacidad del equipo DevOps.

---

## 5. Histórico

| Fecha | Cambio | Por |
|---|---|---|
| 2026-05-19 | Creación. Inventario consolidado post-refresh arquitectónico. | Skill 01 (Claude) |
| 2026-05-19 | Reconciliación con Jira (KT-16368 + KT-16369): DevOps existentes mapeados (KT-16725 In Progress, KT-16726 BLOCKED, KT-16728 DONE, KT-16729 RFC). Decisión: mantener bucket `crown_jewels` (no renombrar). Bloqueante: destrabar KT-16726. | Skill 01 (Claude) |
| 2026-05-19 | **15 tickets DevOps nuevos creados en Jira** bajo épica KT-16369: KT-17009 a KT-17023 (7 Fase 1.5 + 8 Fase 2). Comentario agregado a KT-16728 sobre reuso del bucket `crown_jewels`. Todos en status RFC esperando review/start del equipo DevOps. | Skill 01 (Claude) |
| 2026-05-23 | **Consolidación DDB**: KT-17009 absorbe a KT-17016 (`classifier-cycles-state` única para Fase 1 + Fase 2). KT-17016 marcado como SUPERSEDED. Total efectivo: **14 DevOps tickets nuevos**. Comentarios agregados a los 10 lambda tickets (KT-17024–17033) explicando el cambio + nueva capability `validation_mode` ∈ {enterprise, station}. | Skill 01 (Claude) |
