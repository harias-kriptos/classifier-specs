# Tareas por fase — Backend Classifier V2

> Lista imperativa de tareas por **fase × área**. Cada tarea describe una acción concreta con su destino/detalle.
> Complementa [plan-trabajo.md](plan-trabajo.md) (HU candidatas + tensiones).

---

## FASE 1 · Scan & File Discovery

### Fase 1 — Agente Multiplataforma (PC: Windows/Mac/Linux/FileServer/OneDrive/SharePoint/Google)

- **Tarea 1:** Debe **recorrer cíclicamente el disco/volumen asignado** respetando `excluded_paths` y `allowed_formats` configurados en KEM.
- **Tarea 2:** Debe **construir el árbol de archivos** con los 5 campos por nodo: `name`, `path`, `size`, `extension`, `modified_date` — encoding UTF-8 NFC.
- **Tarea 3:** Debe **agregar al payload del árbol** los campos nuevos `tamaño del documento` y `fecha de creación` (cambio v3).
- **Tarea 4:** Debe **llamar `POST /v2/tree/init`** con `{enterprise_id, station_id, total_lines, fingerprint, agent_version}` y recibir `{tree_id, upload_url, headers, expires_in}`.
- **Tarea 5:** Debe **generar `tree.jsonl.gz`** — NDJSON comprimido con gzip.
- **Tarea 6:** Debe **subir el archivo vía `s3-uploader`** al `upload_url` con los headers `x-amz-meta-*` que firmó el backend (sin alterar ningún header — si no, S3 responde `403 SignatureDoesNotMatch`).
- **Tarea 7:** Debe **escanear por fecha de modificación descendente** respetando el parámetro `fecha_modif` (feature flag llegado desde backend vía `config_scan`).
- **Tarea 8:** Debe **ejecutar en paralelo un full scan** (columna 2) hasta recibir la lista priorizada del backend.
- **Tarea 9:** Debe **detectar formateo de máquina** mediante un fingerprint de hardware/instalación, para no reclasificar archivos migrados.
- **Tarea 10:** Debe **reintentar el upload con backoff exponencial** si falla, sin pedir URL nueva (hasta que expire).

### Fase 1 — Agente Cloud (dentro AWS del cliente)

- **Tarea 1:** Debe **recorrer el disco/volumen asignado** con los mismos criterios del agente PC (mismos parámetros KEM).
- **Tarea 2:** Debe **construir el árbol NDJSON** con los mismos 5 campos + `tamaño` + `fecha_creación`.
- **Tarea 3:** Debe **saltar el paso de compresión gzip** y **saltar s3-uploader**.
- **Tarea 4:** Debe **escribir directo en `s3://decompressed_trees/{enterprise_id}/{station_id}/{tree_id}.jsonl`** usando su IAM role.
- **Tarea 5:** Debe **incluir los headers `x-amz-meta-*`** en el PUT (`enterprise-id`, `station-id`, `total-lines`, `fingerprint`, `uploaded-at`, `agent-version`, `tree-id`).
- **Tarea 6:** Debe **detectar su modo (cloud vs PC) al arrancar** para activar la ruta de upload correcta.

### Fase 1 — Backend (POC validado · tareas pendientes)

- **Tarea 1:** Debe **fixear `joyas-priorizer` (EMR)** para que escriba un `crown_jewels.jsonl` vacío cuando no hay matches, garantizando que todas las stations produzcan un evento downstream. **[Bloquea Phase 2]**
- **Tarea 2:** Debe **renombrar el bucket `crown_jewels` → `suspicious_crown_jewels`** (cambio cosmético para alinear con diagrama nuevo).
- **Tarea 3:** Debe **agregar API key + WAF en `POST /v2/tree/init`** antes de producción.
- **Tarea 4:** Debe **provisionar las 2 DLQs** (`tree-uncompressor-dlq`, `emr-job-trigger-dlq`) con retención 14 días.
- **Tarea 5:** Debe **configurar CloudWatch alarms** sobre errores de cada Lambda, depth de DLQ, y latencia de decompresión.
- **Tarea 6:** Debe **agregar dedup de trees** por `tree_id` o `fingerprint + station_id` (evita re-procesar el mismo árbol).
- **Tarea 7:** Debe **configurar S3 logging bucket** para los logs de EMR Serverless.
- **Tarea 8:** Debe **provisionar el IAM role del Cloud Agent** con permisos mínimos (PUT en `decompressed_trees/{enterprise}/` del Cloud Agent, nada más).

