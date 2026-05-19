# Phase 2 · Priority Sample Collection (GSE) — Overview

> **Status:** Spec lista para planificación
> **Source of truth:** [README.md](../README.md) · este overview detalla el flujo y enumera componentes
> **Infra:** TBD — `v2/infra/phase2-priority-sample-collection/` está vacía, por crear

---

## Scope

Phase 2 cubre desde que Phase 1 deja un `crown_jewels.jsonl` en `suspicious_crown_jewels/` hasta que el Anonymizer terminó con todos los samples del ciclo y el backend notifica al downstream LLM. El agente participa subiendo samples por archivo, pero el agente **es lado cliente** y vive bajo [/v2/new-agent/](../../new-agent/).

Phase 2 **no incluye**:
- La extracción del contenido del archivo (la hace el agente).
- La anonimización del contenido (caja negra: equipo Anonymizer).
- La clasificación con LLM (caja negra: equipo LLM).
- El push al agente (caja negra: equipo Signal Handler).

Phase 2 **sí incluye** la orquestación entre todos esos componentes y la persistencia del estado.

---

## Componentes

### Lambdas (6)

| # | Lambda | Trigger | Spec |
|---|---|---|---|
| 1 | [gse-cycle-init](gse-cycle-init.md) | SQS FIFO `gse-crown-cycle-queue` (y otras a futuro) | get-or-create CYCLE, query KEM, crea STATION/REQUEST, notifica al Signal Handler |
| 2 | [gse-sample-reception-notifier](gse-sample-reception-notifier.md) | SQS `gse-sample-reception-queue` | `samples_received++`, notifica al Anonymizer |
| 3 | [gse-sample-anonymizer-notifier](gse-sample-anonymizer-notifier.md) | SQS `gse-sample-anonymizer-queue` | `samples_anonymized++` |
| 4 | [gse-request-complete](gse-request-complete.md) | API Gateway `POST /v2/gse/request-complete` | `samples_skipped+=N`, marca REQUEST como `sent` |
| 5 | [gse-station-status](gse-station-status.md) | EventBridge Pipe sobre DDB Stream (STATION items) | barrier de station, escala a CYCLE |
| 6 | [gse-enterprise-status](gse-enterprise-status.md) | EventBridge Pipe sobre DDB Stream (CYCLE items) | barrier de cycle, notifica LLM |

### Colas (3) — [queues.md](queues.md)

| # | Cola | Tipo | Productor | Consumidor |
|---|---|---|---|---|
| 1 | `gse-crown-cycle-queue` | SQS FIFO | EventBridge desde S3 `suspicious_crown_jewels` | `gse-cycle-init` |
| 2 | `gse-sample-reception-queue` | SQS standard | EventBridge desde S3 `gse-raw` | `gse-sample-reception-notifier` |
| 3 | `gse-sample-anonymizer-queue` | SQS standard | EventBridge desde S3 `gse-anonymized` | `gse-sample-anonymizer-notifier` |

> En el futuro: `gse-classification-cycle-queue` (segunda fuente de eventos para `gse-cycle-init`). Mismo Lambda, distinto `EventSourceArn` → distinto `process_type`.

### DynamoDB (1) — [gse-cycles-samples.md](gse-cycles-samples.md)

| Tabla | Tipo | Propósito |
|---|---|---|
| `gse-cycles-samples` | Single-table, 3 niveles (CYCLE/STATION/REQUEST), DDB Stream activo | Estado del ciclo + barriers por contador |

### S3 Buckets (3 propios + 1 compartido) — [buckets.md](buckets.md)

| Bucket | Propósito | Writers | Readers |
|---|---|---|---|
| `suspicious_crown_jewels` | Output Phase 1 / trigger Phase 2 | EMR `joyas-priorizer` (Phase 1) | `gse-cycle-init` |
| `gse-raw` | Samples crudos del agente | PC Agent (s3-uploader) + Cloud Agent (PUT IAM) | Anonymizer (caja negra) |
| `gse-anonymized` | Samples anonimizados | Anonymizer (caja negra) | Downstream LLM (caja negra) |

### EventBridge (4 reglas + 2 pipes)

| # | Recurso | Origen | Destino |
|---|---|---|---|
| 1 | Rule | S3 `suspicious_crown_jewels` PutObject | `gse-crown-cycle-queue` |
| 2 | Rule | S3 `gse-raw` PutObject | `gse-sample-reception-queue` |
| 3 | Rule | S3 `gse-anonymized` PutObject | `gse-sample-anonymizer-queue` |
| 4 | Pipe | DDB Stream `gse-cycles-samples` (STATION items) | `gse-station-status` |
| 5 | Pipe | DDB Stream `gse-cycles-samples` (CYCLE items) | `gse-enterprise-status` |

