# External Contracts — Cajas negras de Phase 2

3 componentes son **dependencias externas** (otros equipos). Phase 2 los trata como cajas negras: definimos el contrato (qué le damos / qué esperamos), pero no detallamos su interior.

Este documento existe para que el plan de trabajo identifique claramente **qué bloquea a qué**.

---

## 1 · Signal Handler

**Owner:** Equipo plataforma agente (a confirmar)
**Rol:** Hacer push a la estación del agente del payload de cycle.

### Lo que le damos (Phase 2 → Signal Handler)

Una notificación con el payload completo del cycle por estación:

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

**Quién lo emite:** `gse-cycle-init` Lambda, una vez por STATION creada.

### Lo que esperamos del Signal Handler

1. **Entrega al agente correcto** (`station_id` resuelto a la estación física).
2. **At-least-once** acceptable. El agente debe ser idempotente por `cycle_id`.
3. **Latencia objetivo:** < 60 segundos del trigger al agente.
4. **Fallback** si la estación está offline: persistir el payload y entregarlo al reconectar (TBD: cuánto tiempo retiene).

### Canal de entrega — TBD

Opciones que sabemos viables (sin recomendación, lo decide el otro equipo):
- IoT Core (push real)
- Polling del agente a un endpoint del Signal Handler
- WebSocket persistente

### Canal de Phase 2 → Signal Handler — TBD

Opciones que podemos ofrecer:
- **SNS topic** que ellos suscriban (recomendado por desacople)
- **EventBridge bus** custom
- **SQS** que ellos consuman
- HTTP POST a su endpoint
- Lambda invoke directo

**No bloquea fases 2.A/B/C** — `gse-cycle-init` puede stub-loggear durante desarrollo. Se conecta al final.

### Tareas relacionadas para Phase 2

| # | Tarea | Bloqueado por otro equipo |
|---|---|---|
| 1 | Definir contrato del payload (este documento es la propuesta) | No |
| 2 | Acordar canal con el equipo del Signal Handler | Sí |
| 3 | Implementar el publisher en `gse-cycle-init` | Sí (depende del canal) |
| 4 | Test end-to-end con agente real | Sí (depende del canal y del agente) |

---

## 2 · Anonymizer core

**Owner:** Equipo seguridad / IA (a confirmar)
**Rol:** Anonimizar el contenido de los samples antes de pasarlos al LLM.

### Lo que le damos (Phase 2 → Anonymizer)

Una notificación por sample, con la ubicación en S3:

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

**Quién lo emite:** `gse-sample-reception-notifier` Lambda, una por cada sample que aterriza en `gse-raw`.

### Lo que esperamos del Anonymizer

1. **Lee** el objeto en `gse-raw/{key}`.
2. **Procesa** (anonimización).
3. **Escribe** el resultado en `gse-anonymized/{key}` — **mismo path** (espejado).
4. **Idempotente** por `sample_id` (los mensajes pueden duplicarse).
5. **DLQ propio** del lado del Anonymizer si su procesamiento falla. Phase 2 no se entera; al cycle se le caduca por TTL si nunca cierra.

### Permisos S3 que necesitan

- `s3:GetObject` sobre `gse-raw/*`
- `s3:PutObject` sobre `gse-anonymized/*`

Configurar via bucket policy + cross-account si están en otra cuenta AWS.

### Canal de Phase 2 → Anonymizer — TBD

Mismas opciones que Signal Handler. **Recomendación:** SNS topic propio (`gse-anonymizer-requests`) que ellos suscriban via Lambda. Da fan-out (futuro suscriptor de auditoría) y desacopla.

### Tareas relacionadas para Phase 2

| # | Tarea | Bloqueado por otro equipo |
|---|---|---|
| 1 | Definir contrato del payload | No |
| 2 | Acordar canal | Sí |
| 3 | Coordinar permisos S3 cross-account | Sí |
| 4 | Implementar publisher en `gse-sample-reception-notifier` | Sí (depende del canal) |
| 5 | Test end-to-end (sample → notify → anonymizer escribe → trigger downstream) | Sí |

