# gse-cycle-init

**Type:** Lambda (runtime TBD — equipo backend decide)
**Trigger:** SQS event source (puede tener múltiples, una por `process_type`)
**Purpose:** Punto de entrada del ciclo GSE. Recibe un evento de "lote de archivos a samplear", hace get-or-create del CYCLE, crea STATION/REQUEST en DDB, y notifica al agente vía Signal Handler (caja negra).

---

## Triggers

Una sola Lambda con **N event source mappings** (uno por `process_type`):

| Event Source ARN | process_type | Source bucket origen |
|---|---|---|
| `gse-crown-cycle-queue` | `crown` | `suspicious_crown_jewels` (Phase 1 output) |
| `gse-classification-cycle-queue` (futuro) | `classification` | TBD |

El Lambda discrimina vía `event.Records[].eventSourceARN` mapeado a `process_type` por config (env var o tabla en código).

---

## Input

**Source:** SQS message conteniendo un EventBridge event de S3 PutObject:

```json
{
  "Records": [{
    "messageId": "...",
    "eventSourceARN": "arn:aws:sqs:us-east-1:111:gse-crown-cycle-queue.fifo",
    "body": "{\"version\":\"0\",\"detail-type\":\"Object Created\",\"source\":\"aws.s3\",\"detail\":{\"bucket\":{\"name\":\"kriptos-{env}-suspicious-crown-jewels\"},\"object\":{\"key\":\"ent-001/station-A/crown_jewels.jsonl\",\"size\":12345}}}"
  }]
}
```

**Datos derivados:**

| Campo | Origen |
|---|---|
| `process_type` | `eventSourceARN` → mapeo a env (`PROCESS_TYPE_MAP`) |
| `enterprise_id` | `key.split('/')[0]` |
| `station_id` | `key.split('/')[1]` |
| `bucket` / `key` | del event |

---

## Output

### Side effects en DDB

- 0 ó 1 nuevo `CYCLE` record (depende de get-or-create).
- 1 nuevo `STATION` record.
- 1+ nuevos `REQUEST` records (Modelo A: 1 por STATION).

### Side effect externo

