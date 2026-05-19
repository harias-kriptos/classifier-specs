# S3 Buckets — Phase 2

3 buckets relevantes a Phase 2: 1 compartido con Phase 1 (output) y 2 propios.

---

## 1 · `suspicious_crown_jewels` (compartido con Phase 1)

**Owner:** Phase 1
**Rol en Phase 2:** Trigger
**Físicamente:** la infra POC actual lo tiene como `kriptos-{env}-crown-jewels`. Renombrar a `suspicious-crown-jewels` es un cambio menor sugerido (ver TBD #8 en [README](../README.md#tbds-explícitos)).

### Estructura

```
{enterprise_id}/{station_id}/crown_jewels.jsonl
```

### Contenido

NDJSON UTF-8, una entrada por archivo matched por la EMR de Phase 1:

```jsonl
{"name":"Q1-Report","path":"/Users/foo/Finance/","size":245780,"extension":"pdf","modified_date":"2026-04-14T09:15:22Z","matched_keywords":["financial"]}
```

### Metadata

Hereda los `x-amz-meta-*` del tree original (ver [phase1/overview.md](../phase1/overview.md#s3-object-metadata-contract)).

### Eventos

| Evento | Consumer (Phase 2) |
|---|---|
| `PutObject` con suffix `crown_jewels.jsonl` | EventBridge → `gse-crown-cycle-queue` → `gse-cycle-init` |

### Edge case crítico

**Stations con 0 matches:** la EMR `joyas-priorizer` actualmente **no escribe output** si no hay matches. Esto rompe el barrier de Phase 2 porque:
- KEM dice `stations_expected = 5`
- EMR escribe solo 3 archivos (las 2 stations sin matches no producen nada)
- `gse-cycle-init` crea STATION solo para las 3 → CYCLE `stations_completed` queda atascado en 3, nunca llega a 5

**Fix obligatorio:** la EMR debe escribir un `crown_jewels.jsonl` **vacío** cuando no hay matches. Cambio mínimo en `joyas-priorizer/job.py`. **Bloquea Phase 2.**

---

## 2 · `gse-raw`

**Owner:** Phase 2
**Físico:** `kriptos-{env}-gse-raw`
**Rol:** Drop zone para los samples crudos del agente.

### Estructura

```
{enterprise_id}/{station_id}/{cycle_id}/{request_type}/sample_NNN.json
```

### Writers

| Writer | Mecanismo |
|---|---|
| PC Agent | Pre-signed URL via `s3-uploader` (existente) |
| Cloud Agent | PUT directo con IAM role |

### Readers

| Reader | Operación |
|---|---|
| Anonymizer (caja negra) | `GetObject` |

> Phase 2 (lambdas) **NO lee** este bucket — solo procesa los S3 events. El contenido del sample lo consume el Anonymizer.

### Configuración

| Parámetro | Valor |
|---|---|
| Versioning | Enabled |
| Encryption | SSE-KMS o SSE-S3 |
| Public access | Block all |
| EventBridge notifications | Enabled |
| Lifecycle rule | Delete después de 7 días (samples crudos no se guardan) |
| CORS | No requerido (no hay frontend que lo lea directo) |

### Eventos

| Evento | Consumer |
|---|---|
| `PutObject` con suffix `.json` | EventBridge → `gse-sample-reception-queue` → `gse-sample-reception-notifier` |

### Pre-signed URL config (para PC Agent)

| Parámetro | Valor |
|---|---|
| Operation | `put_object` |
| Expiration | 1 hour |
| Headers firmados | `Content-Type=application/json` + `x-amz-meta-cycle-id`, `x-amz-meta-sample-id` |

> **Quién genera el pre-signed URL:** TBD. Opciones:
> - Lambda nueva `gse-sample-upload-init` (reusable, escala bien)
> - El propio agente lo pide al Signal Handler (si ese canal lo permite)
> - Agente firma con sus propias credenciales (no aplica para PC Agent)
>
> Recomendación: empezar con Lambda dedicada cuando el contrato del agente lo requiera. No bloqueante para POC con Cloud Agent.

---

## 3 · `gse-anonymized`

**Owner:** Phase 2
**Físico:** `kriptos-{env}-gse-anonymized`
**Rol:** Drop zone para los samples ya anonimizados, escritos por la caja negra del Anonymizer.

### Estructura

```
{enterprise_id}/{station_id}/{cycle_id}/{request_type}/sample_NNN.json
```

> Mismo path que `gse-raw` (espejado por el Anonymizer).

### Writers

| Writer | Mecanismo |
|---|---|
| Anonymizer (caja negra) | `PutObject` |

### Readers

| Reader | Operación |
|---|---|
| Downstream LLM (caja negra) | `GetObject` (vía prefix `{ent}/{cycle_id}/`) |

### Configuración

| Parámetro | Valor |
|---|---|
| Versioning | Enabled |
| Encryption | SSE-KMS o SSE-S3 |
| Public access | Block all |
| EventBridge notifications | Enabled |
| Lifecycle rule | Delete después de 30 días (post-clasificación, valor histórico bajo) |

### Eventos

| Evento | Consumer |
|---|---|
| `PutObject` con suffix `.json` | EventBridge → `gse-sample-anonymizer-queue` → `gse-sample-anonymizer-notifier` |

---

## Resumen / matriz de acceso

| Bucket | Phase 2 lambdas | Anonymizer (caja negra) | LLM (caja negra) | Agente |
|---|---|---|---|---|
| `suspicious_crown_jewels` | `gse-cycle-init` GET | — | — | — |
| `gse-raw` | event consumer (sin GET) | GET | — | PUT (signed URL o IAM) |
| `gse-anonymized` | event consumer (sin GET) | PUT | GET | — |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | Crear `gse-raw` con Terraform | S |
| 2 | Crear `gse-anonymized` con Terraform | S |
| 3 | Renombrar (o duplicar) `crown_jewels` → `suspicious_crown_jewels` (decidir) | S |
| 4 | EventBridge notifications enabled en los 3 | S |
| 5 | Lifecycle rules (7 días raw, 30 días anonymized) | S |
| 6 | Bucket policy: Anonymizer (otra cuenta?) puede leer raw + escribir anonymized | M (depende del setup del otro equipo) |
| 7 | Bucket policy: LLM puede leer anonymized | M (idem) |
| 8 | **Fix Phase 1 EMR:** escribir `crown_jewels.jsonl` vacío para stations sin matches | S — **bloquea Phase 2** |
| 9 | (Opcional) Lambda `gse-sample-upload-init` para pre-signed URLs del PC Agent | M |
