# Tickets de implementación del backend

> **Para:** Haroldo (owner del backend).
> **Contexto:** complemento de [orquestacion-backend.md](orquestacion-backend.md). Esos son tickets para DevOps (infra). Estos son los tickets de **código** que tú vas a implementar — uno por Lambda/EMR, con lógica concreta, interacción con KEM y con cajas negras del equipo AI.

---

# 🟦 FASE 1

## Ticket 1 · Implementación — `tree-url-generator`

**Trigger:** API Gateway `POST /v2/tree/init`.

**Función:** validar el body, generar un `tree_id`, firmar una pre-signed URL al bucket `compressed_trees` con headers `x-amz-meta-*` incluidos en la firma, y devolverla al agente.

**Lógica:**
1. Parsear y validar body: campos requeridos `enterprise_id, station_id, total_lines, fingerprint, agent_version`. Sanitizar IDs con regex `^[a-zA-Z0-9\-_]+$` para evitar path traversal.
2. Generar `tree_id = uuid4()`. Construir key `{enterprise_id}/{station_id}/{tree_id}.jsonl.gz`.
3. Generar pre-signed URL (`s3:put_object`, expiración 3600 s) firmando los 7 headers `x-amz-meta-*` (`enterprise-id`, `station-id`, `total-lines`, `fingerprint`, `uploaded-at`, `agent-version`, `tree-id`).
4. Devolver 200 con `{tree_id, upload_url, headers, expires_in: 3600}`.

**Interacción con cajas negras:** ninguna.

**Acceptance criteria:**
- **AC01:** POST con body válido devuelve 200 con la estructura esperada.
- **AC02:** PUT a la URL firmada con los headers correctos aterriza el archivo en `compressed_trees/{ent}/{sta}/{tree_id}.jsonl.gz`.
- **AC03:** PUT con un header alterado responde 403 SignatureDoesNotMatch.
- **AC04:** Body inválido o IDs con caracteres prohibidos → 400.
- **AC05:** Logs estructurados JSON con `enterprise_id`, `station_id`, `tree_id`, `request_id`.

---

## Ticket 2 · Implementación — `tree-uncompressor`

**Trigger:** EventBridge sobre PutObject en `compressed_trees/` (suffix `.jsonl.gz`).

**Función:** descomprimir el `.jsonl.gz` en streaming y escribir el `.jsonl` en `decompressed_trees/`, propagando los headers `x-amz-meta-*` intactos.

**Lógica:**
1. Parsear evento → bucket + key.
2. HEAD del objeto origen para leer headers `x-amz-meta-*`.
3. Iniciar multipart upload en `decompressed_trees/{key sin .gz}` con metadata heredada.
4. Stream: GET origen → `gzip` → upload parts de 8 MB.
5. Complete multipart al terminar. Abort multipart si algo falla a mitad.

**Manejo de errores:**
- Origen 404: log WARN, salir limpiamente.
- Gzip corrupto: abort multipart, log ERROR, no reintentar.
- Línea no UTF-8: log WARN y continuar.

**Interacción con cajas negras:** ninguna.

**Acceptance criteria:**
- **AC01:** Por cada PUT en `compressed_trees`, aparece en `decompressed_trees` el mismo key sin `.gz`, con metadata propagada intacta.
- **AC02:** Si el archivo fuente está corrupto, el destino no se crea (multipart abortado).
- **AC03:** Procesa archivos de hasta 5 GB descomprimidos sin OOM (streaming, no carga todo en memoria).
- **AC04:** Logs incluyen `tree_id`, `enterprise_id`, `station_id`, `total_parts`, `duration_ms`.

---

## Ticket 3 · Implementación — `emr-job-trigger`

**Trigger:** EventBridge sobre PutObject en `decompressed_trees/` (suffix `.jsonl`).

**Función:** parsear el evento y llamar `emr-serverless:StartJobRun` pasando el bucket y el key como argumentos al script Spark.

**Lógica:**
1. Parsear evento → bucket + key.
2. Validar formato del key: `{enterprise_id}/{station_id}/{tree_id}.jsonl`. Si no matchea → log WARN y descartar.
3. Llamar `StartJobRun`:
   - `entryPoint`: `s3://{keywords_bucket}/emr/joyas-priorizer/job.py`.
   - `entryPointArguments`: `[bucket, key]`.
   - `sparkSubmitParameters`: dynamic allocation OFF, 1 g memoria, 1 core driver/executor.