Notificación al **Signal Handler** (caja negra · canal TBD — ver [external-contracts.md](external-contracts.md#signal-handler)).

Payload publicado:

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

---

## Processing logic

```
1. Por cada Record en event.Records:
   a. process_type = PROCESS_TYPE_MAP[record.eventSourceARN]
   b. detail = json.loads(record.body).detail
   c. bucket, key = detail.bucket.name, detail.object.key
   d. enterprise_id, station_id = key.split('/')[:2]
   e. tree_id (opcional) = leer x-amz-meta-tree-id via HeadObject

2. GET S3 object suspicious_crown_jewels/{key}
   - Stream-read el NDJSON
   - files = [ { path: row.path + row.name + '.' + row.extension, size: row.size }, ... ]
   - sample_content_size = config[process_type].sample_content_size  (env var)

3. Find-or-create CYCLE:
   a. Query DDB:
        PK = enterprise_id
        SK begins_with "CYCLE#"
        FilterExpression: status = "collecting" AND process_type = current
   b. Si encontrado → cycle_id = found.cycle_id
   c. Si no encontrado:
        cycle_id = uuid4()
        N = call_kem_api(enterprise_id) → stations activas
        ddb.put_item(
          Item: CYCLE record {
            PK: enterprise_id, SK: "CYCLE#{cycle_id}",
            cycle_id, process_type, status="collecting",
            stations_expected=N, stations_completed=0,
            created_at=now, ...
          },
          ConditionExpression="attribute_not_exists(PK)"
        )
        Si ConditionalCheckFailed → re-query (otra invocación lo creó)

4. PUT STATION:
   ddb.put_item(
     Item: STATION record {
       PK: enterprise_id, SK: "STATION#{station_id}#{cycle_id}",
       station_id, cycle_id,
       status="requested",
       samples_expected=len(files),
       samples_received=0, samples_anonymized=0, samples_skipped=0,
       total_requests=1,
       created_at=now, ...
     },
     ConditionExpression="attribute_not_exists(SK)"
   )
   Si ConditionalCheckFailed → no-op (ya existía → mensaje duplicado)

5. PUT REQUEST (Modelo A: 1 por STATION):
   ddb.put_item(
     Item: REQUEST record {
       PK: enterprise_id,
       SK: "REQUEST#{station_id}#{cycle_id}#{process_type_as_request_type}",
       station_id, cycle_id, request_type=process_type,
       files_to_sample=files, sample_content_size,
       status="requested",
       created_at=now, ...
     },
     ConditionExpression="attribute_not_exists(SK)"
   )

6. NOTIFY Signal Handler (canal TBD):
   payload = build_payload(cycle_id, enterprise_id, station_id, process_type, files, sample_content_size)
   notify_signal_handler(payload)   # stub durante 2.C, real en 2.D

7. Log INFO con cycle_id, station_id, process_type, samples_expected
```

---

## Validations

### Input

1. **EventSourceARN reconocido:** debe estar en `PROCESS_TYPE_MAP`. Si no → ERROR, mensaje a DLQ.
2. **Key con formato `{ent}/{sta}/{filename}`:** mínimo 3 segmentos. Si no → WARN, descartar.
3. **Suffix del key:** `.jsonl`. Si no → WARN, descartar (defensa contra triggers mal configurados).
4. **S3 GetObject:** si el archivo no existe (404) → WARN, retornar (mensaje se elimina, no DLQ).

### Business

5. **`enterprise_id` registrado en KEM:** validar al primer call. Si KEM dice 404 → ERROR, DLQ.
6. **`station_id` pertenece al `enterprise_id`:** opcional en POC, requerido en prod.
7. **N (stations_expected)** retornado por KEM > 0. Si 0 → CYCLE se cierra inmediatamente (status=complete) — caso borde, log WARN.

---

## Error handling

| Escenario | Acción | Log | Retry |
|---|---|---|---|
| EventSourceARN no mapeado | Fail mensaje | ERROR | DLQ tras 3 |
| Key con formato inválido | Eliminar mensaje | WARN | No |
| S3 GetObject 404 | Eliminar mensaje | WARN | No |
| S3 GetObject 5xx | Reintentar | ERROR | SQS retry |
| KEM API timeout | Reintentar | ERROR | SQS retry |
| KEM 404 (enterprise no existe) | Fail mensaje | ERROR | DLQ tras 3 |
| DDB ConditionalCheckFailed (CYCLE existe) | Re-query y continuar | INFO | No es error |
| DDB ConditionalCheckFailed (STATION existe) | No-op (mensaje duplicado) | INFO | No es error |
| DDB throttle | Reintentar | WARN | SQS retry |
| Signal Handler notify fail | Reintentar | ERROR | SQS retry — pero CYCLE/STATION ya existen, por lo que es idempotente |

### Idempotencia

- Mensaje SQS duplicado (ej. EventBridge at-least-once) → mismo `bucket+key` → mismo enterprise/station → CYCLE encontrado existente, STATION conditional fail → 0 escrituras nuevas. **Idempotente.**
- Notify al Signal Handler en mensaje duplicado → puede llegar 2× al agente. El agente debe ser idempotente respecto a `cycle_id+station_id`.

---

## Logging

| Evento | Level | Campos extra |
|---|---|---|
| Mensaje recibido | INFO | message_id, eventSourceARN, process_type |
| S3 NDJSON parseado | INFO | enterprise_id, station_id, files_count |
| KEM consultado | INFO | enterprise_id, stations_expected |
| CYCLE creado | INFO | cycle_id, stations_expected |
| CYCLE encontrado existente | INFO | cycle_id |
| STATION creado | INFO | cycle_id, station_id, samples_expected |
| STATION duplicado (no-op) | INFO | cycle_id, station_id |
| Signal Handler notificado | INFO | cycle_id, station_id |
| Signal Handler fail | ERROR | cycle_id, station_id, exception |
| KEM error | ERROR | enterprise_id, exception |

---

## Configuration

| Env var | Ejemplo | Descripción |
|---|---|---|
| `DDB_TABLE` | `gse-cycles-samples` | Tabla DDB |
| `KEM_API_URL` | `https://kem.internal/...` | Endpoint para query de stations |
| `KEM_API_KEY_SECRET_ARN` | `arn:aws:secretsmanager:...` | Auth a KEM |
| `PROCESS_TYPE_MAP_JSON` | `{"arn:...:gse-crown-cycle-queue.fifo":"crown"}` | Map ARN → process_type |
| `SAMPLE_CONTENT_SIZE_BY_TYPE_JSON` | `{"crown":10240}` | Defaults por type (ajustables vía KEM en futuro) |
| `SIGNAL_HANDLER_TARGET` | `arn:aws:sns:...:gse-signal-handler` (placeholder) | Destino del notify (TBD) |

---

## Performance

| Métrica | Esperada |
|---|---|
| Memoria | 512 MB |
| Timeout | 60 s |
| Cold start | ~400 ms (boto3 + json) |
| Warm execution | ~300 ms — dominado por KEM (~100ms) + S3 GetObject (~50ms) + DDB writes (~50ms × 3) |
| Concurrencia | Limitada por SQS FIFO MessageGroupId — solo 1 invocación concurrente por enterprise |

---

## Security

| Concern | Mitigación |
|---|---|
| Cross-enterprise read | IAM scoped a `suspicious_crown_jewels/*` (no enterprise concreto) — el aislamiento es por key |
| KEM credentials | Secret Manager, no env directo |
| Signal Handler payload | Contiene paths de archivos del cliente — el canal TBD debe ser HTTPS o equivalente |
| DDB write | IAM permite solo `PutItem` y `Query` sobre la tabla |

---

## Dependencies

| Servicio | Operación |
|---|---|
| SQS | `ReceiveMessage`, `DeleteMessage` (gestionado por Lambda runtime) |
| S3 (`suspicious_crown_jewels`) | `GetObject`, `HeadObject` |
| DynamoDB (`gse-cycles-samples`) | `Query`, `PutItem` (con condicional) |
| KEM API | `GET /stations?enterprise_id=...` (contrato a confirmar) |
| Secrets Manager | `GetSecretValue` (KEM key) |
| Signal Handler | TBD canal |
| CloudWatch Logs | Write |

---

## Edge cases

| Caso | Comportamiento |
|---|---|
| Phase 1 produce crown_jewels.jsonl vacío | files=[], samples_expected=0 → STATION cierra al primer `gse-station-status` event (ver caso `samples_expected=0` en su spec) |
| Agente nunca llega a recibir el signal | STATION queda en `requested` para siempre (Reaper TBD) |
| Misma estación procesada en dos cycles distintos por error | Conditional `attribute_not_exists` previene; el segundo es no-op |
| KEM cae justo cuando se crea el primer cycle del enterprise | Mensaje a DLQ tras 3 retries → reprocesar manualmente cuando KEM vuelva |
| Mensaje SQS llega pero la EMR re-procesó (overwrite del .jsonl) | Si CYCLE ya cerró: hay que crear un NUEVO cycle. Hoy: get-or-create solo busca cycles `collecting`, no `complete` → crea nuevo. ✅ |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | Skeleton Python con boto3 + json + structured logging | S |
| 2 | Parser de S3 key + NDJSON streaming | M |
| 3 | KEM API client + auth via Secrets | M (depende de contrato KEM) |
| 4 | Lógica get-or-create CYCLE con conditional + re-query | M |
| 5 | PUT STATION/REQUEST con conditional | S |
| 6 | Stub del Signal Handler notify (logger only) hasta que esté el contrato | S |
| 7 | Conectar Signal Handler real | M (bloqueado por equipo agente) |
| 8 | Tests unitarios (mock DDB + S3 + KEM) | M |
| 9 | Test de integración con cola FIFO real | M |
| 10 | Manejo de `crown_jewels.jsonl` > 50 MB (paginar download / streaming) | M |
