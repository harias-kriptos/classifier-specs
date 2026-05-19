# gse-request-complete

**Type:** Lambda (runtime TBD)
**Trigger:** API Gateway HTTP — `POST /v2/gse/request-complete`
**Purpose:** Endpoint que el agente llama cuando termina de subir todos los samples de una `request_type`. Marca el REQUEST como `sent`, registra `samples_skipped` (los archivos que el agente no pudo procesar), y opcionalmente declara la STATION cerrada si no había nada que procesar (`samples_expected = 0`).

---

## Input

**Source:** API Gateway HTTP POST con body JSON:

```json
{
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "0ce84cb1-0e1a-4b92-bf77-738b2f0a1b7f",
  "request_type": "crown_jewels",
  "total_samples_uploaded": 47,
  "samples_skipped": 3,
  "skipped_reasons": [
    { "path": "/Users/foo/locked.pdf", "reason": "locked_by_other_process" },
    { "path": "/Users/foo/perm.pdf",   "reason": "permission_denied" },
    { "path": "/Users/foo/missing.pdf","reason": "file_not_found" }
  ]
}
```

| Campo | Tipo | Required | Descripción |
|---|---|---|---|
| `enterprise_id` | string | sí | Match con DDB |
| `station_id` | string | sí | Match con DDB |
| `cycle_id` | string | sí | Match con DDB |
| `request_type` | string | sí | Match con SK del REQUEST |
| `total_samples_uploaded` | number | sí | Cuántos samples subió el agente (debe coincidir con `samples_received` modulo retries) |
| `samples_skipped` | number | sí (puede ser 0) | Cuántos archivos el agente NO pudo procesar |
| `skipped_reasons` | array | no | Detalle por path (auditoría) |

---

## Output

**Success (200):**

```json
{
  "ok": true,
  "request_status": "sent",
  "samples_expected": 50,
  "samples_received": 47,
  "samples_anonymized": 30,
  "samples_skipped": 3
}
```

**Error responses:**

| Status | Cuándo | Body |
|---|---|---|
| 400 | Body inválido / campos faltantes | `{"error":"validation_failed","details":[...]}` |
| 404 | REQUEST no existe en DDB | `{"error":"request_not_found"}` |
| 409 | REQUEST ya estaba en `sent` o `complete` (idempotencia ok pero diferente a primer call) | `{"error":"already_completed","current_status":"complete"}` |
| 500 | DDB error | `{"error":"internal_error"}` |

---

## Processing logic

```
1. Validar body (schema)

2. UpdateItem REQUEST conditional:
     Key: PK=enterprise_id, SK=REQUEST#{station_id}#{cycle_id}#{request_type}
     UpdateExpression:
       SET #status = :sent,
           total_samples_uploaded = :total,
           samples_skipped = :skipped,
           skipped_reasons = :reasons,
           request_complete_at = :now
     ConditionExpression:
       attribute_exists(SK) AND #status = :requested
     ExpressionAttributeValues:
       :sent="sent", :requested="requested",
       :total=body.total_samples_uploaded,
       :skipped=body.samples_skipped,
       :reasons=body.skipped_reasons,
       :now=iso_now()

   Si ConditionalCheckFailed:
     - GetItem para saber si está en "sent" o "complete" o "request_not_found"
     - Si "sent" o "complete" → 409 con current_status
     - Si attribute_not_exists → 404

3. UpdateItem STATION:
     Key: PK=enterprise_id, SK=STATION#{station_id}#{cycle_id}
     UpdateExpression: ADD samples_skipped :n
     ExpressionAttributeValues: {":n": body.samples_skipped}
   (Acumula al contador de la station — el barrier de gse-station-status lee esto)

4. Edge case: si body.total_samples_uploaded == 0 AND body.samples_skipped == samples_expected
   → no hay nada que esperar del Anonymizer
   → el ADD del paso 3 hace que el DDB Stream dispare gse-station-status
   → gse-station-status verá (anonymized=0 + skipped==expected) → cierra STATION

5. Devolver 200 con counters actuales
```

**Idempotencia:** la conditional `status = "requested"` previene doble-aplicación. Llamadas duplicadas devuelven 409.

---

## Validations

### Schema

1. JSON parseable.
2. Todos los campos required presentes.
3. `total_samples_uploaded >= 0`, `samples_skipped >= 0`.
4. `skipped_reasons` opcional pero si existe, debe ser array de `{path: string, reason: string}`.
5. `request_type` debe estar en lista permitida (`crown_jewels`, futuros). Validación contra env `ALLOWED_REQUEST_TYPES_JSON`.

### Business

6. Enterprise/station/cycle deben existir (implícito por la conditional).
7. **NO** validamos que `total_samples_uploaded == samples_received` — pueden diferir por retries del agente o por dedup. El barrier real usa `samples_anonymized + samples_skipped`.

---

## Error handling