### API Gateway (1 ruta)

| Method | Path | Lambda |
|---|---|---|
| POST | `/v2/gse/request-complete` | `gse-request-complete` |

### Cajas negras (otros equipos) — [external-contracts.md](external-contracts.md)

| Componente | Owner | Rol |
|---|---|---|
| Signal Handler | Equipo plataforma agente | Push del payload de cycle a la estación |
| Anonymizer core | Equipo seguridad/IA | Lee de `gse-raw`, escribe en `gse-anonymized` |
| LLM Process Queue + LLM | Equipo IA | Consume `cycle_id` listo, clasifica |

---

## Flujo end-to-end (paso a paso)

### 1. Cycle init

```
Phase 1 termina para station-A de ent-001
   └─ EMR escribe suspicious_crown_jewels/ent-001/station-A/crown_jewels.jsonl

S3 PutObject ──▶ EventBridge ──▶ gse-crown-cycle-queue
                                       │ MessageGroupId = "ent-001"
                                       │ MessageDeduplicationId = sha256(bucket+key)
                                       ▼
                                  λ gse-cycle-init
                                     1. process_type ← env (mapeado por EventSourceArn)
                                     2. Lee S3 metadata + jsonl → enterprise_id, station_id, len(files)
                                     3. Query DDB: ¿hay CYCLE abierto para ent-001?
                                          - sí → usa ese cycle_id
                                          - no → crea CYCLE nuevo:
                                                   query KEM → N=stations_expected
                                                   PUT CYCLE con condicional attribute_not_exists
                                     4. PUT STATION (samples_expected = len(files), status="requested")
                                     5. PUT REQUEST (1 por station — Modelo A)
                                     6. NOTIFY Signal Handler (canal TBD)
                                          payload: { cycle_id, process_type, requests:[{type,files,size}] }
```

### 2. Agente sube samples (loop por file)

```
Agente recibe payload del Signal Handler
   por cada file en files_to_sample:
       extrae chunk + path → JSON
       si PC Agent:    s3-uploader → presigned URL → S3 gse-raw
       si Cloud Agent: PUT direct (IAM)              → S3 gse-raw
       path: gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json

cada PUT en gse-raw:
   S3 PutObject ──▶ EventBridge ──▶ gse-sample-reception-queue ──▶ λ gse-sample-reception-notifier
                                                                       1. ADD samples_received=1
                                                                       2. NOTIFY Anonymizer (canal TBD)
                                                                            payload: { bucket, key, ent, sta, cycle, request_type, sample_id }
```

### 3. Anonymizer procesa (caja negra)

```
Anonymizer (caja negra del otro equipo):
   1. Recibe la notificación con bucket+key
   2. GET gse-raw/{path}/sample_NNN.json
   3. Ejecuta el core de anonimización
   4. PUT gse-anonymized/{path}/sample_NNN.json   ← mismo path

cada PUT en gse-anonymized:
   S3 PutObject ──▶ EventBridge ──▶ gse-sample-anonymizer-queue ──▶ λ gse-sample-anonymizer-notifier
                                                                        1. ADD samples_anonymized=1
```

### 4. Cierre por request (agente confirma)

```
Agente termina todos los samples de una request:
   POST /v2/gse/request-complete
        body: { enterprise_id, station_id, cycle_id, request_type,
                total_samples_uploaded, samples_skipped }

   ──▶ λ gse-request-complete
          1. Validar que REQUEST exista
          2. ADD samples_skipped += body.samples_skipped (idempotente con request_complete_at)
          3. SET REQUEST.status = "sent"
```

### 5. Cascada de barriers (automático vía DDB Streams)

```
Cualquier UPDATE a STATION ──▶ DDB Stream ──▶ EventBridge Pipe ──▶ λ gse-station-status
                                                                       lee NewImage de STATION
                                                                       if STATION.status != "complete"
                                                                       and (samples_anonymized + samples_skipped) >= samples_expected:
                                                                           UPDATE STATION conditional:
                                                                               SET status="complete"
                                                                               IF status<>"complete"
                                                                           ADD CYCLE.stations_completed=1

Cualquier UPDATE a CYCLE ──▶ DDB Stream ──▶ EventBridge Pipe ──▶ λ gse-enterprise-status
                                                                     lee NewImage de CYCLE
                                                                     if CYCLE.status != "complete"
                                                                     and stations_completed >= stations_expected:
                                                                         UPDATE CYCLE conditional:
                                                                             SET status="complete"
                                                                             IF status<>"complete"
                                                                         NOTIFY LLM Process Queue (canal TBD)
                                                                            payload: { cycle_id, enterprise_id, process_type }
```

---

## JSON Formats

