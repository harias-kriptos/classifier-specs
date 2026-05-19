# gse-sample-reception-notifier

**Type:** Lambda (runtime TBD)
**Trigger:** SQS `gse-sample-reception-queue` (alimentada por EventBridge sobre PutObject en `gse-raw`)
**Purpose:** Cuando un sample crudo aterriza en `gse-raw`, este Lambda hace dos cosas: incrementa `samples_received` en la STATION correspondiente y notifica al Anonymizer (caja negra) con la ubicación del sample para que lo procese.

---

## Input

**Source:** SQS message conteniendo un EventBridge event de S3 PutObject:

```json
{
  "Records": [{
    "messageId": "...",
    "eventSourceARN": "arn:aws:sqs:us-east-1:111:gse-sample-reception-queue",
    "body": "{\"version\":\"0\",\"detail-type\":\"Object Created\",\"source\":\"aws.s3\",\"detail\":{\"bucket\":{\"name\":\"kriptos-{env}-gse-raw\"},\"object\":{\"key\":\"ent-001/station-A/0ce84cb1-.../crown_jewels/sample_001.json\",\"size\":12345}}}"
  }]
}
```

**Datos derivados del key:**

```
{enterprise_id}/{station_id}/{cycle_id}/{request_type}/sample_NNN.json
```

| Campo | Origen |
|---|---|
| `enterprise_id` | `key.split('/')[0]` |
| `station_id` | `key.split('/')[1]` |
| `cycle_id` | `key.split('/')[2]` |
| `request_type` | `key.split('/')[3]` |
| `sample_id` | filename sin extensión, o leído de `x-amz-meta-sample-id` (preferido) |

---

## Output

### Side effect en DDB

`UpdateItem` ADD `samples_received += 1` en `STATION#{station_id}#{cycle_id}` del enterprise.

Si es el primer sample, también transiciona `STATION.status` de `requested` a `uploading` con conditional write.

### Side effect externo