4. Loguear `jobRunId` para tracking.

**Interacción con cajas negras:** ninguna.

**Acceptance criteria:**
- **AC01:** Cada PUT válido en `decompressed_trees` dispara un EMR job con argumentos correctos.
- **AC02:** Key con formato inválido → log WARN, no aborta.
- **AC03:** Si `StartJobRun` falla, mensaje a DLQ tras 2 reintentos.
- **AC04:** Logs incluyen `enterprise_id`, `station_id`, `tree_id`, `job_run_id`.

---

## Ticket 4 · Implementación — `joyas-priorizer` (PySpark)

**Trigger:** invocado por `emr-job-trigger` con argumentos `<decompressed_bucket> <tree_key>`.

**Función:** cargar las keywords del enterprise como broadcast variable, scan del NDJSON, match por nombre de archivo, y escribir `crown_jewels/{ent}/{sta}/crown_jewels.jsonl` (incluso vacío).

**Lógica:**
1. Parsear `enterprise_id` y `station_id` desde `tree_key`.
2. Cargar `keywords/{enterprise_id}.json` (soportar `{"keywords": [...]}` o array directo).
3. Si no existe el archivo de keywords: **igual escribir un crown_jewels.jsonl vacío** y salir con código 0.
4. Lowercase + strip de las keywords. Crear broadcast variable.
5. Read NDJSON → DataFrame.
6. UDFs:
   - `has_match(name) -> bool`: ¿el nombre contiene alguna keyword?
   - `get_matches(name) -> list[str]`: ¿qué keywords matchearon?
7. Filter + add column `matched_keywords`.
8. Coalesce a 1 partition.
9. Write como JSON a `crown_jewels/{enterprise_id}/{station_id}/crown_jewels.jsonl` con `mode("overwrite")`. **Crítico: si no hay matches, igual escribir el archivo (puede ser vacío con header solo o cero filas).**

**Interacción con cajas negras (Equipo AI):** lee `keywords/{enterprise_id}.json` que el equipo AI deposita previamente. Si no existe, no falla — produce archivo vacío.

**Acceptance criteria:**
- **AC01:** Tree con N matches → crown_jewels.jsonl con N filas + columna `matched_keywords`.
- **AC02:** Tree con 0 matches → crown_jewels.jsonl **vacío** (clave para que Fase 2 detecte el evento del PUT).
- **AC03:** Sin archivo de keywords → crown_jewels.jsonl vacío, exit code 0, log WARN.
- **AC04:** Mode overwrite — reprocesar el mismo tree reemplaza el output anterior.
- **AC05:** Match es case-insensitive y soporta caracteres UTF-8 NFC.

---

# 🟪 FASE 2

## Ticket 5 · Implementación — `gse-cycle-init`

**Trigger:** SQS FIFO `gse-crown-cycle-queue.fifo`.

**Función:** inicializar un ciclo GSE cuando llega un crown_jewels.jsonl. Get-or-create del CYCLE en DDB, query a KEM para `stations_expected`, crear STATION + REQUEST, y notificar al agente vía Signal Handler.

**Lógica:**
1. Parsear mensaje SQS → S3 event → bucket + key.
2. Derivar `process_type` desde `EventSourceArn` (mapeo en env var). Por ahora siempre `crown`.
3. Derivar `enterprise_id`, `station_id` del key.
4. GET del crown_jewels.jsonl, parsear NDJSON, contar líneas → `samples_expected = len(files)`.
5. **Get-or-create CYCLE:**
   - Query DDB: `PK=enterprise_id, SK begins_with "CYCLE#"`, filter `status="collecting" AND process_type=current`.
   - Si existe → reusar `cycle_id`.
   - Si no existe →
     - `cycle_id = uuid4()`.
     - **Llamar KEM API** (ver "Interacción con cajas negras" abajo) → obtener `N`.
     - PUT CYCLE record con `ConditionExpression="attribute_not_exists(SK)"`.
     - Si la conditional falla (race con otra invocación): re-query y usar el existente.