| Escenario | Status | Acción |
|---|---|---|
| Body inválido | 400 | Devolver detalles de validación |
| REQUEST no existe | 404 | Devolver error |
| REQUEST ya en `sent`/`complete` | 409 | Devolver current_status (idempotencia tolerada) |
| DDB throttle | 503 con Retry-After | Cliente reintenta |
| DDB ConditionalCheckFailed por race (otro caller cerró) | 409 | Devolver current_status |
| Lambda timeout (30s) | 504 | API GW devuelve, agente reintenta |

**Sin DLQ** porque es síncrono (el cliente reintenta).

---

## Logging

| Evento | Level | Campos |
|---|---|---|
| Request recibida | INFO | enterprise_id, station_id, cycle_id, request_type, total, skipped |
| REQUEST cerrado | INFO | request_type, current counters |
| REQUEST ya cerrado (idempotencia) | INFO | current_status |
| REQUEST not found | WARN | enterprise_id, station_id, cycle_id, request_type |
| Validación fallida | WARN | error_details |
| DDB error | ERROR | exception |

---

## Configuration

| Env var | Ejemplo | Descripción |
|---|---|---|
| `DDB_TABLE` | `gse-cycles-samples` | Tabla DDB |
| `ALLOWED_REQUEST_TYPES_JSON` | `["crown_jewels"]` | Whitelist de tipos válidos |
| `MAX_SKIPPED_REASONS_BYTES` | `100000` | Cap defensivo (DDB item < 400 KB) |

---

## Performance

| Métrica | Esperada |
|---|---|
| Memoria | 256 MB |
| Timeout | 30 s (real < 200 ms) |
| Cold start | ~250 ms |
| Warm execution | ~80 ms (1 conditional UpdateItem + 1 UpdateItem ADD) |

---

## Security

| Concern | Mitigación |
|---|---|
| Auth en API GW | API key + WAF (TODO antes de producción) |
| `enterprise_id` spoofing | El agente lo manda; en producción debe validarse contra el cert/auth del agente |
| Rate limiting | API GW throttling per API key |
| Permisos DDB | Solo `UpdateItem` y `GetItem` sobre la tabla |

---

## Dependencies

| Servicio | Operación |
|---|---|
| API Gateway HTTP | route `POST /v2/gse/request-complete` |
| DynamoDB | `UpdateItem` (conditional), `GetItem` |
| CloudWatch Logs | Write |

---

## Idempotencia

- Misma request 2× → segundo call falla la conditional `status="requested"` → devuelve 409 con `current_status`.
- Cliente bien implementado trata 409 como éxito si el status retornado es `sent`/`complete`.
- `samples_skipped` solo se aplica una vez (la primera) gracias a la conditional sobre REQUEST. La segunda no llega al UpdateItem de STATION.

**Caveat:** si la primera llamada falló entre paso 2 (REQUEST sent) y paso 3 (STATION ADD), reintentos posteriores no aplican el ADD porque la conditional sobre REQUEST falla. → **Bug potencial:** la STATION queda con `samples_skipped` sub-contado.

**Mitigación:** usar `TransactWriteItems` para hacer paso 2 + 3 atómicos:

```python
ddb.transact_write_items(TransactItems=[
    { "Update": {<update REQUEST con conditional>} },
    { "Update": {<add a STATION>} }
])
```

Si cualquiera falla, ambos rollback. Recomendado para producción.

---

## Edge cases

| Caso | Comportamiento |
|---|---|
| `samples_skipped > samples_expected` | Permitido (cosmético). El barrier `>= expected` cierra igual |
| `total_samples_uploaded < samples_received` (DDB) | OK — el agente puede haber subido menos de lo que el bucket recibió por retries |
| Request llamada antes de subir todos los samples | El barrier no cierra hasta que `(anonymized+skipped) >= expected`. Si el agente miente con `samples_skipped`, cierra prematuramente. Confiamos en el agente |
| `samples_skipped` reportado pero el agente luego sube ese sample | Inconsistencia: contadores `received` y `skipped` ambos suman ese sample. El barrier sigue funcionando porque `>=` |
| CYCLE ya está `complete` (otro path cerró) | REQUEST se marca `sent` igual; STATION ADD se aplica; status lambdas no transicionan (ya complete) |
| `cycle_id` distinto al actual del enterprise | REQUEST not found → 404. El agente debió leer un cycle_id viejo |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | API GW route + Lambda integration | S |
| 2 | Schema validation (pydantic / jsonschema) | S |
| 3 | DDB conditional UpdateItem en REQUEST | S |
| 4 | DDB ADD en STATION | S |
| 5 | Promover a TransactWriteItems para atomicidad | S |
| 6 | Tests unitarios (schema + DDB mocks) | M |
| 7 | Tests de idempotencia (llamada 2× → 409) | S |
| 8 | API auth (API key) | S |
| 9 | Rate limiting + WAF | M |
