# gse-cycles-samples (DynamoDB)

**Type:** DynamoDB single-table
**Stream:** Enabled · `NEW_AND_OLD_IMAGES`
**Billing:** PAY_PER_REQUEST (recomendado para POC; switch a provisioned cuando haya métricas)

Tabla central de Phase 2. Persiste el estado de los ciclos GSE en 3 niveles (CYCLE, STATION, REQUEST) bajo un mismo PK por enterprise. Sus DDB Streams alimentan dos EventBridge Pipes que disparan los lambdas de cascada (`gse-station-status`, `gse-enterprise-status`).

---

## Esquema

### Primary Key

| Atributo | Tipo | Descripción |
|---|---|---|
| `PK` | String | Siempre `enterprise_id` |
| `SK` | String | Discriminador de nivel — `CYCLE#…` / `STATION#…` / `REQUEST#…` |

### Stream

`StreamSpecification.StreamViewType = NEW_AND_OLD_IMAGES`

Permite a los consumidores (EventBridge Pipes) ver `OldImage` y `NewImage` para filtrar transiciones (ej. ignorar updates donde el contador no cambió).

### TTL

Atributo `ttl` (Number, epoch seconds). Auto-cleanup configurable por record:
- CYCLE / STATION / REQUEST: TTL = `complete_at + 30 días` (set cuando el record cierra).
- Cycles huérfanos: TTL = `created_at + 7 días` (mecanismo de cleanup defensivo).

---

## Records

### Nivel 1 · CYCLE

```
PK: ent-001
SK: CYCLE#0ce84cb1-0e1a-4b92-bf77-738b2f0a1b7f

Atributos:
  cycle_id:             String   "0ce84cb1-..."
  process_type:         String   "crown" | "classification"
  status:               String   "collecting" | "complete"
  stations_expected:    Number   N (snapshot de KEM al crear el cycle)
  stations_completed:   Number   ADD-incrementado por gse-station-status
  created_at:           String   ISO-8601
  completed_at:         String   ISO-8601 (set cuando status="complete")
  source_event:         Map      { source_bucket, source_key, queue_arn } primer disparo
  ttl:                  Number   epoch seconds
```

**Invariantes:**
- Solo puede haber **1 CYCLE en status="collecting"** por `(enterprise_id, process_type)`. Permite cycles concurrentes de distinto type para el mismo enterprise.
- `stations_completed` nunca debe superar `stations_expected`.

### Nivel 2 · STATION

```
PK: ent-001
SK: STATION#station-A#0ce84cb1-...

Atributos:
  station_id:           String   "station-A"
  cycle_id:             String   "0ce84cb1-..."
  status:               String   "requested" | "uploading" | "complete"
  samples_expected:     Number   sum(len(files) for req in requests)  ← set en gse-cycle-init
  samples_received:     Number   ADD-incrementado por gse-sample-reception-notifier
  samples_anonymized:   Number   ADD-incrementado por gse-sample-anonymizer-notifier
  samples_skipped:      Number   ADD-incrementado por gse-request-complete (reportado por agente)
  total_requests:       Number   M = número de request_types para esta station (1 con Modelo A)
  requests_completed:   Number   contador interno (opcional con Modelo A)
  created_at:           String   ISO-8601
  notified_at:          String   ISO-8601 — cuando el Signal Handler aceptó el push
  completed_at:         String   ISO-8601 — set por gse-station-status al cerrar
  ttl:                  Number
```

