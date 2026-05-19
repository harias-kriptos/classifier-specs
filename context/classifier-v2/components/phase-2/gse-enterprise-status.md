# gse-enterprise-status

**Type:** Lambda (runtime TBD)
**Trigger:** EventBridge Pipe sobre DDB Stream de `gse-cycles-samples`, filtrado a CYCLE items
**Purpose:** Cierra el CYCLE cuando todas las stations terminaron, y notifica al downstream LLM (caja negra).

---

## Trigger configuration

**EventBridge Pipe:**

```yaml
source: arn:aws:dynamodb:...:table/gse-cycles-samples/stream/...
filter:
  Patterns:
    - eventName: ["MODIFY"]
      dynamodb:
        NewImage:
          SK:
            S: [{ prefix: "CYCLE#" }]
target: arn:aws:lambda:...:gse-enterprise-status
batch_size: 10
maximum_batching_window_in_seconds: 5
```

> Filtra a CYCLE items, eventName MODIFY (ignoramos INSERT — al crear el cycle todavía no hay stations completadas).

---

## Input

**Source:** Batch de DDB Stream records:

```json
{
  "eventID": "...",
  "eventName": "MODIFY",
  "dynamodb": {
    "Keys": {
      "PK": { "S": "ent-001" },
      "SK": { "S": "CYCLE#0ce84cb1-..." }
    },
    "NewImage": {
      "PK": {"S": "ent-001"},
      "SK": {"S": "CYCLE#0ce84cb1-..."},
      "cycle_id": {"S": "0ce84cb1-..."},
      "process_type": {"S": "crown"},
      "status": {"S": "collecting"},
      "stations_expected": {"N": "5"},
      "stations_completed": {"N": "5"},
      ...
    },
    "OldImage": {
      "stations_completed": {"N": "4"},
      ...
    }
  }
}
```

---

## Output

### Side effect en DDB

Si el barrier cierra: `UpdateItem` conditional SET `status="complete"`, `completed_at=now`.

### Side effect externo

