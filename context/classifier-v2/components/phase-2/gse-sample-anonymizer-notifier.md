# gse-sample-anonymizer-notifier

**Type:** Lambda (runtime TBD)
**Trigger:** SQS `gse-sample-anonymizer-queue` (alimentada por EventBridge sobre PutObject en `gse-anonymized`)
**Purpose:** Cuando el Anonymizer (caja negra) deja un sample procesado en `gse-anonymized`, este Lambda incrementa `samples_anonymized` en la STATION correspondiente. La transición de STATION a `complete` la hace `gse-station-status` (vía DDB Stream), no este Lambda.

---

## Input

**Source:** SQS message conteniendo un EventBridge event de S3 PutObject:

```json
{
  "Records": [{
    "messageId": "...",
    "eventSourceARN": "arn:aws:sqs:us-east-1:111:gse-sample-anonymizer-queue",
    "body": "{\"version\":\"0\",\"detail-type\":\"Object Created\",\"source\":\"aws.s3\",\"detail\":{\"bucket\":{\"name\":\"kriptos-{env}-gse-anonymized\"},\"object\":{\"key\":\"ent-001/station-A/0ce84cb1-.../crown_jewels/sample_001.json\",\"size\":12345}}}"
  }]
}
```

**Datos derivados:** mismo formato de key que `gse-raw` — el Anonymizer espeja el path al escribir en `gse-anonymized`.

```
{enterprise_id}/{station_id}/{cycle_id}/{request_type}/sample_NNN.json
```

---

## Output

### Side effect en DDB

`UpdateItem` ADD `samples_anonymized += 1` en `STATION#{station_id}#{cycle_id}` del enterprise.

**No notifica a ningún componente externo.** El barrier y la notificación al downstream LLM la maneja `gse-station-status` + `gse-enterprise-status` vía DDB Streams.

---

## Processing logic

```
Por cada Record en event.Records:
   1. Parsear body → bucket, key
   2. Validar key con regex {ent}/{sta}/{cycle}/{req_type}/sample_*.json
   3. Derivar enterprise_id, station_id, cycle_id

   4. UpdateItem en DDB:
        Key: PK=enterprise_id, SK=STATION#{station_id}#{cycle_id}
        UpdateExpression: ADD samples_anonymized :one
        ExpressionAttributeValues: {":one": 1}
      Si STATION no existe → WARN, descartar (Anonymizer procesó algo huérfano)

   5. Log INFO: sample_anonymized con station/cycle/sample_id
```

**Eso es todo.** El Lambda no decide cuándo cerrar la STATION — eso lo hace `gse-station-status` reaccionando al DDB Stream que este UpdateItem genera.

**Concurrencia:** SQS standard, múltiples invocaciones en paralelo. DDB `ADD` es atómico.

---

## Validations

### Input

1. **Bucket esperado:** `gse-anonymized`. Si no → ERROR.
2. **Key con 5 segmentos** terminando en `sample_*.json`. Si no → WARN, descartar.

### Business

3. **STATION debe existir:** si no → WARN. Posibles causas:
   - Cycle ya cerró y STATION fue limpiada por TTL (improbable a la velocidad del Anonymizer).
   - Anonymizer procesó un sample con path inválido (bug del otro equipo).

---

## Error handling

| Escenario | Acción | Log | Retry |
|---|---|---|---|
| Key inválido | Descartar | WARN | No |
| Bucket inesperado | Fail | ERROR | DLQ |
| STATION no existe | Descartar (no útil reintentar) | WARN | No |
| DDB throttle | Reintentar | WARN | SQS retry |
| Lambda timeout | Reintentar | ERROR | DLQ tras N |

---

## Logging

| Evento | Level | Campos |
|---|---|---|
| Batch recibido | INFO | record_count |
| Sample anonymized | INFO | enterprise_id, station_id, cycle_id, sample_id, current_anonymized |
| STATION no existe | WARN | enterprise_id, station_id, cycle_id |
| DDB error | ERROR | exception |

---

## Configuration

| Env var | Ejemplo | Descripción |
|---|---|---|
| `DDB_TABLE` | `gse-cycles-samples` | Tabla DDB |
| `EXPECTED_BUCKET` | `kriptos-{env}-gse-anonymized` | Validación defensiva |

---

## Performance

| Métrica | Esperada |
|---|---|
| Memoria | 256 MB |
| Timeout | 30 s |
| Batch size SQS | 10 |
| Batch window | 5 s |
| Cold start | ~250 ms |
| Warm execution | ~40 ms × record (DDB UpdateItem) |
| Concurrencia | Hasta 100 invocaciones paralelas |

Más rápido que `gse-sample-reception-notifier` porque no hay notify externo.

---

## Security

| Concern | Mitigación |
|---|---|
| Permisos DDB | Solo `UpdateItem` sobre la tabla |
| Permisos S3 | **Ninguno** — solo el key del event |
| Cross-enterprise | El key embebe enterprise_id |

---

## Dependencies

| Servicio | Operación |
|---|---|
| SQS | runtime gestiona |
| DynamoDB | `UpdateItem` |
| CloudWatch Logs | Write |

---

## Idempotencia

**Mensaje SQS duplicado:** ADD se aplica 2 veces → `samples_anonymized` queda inflado.

**Impacto:** `samples_anonymized > samples_expected` cosmético. Barrier sigue cerrando (`>=`).

**Recomendación:** mismo enfoque que `gse-sample-reception-notifier` — aceptar sobre-conteo en POC. Si se decide dedup formal por `sample_id`, aplicar la misma estrategia aquí.

---

## Edge cases

| Caso | Comportamiento |
|---|---|
| Anonymizer overwrite el mismo sample | 2 PUT events → 2 ADD → samples_anonymized inflado. Cosmético |
| Anonymizer escribe en path que no matchea ningún cycle (orphan) | STATION not found → WARN, descartar |
| Sample llega a `gse-anonymized` sin haber pasado por `gse-raw` (bug del Anonymizer) | Igual incrementa el contador. Si lo hace antes que `samples_received`, podría darse el caso `anonymized > received`. Cosmético si nadie audita esa relación |
| CYCLE ya `complete` cuando llega un anonymized tardío | UpdateItem se aplica igual; `gse-station-status` no transiciona porque ya está en `complete` (conditional fail) |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | Parser del S3 event + key validation | S |
| 2 | DDB UpdateItem con ADD | S (es muy simple) |
| 3 | Tests unitarios | S |
| 4 | Test de batching + idempotencia | S |
