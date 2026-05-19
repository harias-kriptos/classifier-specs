# gse-station-status

**Type:** Lambda (runtime TBD)
**Trigger:** EventBridge Pipe sobre DDB Stream de `gse-cycles-samples`, filtrado a STATION items
**Purpose:** Centraliza la lógica de "esta STATION ya terminó". Cualquiera de los 3 lambdas que tocan contadores (`received`, `anonymized`, `skipped`) genera un DDB Stream record; este Lambda lee el `NewImage`, decide si la STATION debe transicionar a `complete`, y si sí, escala al CYCLE.

---

## Por qué existe

Tres Lambdas modifican STATION:
- `gse-sample-reception-notifier` → `samples_received++`
- `gse-sample-anonymizer-notifier` → `samples_anonymized++`
- `gse-request-complete` → `samples_skipped += N`

Cualquiera puede ser "el último" que dispara la transición. En lugar de poner la lógica de barrier en los 3 (con riesgo de bugs / divergencia), la centralizamos en este Lambda **post-hoc** vía DDB Stream.

**Trade-off:** hay latencia adicional (~1-2s entre el UpdateItem y el Pipe disparando este Lambda). Aceptable.

---

## Trigger configuration

**EventBridge Pipe:**

```yaml
source: arn:aws:dynamodb:...:table/gse-cycles-samples/stream/...
filter:
  Patterns:
    - eventName: ["MODIFY", "INSERT"]
      dynamodb:
        NewImage:
          SK:
            S: [{ prefix: "STATION#" }]
target: arn:aws:lambda:...:gse-station-status
batch_size: 10
maximum_batching_window_in_seconds: 5
```

> El filtro descarta records de CYCLE/REQUEST. Solo STATION llega aquí.

---

## Input

**Source:** Batch de DDB Stream records (envueltos por el Pipe), cada uno con shape:

```json
{
  "eventID": "...",
  "eventName": "MODIFY",
  "dynamodb": {
    "Keys": {
      "PK": { "S": "ent-001" },
      "SK": { "S": "STATION#station-A#cycle-id" }
    },
    "NewImage": {
      "PK": {"S": "ent-001"},
      "SK": {"S": "STATION#station-A#cycle-id"},
      "station_id": {"S": "station-A"},
      "cycle_id": {"S": "cycle-id"},
      "status": {"S": "uploading"},
      "samples_expected": {"N": "50"},
      "samples_received": {"N": "47"},
      "samples_anonymized": {"N": "47"},
      "samples_skipped": {"N": "3"},
      ...
    },
    "OldImage": { ... },
    "SequenceNumber": "...",
    "StreamViewType": "NEW_AND_OLD_IMAGES"
  }
}
```

---

## Processing logic

```
Por cada record en batch:
   1. img = record.dynamodb.NewImage
   2. enterprise_id = img.PK
   3. station_id = img.station_id
   4. cycle_id = img.cycle_id

   5. Skip si img.status == "complete"   (idempotencia rápida)
   6. expected = int(img.samples_expected)
   7. anonymized = int(img.samples_anonymized)
   8. skipped = int(img.samples_skipped)

   9. Si (anonymized + skipped) < expected:
        # Aún no cerró
        log DEBUG, continue

  10. Conditional close de STATION:
        ddb.update_item(
          Key={"PK": enterprise_id, "SK": f"STATION#{station_id}#{cycle_id}"},
          UpdateExpression="SET #status = :complete, completed_at = :now",
          ConditionExpression="#status <> :complete",
          ExpressionAttributeValues={
            ":complete": "complete",
            ":now": iso_now()
          },
          ExpressionAttributeNames={"#status": "status"}
        )
        Si ConditionalCheckFailed → ya estaba complete (otro stream record en el batch lo cerró). Continue.

  11. Si la conditional pasó (esta es la invocación que cerró la STATION):
        ddb.update_item(
          Key={"PK": enterprise_id, "SK": f"CYCLE#{cycle_id}"},
          UpdateExpression="ADD stations_completed :one",
          ExpressionAttributeValues={":one": 1}
        )

  12. Log INFO: station closed con stations_completed actual del CYCLE
```

**Punto crítico:** el `ADD CYCLE.stations_completed` solo ocurre si la conditional close de STATION pasó. Esto garantiza **exactly-once** del increment a CYCLE — sin double-counting incluso si el stream entrega el record duplicado.

---

## Validations

### Input