Notificación al **Anonymizer** (caja negra · canal TBD — ver [external-contracts.md](external-contracts.md#anonymizer-core)).

Payload publicado:

```json
{
  "bucket": "kriptos-{env}-gse-raw",
  "key": "ent-001/station-A/0ce84cb1-.../crown_jewels/sample_001.json",
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "0ce84cb1-...",
  "request_type": "crown_jewels",
  "sample_id": "01HX7K9..."
}
```

---

## Processing logic

```
Por cada Record en event.Records (batch hasta 10):
   1. Parsear body → bucket, key
   2. Validar key con regex {ent}/{sta}/{cycle}/{req_type}/sample_*.json
   3. Derivar enterprise_id, station_id, cycle_id, request_type, sample_id

   4. UpdateItem en DDB:
        Key: PK=enterprise_id, SK=STATION#{station_id}#{cycle_id}
        UpdateExpression:
          ADD samples_received :one
          SET #status = if_not_exists(#status, :uploading)
        ExpressionAttributeValues: {":one": 1, ":uploading": "uploading"}
      Si STATION no existe → log WARN, descartar (mensaje huérfano — race con cycle-init?)

   5. Transición opcional a "uploading":
      UpdateItem condicional:
        Key: PK=enterprise_id, SK=STATION#...
        UpdateExpression: SET #status = :uploading
        ConditionExpression: #status = :requested
      Si falla → ya no está en "requested" (otro sample lo cambió) → ignorar

   6. NOTIFY Anonymizer (canal TBD):
        publish_to_anonymizer({bucket, key, ent, sta, cycle, request_type, sample_id})

   7. Log INFO: sample_received con enterprise/station/cycle/sample_id
```

**Concurrencia:** la cola es SQS standard (no FIFO). Múltiples invocaciones pueden incrementar `samples_received` en la misma STATION en paralelo — DDB `ADD` es atómico, sin race.

---

## Validations

### Input

1. **Key con 5 segmentos:** `{ent}/{sta}/{cycle}/{req_type}/sample_NNN.json`. Si no → WARN, descartar.
2. **Bucket esperado:** debe ser `gse-raw` (defensivo). Si no → ERROR.
3. **Filename pattern:** debe matchear `sample_*.json`. Si no → WARN, descartar.

### Business

4. **STATION debe existir:** si DDB devuelve `ConditionalCheckFailed` o `ResourceNotFound` → log WARN. Posible race con `gse-cycle-init` (sample subido antes de que el cycle-init terminara). Reintentar con backoff o esperar al SQS retry.

---

## Error handling

| Escenario | Acción | Log | Retry |
|---|---|---|---|
| Key inválido | Descartar mensaje | WARN | No |
| STATION no existe en DDB | Reintentar (puede ser race con cycle-init) | WARN | SQS retry, eventualmente DLQ |
| DDB throttle | Reintentar | WARN | SQS retry |
| Anonymizer notify fail | Reintentar | ERROR | SQS retry |
| Lambda timeout | Reintentar | ERROR | DLQ tras N |

---

## Logging

| Evento | Level | Campos |
|---|---|---|
| Batch recibido | INFO | record_count |
| Sample recibido | INFO | enterprise_id, station_id, cycle_id, sample_id, current_received |
| Transición a uploading | INFO | station_id, cycle_id |
| STATION no existe | WARN | enterprise_id, station_id, cycle_id |
| Anonymizer notify ok | DEBUG | sample_id |
| Anonymizer notify fail | ERROR | sample_id, exception |

---

## Configuration

| Env var | Ejemplo | Descripción |
|---|---|---|
| `DDB_TABLE` | `gse-cycles-samples` | Tabla DDB |
| `ANONYMIZER_TARGET` | `arn:aws:sns:...:gse-anonymizer-requests` (placeholder) | Destino del notify (TBD) |
| `EXPECTED_BUCKET` | `kriptos-{env}-gse-raw` | Validación defensiva |

---

## Performance

| Métrica | Esperada |
|---|---|
| Memoria | 256 MB |
| Timeout | 30 s |
| Batch size SQS | 10 |
| Batch window | 5 s |
| Cold start | ~300 ms |
| Warm execution | ~80 ms × record (DDB UpdateItem ~30ms + notify ~30ms) |
| Concurrencia | Hasta 100 invocaciones paralelas (límite Lambda default) |

**Throughput esperado:** N stations × 50 samples/cycle / window de minutos. Para 100 stations × 50 samples = 5K samples por cycle. Con batch de 10 = 500 invocaciones, ~1 min con 100 concurrencia.

---

## Security

| Concern | Mitigación |
|---|---|
| Permisos DDB | Solo `UpdateItem` sobre la tabla |
| Permisos S3 | **Ninguno** — el Lambda no lee el contenido del sample, solo el key del event |
| Anonymizer notify | Permisos solo al canal TBD (SNS publish, etc.) |
| Cross-enterprise | El key embebe enterprise_id; IAM no necesita scope adicional |

---

## Dependencies

| Servicio | Operación |
|---|---|
| SQS | runtime gestiona |
| DynamoDB | `UpdateItem` |
| Canal del Anonymizer (TBD) | Publish |
| CloudWatch Logs | Write |

---

## Idempotencia

**Mensaje SQS duplicado** (EventBridge at-least-once):
- El mismo PUT de S3 puede generar 2 eventos → 2 mensajes en cola → 2 invocaciones del Lambda.
- Cada invocación incrementa `samples_received += 1` → contador queda inflado en 1.
- **Impacto:** `samples_received > samples_expected` (cosmético).
- **Barrier no se rompe** porque cierra con `(anonymized + skipped) >= expected`, no con `received == expected`.
- Notify al Anonymizer también se duplica → el Anonymizer debe ser idempotente o el sample se procesa 2× (overwrite en gse-anonymized → S3 trigger 2× en gse-anonymizer-queue → samples_anonymized inflado también).
- **Mitigación opcional (TBD):** dedup por `sample_id` con tabla auxiliar (ver [gse-cycles-samples.md#idempotencia](gse-cycles-samples.md#idempotencia)).

**Recomendación POC:** aceptar el sobre-conteo. La barrier es `>=`. Diferencia: contadores no son fuente de verdad para auditoría.

---

## Edge cases

| Caso | Comportamiento |
|---|---|
| Sample subido antes de que cycle-init termine | STATION no existe → WARN + SQS retry. Eventualmente cycle-init crea la STATION y el siguiente retry funciona |
| Sample subido a un CYCLE ya `complete` | STATION existe pero ya está `complete`. ADD se aplica igual (cosmético). El Anonymizer aún se notifica → procesará el sample sin que importe (output a gse-anonymized fuera de barrier) |
| Sample con sample_id duplicado pero contenido distinto | S3 overwrite → 2 PutObject events → 2 invocaciones → 2 ADDs. Mismo problema de sobre-conteo |
| Bucket distinto al esperado en el event | ERROR + DLQ — algo está mal configurado |
| Key con caracteres exóticos en path | URL-decode el key antes de parsear (S3 events los URL-encodean) |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | Parser del S3 event + key validation | S |
| 2 | DDB UpdateItem con ADD + transición de status | S |
| 3 | Stub del Anonymizer notify (logger) hasta contrato | S |
| 4 | Conectar Anonymizer real | M (bloqueado por equipo) |
| 5 | Tests unitarios (mock DDB) | S |
| 6 | Test de batching + idempotencia | M |
| 7 | Decidir y aplicar dedup `sample_id` (si se opta por opción a/b) | M (opcional) |