Notificación al **LLM Process Queue** (caja negra · canal TBD — ver [external-contracts.md](external-contracts.md#llm-process-queue)).

Payload publicado:

```json
{
  "cycle_id": "0ce84cb1-...",
  "enterprise_id": "ent-001",
  "process_type": "crown",
  "stations_completed": 5,
  "samples_anonymized_total": 312,
  "anonymized_prefix": "kriptos-{env}-gse-anonymized/ent-001/0ce84cb1-.../",
  "completed_at": "2026-04-22T12:34:56Z"
}
```

> `samples_anonymized_total` requiere un Query a STATION items para sumar — opcional. Si encarece, omitir y dejar que el LLM cuente al leer S3.

---

## Processing logic

```
Por cada record en batch:
   1. img = record.dynamodb.NewImage
   2. enterprise_id = img.PK
   3. cycle_id = img.cycle_id
   4. process_type = img.process_type

   5. Skip si img.status == "complete"     (idempotencia rápida)
   6. expected = int(img.stations_expected)
   7. completed = int(img.stations_completed)

   8. Si completed < expected:
        # Aún no cierra
        log DEBUG, continue

   9. Conditional close de CYCLE:
        ddb.update_item(
          Key={"PK": enterprise_id, "SK": f"CYCLE#{cycle_id}"},
          UpdateExpression="SET #status = :complete, completed_at = :now",
          ConditionExpression="#status <> :complete AND stations_completed >= stations_expected",
          ExpressionAttributeValues={
            ":complete": "complete",
            ":now": iso_now()
          },
          ExpressionAttributeNames={"#status": "status"}
        )
        Si ConditionalCheckFailed → ya cerrado o expectativa cambió. Continue.

  10. Si la conditional pasó (esta es la invocación que cerró el CYCLE):
        # (Opcional) sumar samples_anonymized total
        total = sum_anonymized(enterprise_id, cycle_id)

        # NOTIFY downstream LLM
        notify_llm_queue({
          cycle_id, enterprise_id, process_type,
          stations_completed: completed,
          samples_anonymized_total: total,
          anonymized_prefix: f"s3://kriptos-{env}-gse-anonymized/{enterprise_id}/{cycle_id}/",
          completed_at: iso_now()
        })

  11. Log INFO: cycle closed con metrics
```

---

## Validations

| Validación | Acción si falla |
|---|---|
| NewImage presente | Skip si REMOVE (TTL cleanup) |
| Atributos numéricos esperados (`stations_expected`, `stations_completed`) | Asumir 0, log WARN |
| `process_type` presente | Asumir `unknown`, log WARN, igual notificar |

---

## Error handling

| Escenario | Acción | Log | Retry |
|---|---|---|---|
| NewImage incompleta | Skip | WARN | No |
| ConditionalCheckFailed (ya cerrado o cuentas no cuadran) | No-op | INFO | No es error |
| LLM Queue notify fail | Reintentar (Pipe retry) | ERROR | Pipe retry, eventualmente DLQ |
| DDB throttle | Reintentar | WARN | Pipe retry |
| Lambda timeout | Pipe retry | ERROR | DLQ tras N |

**Importante:** si el notify al LLM falla pero el CYCLE ya está marcado `complete`, el LLM no se entera. Reintentos deberían venir del Pipe retry, pero después del DLQ podría requerir reaper manual.

**Mitigación:** considerar SET `status="complete"` SOLO después de que el notify al LLM tenga éxito. Trade-off: complejidad extra. Recomendación POC: aceptar el caso borde, alertar en DLQ.

---

## Logging

| Evento | Level | Campos |
|---|---|---|
| Batch recibido | INFO | record_count |
| Cycle aún no cierra | DEBUG | cycle_id, completed, expected |
| Cycle cerrado (1ª vez) | INFO | enterprise_id, cycle_id, process_type, stations_completed |
| Cycle ya estaba cerrado | INFO | cycle_id |
| LLM notify ok | INFO | cycle_id |
| LLM notify fail | ERROR | cycle_id, exception |
| DDB error | ERROR | exception |

---

## Configuration

| Env var | Ejemplo | Descripción |
|---|---|---|
| `DDB_TABLE` | `gse-cycles-samples` | Tabla DDB |
| `LLM_QUEUE_TARGET` | `arn:aws:sqs:...:llm-process-queue` (placeholder) | Canal TBD |
| `ANONYMIZED_BUCKET_NAME` | `kriptos-{env}-gse-anonymized` | Para construir prefix |
| `INCLUDE_TOTAL_SAMPLES` | `false` | Si `true`, hace Query extra para sumar samples_anonymized |

---

## Performance

| Métrica | Esperada |
|---|---|
| Memoria | 256 MB |
| Timeout | 30 s |
| Batch size | 10 records |
| Cold start | ~250 ms |
| Warm execution | ~50 ms × record (sin total) / ~150 ms × record (con total — Query a STATIONs) |

---

## Security

| Concern | Mitigación |
|---|---|
| Permisos DDB | `UpdateItem` (conditional) y opcionalmente `Query` |
| Permisos al LLM Queue | Solo el canal TBD (SendMessage / Publish) |

---

## Dependencies

| Servicio | Operación |
|---|---|
| DDB Stream (vía Pipe) | Read |
| DynamoDB | `UpdateItem`, opcional `Query` |
| LLM Queue (TBD) | Send |
| CloudWatch Logs | Write |

---

## Idempotencia

- Stream record duplicado → conditional fail → no-op. ✅
- Múltiples records del mismo CYCLE en el mismo batch → solo el primero pasa la conditional. ✅
- Race con otra invocación (distinto batch) → solo una pasa la conditional. ✅
- **Notify al LLM:** si la conditional pasa pero el notify falla, próximo retry vuelve a pasar la conditional? **NO** — `status` ya es `complete` → conditional `<> :complete` falla → notify no se reintenta.

**Trampa potencial:** si quieres garantizar at-least-once del notify al LLM, debes:
- Opción 1: notify primero, luego SET status (riesgo de notify duplicado pero LLM debe ser idempotente).
- Opción 2: usar transactional outbox pattern (escribir mensaje pendiente en DDB, otro Lambda lo despacha).

**Recomendación POC:** Opción 1 — el LLM debe ser idempotente por `cycle_id`. Si el LLM no lo es, escalar a Opción 2.

---

## Edge cases

| Caso | Comportamiento |
|---|---|
| `stations_expected = 0` (KEM no devolvió stations) | INSERT del CYCLE no dispara este Lambda (filter ignora INSERT). Necesita que algún MODIFY suceda. **Bug potencial:** cycle queda en `collecting` para siempre. **Fix:** cycle-init debe cerrar inmediatamente si N=0, o este filter debe incluir INSERT |
| Race: dos increments simultáneos llevan stations_completed de 4 a 5 (con expected=5) | Ambos generan stream records. El primero que llega aquí pasa la conditional, el segundo falla. ✅ |
| `stations_completed` > `stations_expected` (sobre-conteo) | Cierra. La conditional `>=` lo permite |
| Cycle sin process_type (bug) | Notifica al LLM con `process_type=unknown` |
| LLM Queue caída | Notify falla, mensaje a DLQ. El cycle queda `complete` en DDB pero LLM no procesa. Reaper / alertas necesarios |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | EventBridge Pipe con filtro SK prefix CYCLE# | S |
| 2 | Lambda con parser de stream record | S |
| 3 | Lógica de barrier + conditional close | S |
| 4 | Stub del LLM notify (logger) hasta contrato | S |
| 5 | Conectar LLM real | M (bloqueado por equipo LLM) |
| 6 | Decidir orden notify-then-set vs set-then-notify | S |
| 7 | Tests unitarios | M |
| 8 | Test con `stations_expected=0` (validar filter incluye INSERT si necesario) | S |
| 9 | Decidir si incluir `samples_anonymized_total` en payload (tradeoff costo) | S |