1. **NewImage presente:** si `eventName=REMOVE` → skip (TTL cleanup, no relevante).
2. **PK y SK presentes:** debe ser STATION (filter del Pipe ya garantiza).
3. **Atributos numéricos:** `samples_expected`, `samples_anonymized`, `samples_skipped` deben existir (set en cycle-init y notifiers). Si falta alguno → log WARN, asumir 0.

---

## Error handling

| Escenario | Acción | Log | Retry |
|---|---|---|---|
| NewImage incompleta (atributos esperados faltantes) | Asumir 0 / skip | WARN | No |
| DDB ConditionalCheckFailed (STATION ya cerrada) | No-op | INFO | No es error |
| DDB throttle en update | Reintentar | WARN | Pipe retry |
| Lambda timeout | Pipe retry | ERROR | DLQ tras N |
| `stations_completed` ya == `stations_expected` cuando agregamos | OK — `gse-enterprise-status` cerrará el cycle | INFO | No |

---

## Logging

| Evento | Level | Campos |
|---|---|---|
| Batch recibido | INFO | record_count |
| Station aún no cierra | DEBUG | station_id, anonymized, skipped, expected |
| Station cerrada (1ª vez) | INFO | enterprise_id, station_id, cycle_id, expected, anonymized, skipped |
| Station ya estaba cerrada | INFO | station_id (duplicate stream record) |
| CYCLE incrementado | INFO | cycle_id, stations_completed |
| DDB error | ERROR | exception |

---

## Configuration

| Env var | Ejemplo | Descripción |
|---|---|---|
| `DDB_TABLE` | `gse-cycles-samples` | Tabla DDB |

---

## Performance

| Métrica | Esperada |
|---|---|
| Memoria | 256 MB |
| Timeout | 30 s |
| Batch size | 10 records |
| Batch window | 5 s |
| Cold start | ~250 ms |
| Warm execution | ~30 ms × record (1-2 UpdateItem) |
| Concurrencia | 1 invocación por shard del DDB Stream — paralelismo natural por hash del PK |

---

## Security

| Concern | Mitigación |
|---|---|
| Permisos DDB | `UpdateItem` solo en la tabla |
| Permisos Pipe | El Pipe asume rol con permisos de stream + invoke Lambda |
| Cross-enterprise | El record viene del stream, no hay input externo |

---

## Dependencies

| Servicio | Operación |
|---|---|
| DDB Stream (vía Pipe) | Read |
| DynamoDB | `UpdateItem` (conditional + ADD) |
| CloudWatch Logs | Write |

---

## Idempotencia

**Stream record duplicado** (DDB Streams at-least-once vía Pipe):
- Misma STATION en `complete` ya → conditional fail en paso 10 → `ADD CYCLE.stations_completed` no se ejecuta → no double-counting.
- ✅ Garantía: **al menos un increment de CYCLE por STATION cerrada, exactly-once**.

**Multiple records de la misma STATION en el mismo batch:**
- Iteramos uno por uno; el primero hace la conditional close (éxito) + ADD; los siguientes ven `status="complete"` o fallan la conditional. ✅

**Race entre 2 invocaciones (distintos batches del stream):**
- Solo una pasa la conditional. ✅

---

## Edge cases

| Caso | Comportamiento |
|---|---|
| `samples_expected = 0` (station sin archivos) | El primer record del stream (cuando se crea la STATION en cycle-init, eventName=INSERT) ya cumple `0 + 0 >= 0`. STATION cierra inmediatamente. CYCLE incrementado |
| Station con `expected=50` que recibe `anonymized=51` (sobre-conteo por dedup laxa) | Cierra con `(51+0) >= 50`. ✅ |
| `samples_anonymized + samples_skipped > samples_expected` | Cierra. Cosmético |
| Stream record `eventName=INSERT` (cycle-init recién creó la STATION) | Si `expected=0` → cierra. Si `expected>0` → `0+0 < expected`, no cierra. Continue normal |
| `eventName=REMOVE` (TTL cleanup) | Skip explícito |
| Stream lag (records llegan minutos tarde) | Aceptable. CYCLE solo cierra después de procesar todos |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | EventBridge Pipe con filtro de SK prefix STATION# | S |
| 2 | Lambda con parser de DDB Stream record (deserializer) | S |
| 3 | Lógica de barrier + conditional close | S |
| 4 | ADD a CYCLE.stations_completed solo en éxito de conditional | S |
| 5 | Tests unitarios (varios escenarios de stream record) | M |
| 6 | Test de idempotencia con records duplicados en batch | S |
| 7 | Test con `samples_expected=0` (cierre inmediato) | S |
