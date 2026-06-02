# Decisiones cerradas — Fase 2

> Cerradas: **2026-05-23** en sesión con Haroldo (después de cerrar Fase 1).
> Aplican a las 6 specs de Fase 2: KT-17028, KT-17029, KT-17030, KT-17031, KT-17032, KT-17033.
> Las specs en `specs-staging/` deben leerse junto con este doc.

---

## 1. Decisiones técnicas (internas)

| # | Pregunta | Decisión |
|---|---|---|
| D17 | KT-17028 — Modelo de STATION row entre Fase 1 y Fase 2 | **UPDATE la misma STATION row, agregar atributos de Fase 2**. Mismo `SK=STATION#{sta}#{cycle}`. La STATION es la unidad atómica de trabajo a través de TODO el pipeline; no se duplica. |
| D18 | KT-17028 — Re-consulta KEM en Fase 2 | **No re-consulta**. La info de stations viene del manifest (lo que el cliente confirmó). Si stations cambiaron entre Fase 1 y Fase 2, eso afecta al próximo cycle, no a éste. |
| D19 | KT-17032 / KT-17009 — Counters y sub-estados | **NO tocar Fase 1**. Agregar nuevos campos a STATION/CYCLE para Fase 2:<br>• `STATION.sampling_status`: sub-estados `requested → uploading → sample_recolected → sample_anonymized`<br>• `STATION.samples_expected, samples_received, samples_anonymized, samples_skipped`: counters Fase 2<br>• `CYCLE.stations_sample_anonymized`: NEW counter para barrier Fase 2.<br>`CYCLE.stations_completed` y `STATION.scan_status` quedan intactos (Fase 1). |
| D20 | KT-17025 / KT-17032 — Filter del Pipe (state lambdas) | **Filter por atributo** en el Pipe pattern:<br>• KT-17025 (crown-enterprise-barrier): filter `NewImage.scan_status = "complete"`.<br>• KT-17032 (gse-station-status): filter `NewImage.sampling_status exists`.<br>Cada Lambda solo ve eventos de su fase. Menos invocaciones desperdiciadas. |
| D21 | KT-17033 — Estrategia publish al LLM Process Queue | **Publish-first, set status después**. Si el publish falla → SQS retry del Pipe → eventual DLQ + alarma. **Contrato con Equipo IA: el LLM debe ser idempotente por `cycle_id`** (gestión de duplicados es responsabilidad de ellos, son caja negra). |
| D22 | KT-17029 — Generación de `sample_id` | **Filename NNN** del archivo (`sample_001.json` → sample_id=`001`). Simple, sin código extra. El path S3 completo (`{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json`) es la fuente de verdad para dedupe. |
| D23 | Formato de samples en `gse-raw/` | **Samples son `.json` singular** (un sample = un archivo S3, un objeto JSON con chunk + metadata de UN file). NO son `.jsonl`. Trees/keywords/matches sí son `.jsonl` porque tienen múltiples records por archivo. |
| D24 | KT-17031 — Auth de `/v2/gse/request-complete` | **API key compartida con `/v2/tree/init`** (la que ya usa el agente para KT-16612). Simple, consistente, ya validado. Limitación conocida: una key comprometida afecta ambos endpoints (aceptable MVP). |
| D25 | KT-17033 — Formato del `anonymized_prefix` en payload al LLM | **S3 URI completo** `s3://kriptos-{env}-gse-anonymized/{ent}/{cycle_id}/`. Self-contained, sin acoplamiento de naming convention entre equipos. El LLM hace GET directo. |
| D26 | KT-17009 / cleanup — Política de retención de DDB rows | **TTL maneja el cleanup**. Al cerrar CYCLE (status=complete), gse-enterprise-status setea `ttl = now + 90d` en CYCLE + cascade a STATION + REQUEST rows. DDB los borra automáticamente. 90 días de auditoría histórica disponibles. |

## 2. Decisiones externas pendientes (Equipo IA + DevOps)

Estas 4 NO se pueden cerrar acá — necesitan coordinación con los respectivos equipos. **No bloquean Skill 04 inmediato** porque cada Lambda tiene stub mientras tanto.

| # | Pregunta | Owner externo | Bloquea a |
|---|---|---|---|
| E-F2-1 | Canal del **Signal Handler** (cómo se le notifica al agente del cycle) | Equipo IA | KT-17028 deploy real (stub con log mientras tanto) |
| E-F2-2 | Canal del **Anonymizer** (cómo se le notifica de cada sample en gse-raw) | Equipo IA | KT-17029 deploy real |
| E-F2-3 | Canal del **LLM Process Queue** (cómo se le notifica del cycle cerrado) | Equipo IA | KT-17033 deploy real |
| E-F2-4 | WAF rules sobre `/v2/gse/request-complete` para prevenir abuso | DevOps | KT-17021 hardening post-MVP |