6. PUT STATION record: `samples_expected, samples_received=0, samples_anonymized=0, samples_skipped=0, status="requested"` con conditional.
7. PUT REQUEST record: `files_to_sample, sample_content_size, status="requested"` con conditional.
8. **Publicar payload al Signal Handler** (ver abajo).

**Interacción con KEM:**
- Leer API key de Secrets Manager (`secretsmanager:GetSecretValue`).
- Llamar `GET {KEM_API_URL}/stations?enterprise_id={ent}` con header `Authorization: ApiKey {key}`.
- Esperar respuesta `{"stations": [...], "total": N}`. Usar `total` como `stations_expected`.
- Si KEM responde 404: mensaje a DLQ tras 3 reintentos.
- Si KEM timeout: SQS retry.

**Interacción con caja negra Signal Handler (Equipo AI):**
- Construir payload:
  ```json
  {
    "cycle_id": "...", "process_type": "crown",
    "enterprise_id": "...", "station_id": "...",
    "requests": [
      { "type": "crown_jewels", "files": [{"path": "...", "size": ...}], "sample_content_size": 10240 }
    ]
  }
  ```
- Publicar al canal del Signal Handler. **Durante desarrollo: stub que loguea. Cuando AI entregue el ARN/endpoint, reemplazar por publish real (SNS publish / SQS send / HTTP POST según el canal).**

**Acceptance criteria:**
- **AC01:** Por cada crown_jewels.jsonl, se crea (o reusa) un CYCLE y se crea una STATION + REQUEST.
- **AC02:** Si dos eventos del mismo enterprise llegan simultáneamente, solo se crea 1 CYCLE.
- **AC03:** `STATION.samples_expected` = número de líneas en el crown_jewels.jsonl.
- **AC04:** Mensaje SQS duplicado no genera registros duplicados (idempotencia por conditional writes).
- **AC05:** KEM 404 → mensaje a DLQ + alarma SNS.
- **AC06:** El Signal Handler recibe el payload con el formato correcto (validable contra contrato AI cuando esté).

---

## Ticket 6 · Implementación — `gse-sample-reception-notifier`

**Trigger:** SQS `gse-sample-reception-queue`.

**Función:** por cada sample crudo que aterriza en `gse-raw`, incrementar `samples_received` en DDB y notificar al Anonymizer.

**Lógica:**
1. Parsear mensaje SQS → S3 event → bucket + key.
2. Derivar `enterprise_id, station_id, cycle_id, request_type, sample_id` del key con regex `{ent}/{sta}/{cycle}/{req_type}/sample_NNN.json`.
3. UpdateItem en DDB:
   - `Key: PK=enterprise_id, SK=STATION#{station_id}#{cycle_id}`.
   - `UpdateExpression: ADD samples_received :one`.
   - Adicional: transicionar `status` de `requested` a `uploading` la primera vez (`SET #status = if_not_exists(#status, :uploading)` o conditional separada).
4. **Publicar payload al Anonymizer** (ver abajo).

**Manejo de errores:**
- STATION no existe en DDB: log WARN. Posible race con `gse-cycle-init` que aún no terminó. SQS reintentará — eventualmente DLQ.

**Interacción con caja negra Anonymizer (Equipo AI):**
- Construir payload:
  ```json
  {
    "bucket": "gse-raw", "key": "ent/sta/cycle/req_type/sample_NNN.json",
    "enterprise_id": "...", "station_id": "...",
    "cycle_id": "...", "request_type": "...", "sample_id": "..."
  }
  ```
- Publicar al canal del Anonymizer. **Stub durante desarrollo, real cuando AI entregue ARN/endpoint.**

**Acceptance criteria:**
- **AC01:** Cada PUT en `gse-raw` incrementa `samples_received` en +1 atómicamente.
- **AC02:** Primera invocación transiciona `STATION.status` de `requested` a `uploading`.
- **AC03:** Por cada sample, el Anonymizer recibe la notificación con el payload correcto.
- **AC04:** Mensaje SQS duplicado puede sobre-contar en +1 (aceptable — el barrier final usa `>=`).

---

## Ticket 7 · Implementación — `gse-sample-anonymizer-notifier`

**Trigger:** SQS `gse-sample-anonymizer-queue`.