---

## 3 · LLM Process Queue (+ LLM)

**Owner:** Equipo IA (a confirmar)
**Rol:** Consumir cycles cerrados y disparar la clasificación con LLM.

### Lo que le damos (Phase 2 → LLM)

Una notificación por CYCLE cerrado:

```json
{
  "cycle_id": "0ce84cb1-...",
  "enterprise_id": "ent-001",
  "process_type": "crown",
  "stations_completed": 5,
  "samples_anonymized_total": 312,
  "anonymized_prefix": "s3://kriptos-{env}-gse-anonymized/ent-001/0ce84cb1-.../",
  "completed_at": "2026-04-22T12:34:56Z"
}
```

**Quién lo emite:** `gse-enterprise-status` Lambda, una por CYCLE cerrado.

### Lo que esperamos del LLM

1. **Consume** la notificación.
2. **Lee** los samples anonimizados desde `anonymized_prefix`.
3. **Clasifica** y deja el resultado donde el frontend lo lea (DDB analyses table — fuera del scope de Phase 2).
4. **Idempotente** por `cycle_id`.

### Permisos S3 que necesitan

- `s3:GetObject` + `s3:ListBucket` sobre `gse-anonymized/*`

### Canal de Phase 2 → LLM — TBD

Recomendación: **SQS dedicada** (`llm-process-queue`) que ellos consuman. Da retries y DLQ del lado de ellos. Si prefieren push (Lambda invoke / SNS), es alternativa.

### Tareas relacionadas para Phase 2

| # | Tarea | Bloqueado por otro equipo |
|---|---|---|
| 1 | Definir contrato del payload | No |
| 2 | Acordar canal | Sí |
| 3 | Coordinar permisos S3 cross-account | Sí |
| 4 | Implementar publisher en `gse-enterprise-status` | Sí (depende del canal) |
| 5 | Test end-to-end (cycle cierra → LLM clasifica → resultado en analyses) | Sí |

---

## KEM API

> No es una caja negra "opaca", pero es una **dependencia** que `gse-cycle-init` consume.

**Owner:** Equipo backend (interno o adyacente — confirmar)

### Lo que le pedimos

```http
GET /v2/kem/stations?enterprise_id=ent-001&status=active
Authorization: ApiKey {kem_api_key}
```

### Lo que esperamos

```json
{
  "enterprise_id": "ent-001",
  "stations": [
    { "station_id": "station-A", "agent_type": "windows", "last_seen": "..." },
    { "station_id": "station-B", "agent_type": "cloud",   "last_seen": "..." },
    ...
  ],
  "total": 5
}
```

`gse-cycle-init` solo necesita `total` para `stations_expected`.

### Tareas relacionadas

| # | Tarea | Bloqueado |
|---|---|---|
| 1 | Confirmar contrato del endpoint | KEM team |
| 2 | API key + Secret en Secrets Manager | KEM team |
| 3 | Implementar cliente HTTP en `gse-cycle-init` | No |

---

## Resumen — quién bloquea qué

| Equipo externo | Componente | Bloquea | No bloquea |
|---|---|---|---|
| Signal Handler | Push al agente | `gse-cycle-init` notify · test e2e | Construcción de Lambda |
| Anonymizer | Procesamiento de samples | `gse-sample-reception-notifier` notify · permisos S3 cross-account · test e2e | Construcción de buckets/colas/lambdas |
| LLM | Clasificación | `gse-enterprise-status` notify · permisos S3 · test e2e | Cierre del cycle en DDB |
| KEM | Stations activas | `gse-cycle-init` (sin esto no puede crear CYCLE) | Resto de fases |

**Fase 2.A → 2.C** (foundation + lambdas internas) **NO requiere** estos contratos. Pueden arrancar en paralelo y se stubean los notifiers.

**Fase 2.D** (integración) **sí requiere** los 4 contratos firmes.