### Trigger payload — message en `gse-crown-cycle-queue`

EventBridge transforma el S3 event en este body SQS:

```json
{
  "version": "0",
  "id": "...",
  "detail-type": "Object Created",
  "source": "aws.s3",
  "detail": {
    "bucket": { "name": "kriptos-{env}-suspicious-crown-jewels" },
    "object": { "key": "ent-001/station-A/crown_jewels.jsonl", "size": 12345 }
  }
}
```

`gse-cycle-init` deriva `enterprise_id` y `station_id` del key, y `process_type` del `EventSourceArn` del trigger.

### Signal Handler payload (lo que `gse-cycle-init` publica)

```json
{
  "cycle_id": "0ce84cb1-0e1a-4b92-bf77-738b2f0a1b7f",
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "process_type": "crown",
  "requests": [
    {
      "type": "crown_jewels",
      "files": [
        { "path": "/Users/foo/Q1.pdf", "size": 245780 },
        { "path": "/Users/foo/contract.docx", "size": 91234 }
      ],
      "sample_content_size": 10240
    }
  ]
}
```

> Modelo A: `requests` siempre tiene 1 elemento (1 cycle = 1 process_type = 1 request_type). El array se mantiene para tolerar Modelo B en el futuro sin romper contrato.

### Sample upload (agente → `gse-raw`)

```json
{
  "sample_id": "01HX7K9...",
  "path": "/Users/foo/Q1.pdf",
  "extension": "pdf",
  "size": 245780,
  "language": "es",
  "ml_version": "1.4.2",
  "fuzzy_hash": "...",
  "embedding": [...],
  "chunks": [
    { "index": 0, "content": "<<chunk text>>" }
  ]
}
```

> Estructura propuesta — el contrato exacto del sample lo define el agente. Backend solo necesita `sample_id` (para idempotencia) y la metadata path/extensión/etc para downstream.

### Anonymizer notification (lo que `gse-sample-reception-notifier` publica)

```json
{
  "bucket": "kriptos-{env}-gse-raw",
  "key": "ent-001/station-A/cycle-id/crown_jewels/sample_001.json",
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "0ce84cb1-...",
  "request_type": "crown_jewels",
  "sample_id": "01HX7K9..."
}
```

### LLM notification (lo que `gse-enterprise-status` publica al cerrar el cycle)

```json
{
  "cycle_id": "0ce84cb1-...",
  "enterprise_id": "ent-001",
  "process_type": "crown",
  "stations_completed": 5,
  "samples_anonymized_total": 312,
  "anonymized_prefix": "kriptos-{env}-gse-anonymized/ent-001/{cycle-id}/"
}
```

### `POST /v2/gse/request-complete` (agente → backend)

```json
{
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "0ce84cb1-...",
  "request_type": "crown_jewels",
  "total_samples_uploaded": 47,
  "samples_skipped": 3,
  "skipped_reasons": [
    { "path": "/Users/foo/locked.pdf", "reason": "locked_by_other_process" }
  ]
}
```

---

## Cross-Cutting Concerns

### Logging Standard

Todas las Lambdas de Phase 2 usan structured JSON logging:

```json
{
  "level": "INFO|WARN|ERROR",
  "timestamp": "ISO-8601",
  "lambda": "gse-cycle-init",
  "request_id": "Lambda request ID",
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "0ce84cb1-...",
  "request_type": "crown_jewels",
  "sample_id": "01HX7K9...",
  "message": "human-readable",
  "error": "stack trace si ERROR"
}
```

CloudWatch Log Groups: `/aws/lambda/{function-name}` con 30 días de retención.

### Error Handling Strategy

| Error | Estrategia | Alerta |
|---|---|---|
| Mensaje inválido en SQS | Log ERROR, dejar que vaya a DLQ tras N reintentos | Sí — DLQ > 0 |
| DDB ConditionalCheckFailedException (writer perdió la carrera) | Log INFO, no es error — otra invocación lo manejó | No |
| KEM API timeout | Log ERROR, reintento por SQS retry policy | Sí — sostenido |
| S3 GetObject 404 | Log WARN, descartar mensaje (race con delete) | No |
| Lambda timeout | Reintento SQS, eventual DLQ | Sí — DLQ > 0 |
| Anonymizer no procesa un sample (cycle nunca cierra) | Reaper Lambda con TTL (TBD) | Sí — cycles abiertos > umbral horas |

### DLQs

| Cola origen | DLQ | Retention |
|---|---|---|
| `gse-crown-cycle-queue` | `gse-crown-cycle-dlq` | 14 días |
| `gse-sample-reception-queue` | `gse-sample-reception-dlq` | 14 días |
| `gse-sample-anonymizer-queue` | `gse-sample-anonymizer-dlq` | 14 días |
| EventBridge Pipes (status lambdas) | DLQ propio por Pipe | 14 días |