**Función:** por cada sample anonimizado que aterriza en `gse-anonymized`, incrementar `samples_anonymized` en DDB. **No notifica nada externo** — el cierre del ciclo lo dispara el DDB Stream.

**Lógica:**
1. Parsear mensaje SQS → S3 event → bucket + key.
2. Derivar `enterprise_id, station_id, cycle_id` del key.
3. UpdateItem en DDB: `ADD samples_anonymized :one`.

**Interacción con cajas negras:** ninguna directa. El Anonymizer (Equipo AI) escribe al bucket `gse-anonymized` y eso dispara este Lambda; pero no hay comunicación de vuelta.

**Acceptance criteria:**
- **AC01:** Cada PUT en `gse-anonymized` incrementa `samples_anonymized` en +1.
- **AC02:** Esta Lambda no publica a ningún canal externo.
- **AC03:** Mensaje duplicado puede sobre-contar (aceptable).

---

## Ticket 8 · Implementación — `gse-request-complete`

**Trigger:** API Gateway `POST /v2/gse/request-complete`.

**Función:** marcar la REQUEST como `sent` y sumar `samples_skipped` a la STATION padre, atómicamente.

**Body esperado:**
```json
{
  "enterprise_id": "...", "station_id": "...",
  "cycle_id": "...", "request_type": "...",
  "total_samples_uploaded": 47,
  "samples_skipped": 3,
  "skipped_reasons": [{"path": "...", "reason": "locked_by_other_process"}]
}
```

**Lógica:**
1. Validar body: campos requeridos, tipos, `request_type` en lista permitida (env var `ALLOWED_REQUEST_TYPES_JSON`).
2. `TransactWriteItems` para hacer ambos updates atómicamente:
   - **Update REQUEST:** `SET status="sent", total_samples_uploaded, samples_skipped, skipped_reasons, request_complete_at=now`. Conditional `attribute_exists(SK) AND status="requested"`.
   - **Update STATION:** `ADD samples_skipped :n`.
3. Si la conditional falla (REQUEST ya en `sent`/`complete`): GetItem para devolver `current_status` y responder 409.

**Respuestas:**
- **200:** `{ok: true, request_status, samples_expected, samples_received, samples_anonymized, samples_skipped}`.
- **400:** body inválido (con detalles).
- **404:** REQUEST no existe.
- **409:** ya estaba cerrada (idempotencia tolerada).

**Interacción con cajas negras:** ninguna.

**Acceptance criteria:**
- **AC01:** Llamada válida con REQUEST en `requested` → 200, marca `sent`, suma `samples_skipped` en STATION.
- **AC02:** Llamada repetida → 409 con `current_status`.
- **AC03:** Body inválido → 400 con detalles.
- **AC04:** REQUEST inexistente → 404.
- **AC05:** `TransactWriteItems` garantiza atomicidad (REQUEST update y STATION ADD se aplican juntos o ninguno).

---

## Ticket 9 · Implementación — `gse-station-status`

**Trigger:** EventBridge Pipe sobre DDB Stream filtrado a `STATION#`.

**Función:** cuando una STATION tiene contadores cuadrados, cerrarla y escalar al CYCLE incrementando `stations_completed` en +1.

**Lógica:**
Para cada record del batch:
1. Leer `NewImage` del DDB Stream record.
2. **Skip rápido si `status == "complete"`** (idempotencia — evita procesar records ya manejados).
3. Si `(samples_anonymized + samples_skipped) < samples_expected`: log DEBUG, no cerrar aún.
4. **Conditional close de STATION:**
   - `UpdateItem`: `SET status="complete", completed_at=now`.
   - `ConditionExpression: status <> :complete`.
   - Si la conditional falla → ya estaba cerrada (otro stream record en el batch o invocación previa la cerró). No-op.
5. **Solo si la conditional pasó (esta invocación cerró la STATION):**
   - `UpdateItem` en CYCLE: `ADD stations_completed :one`.

**Garantía clave:** el ADD a CYCLE solo se ejecuta cuando la conditional close pasa. Esto da **exactly-once** en el incremento del CYCLE incluso con records duplicados del stream.

**Interacción con cajas negras:** ninguna.