### Fase 1 — Dependencias externas (otros equipos)

- **KEM:** Debe **exponer endpoint** que valide `enterprise_id` y `station_id` del agente (opcional en POC, requerido en producción).
- **Bedrock (equipo data):** Debe **generar `keywords/{enterprise_id}.json`** con contexto de empresa/sector/país y subirlo manualmente a S3.

### Fase 1 — Entregable agregado

> Un `suspicious_crown_jewels/{ent}/{sta}/crown_jewels.jsonl` por cada tree escaneado (incluso vacío), con metadata `x-amz-meta-*` propagada, listo para disparar Phase 2.

---

## FASE 2 · Priority Sample Collection (GSE)

### Fase 2 — Agente Multiplataforma (PC)

- **Tarea 1:** Debe **recibir el push del Signal Handler** con el payload `{cycle_id, process_type, enterprise_id, station_id, requests:[{type, files:[...], sample_content_size}]}` — canal TBD (el otro equipo lo define).
- **Tarea 2:** Debe **ser idempotente por `cycle_id`**: si recibe dos veces el mismo cycle, no duplicar samples.
- **Tarea 3:** Debe **por cada `file` en `files_to_sample` extraer un chunk** respetando `sample_content_size` (bytes configurados).
- **Tarea 4:** Debe **anonimizar el contenido del chunk localmente** antes de enviarlo al backend ⚠️ **(pendiente tensión #1 — puede quedar del lado backend)**.
- **Tarea 5:** Debe **pedir al backend un pre-signed URL** (endpoint TBD si se mantiene PC path) para cada `sample`.
- **Tarea 6:** Debe **subir cada sample vía `s3-uploader`** a `s3://gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json`.
- **Tarea 7:** Debe **registrar archivos que no pudo procesar** (locked, permission_denied, file_not_found) en una lista local de `skipped`.
- **Tarea 8:** Debe **llamar `POST /v2/gse/request-complete`** al terminar todos los samples de una `request`, con `{enterprise_id, station_id, cycle_id, request_type, total_samples_uploaded, samples_skipped, skipped_reasons:[{path, reason}]}`.
- **Tarea 9:** Debe **recibir los tags por grupo del backend** (canal TBD — probablemente el mismo Signal Handler del paso 1, pero TBD).
- **Tarea 10:** Debe **persistir los tags en la BDD local de grupos + cache**.
- **Tarea 11:** Debe **sincronizar los archivos `pending`** que ya tienen grupo con clasificación resuelta.
- **Tarea 12:** Debe **llamar a Tagging por grupo** para aplicar la etiqueta a cada documento `pending` del grupo.
- **Tarea 13:** Debe **detectar y loguear "sin grupo asignado"** cuando el lookup local y el backend no devuelvan grupo (queda para validación manual en plataforma).

### Fase 2 — Agente Cloud

- **Tarea 1:** Debe **recibir el push del Signal Handler** con el mismo payload (canal TBD — puede ser distinto al del PC Agent si el equipo decide).
- **Tarea 2:** Debe **extraer chunks por archivo** con los mismos criterios que el PC Agent.
- **Tarea 3:** Debe **anonimizar localmente** (si aplica — tensión #1).
- **Tarea 4:** Debe **saltar el pre-signed URL y el s3-uploader**.
- **Tarea 5:** Debe **escribir direct** `PUT` **en `s3://gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json`** usando su IAM role.
- **Tarea 6:** Debe **llamar `POST /v2/gse/request-complete`** (mismo endpoint que el PC Agent).
- **Tarea 7:** Debe **recibir los tags** (mismo canal).
- **Tarea 8:** Debe **persistir tags localmente, sincronizar pending y llamar Tagging** (idéntico al PC Agent).

### Fase 2 — Backend

#### Infraestructura (sub-fase 2.A)

- **Tarea 1:** Debe **crear la tabla DynamoDB `gse-cycles-samples`** con schema single-table, 3 niveles (CYCLE/STATION/REQUEST), stream `NEW_AND_OLD_IMAGES` activo, TTL en atributo `ttl`.
- **Tarea 2:** Debe **crear el bucket `gse-raw`** con encryption AES-256, public-access block, EventBridge notifications enabled, lifecycle rule de 7 días.
- **Tarea 3:** Debe **crear el bucket `gse-anonymized`** con misma configuración + lifecycle de 30 días.
- **Tarea 4:** Debe **crear la cola SQS FIFO `gse-crown-cycle-queue`** + su DLQ, con visibility 90s y max receive 3.
- **Tarea 5:** Debe **crear la cola SQS standard `gse-sample-reception-queue`** + su DLQ, visibility 60s max receive 5.
- **Tarea 6:** Debe **crear la cola SQS standard `gse-sample-anonymizer-queue`** + su DLQ, igual config.
- **Tarea 7:** Debe **crear la EventBridge rule `suspicious-crown-jewels-to-cycle-queue`** filtrando suffix `crown_jewels.jsonl` → target SQS FIFO.
- **Tarea 8:** Debe **crear la EventBridge rule `gse-raw-to-reception-queue`** filtrando suffix `.json` → SQS reception.
- **Tarea 9:** Debe **crear la EventBridge rule `gse-anonymized-to-anonymizer-queue`** filtrando suffix `.json` → SQS anonymizer.
- **Tarea 10:** Debe **crear el EventBridge Pipe `ddb-to-station-status`** con filtro `SK begins_with "STATION#"` → target Lambda `gse-station-status`.
- **Tarea 11:** Debe **crear el EventBridge Pipe `ddb-to-enterprise-status`** con filtro `SK begins_with "CYCLE#"` → target Lambda `gse-enterprise-status`.
- **Tarea 12:** Debe **crear las 3 CloudWatch alarms** sobre depth de cada DLQ (threshold > 0).

#### Lambdas de cascada (sub-fase 2.B)

- **Tarea 13:** Debe **implementar el Lambda `gse-station-status`**: recibe DDB Stream records de STATION, lee `NewImage`, y si `(samples_anonymized + samples_skipped) >= samples_expected AND status != "complete"`, hace **conditional write** `SET status="complete"` + `ADD CYCLE.stations_completed=1`.
- **Tarea 14:** Debe **implementar el Lambda `gse-enterprise-status`**: recibe DDB Stream records de CYCLE, y si `stations_completed >= stations_expected AND status != "complete"`, hace **conditional write** `SET status="complete"` + **notifica al downstream LLM Process Queue** (canal TBD).

#### Lambdas de ingest (sub-fase 2.C)

- **Tarea 15:** Debe **implementar el Lambda `gse-cycle-init`** con event source mapping en `gse-crown-cycle-queue` (y a futuro `gse-classification-cycle-queue`):
  - Derivar `process_type` del `EventSourceArn`.
  - Leer `crown_jewels.jsonl` del S3 para obtener `files_to_sample`.
  - **Get-or-create CYCLE**: query DDB por `(enterprise_id, status="collecting", process_type)`; si no existe, query KEM para `N=stations_expected` y crear CYCLE con `attribute_not_exists`.
  - Crear STATION con `samples_expected=len(files)`, status=`requested`.
  - Crear REQUEST (1 por STATION — Modelo A).
  - **Notificar al Signal Handler** con `{cycle_id, process_type, enterprise_id, station_id, requests:[{type, files, sample_content_size}]}` (canal TBD).
- **Tarea 16:** Debe **implementar el Lambda `gse-sample-reception-notifier`** con event source en `gse-sample-reception-queue`:
  - Parsear `bucket+key` del event.
  - `UpdateItem` `ADD samples_received=1` en STATION.
  - Transicionar STATION.status de `requested` → `uploading` (conditional) en el primer sample.
  - **Notificar al Anonymizer** con `{bucket, key, enterprise_id, station_id, cycle_id, request_type, sample_id}` (canal TBD).
- **Tarea 17:** Debe **implementar el Lambda `gse-sample-anonymizer-notifier`** con event source en `gse-sample-anonymizer-queue`:
  - Parsear `bucket+key` del event.
  - `UpdateItem` `ADD samples_anonymized=1` en STATION.
  - No notifica nada externo (el barrier se dispara vía DDB Stream).

#### API endpoint (sub-fase 2.C)

- **Tarea 18:** Debe **crear la ruta API Gateway `POST /v2/gse/request-complete`** con API key + throttling.
- **Tarea 19:** Debe **implementar el Lambda `gse-request-complete`**:
  - Validar body (`enterprise_id`, `station_id`, `cycle_id`, `request_type`, `total_samples_uploaded`, `samples_skipped`, `skipped_reasons`).
  - Usar `TransactWriteItems` para **atomically**: `UPDATE REQUEST status="sent"` (conditional `status="requested"`) + `ADD STATION.samples_skipped += body.samples_skipped`.
  - Devolver 200 con counters actuales · 409 si ya estaba cerrado (idempotencia).

#### Integración con cajas negras (sub-fase 2.D · bloqueada por otros equipos)

- **Tarea 20:** Debe **acordar con el equipo Signal Handler** el canal de notificación (SNS/SQS/IoT/HTTP) y el contrato del payload.
- **Tarea 21:** Debe **conectar `gse-cycle-init`** al canal real del Signal Handler (reemplazar stub).
- **Tarea 22:** Debe **acordar con el equipo Anonymizer** el canal y los permisos cross-account para `gse-raw` (GET) y `gse-anonymized` (PUT).
- **Tarea 23:** Debe **conectar `gse-sample-reception-notifier`** al canal real del Anonymizer.
- **Tarea 24:** Debe **acordar con el equipo LLM** el canal de consumo de cycles cerrados.
- **Tarea 25:** Debe **conectar `gse-enterprise-status`** al canal real del LLM Process Queue.
- **Tarea 26:** Debe **acordar con el equipo KEM** el contrato del endpoint de stations activas por enterprise, y provisionar el API key en Secrets Manager.

#### Hardening (sub-fase 2.E)

- **Tarea 27:** Debe **implementar un Reaper Lambda** (scheduled cada N minutos) que detecta cycles con `status="collecting"` desde hace > X horas y los marca como `failed`.
- **Tarea 28:** Debe **implementar dedup por `sample_id`** (tabla auxiliar `sample-dedup` con TTL corto, write-once) — opcional si se acepta sobre-conteo.
- **Tarea 29:** Debe **configurar CloudWatch dashboard** con métricas de Phase 2: cycles abiertos, latencia por etapa, errores por Lambda, DLQ depth.
- **Tarea 30:** Debe **ejecutar pruebas de carga** simulando N stations × M samples para validar throughput y costo DDB.
- **Tarea 31:** Debe **evaluar switch de DDB on-demand → provisioned** con auto-scaling según métricas reales.

### Fase 2 — Plataforma Web

- **Tarea 1:** Debe **agregar el campo `id_grupo`** en la tabla DDB `kr-dat-ana-{enterprise_id}-dydb`.
- **Tarea 2:** Debe **leer sensibilidad desde la tabla de grupos** vía `id_grupo` (no desde el análisis individual).
- **Tarea 3:** Debe **crear vista de documentos en estado `pending`** con filtro por station, grupo y fecha.
- **Tarea 4:** Debe **crear vista de grupos** detectados localmente por cada agente.
- **Tarea 5:** Debe **permitir asignar manualmente un grupo** a los documentos "sin grupo asignado".
- **Tarea 6:** Debe **mostrar los clusters generados** con criterios y lista de documentos asignados.
- **Tarea 7:** Debe **agregar columna `tamaño`** en las vistas de análisis y el explorador de archivos.
- **Tarea 8:** Debe **ajustar los contadores** para mostrar: por grupo, por estado (`pending`/`classified`/`big_file`), separados por agente.
- **Tarea 9:** Debe **mostrar fecha de última conexión** de cada agente (desde el sistema de auth existente).
- **Tarea 10:** Debe **limitar la vista de observabilidad** a archivos `big_file`, con separación visual entre agentes.
- **Tarea 11:** Debe **crear la vista de configuración del agente** para los 9 parámetros editables (`chunk_size_kb`, `max_chunks`, `big_file_threshold`, `sample_content_size`, `fecha_modif`, `excluded_paths`, `fixed_classification_paths`, `allowed_formats`, `max_threads`), persistiendo en KEM.
- **Tarea 12:** Debe **crear la UX para movimiento de archivos clasificados entre máquinas**, incluyendo la confirmación del formateo de máquina detectado por el agente.
- **Tarea 13:** Debe **mostrar visualmente** los documentos "sin grupo asignado" para que el operador los atienda.

### Fase 2 — Dependencias externas (otros equipos)

- **Signal Handler (equipo plataforma agente):** Debe **recibir del backend el payload del cycle** y hacer push a la estación correcta (IoT, polling, o el mecanismo que decidan). Debe retener el payload si la estación está offline.
- **Anonymizer (equipo seguridad/IA):** Debe **leer samples de `gse-raw`**, ejecutar el core de anonimización, y **escribir en `gse-anonymized`** en el mismo path. Debe ser idempotente por `sample_id`.
- **LLM (equipo IA):** Debe **consumir la notificación de cycle cerrado**, leer los samples anonimizados desde el prefix S3, clasificar, y persistir resultados en la tabla de analyses.
- **KEM:** Debe **exponer endpoint** que devuelva la lista de stations activas por enterprise.

### Fase 2 — Entregable agregado

> Para cada `crown_jewels.jsonl` que aterrice, dentro de un tiempo razonable (TBD según volumen) el LLM downstream recibe una notificación con `cycle_id` cerrado + el prefix S3 de los samples anonimizados listos para clasificar.

---

## Orden recomendado de arranque (paralelización)

### Se puede arrancar HOY (sin dependencias externas)

- Backend — todas las tareas de **sub-fase 2.A** (infra).
- Backend — tareas 13, 14 de **sub-fase 2.B** (lambdas de cascada, sin notify externos).
- Backend — tareas 15–19 de **sub-fase 2.C** (lambdas de ingest + API, con stubs de notify).
- Agente PC — tareas 1–3, 7–10 de Fase 1.
- Agente Cloud — tareas 1–5 de Fase 1.
- Plataforma Web — tareas 1, 11 de Fase 2 (schema + config UI con mock data).

### Bloqueado por otros equipos

- Backend — tareas 20–26 (integración cajas negras).
- Agente PC/Cloud — Fase 2 completa (bloqueado por canal Signal Handler).
- Plataforma Web — tareas 3–13 (necesitan datos reales del agente).

### Bloqueantes críticos para el resto

- **Backend Phase 1 Tarea 1** (EMR fix de 0 matches) → bloquea todo el barrier de Phase 2.
- **KEM endpoint** → bloquea `gse-cycle-init`.
- **Tensión #1** (anonimización agente vs backend) → bloquea Agente Fase 2 Tarea 4.

---

## Referencias

- Plan con HU y tensiones: [plan-trabajo.md](plan-trabajo.md)
- Plan visual: [plan-trabajo.html](plan-trabajo.html)
- Specs backend: [new-backend/README.md](new-backend/README.md) · [new-backend/phase1/](new-backend/phase1/) · [new-backend/phase2/](new-backend/phase2/)
- Specs agente: [new-agent/README.md](new-agent/README.md)
- Diagramas: [new-backend/arquitectura-completa.html](new-backend/arquitectura-completa.html) · [new-backend/phase2-priority-sample-collection.html](new-backend/phase2-priority-sample-collection.html)