### Retry Policy

| Recurso | Max Receives | DLQ tras |
|---|---|---|
| `gse-crown-cycle-queue` (FIFO) | 3 | 3 |
| `gse-sample-reception-queue` | 5 | 5 |
| `gse-sample-anonymizer-queue` | 5 | 5 |
| Pipes a status lambdas | 3 | 3 |

### Monitoring & Alerting

| Métrica | Source | Umbral | Acción |
|---|---|---|---|
| Lambda errors (cualquiera) | CloudWatch Lambda metrics | > 3 en 5 min | SNS alert |
| DLQ depth (cualquiera) | CloudWatch SQS metrics | > 0 | SNS alert |
| CYCLE stuck (status=collecting > N hrs) | Custom metric / Reaper | TBD | SNS alert |
| API GW 5xx en `/v2/gse/request-complete` | CloudWatch | > 5 en 5 min | SNS alert |
| DDB throttles | CloudWatch DDB metrics | > 0 sostenido | Capacity review |

### Security

| Concern | Mitigación |
|---|---|
| Cross-enterprise access en gse-raw | S3 key pattern `{ent}/...` + IAM por enterprise (Cloud Agent) |
| Pre-signed URL leakage (PC Agent) | 1h expiration, scoped a key exacto |
| API auth en `/v2/gse/request-complete` | API key + WAF (TODO antes de producción) |
| Permisos Lambda | Mínimo: solo el bucket/queue/DDB que necesita cada una |
| Encryption at rest | AES-256 en todos los buckets + DDB encryption por defecto |

---

## Open Questions

| # | Tema | Detalle |
|---|---|---|
| 1 | Trigger del cycle `classification` | Quién/qué dispara, formato del input |
| 2 | Modelo A vs B para `request_types` | Confirmar que crown nunca tendrá multi-type |
| 3 | Cycles concurrentes por enterprise | ¿Pueden coexistir un crown y un classification activos? Hoy el get-or-create busca por status; si distintos process_type → distinto cycle. Validar |
| 4 | Política de timeout / Reaper | ¿Cuándo declarar un cycle como `failed`? |
| 5 | Idempotencia de samples | Dedup key cuando un PUT se duplica en gse-raw |
| 6 | Renombrar bucket `crown_jewels` | Trivial pero requiere coordinación con Phase 1 |
| 7 | KEM API contract | Endpoint, auth, formato de respuesta (lista de stations activas) |

---

## Plan de implementación sugerido

Orden de construcción (cada paso desbloquea al siguiente):

### Fase 2.A — Foundation (paralelo)

1. Crear `gse-cycles-samples` (DDB) con stream activo.
2. Crear los 3 buckets (`suspicious_crown_jewels` si no existe, `gse-raw`, `gse-anonymized`).
3. Crear las 3 colas SQS + sus DLQ.
4. Crear las 3 EventBridge rules de S3 → SQS.
5. Crear las 2 EventBridge pipes (DDB stream → status lambdas) — sin Lambda destino aún.

### Fase 2.B — Lambdas de cascada (sin notificaciones externas)

6. Implementar `gse-station-status` (puro DDB, no toca cajas negras).
7. Implementar `gse-enterprise-status` (idem; el push al LLM queda como TODO).
8. Test con datos sintéticos: insertar CYCLE/STATION/REQUEST a mano y verificar cascada.

### Fase 2.C — Lambdas de ingest (sin notificaciones externas)

9. Implementar `gse-cycle-init` (sin la notificación al Signal Handler — log y stub).
10. Implementar `gse-sample-reception-notifier` (sin la notificación al Anonymizer — log y stub).
11. Implementar `gse-sample-anonymizer-notifier`.
12. Implementar `gse-request-complete` + API Gateway route.
13. Test end-to-end con archivos de Phase 1 + samples mock subidos manualmente al `gse-raw`.

### Fase 2.D — Integración con cajas negras (bloqueada por otros equipos)

14. **[bloqueado]** Conectar Signal Handler — esperar contrato del equipo del agente.
15. **[bloqueado]** Conectar Anonymizer — esperar contrato del equipo de anonimización.
16. **[bloqueado]** Conectar LLM Process Queue — esperar contrato del equipo de LLM.

### Fase 2.E — Hardening

17. Resiliencia: Reaper Lambda para cycles colgados.
18. Idempotencia: dedup de samples.
19. Monitoring + alarms.
20. Pruebas de carga.

**Crítico para planificación:** las fases 2.A → 2.C **no dependen de otros equipos** y pueden arrancar de inmediato. La fase 2.D queda bloqueada hasta tener los contratos firmes con las cajas negras.