**Acceptance criteria:**
- **AC01:** Cuando los contadores cuadran, STATION pasa a `complete` exactamente una vez.
- **AC02:** `CYCLE.stations_completed` se incrementa exactamente una vez por STATION cerrada.
- **AC03:** Stream record duplicado → conditional fail → no double-counting.
- **AC04:** STATION con `samples_expected = 0` cierra inmediatamente al primer evento del stream.
- **AC05:** Records de tipo CYCLE o REQUEST no procesados (filter del Pipe los descarta).

---

## Ticket 10 · Implementación — `gse-enterprise-status`

**Trigger:** EventBridge Pipe sobre DDB Stream filtrado a `CYCLE#`.

**Función:** cuando un CYCLE tiene todas las stations cerradas, cerrarlo y notificar al downstream LLM.

**Lógica:**
Para cada record del batch:
1. Leer `NewImage`.
2. Skip rápido si `status == "complete"`.
3. Si `stations_completed < stations_expected`: log DEBUG, no cerrar aún.
4. **Conditional close de CYCLE:**
   - `UpdateItem`: `SET status="complete", completed_at=now`.
   - `ConditionExpression: status <> :complete AND stations_completed >= stations_expected` (doble candado: solo cierra si está abierto y si efectivamente las cuentas cuadran).
   - Si la conditional falla → no-op.
5. **Si la conditional pasó:**
   - **Publicar al LLM Process Queue** (ver abajo).

**Interacción con caja negra LLM Process Queue (Equipo AI):**
- Construir payload:
  ```json
  {
    "cycle_id": "...", "enterprise_id": "...",
    "process_type": "crown",
    "stations_completed": N,
    "anonymized_prefix": "s3://gse-anonymized/{ent}/{cycle_id}/",
    "completed_at": "ISO-8601"
  }
  ```
- Publicar al canal del LLM. **Stub durante desarrollo, real cuando AI entregue ARN/endpoint.**

**Caveat:** si la conditional pasa pero el publish al LLM falla, el CYCLE ya está marcado `complete` en DDB pero el LLM no se entera. Dos opciones:
- **(a) publish-then-set:** publicar primero, luego SET status. Riesgo: notify duplicado si el publish reintenta — el LLM debe ser idempotente por `cycle_id`.
- **(b) outbox pattern:** escribir un mensaje pendiente en otra tabla, despacharlo aparte.

**Recomendación:** opción (a) — el LLM debe ser idempotente por `cycle_id` por contrato (AC13 del ticket Equipo AI en la épica).

**Acceptance criteria:**
- **AC01:** Cuando todas las stations cierran, el CYCLE pasa a `complete` exactamente una vez.
- **AC02:** El LLM Process Queue recibe la notificación con el payload correcto.
- **AC03:** Records duplicados del stream no causan notificaciones duplicadas al LLM (gracias al conditional).
- **AC04:** Si el publish al LLM falla, mensaje a DLQ del Pipe + alarma.
- **AC05:** Records de tipo STATION o REQUEST no procesados (filter del Pipe los descarta).

---

# Resumen

| # | Componente | Interacción con cajas negras |
|---|---|---|
| 1 | tree-url-generator | ninguna |
| 2 | tree-uncompressor | ninguna |
| 3 | emr-job-trigger | ninguna |
| 4 | joyas-priorizer | lee `keywords/{ent}.json` que deposita el equipo AI |
| 5 | gse-cycle-init | **KEM** (existe — query stations) + **Signal Handler** (publica payload del cycle al agente) |
| 6 | gse-sample-reception-notifier | **Anonymizer** (publica `bucket+key` del sample) |
| 7 | gse-sample-anonymizer-notifier | ninguna directa (Anonymizer escribe a S3 y eso me dispara) |
| 8 | gse-request-complete | ninguna |
| 9 | gse-station-status | ninguna |
| 10 | gse-enterprise-status | **LLM Process Queue** (publica cycle cerrado) |

**Bloqueos por canal:** los tickets 5, 6 y 10 tienen un stub de notify durante desarrollo. La integración real con el canal definitivo se hace cuando el equipo AI entregue el ARN/endpoint correspondiente — eso desbloquea cerrar AC06 (ticket 5), AC03 (ticket 6) y AC02 (ticket 10).