**Invariantes:**
- `samples_received <= samples_expected` (modulo race con S3 retries — ver [Idempotencia](#idempotencia)).
- `samples_anonymized <= samples_received` (no se puede anonimizar lo que no se recibió).
- `samples_anonymized + samples_skipped <= samples_expected`.
- Transición a `status="complete"` cuando `(anonymized + skipped) >= expected`. Hecha por `gse-station-status` con conditional write.

### Nivel 3 · REQUEST

```
PK: ent-001
SK: REQUEST#station-A#0ce84cb1-...#crown_jewels

Atributos:
  station_id:           String
  cycle_id:             String
  request_type:         String   "crown_jewels" | (futuros)
  files_to_sample:      List     [ { path, size }, ... ]   ← snapshot del crown_jewels.jsonl
  sample_content_size:  Number   bytes a extraer por sample (param del agente)
  status:               String   "requested" | "sent" | "complete"
  total_samples_uploaded: Number reportado por agente vía /v2/gse/request-complete
  samples_skipped:      Number   reportado por agente
  skipped_reasons:      List     [ { path, reason }, ... ]
  created_at:           String
  request_complete_at:  String   ISO-8601 — cuando agente cerró la request
  ttl:                  Number
```

**Invariantes:**
- `status="sent"` cuando agente llamó `/v2/gse/request-complete`. La transición la hace `gse-request-complete` con conditional write.
- `status="complete"` cuando STATION cierra (delegado por `gse-station-status`).
- Modelo A: una sola REQUEST por STATION (hoy crown_jewels). Si Modelo B aparece, hay N por STATION sin cambios estructurales.

---

## Operaciones por Lambda

| Lambda | Operación | Records tocados |
|---|---|---|
| `gse-cycle-init` | `Query` (find open CYCLE), `PutItem` con `attribute_not_exists` (CYCLE), `BatchWriteItem` (STATION + REQUEST) | CYCLE, STATION, REQUEST |
| `gse-sample-reception-notifier` | `UpdateItem ADD samples_received=1` | STATION |
| `gse-sample-anonymizer-notifier` | `UpdateItem ADD samples_anonymized=1` | STATION |
| `gse-request-complete` | `UpdateItem` SET status="sent", ADD samples_skipped, total_samples_uploaded | REQUEST |
| `gse-station-status` | `UpdateItem` conditional SET status="complete", ADD CYCLE.stations_completed=1 | STATION + CYCLE |
| `gse-enterprise-status` | `UpdateItem` conditional SET CYCLE.status="complete" | CYCLE |

---

## Patrones de query

> Los snippets siguientes están en pseudocódigo estilo boto3 por familiaridad. La implementación real se hará en el runtime que decida el equipo backend.

### Find open CYCLE para enterprise + process_type (en `gse-cycle-init`)

Sin GSI — Query directo sobre la tabla:

```
ddb.query(
    KeyConditionExpression="PK = :ent AND begins_with(SK, :prefix)",
    FilterExpression="#status = :collecting AND process_type = :ptype",
    ExpressionAttributeValues={
        ":ent":         {"S": "ent-001"},
        ":prefix":      {"S": "CYCLE#"},
        ":collecting":  {"S": "collecting"},
        ":ptype":       {"S": "crown"},
    },
    ExpressionAttributeNames={"#status": "status"},
)
```

Cada enterprise tiene a lo más unos pocos cycles activos en cualquier momento → query barato.

### Listar STATIONs de un CYCLE (debugging / dashboards)

```python
ddb.query(
    KeyConditionExpression="PK = :ent AND begins_with(SK, :prefix)",
    ExpressionAttributeValues={
        ":ent":    {"S": "ent-001"},
        ":prefix": {"S": "STATION#station-A#0ce84cb1-..."}  # incluir cycle para narrow
    }
)
```

Si necesitas todas las stations de un cycle (sin saber station_id), usa `begins_with(SK, "STATION#")` y filtra por cycle_id.

### Listar REQUESTs de una STATION

```python
ddb.query(
    KeyConditionExpression="PK = :ent AND begins_with(SK, :prefix)",
    ExpressionAttributeValues={
        ":ent":    {"S": "ent-001"},
        ":prefix": {"S": "REQUEST#station-A#0ce84cb1-..."}
    }
)
```

---

## Conditional writes — patrón

### Crear CYCLE (`gse-cycle-init`)

Race entre dos invocaciones que vieron el mismo enterprise sin cycle:

```python
ddb.put_item(
    Item={
        "PK": "ent-001",
        "SK": f"CYCLE#{cycle_id}",
        "status": "collecting",
        "process_type": "crown",
        "stations_expected": N,
        "stations_completed": 0,
        ...
    },
    ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)"
)
# Si falla con ConditionalCheckFailed → otra invocación lo creó. Re-query y usa el existente.
```

### Cerrar STATION (`gse-station-status`)

```python
ddb.update_item(
    Key={"PK": "ent-001", "SK": "STATION#station-A#cycle-id"},
    UpdateExpression="SET #status = :complete, completed_at = :now",
    ConditionExpression="#status <> :complete",
    ExpressionAttributeValues={
        ":complete": {"S": "complete"},
        ":now": {"S": iso_now()}
    },
    ExpressionAttributeNames={"#status": "status"}
)
# Si falla → ya estaba complete (otro stream event lo cerró). No-op.
```

Solo después de éxito, incrementa CYCLE:

```python
ddb.update_item(
    Key={"PK": "ent-001", "SK": f"CYCLE#{cycle_id}"},
    UpdateExpression="ADD stations_completed :one",
    ExpressionAttributeValues={":one": {"N": "1"}}
)
```

Garantiza **al menos una STATION cerrada → al menos un increment de CYCLE.stations_completed**, sin double-counting.

### Cerrar CYCLE (`gse-enterprise-status`)

```python
ddb.update_item(
    Key={"PK": "ent-001", "SK": f"CYCLE#{cycle_id}"},
    UpdateExpression="SET #status = :complete, completed_at = :now",
    ConditionExpression="#status <> :complete AND stations_completed >= stations_expected",
    ...
)
```

Doble candado: solo cierra si está abierto **y** si efectivamente las stations cuadran.

---

## DDB Stream → EventBridge Pipes

### Pipe 1 · STATION updates → `gse-station-status`

**Source:** DDB Stream de `gse-cycles-samples`
**Filter pattern (Pipe-level):**

```json
{
  "eventName": ["MODIFY", "INSERT"],
  "dynamodb": {
    "NewImage": {
      "SK": { "S": [{ "prefix": "STATION#" }] }
    }
  }
}
```

**Target:** `gse-station-status` Lambda
**Batch:** 10 records, 5s window
**Retry:** 3 attempts, DLQ después

> El filtro evita disparar el Lambda con records de CYCLE o REQUEST. Lo demás (decidir si transicionar) lo hace el Lambda con NewImage.

### Pipe 2 · CYCLE updates → `gse-enterprise-status`

```json
{
  "eventName": ["MODIFY"],
  "dynamodb": {
    "NewImage": {
      "SK": { "S": [{ "prefix": "CYCLE#" }] }
    }
  }
}
```

**Target:** `gse-enterprise-status` Lambda
**Batch:** 10 records, 5s window
**Retry:** 3 attempts, DLQ después

---

## Idempotencia

| Operación | Mecanismo |
|---|---|
| Crear CYCLE | `attribute_not_exists` condicional + retry seguro |
| Crear STATION | `attribute_not_exists` condicional |
| Crear REQUEST | `attribute_not_exists` condicional |
| ADD samples_received | **NO idempotente por sí mismo** — si el SQS entrega el mismo S3 event 2 veces, suma 2. Mitigado por sample_id dedup (TBD) o por aceptar el sobre-conteo (recibido > esperado pero (anonimizado+skipped)==expected sigue funcionando) |
| ADD samples_anonymized | Mismo caveat |
| ADD samples_skipped | Idempotente vía `request_complete_at` — solo se aceptan increments si `request_complete_at` no existe |
| SET STATION.status=complete | Conditional `<> complete` |
| SET CYCLE.status=complete | Conditional `<> complete AND stations_completed >= stations_expected` |

**TBD:** mecanismo formal de dedup por `sample_id`. Opciones:
- (a) tabla auxiliar `sample-dedup` con TTL corto, write-once
- (b) `sample_id` como atributo en STATION con `ADD` a un set + check de tamaño (no escalable)
- (c) aceptar el sobre-conteo (cycle cierra cuando anonymized + skipped >= expected, no por igualdad estricta)

Recomendación: **(c) por ahora** — simple, sin nueva tabla, y el conditional `>=` ya lo permite.

---

## Capacidad y costos

| Carga | Justificación |
|---|---|
| Reads/sec | Bajos — solo `gse-cycle-init` hace Query (1 vez por crown_jewels.jsonl). Status lambdas leen NewImage del stream (no consume RCU) |
| Writes/sec | Pico = N stations × M samples/station × 2 (received + anonymized) por ciclo. Para 100 stations × 50 samples = 10K writes en ráfaga |
| Item size | < 4 KB típico (REQUEST con files_to_sample puede ser grande — 5K files × 200 bytes = 1 MB ⇒ partir si > 400 KB) |

**Decisión:** PAY_PER_REQUEST para POC. Migrar a provisioned con auto-scaling cuando haya métricas.

**Alerta:** si `files_to_sample` excede 400 KB (DDB item limit) — necesitamos guardarlo en S3 y referenciar el path en DDB. Ver [TBD #X en overview](overview.md#open-questions).

---

## Operaciones admin

### Reabrir un cycle "atascado"

```bash
# 1. Inspeccionar el cycle
aws dynamodb get-item --table-name gse-cycles-samples \
  --key '{"PK":{"S":"ent-001"},"SK":{"S":"CYCLE#xxx"}}'

# 2. Listar STATIONs incompletas
aws dynamodb query --table-name gse-cycles-samples \
  --key-condition-expression "PK = :ent AND begins_with(SK, :prefix)" \
  --expression-attribute-values '{":ent":{"S":"ent-001"},":prefix":{"S":"STATION#"}}' \
  --filter-expression "#s <> :c AND cycle_id = :cid" \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":c":{"S":"complete"},":cid":{"S":"xxx"}}'

# 3. Decidir: forzar complete (admin) o re-disparar el sample faltante
```

### Backfill (reprocesar Phase 1 sin re-EMR)

```bash
# Re-disparar gse-cycle-init para un crown_jewels.jsonl ya existente
aws s3 cp s3://kriptos-{env}-suspicious-crown-jewels/ent-001/station-A/crown_jewels.jsonl \
          s3://kriptos-{env}-suspicious-crown-jewels/ent-001/station-A/crown_jewels.jsonl \
          --metadata-directive COPY
# El copy in place dispara un PutObject event nuevo
```

---

## Edge cases

| Caso | Comportamiento |
|---|---|
| Mismo crown_jewels.jsonl re-subido | FIFO `MessageDeduplicationId = sha256(bucket+key)` evita duplicados en la cola. Si pasa: `gse-cycle-init` encuentra el CYCLE/STATION existente, conditional fail → no-op |
| KEM dice 5 stations pero solo llegan 3 (otras 0 matches en EMR) | CYCLE.stations_expected=5, stations_completed se queda en 3 → ciclo nunca cierra. **Fix:** Phase 1 debe escribir un crown_jewels.jsonl **vacío** para stations sin matches, garantizando que todas las N producen un evento |
| Agente sube más samples que `samples_expected` | `samples_received` excede `samples_expected`. Cycle igual cierra (barrier es `>=`). Log WARN |
| Agente sube 0 samples y reporta `samples_skipped == samples_expected` | STATION cierra inmediatamente al primer `request-complete` |
| Anonymizer falla en 1 sample → samples_anonymized < samples_expected | Cycle nunca cierra. Reaper Lambda (TBD) marca como `failed` tras N horas |
| Dos process_types concurrentes para mismo enterprise | Permitido por diseño — distinto cycle_id, distinto SK. Conviven sin conflicto |
| Borrado accidental de un STATION record | CYCLE no se entera; cycle queda con `stations_completed < stations_expected`. Solo recuperable manualmente |

---

## Dependencias

| Servicio | Operación | Por qué |
|---|---|---|
| DynamoDB Streams | Read | Alimenta los Pipes |
| EventBridge Pipes | Source filter | Ruta los stream records al Lambda correcto |
| KMS (opcional) | Encrypt | DDB encryption (default AWS-managed key) |

---

## Tareas de implementación

| # | Tarea | Bloquea |
|---|---|---|
| 1 | Definir Terraform de la tabla con stream + TTL | Todo Phase 2 |
| 2 | Crear los 2 Pipes con filtros de prefijo SK | Lambdas de cascada |
| 3 | Probar que el filtro de Pipe descarte correctamente CYCLE vs STATION | gse-station-status / gse-enterprise-status |
| 4 | Decidir si necesitamos GSI para queries cross-enterprise (futuro) | Operativa avanzada |
| 5 | Decidir manejo de `files_to_sample` cuando excede 400 KB | Edge case raro pero posible |
| 6 | Definir mecanismo de dedup por `sample_id` (o aceptar opción (c)) | Idempotencia |