Los 3 canales del Equipo IA pueden ser SNS topic, SQS queue, HTTP webhook, o invocación directa de Lambda — TBD según preferencia del Equipo IA. Mientras entregan los ARNs/endpoints, los Lambdas funcionan con stubs que loguean el payload.

## 3. Modelo de datos consolidado (DDB classifier-cycles-state)

Reflejando decisiones D17-D19:

### STATION row (evoluciona a través de las dos fases)

```
PK: enterprise_id
SK: STATION#{station_id}#{cycle_id}

# Fase 1 fields (escritos por crown-candidates-indexer KT-17024)
scan_status: "scanning" | "complete"
candidates_count: int
barrier_counted: bool          # exactly-once flag para KT-17025
scan_completed_at: timestamp

# Fase 2 fields (agregados por gse-cycle-init KT-17028 al iniciar Fase 2)
sampling_status: "requested" | "uploading" | "sample_recolected" | "sample_anonymized"
samples_expected: int
samples_received: int          # incrementado por KT-17029
samples_anonymized: int        # incrementado por KT-17030
samples_skipped: int           # incrementado por KT-17031
files_to_sample: [{path, size}]  # del manifest
sample_content_size: int       # chunk size
sampling_complete_at: timestamp
```

### CYCLE row

```
PK: enterprise_id
SK: CYCLE#{cycle_id}

# Fields generales
status: "scanning" | "stations_complete" | "confirmed" | "phase2_collecting" | "phase2_skipped" | "complete"
process_type: "crown_validated" | "classification" | ...
created_at, ready_at, confirmed_at, confirmed_by, completed_at

# Fase 1 counters (escritos por KT-17024 y KT-17025)
stations_expected: int          # de KEM
stations_completed: int         # NEW: count de STATIONs con scan_status="complete"
candidates_count: int
approved_count, rejected_count, manually_added_count: int

# Fase 2 counters (escritos por KT-17032 y KT-17033)
stations_sample_anonymized: int # NEW: count de STATIONs con sampling_status="sample_anonymized"

# TTL
ttl: int  # epoch seconds, set al cerrar (now + 90d)
```

### REQUEST row (Fase 2 solo)

```
PK: enterprise_id
SK: REQUEST#{station_id}#{cycle_id}#{request_type}

request_type: "crown_jewels" | ...
files_to_sample: [{path, size}]
sample_content_size: int
total_samples_uploaded: int    # del body de POST /v2/gse/request-complete
samples_skipped: int
skipped_reasons: [...]
status: "requested" | "sent"
request_complete_at: timestamp
ttl: int
```

### Filters del Pipe (state lambdas)

```
# KT-17025 crown-enterprise-barrier
{
  "eventName": ["INSERT", "MODIFY"],
  "dynamodb": {"NewImage": {
    "SK": {"S": [{"prefix": "STATION#"}]},
    "scan_status": {"S": ["complete"]}
  }}
}

# KT-17032 gse-station-status
{
  "eventName": ["INSERT", "MODIFY"],
  "dynamodb": {"NewImage": {
    "SK": {"S": [{"prefix": "STATION#"}]},
    "sampling_status": {"S": ["uploading", "sample_recolected", "sample_anonymized"]}
  }}
}

# KT-17033 gse-enterprise-status
{
  "eventName": ["MODIFY"],
  "dynamodb": {"NewImage": {
    "SK": {"S": [{"prefix": "CYCLE#"}]},
    "status": {"S": ["phase2_collecting"]}
  }}
}
```

---

## 4. Estado final de Fase 2

**9 decisiones técnicas cerradas + 4 decisiones externas identificadas con stubs.**

Las 6 specs de Fase 2 están listas para arrancar Skill 03 (Plan) → Skill 04 (TDD) apenas DevOps cree los recursos shared (DDB ya está incluida en KT-17009 con modelo expandido, buckets gse-raw/anonymized en KT-17017, etc.).

Las 3 dependencias con Equipo IA (Signal Handler, Anonymizer, LLM Process Queue) **no bloquean implementación de código** — los Lambdas tienen stubs que loguean el payload mientras se cierran los canales reales con el Equipo IA.
