# Épicas y sub-tareas — listas para PM

> **Para:** PM que aterriza esto en JIRA.
> Documento auto-contenido: todo el detalle que necesita la PM para crear/actualizar las sub-tareas está aquí.

---

## 📖 Convenciones

| Concepto | Significado |
|---|---|
| **AC** | Acceptance Criteria — condición verificable que debe cumplirse para aceptar la tarea |
| **Agente Multiplataforma** | Binario instalado en **Windows / Mac / Linux / FileServer**. Owner: **Sol** |
| **Agente Cloud** | Conectores a servicios de nube externos: **OneDrive / SharePoint / Google**. Owner: **Jeff** |
| **Backend** | Infra AWS (Lambdas, colas, S3, DynamoDB, API Gateway). Owner: **Haroldo** |
| **Equipo AI** | Piezas externas (Bedrock, Signal Handler, Anonymizer, LLM Classifier) |

---

## ⚠️ Nota sobre JIRA actual

- **KT-16368 · Fase 1 Scan & File Discovery** — título y alcance correctos. Mantener.
- **KT-16369 · hoy dice "Priority Crown Jewel Detection & Prioritization"** — el alcance cambió. Ya no existe una caja negra de priorización separada. Fase 2 ahora es **Priority Sample Collection (GSE)**; el scoring/priorización se hace inline dentro del motor GSE del backend. **Acción PM: actualizar título + descripción de KT-16369** con el contenido de la Épica Fase 2 de este documento.

---

# 🧩 ÉPICA FASE 1 · Scan & File Discovery (KT-16368)

## 🎯 Objetivo de la épica

Implementar el pipeline v2 de descubrimiento del Agente Kriptos: desde que el agente recorre las fuentes de archivos (disco local en OS tradicionales, o APIs de nube externa) hasta que el backend produce por estación el archivo de "joyas candidatas" (vacío o con registros) que alimenta a la Fase 2.

## 📋 Alcance de la épica

- Scanner local del **Agente Multiplataforma** sobre Windows/Mac/Linux/FileServer.
- Scanner por API de OneDrive/SharePoint/Google del **Agente Cloud**.
- Pipeline en AWS: endpoint `POST /v2/tree/init`, descompresión, convergencia del árbol, matching de keywords (EMR Serverless) y output a S3.
- Generación manual de keywords por Bedrock (Equipo AI).

## ✅ Criterio de aceptación de la épica

**Por cada estación (equipo local o tenant de servicio cloud) escaneada, existe en S3 un archivo `crown_jewels/{enterprise_id}/{station_id}/crown_jewels.jsonl` (vacío o con registros), con metadata de trazabilidad propagada, listo para disparar la Épica Fase 2.**

---

## Sub-tareas Fase 1

### [Fase 1 · Backend/Pipeline] — Ingesta, descompresión y matching de keywords

**Owner sugerido:** Haroldo

#### 🎯 Objetivo

Construir el pipeline en AWS que recibe el árbol del agente (sea multiplataforma o cloud), descomprime, converge en un único bucket, matchea contra los keywords del enterprise y produce el archivo de joyas candidatas.

#### 📋 Contexto

Pieza nube de Fase 1 ya validada en un POC. Quedan pendientes: producir archivo vacío cuando no hay matches, DLQs, alarmas, auth en API, dedup de trees.

#### 🏗️ Alcance

- Lambda `tree-url-generator` detrás de API Gateway (`POST /v2/tree/init`) que firma una pre-signed URL de subida.
- Lambda `tree-uncompressor` (EventBridge sobre bucket `compressed_trees/`) que descomprime a `decompressed_trees/`.
- Lambda `emr-job-trigger` (EventBridge sobre `decompressed_trees/`) que arranca el job de EMR.
- EMR Serverless `joyas-priorizer` (Spark con keyword matching).
- 4 buckets S3 (`compressed_trees`, `decompressed_trees`, `keywords`, `crown_jewels`) con encryption y public-access block.
- Propagación end-to-end de headers de metadata (`x-amz-meta-enterprise-id`, `x-amz-meta-station-id`, etc.).
- DLQs + alarmas CloudWatch.
- API key + WAF en `POST /v2/tree/init`.

#### ✅ Acceptance Criteria

- **AC01:** `POST /v2/tree/init` con body válido devuelve 200 con `{tree_id, upload_url, headers, expires_in:3600}`.
- **AC02:** El PUT del `.jsonl.gz` al `upload_url` con los headers firmados aterriza en `compressed_trees/{ent}/{sta}/{tree_id}.jsonl.gz`.
- **AC03:** Por cada objeto en `compressed_trees/`, en menos de ~3 min aparece su `.jsonl` descomprimido en `decompressed_trees/` con metadata propagada intacta.
- **AC04:** El Agente Cloud puede escribir directo en `decompressed_trees/{ent}/{sta}/{tree_id}.jsonl` con credenciales IAM (sin pasar por API Gateway ni Lambda de descompresión).
- **AC05:** Por cada objeto en `decompressed_trees/`, el EMR `joyas-priorizer` corre y produce `crown_jewels/{ent}/{sta}/crown_jewels.jsonl` **incluso si el archivo sale vacío** (0 matches). *Bloqueante para Fase 2.*
- **AC06:** El `crown_jewels.jsonl` tiene formato NDJSON UTF-8 con los 5 campos originales del árbol más `matched_keywords[]`.
- **AC07:** Errores en cualquiera de las 3 Lambdas llegan a DLQ y disparan alarma SNS.
- **AC08:** Si el mismo tree (identificado por `tree_id` o `fingerprint + station_id`) llega dos veces, el pipeline no duplica el procesamiento.
- **AC09:** `POST /v2/tree/init` requiere API key válida (rechaza 401 sin auth).

#### 🔗 Dependencias

- **Equipo AI:** archivo `keywords/{enterprise_id}.json` existente en S3 (sin keywords el EMR produce 0 matches — igual cumple AC05 con archivo vacío).
- **KEM:** endpoint de validación de enterprise/station (requerido para AC09 en producción).

#### 📎 Observaciones

- POC ya desplegado en el ambiente de pruebas.
- AC05 es el cambio más importante: hoy el EMR no escribe output cuando no hay matches, lo que dejaría a Fase 2 sin saber que esa estación terminó.
- Runtime (Python / Node / Go) pendiente de decidir — no bloquea el diseño.

---

### [Fase 1 · Agente Multiplataforma] — Scanner local y upload del árbol

**Owner sugerido:** Sol
**Fuentes cubiertas:** Windows, Mac, Linux, FileServer

#### 🎯 Objetivo

Recorrer cíclicamente el disco/volumen local del equipo (o el share del FileServer), construir el árbol NDJSON con el payload v3 y subirlo al backend vía pre-signed URL.

#### 📋 Contexto

Reemplazo del Scanner del agente legacy. Corre como binario instalado en el OS. Debe funcionar en Windows, macOS, Linux y sobre shares de FileServer montados. Incluye detección de formateo de máquina y dos columnas de scan en paralelo (descendente por fecha + full scan).

#### 🏗️ Alcance

- Recorrido cíclico del disco/volumen respetando `excluded_paths`, `allowed_formats` y schedules configurables (no saturar recursos mientras el usuario trabaja).
- Payload del árbol con 7 campos por nodo: `name`, `path`, `size`, `extension`, `modified_date`, `created_date`, y metadata de trazabilidad del tree completo.
- Dos columnas de scan en paralelo:
  - Columna 1: por fecha descendente hasta `fecha_modif` (feature flag).
  - Columna 2: full scan en paralelo hasta converger.
- Cross-platform: Windows, macOS, Linux, FileServer.
- Detección de formateo de máquina (fingerprint de hardware/instalación).
- Detección de eliminación de archivos + notificación al backend.
- Integración con `s3-uploader` existente para el upload vía pre-signed URL.

#### ✅ Acceptance Criteria

- **AC01:** El agente construye el árbol NDJSON del disco/volumen completo (respetando `excluded_paths`) con los 7 campos por nodo y encoding UTF-8 NFC.
- **AC02:** El agente llama `POST /v2/tree/init` con `{enterprise_id, station_id, total_lines, fingerprint, agent_version}` y procesa la respuesta (`tree_id`, `upload_url`, `headers`).
- **AC03:** El agente comprime el árbol como `tree.jsonl.gz` (gzip) y lo sube vía `s3-uploader` usando el `upload_url` y los headers de metadata firmados, **sin alterar ningún header** (si lo altera, S3 rechaza con 403).
- **AC04:** Cuando el feature flag está activo, el agente escanea primero archivos con `modified_date >= fecha_modif` y en paralelo ejecuta un full scan.
- **AC05:** El agente detecta formateo de máquina y reporta el nuevo `fingerprint` al backend para diferenciarlo del anterior.
- **AC06:** El agente detecta archivos eliminados respecto a la última iteración y envía la notificación correspondiente al backend.
- **AC07:** El agente respeta `classification_schedules` (ej. no saturar recursos cuando el usuario está trabajando).
- **AC08:** El agente reintenta el upload con backoff exponencial si falla, sin pedir URL nueva hasta que expire (1 hora).
- **AC09:** El agente funciona en Windows, macOS, Linux y sobre shares de FileServer sin cambios en el contrato de output.

#### 🔗 Dependencias

- **Backend Fase 1:** endpoint `POST /v2/tree/init` y bucket `compressed_trees/` operativos.
- **`s3-uploader`:** componente existente del ecosistema Kriptos.
- **KEM:** exposición de parámetros `excluded_paths`, `allowed_formats`, `classification_schedules`, `fecha_modif`.

#### 📎 Observaciones

- Honey pods (detección de comportamiento anómalo mediante archivos señuelo) queda TBD — sin arquitectura definida aún.
- Mecanismo exacto del fingerprint de formateo: decisión interna del equipo del agente.

---

### [Fase 1 · Agente Cloud] — Scanner de servicios de nube externos

**Owner sugerido:** Jeff
**Fuentes cubiertas:** OneDrive, SharePoint, Google Drive

#### 🎯 Objetivo

Descubrir archivos en servicios de nube externos (OneDrive / SharePoint / Google Drive), construir el mismo árbol NDJSON que produce el Agente Multiplataforma y entregarlo al backend.

#### 📋 Contexto

A diferencia del Agente Multiplataforma, este agente **no corre como binario en el equipo del usuario**. Es un conector/servicio que consume las APIs oficiales de cada proveedor cloud (Microsoft Graph para OneDrive/SharePoint, Google Drive API para Google). Se conecta con credenciales OAuth por tenant/enterprise. El output de descubrimiento es idéntico al del Agente Multiplataforma: el mismo formato de árbol NDJSON, para que el pipeline backend trate a todos los agentes de forma uniforme.

#### 🏗️ Alcance

- Autenticación OAuth / service account contra cada proveedor (OneDrive, SharePoint, Google).
- Gestión de credenciales por enterprise/tenant con rotación.
- Enumeración de archivos vía API (Microsoft Graph, Google Drive), manejando paginación y rate limiting.
- Construcción del árbol NDJSON con los mismos 7 campos que el Agente Multiplataforma (`name`, `path`, `size`, `extension`, `modified_date`, `created_date`, + metadata de trazabilidad). Normalización de paths al formato contractual.
- Upload del árbol a S3. Si el servicio corre dentro de AWS: PUT directo con IAM role al bucket `decompressed_trees/` (sin compresión, sin `s3-uploader`). Si no: mismo path que el Agente Multiplataforma.
- Detección de eliminación de archivos en el tenant + notificación al backend.
- Aislamiento cross-enterprise: un tenant no puede leer archivos de otro.

#### ✅ Acceptance Criteria

- **AC01:** El agente se autentica correctamente contra OneDrive, SharePoint y Google Drive usando credenciales por enterprise/tenant, con rotación funcional.
- **AC02:** El agente enumera archivos vía API de cada proveedor, manejando paginación hasta agotar el listado y respetando rate limits.
- **AC03:** El árbol producido tiene el mismo formato NDJSON que el Agente Multiplataforma: 7 campos por nodo, UTF-8 NFC, path normalizado.
- **AC04:** El agente escribe directo en `decompressed_trees/{ent}/{sta}/{tree_id}.jsonl` con credenciales IAM (asumiendo despliegue dentro de AWS), incluyendo los 7 headers de metadata (`enterprise-id`, `station-id`, `total-lines`, `fingerprint`, `uploaded-at`, `agent-version`, `tree-id`).
- **AC05:** Si la API devuelve error de auth (token expirado), el agente lo refresca y reintenta sin perder trabajos.
- **AC06:** Si la API devuelve rate limit (429), el agente aplica backoff exponencial respetando los headers de `Retry-After` del proveedor.
- **AC07:** El aislamiento cross-enterprise está garantizado: las credenciales IAM del agente solo permiten escritura dentro del prefix del enterprise asociado.
- **AC08:** El agente detecta archivos eliminados en el tenant respecto a la última iteración y envía la notificación al backend.
- **AC09:** El agente soporta los 3 proveedores (OneDrive, SharePoint, Google Drive) sin cambios en el contrato de output.

#### 🔗 Dependencias

- **Backend Fase 1:** bucket `decompressed_trees/` creado + IAM role provisionado para el Agente Cloud con permisos mínimos.
- **Equipo AI / seguridad:** mecanismo de almacenamiento seguro de credenciales OAuth por tenant (Secrets Manager u otro).
- **Configuración por cliente:** onboarding para obtener consentimiento OAuth del tenant por cada proveedor.

#### 📎 Observaciones

- A diferencia del Agente Multiplataforma, aquí no aplica "detección de formateo de máquina" (no hay máquina física) — el `fingerprint` puede ser un identificador estable del tenant.
- Filewatcher tiempo real (Fase 2) usa webhooks/notifications de cada API (no `inotify`/FSEvents): Microsoft Graph subscriptions, Google Drive push notifications. Fuera del scope de esta sub-tarea.

---

### [Fase 1 · Equipo AI] — Generación de keywords por enterprise (Bedrock)

**Owner sugerido:** Equipo AI (ya existe ticket KAIM-5793)

#### 🎯 Objetivo

Generar el archivo `keywords/{enterprise_id}.json` (2K–5K keywords) que el EMR usa como referencia para identificar joyas candidatas al matchear contra nombres de archivos.

#### 📋 Contexto

El EMR `joyas-priorizer` lee este archivo por enterprise y matchea contra el nombre de cada archivo del árbol. Sin este archivo, el EMR corre pero produce 0 matches (el AC05 de la sub-tarea de backend igual se cumple con archivo vacío).

#### 🏗️ Alcance

- Prompt a Bedrock con contexto: empresa, sector, país.
- Generación de 2K–5K keywords relevantes (palabras, siglas, términos de dominio).
- Normalización a UTF-8 NFC y deduplicación.
- Upload manual a `s3://keywords/{enterprise_id}.json` con el schema:
  ```json
  { "enterprise_id": "...", "version": "ISO-8601", "keywords": ["kw1", "kw2", ...] }
  ```

#### ✅ Acceptance Criteria

- **AC01:** Para cada enterprise onboarded existe un archivo `keywords/{enterprise_id}.json` en S3.
- **AC02:** El archivo pasa validación de schema: `enterprise_id` coincide con el path del objeto, `keywords` es un array no vacío de strings.
- **AC03:** Las keywords están en UTF-8 NFC y no contienen caracteres de control.
- **AC04:** La generación es reproducible: mismo contexto de entrada produce el mismo output semántico (sin depender de temperatura alta del modelo).
- **AC05:** Al regenerar el archivo (cambio de contexto), el campo `version` se actualiza al timestamp nuevo.

#### 🔗 Dependencias

- **Backend Fase 1:** bucket `keywords/` creado con permisos de PUT para el Equipo AI.

#### 📎 Observaciones

- El proceso es manual por ahora. Automatización (trigger al onboardar un enterprise) queda fuera de esta épica.
- Decisión pendiente: el keywords.json, ¿se sobrescribe o se versiona? Afecta auditoría de "con qué keywords se priorizó la estación X".

---

# 🧩 ÉPICA FASE 2 · Priority Sample Collection (GSE)

> ⚠️ **Acción PM:** esta épica debe reemplazar el contenido actual de **KT-16369**. El diseño cambió: **no hay caja negra intermedia de priorización**. El motor GSE consume directamente el `crown_jewels.jsonl` de Fase 1 y hace el scoring inline cuando es necesario.

## 🎯 Objetivo de la épica

Construir el motor genérico de colecta + anonimización de muestras de contenido que consume el output de Fase 1 (`crown_jewels.jsonl`), coordina con el agente (multiplataforma o cloud) para que extraiga el contenido de los archivos candidatos, los manda al Anonymizer, y cuando todas las muestras del ciclo están anonimizadas notifica al downstream LLM para que clasifique.

## 📋 Alcance de la épica

- Motor backend en AWS: DynamoDB (single-table con 3 niveles CYCLE/STATION/REQUEST), 3 colas SQS, 3 buckets S3, 2 EventBridge Pipes con DDB Streams, 6 Lambdas (cycle init, 3 notifiers, 2 barriers), endpoint `POST /v2/gse/request-complete`.
- Cliente GSE del **Agente Multiplataforma** (Windows/Mac/Linux/FileServer): recibir signal → extraer chunks del disco → subir samples → reportar cierre → recibir tags → taggear localmente.
- Cliente GSE del **Agente Cloud** (OneDrive/SharePoint/Google): mismo flujo, pero extrayendo contenido vía API del proveedor y aplicando tagging vía API en vez de filesystem.
- Plataforma Web: sensibilidad desde tabla de grupos, configuración de parámetros, vistas de pending/grupos.
- Dependencias externas (Equipo AI): Signal Handler (push al agente), Anonymizer core (lee gse-raw, escribe gse-anonymized), LLM Process Queue + Classifier (consume cycles cerrados).

## ✅ Criterio de aceptación de la épica

**Por cada `crown_jewels.jsonl` que aterriza en `crown_jewels/`, dentro de un tiempo razonable (SLA por definir según volumen) el LLM downstream recibe una notificación con `cycle_id` cerrado y el prefix S3 donde están las muestras anonimizadas listas para clasificar.**

## 🗓️ Secuenciación sugerida (sub-fases del backend)

| Sub-fase | Contenido | Bloqueado por |
|---|---|---|
| **2.A** · Foundation | DDB + buckets + colas + EventBridge rules/pipes | nada |
| **2.B** · Lambdas de cascada | Lambdas de barrier para station + enterprise | 2.A |
| **2.C** · Lambdas de ingest | Cycle init + 3 notifiers + API `request-complete` | 2.B |
| **2.D** · Integración cajas negras | Signal Handler + Anonymizer + LLM | contratos con Equipo AI |
| **2.E** · Hardening | Reaper + dedup + alarms + load test | 2.D |

---

## Sub-tareas Fase 2

### [Fase 2 · Backend/Pipeline] — Motor GSE completo

**Owner sugerido:** Haroldo

#### 🎯 Objetivo

Construir la infraestructura AWS que orquesta el ciclo GSE de principio a fin: dispara ciclos desde el output de Fase 1, coordina el upload de muestras por parte del agente, propaga la anonimización y notifica al LLM cuando un ciclo cierra.

#### 📋 Contexto

Motor genérico que hoy soporta un solo tipo de ciclo (`crown`, disparado por Fase 1). A futuro se pueden añadir otros tipos sin tocar el core — solo agregando una cola adicional. El estado se persiste en DDB single-table y la cascada de cierre (sample → station → cycle) se hace con contadores atómicos + DDB Streams + EventBridge Pipes.

#### 🏗️ Alcance

**Foundation (2.A):**
- DynamoDB `gse-cycles-samples` single-table con stream `NEW_AND_OLD_IMAGES` y TTL.
- Buckets S3: `gse-raw` (samples crudos) y `gse-anonymized` (samples procesados).
- 3 colas SQS + 3 DLQ: `gse-crown-cycle-queue` (FIFO), `gse-sample-reception-queue`, `gse-sample-anonymizer-queue`.
- 3 EventBridge rules (S3 → SQS).
- 2 EventBridge Pipes (DDB Stream → Lambdas de cascada) con filtros por prefijo del sort key.

**Lambdas de cascada (2.B):**
- Lambda que cierra STATION cuando `(samples_anonymized + samples_skipped) >= samples_expected` y al hacerlo incrementa el contador del CYCLE.
- Lambda que cierra CYCLE cuando `stations_completed >= stations_expected` y notifica al LLM.

**Lambdas de ingest (2.C):**
- Lambda `gse-cycle-init`: lee `crown_jewels.jsonl`, hace get-or-create del CYCLE, query a KEM para `stations_expected`, crea STATION + REQUEST en DDB, notifica al Signal Handler con el payload.
- Lambda que recibe events de `gse-raw`: incrementa `samples_received` y notifica al Anonymizer.
- Lambda que recibe events de `gse-anonymized`: incrementa `samples_anonymized`.
- Lambda detrás de API Gateway (`POST /v2/gse/request-complete`): marca REQUEST como `sent`, suma `samples_skipped`.

**Integración + Hardening (2.D–E):**
- Reemplazar los stubs de notify con los canales reales del Signal Handler, Anonymizer y LLM.
- Reaper Lambda para cycles colgados (status `collecting` por más de N horas → marcar `failed`).
- Alarmas CloudWatch sobre DLQs, errores, cycles stuck.

#### ✅ Acceptance Criteria

- **AC01:** Cuando un `crown_jewels.jsonl` aterriza en `crown_jewels/`, la Lambda `gse-cycle-init` crea en DDB los records CYCLE / STATION / REQUEST con `samples_expected = len(files_en_el_archivo)`.
- **AC02:** Si llegan dos eventos del mismo enterprise simultáneamente, se crea **un único CYCLE** (idempotencia por conditional write + FIFO MessageGroupId = enterprise_id).
- **AC03:** `gse-cycle-init` consulta KEM y setea `stations_expected = N` correctamente.
- **AC04:** `gse-cycle-init` publica al Signal Handler un payload `{cycle_id, process_type, enterprise_id, station_id, requests:[{type, files, sample_content_size}]}` por cada STATION creada.
- **AC05:** Cada PUT en `gse-raw/{...}/sample_NNN.json` incrementa `STATION.samples_received` en +1 de forma atómica.
- **AC06:** La Lambda de recepción notifica al Anonymizer con `{bucket, key, enterprise_id, station_id, cycle_id, request_type, sample_id}` por cada sample recibido.
- **AC07:** Cada PUT en `gse-anonymized/{...}/sample_NNN.json` incrementa `STATION.samples_anonymized` en +1.
- **AC08:** `POST /v2/gse/request-complete` acepta body válido, marca REQUEST como `sent` y suma `samples_skipped` a STATION de forma atómica (`TransactWriteItems`). Llamadas duplicadas devuelven 409 sin doble-aplicar.
- **AC09:** Cuando `(samples_anonymized + samples_skipped) >= samples_expected`, la Lambda de station cierra la STATION (conditional write) e incrementa `CYCLE.stations_completed` en +1 **exactamente una vez**, incluso si el stream entrega el record duplicado.
- **AC10:** Cuando `stations_completed >= stations_expected`, la Lambda de enterprise cierra el CYCLE (conditional write) y notifica al LLM Process Queue con `{cycle_id, enterprise_id, process_type, anonymized_prefix}`.
- **AC11:** Mensajes SQS duplicados no causan double-counting en el barrier (puede haber sobre-conteo cosmético en los contadores pero `>=` lo absorbe).
- **AC12:** DLQs configuradas en las 3 colas + 2 pipes, con alarmas CloudWatch sobre depth > 0.
- **AC13:** `POST /v2/gse/request-complete` requiere API key (rechaza 401 sin auth).
- **AC14:** Reaper Lambda detecta cycles con `status = "collecting"` desde hace más de N horas y los marca como `failed`, disparando alerta SNS.

#### 🔗 Dependencias

- **Fase 1 AC05:** `crown_jewels.jsonl` debe escribirse **siempre** (incluso vacío). Sin esto, AC09/AC10 no se cumplen — stations sin matches dejarían el ciclo colgado.
- **Equipo AI:** contratos del Signal Handler, Anonymizer y LLM Process Queue (ver sub-tarea del Equipo AI).
- **KEM:** endpoint de stations activas por enterprise + API key en Secrets Manager.

#### 📎 Observaciones

- Runtime (Python / Node / Go) pendiente de decidir — no bloquea el diseño.
- Las sub-fases 2.A / 2.B / 2.C pueden arrancar sin esperar al Equipo AI (stubs en los notifiers).
- La sub-fase 2.D queda bloqueada hasta tener los 3 canales firmes.

---

### [Fase 2 · Agente Multiplataforma] — Cliente GSE del agente local

**Owner sugerido:** Sol
**Fuentes cubiertas:** Windows, Mac, Linux, FileServer

#### 🎯 Objetivo

Implementar en el binario del agente los 6 pasos del GSE del lado cliente: recibir el signal del backend con la lista de archivos a muestrear, extraer chunks del filesystem local, subirlos al backend, reportar cierre, recibir tags de grupo y aplicar tagging local a los documentos pending.

#### 📋 Contexto

Lado cliente del motor GSE para el agente local. El agente orquesta la colecta local y la sincronización con el backend. Opera sobre archivos en el disco / volumen del usuario o sobre el share del FileServer. El tagging se aplica escribiendo en metadatos del sistema de archivos del OS sin alterar la fecha de modificación.

#### 🏗️ Alcance

- Recepción del push del Signal Handler con `{cycle_id, process_type, requests:[{type, files, sample_content_size}]}`.
- Idempotencia local por `cycle_id` (no re-ejecutar si el mismo signal llega dos veces).
- Por cada `file` en `files_to_sample`: extracción del chunk desde el filesystem respetando `sample_content_size`.
- Upload del sample vía `s3-uploader` (pre-signed URL) a `gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json`.
- Tracking local de archivos que no se pudieron procesar (locked, permission_denied, file_not_found).
- Llamada a `POST /v2/gse/request-complete` al cerrar cada request con `total_samples_uploaded + samples_skipped + skipped_reasons`.
- Recepción de tags por grupo desde el backend.
- Persistencia local de tags en la BDD de grupos + cache.
- Sincronización selectiva de documentos `pending` con grupo + clasificación resueltos.
- Aplicación de tagging a los documentos del grupo con status `pending`, **escribiendo en metadatos del filesystem sin alterar `fecha_modif`** (en Windows vía `SetFileTime`-preserve; en Unix vía `utime`/`utimensat` pre/post).

#### ✅ Acceptance Criteria

- **AC01:** El agente recibe el signal del backend y parsea el payload sin errores.
- **AC02:** Por cada `file` en `files_to_sample`, el agente extrae del disco un chunk del tamaño `sample_content_size` (bytes) y lo serializa como JSON.
- **AC03:** El agente sube cada sample a `gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json` vía `s3-uploader` usando pre-signed URL.
- **AC04:** Archivos que no se pudieron procesar quedan registrados con razón: `locked`, `permission_denied`, `file_not_found`.
- **AC05:** El agente llama `POST /v2/gse/request-complete` exactamente una vez por request cerrada, con `total_samples_uploaded` y `samples_skipped` correctos.
- **AC06:** Si el signal llega dos veces para el mismo `cycle_id`, el agente **no duplica los samples**.
- **AC07:** El agente recibe los tags por grupo del backend y los persiste en la BDD local + cache.
- **AC08:** El agente aplica el tag solo a documentos con estado `pending` del grupo recibido.
- **AC09:** El tagging **no altera `fecha_modif`** del archivo (requisito crítico; mecanismo dependiente del OS).
- **AC10:** El self-write del tagging no dispara eventos del Filewatcher (filtro de self-writes).
- **AC11:** Funciona en Windows, macOS, Linux y FileServer sin cambios en el contrato.

#### 🔗 Dependencias

- **Backend Fase 2:** endpoint `POST /v2/gse/request-complete` y bucket `gse-raw/` operativos.
- **Equipo AI — Signal Handler:** canal de push al agente definido y funcional.
- **`s3-uploader`:** disponibilidad de pre-signed URLs para el upload de samples (mecanismo de entrega del URL: se incluye en el payload del Signal Handler, o se pide vía endpoint adicional — decisión pendiente).

#### 📎 Observaciones

- **Tensión pendiente (producto + seguridad):** ¿el agente debe anonimizar PII localmente **antes** de subir al backend? El backend Fase 2 ya incluye un Anonymizer cloud. Opciones: (a) defensa en profundidad en ambos lados, (b) solo backend, (c) solo agente. Bloquea parcialmente esta sub-tarea.

---

### [Fase 2 · Agente Cloud] — Cliente GSE para servicios de nube externos

**Owner sugerido:** Jeff
**Fuentes cubiertas:** OneDrive, SharePoint, Google Drive

#### 🎯 Objetivo

Implementar el lado cliente del GSE para fuentes cloud: recibir el signal del backend, descargar contenido de archivos vía API del proveedor (OneDrive / SharePoint / Google), subir las muestras al backend, reportar cierre, recibir tags y aplicar tagging vía API sobre los archivos del tenant.

#### 📋 Contexto

Versión del cliente GSE cuando la fuente no es un disco local, sino un servicio de nube externo. El agente NO lee del filesystem: usa las APIs oficiales (Microsoft Graph, Google Drive API) para descargar contenido y para escribir tags/metadata de vuelta al servicio. El tagging en estos servicios es distinto al filesystem: se hace vía properties de SharePoint, custom metadata de OneDrive, labels de Google Drive.

#### 🏗️ Alcance

- Recepción del push del Signal Handler con el mismo payload que el Agente Multiplataforma.
- Idempotencia local por `cycle_id` (persistida en el store del servicio).
- Por cada `file` en `files_to_sample`: descarga de un rango de bytes (`sample_content_size`) vía API del proveedor (Microsoft Graph range download / Google Drive partial media).
- Upload del sample a `gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json` con PUT directo vía IAM (asumiendo despliegue en AWS).
- Tracking de archivos no descargables (permisos insuficientes, archivo eliminado en el tenant, rate limit no recuperable).
- Llamada a `POST /v2/gse/request-complete` al cerrar cada request.
- Recepción de tags por grupo del backend y aplicación vía API del proveedor:
  - **SharePoint:** `list item` properties o managed metadata.
  - **OneDrive:** `driveItem` custom facet o extended property.
  - **Google Drive:** `labels` o `properties` vía Files API.
- Preservación del estado "sin alterar" del archivo en la medida que la API del proveedor lo permita (equivalente cloud al "no alterar fecha_modif" del agente local).

#### ✅ Acceptance Criteria

- **AC01:** El agente recibe el signal del backend y parsea el payload sin errores.
- **AC02:** Por cada `file` en `files_to_sample`, el agente descarga vía API del proveedor un chunk del tamaño `sample_content_size` (usando range download para no bajar el archivo completo).
- **AC03:** El agente sube cada sample a `gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json` con PUT directo vía IAM (o vía `s3-uploader` si el despliegue no está en AWS).
- **AC04:** Archivos no descargables quedan registrados como skipped con razón (`permission_denied`, `file_not_found`, `rate_limit_exceeded`, etc.).
- **AC05:** El agente llama `POST /v2/gse/request-complete` exactamente una vez por request cerrada.
- **AC06:** Si el signal llega dos veces para el mismo `cycle_id`, el agente no duplica samples.
- **AC07:** El agente aplica el tag vía API del proveedor a documentos con estado `pending` del grupo recibido — el mecanismo es específico por proveedor (properties en SharePoint, custom metadata en OneDrive, labels/properties en Google Drive) y queda documentado por proveedor.
- **AC08:** La aplicación del tag **no altera la fecha de modificación visible al usuario final** del archivo en el servicio cloud, en la medida que la API del proveedor lo permita. Si la API no lo permite, se documenta el comportamiento esperado.
- **AC09:** El agente respeta rate limits de cada API (backoff con `Retry-After`) y nunca pierde samples por throttling.
- **AC10:** Funciona con los 3 proveedores (OneDrive, SharePoint, Google Drive) con el mismo contrato hacia el backend.

#### 🔗 Dependencias

- **Backend Fase 2:** bucket `gse-raw/` operativo + IAM role provisionado.
- **Equipo AI — Signal Handler:** canal de push al agente.
- **Credenciales OAuth / service account** vigentes por tenant (heredadas de Fase 1).

#### 📎 Observaciones

- La aplicación de tags en servicios cloud tiene limitaciones por proveedor — algunos servicios pueden actualizar automáticamente la `modified_date` al escribir properties. Queda documentado por proveedor en esta sub-tarea.
- **Misma tensión de anonimización:** aplica la misma decisión que para el Agente Multiplataforma.

---

### [Fase 2 · Plataforma Web] — UI de grupos, sensibilidad y configuración del agente

**Owner sugerido:** equipo frontend

#### 🎯 Objetivo

Adaptar la plataforma web al modelo nuevo: la sensibilidad se lee de la tabla de grupos (vía `id_grupo`, no del análisis individual), permitir la validación manual de documentos sin grupo asignado, exponer la configuración del agente desde la UI y ajustar las vistas para reflejar el modelo de grupos.

#### 📋 Contexto

9 cambios identificados en el diseño del agente v3. Depende de un cambio de schema en DDB (campo `id_grupo` en la tabla de analyses) y de que los datos reales del agente fluyan (para el detalle completo).

#### 🏗️ Alcance

- **Schema:** agregar `id_grupo` en la DDB `kr-dat-ana-{enterprise_id}-dydb`.
- **Sensibilidad:** frontend lee de la tabla de grupos (no del análisis individual).
- **Vistas nuevas:** documentos en `pending`, grupos detectados, clusters con criterios.
- **Asignación manual:** UX para asignar grupo a documentos "sin grupo asignado".
- **Configuración:** UI para los 9 parámetros editables del agente, persistidos en KEM (`chunk_size_kb`, `max_chunks`, `big_file_threshold`, `sample_content_size`, `fecha_modif`, `excluded_paths`, `fixed_classification_paths`, `allowed_formats`, `max_threads`).
- **Observabilidad:** vista limitada a `big_file` con separación por agente.
- **Contadores:** por grupo, por estado (`pending` / `classified` / `big_file`), separados por agente.
- **Columnas:** tamaño de documento visible, fecha de última conexión del agente.
- **Movimiento entre máquinas:** UX para confirmar formateo de máquina detectado.

#### ✅ Acceptance Criteria

- **AC01:** La DDB `kr-dat-ana-{ent}-dydb` tiene el campo `id_grupo` y los nuevos análisis lo escriben.
- **AC02:** El frontend consulta la tabla de grupos vía `id_grupo` para mostrar la sensibilidad (ya no lo lee del análisis).
- **AC03:** Existe una vista que lista documentos en estado `pending` con filtros por station, grupo y fecha.
- **AC04:** Existe una vista que muestra los grupos detectados localmente por cada agente.
- **AC05:** El operador puede asignar manualmente un grupo a un documento en "sin grupo asignado" y el cambio se persiste.
- **AC06:** Existe una vista de clusters con criterios y lista de miembros.
- **AC07:** La vista de observabilidad está limitada a `big_file` y separa visualmente por agente (multiplataforma / cloud).
- **AC08:** Los contadores muestran: por grupo, por estado, por agente.
- **AC09:** La columna `tamaño` aparece en análisis y explorador.
- **AC10:** La fecha de última conexión del agente se muestra usando el sistema de auth existente.
- **AC11:** El operador puede configurar desde la UI los 9 parámetros del agente y se persisten en KEM.
- **AC12:** Existe una UX para validar el movimiento de archivos clasificados entre máquinas (confirmación del formateo).

#### 🔗 Dependencias

- **Backend:** definir el schema exacto del campo `id_grupo` + estrategia de backfill para análisis existentes.
- **Agente (ambos):** payload de tagging que incluya `id_grupo`.
- **KEM:** endpoint de configuración de parámetros (read/write).

#### 📎 Observaciones

- Algunas vistas (pending, clusters, contadores) pueden mockearse con datos sintéticos mientras el agente produce data real.
- Backfill de `id_grupo` para análisis históricos: decisión pendiente (mostrar "legacy" vs. ocultar).

---

### [Fase 2 · Equipo AI] — Signal Handler + Anonymizer core + LLM Process Queue

**Owner sugerido:** Equipo AI

#### 🎯 Objetivo

Proveer las 3 piezas externas que Fase 2 consume como cajas negras: el canal de push al agente (Signal Handler), el servicio de anonimización de muestras (Anonymizer core) y el consumidor de ciclos cerrados que ejecuta la clasificación final (LLM Process Queue + Classifier).

#### 📋 Contexto

El backend de Fase 2 define el contrato de entrada/salida para las 3 piezas. El Equipo AI las implementa y acuerda el canal específico de comunicación con el backend (SNS / SQS / EventBridge / IoT / HTTP).

#### 🏗️ Alcance

**Signal Handler:**
- Canal que recibe del backend el payload `{cycle_id, process_type, enterprise_id, station_id, requests}` (emitido por la Lambda `gse-cycle-init`).
- Push a la station/tenant correspondiente del agente.
- Retención del payload si el agente está offline, con TTL definido.
- Idempotencia documentada: el agente debe asumir al menos 1 entrega, posiblemente más.
- Canal reverso para entregar los tags por grupo de vuelta al agente (mismo canal o alterno — decisión del Equipo AI).

**Anonymizer core:**
- Recibe notificaciones del backend con `{bucket, key, enterprise_id, station_id, cycle_id, request_type, sample_id}`.
- Lee el sample desde `gse-raw/{path}` (requiere permisos S3).
- Ejecuta el core de anonimización.
- Escribe el resultado en `gse-anonymized/{mismo path}` (requiere permisos S3).
- Idempotente por `sample_id`.
- DLQ propia para fallos internos.

**LLM Process Queue + Classifier:**
- Recibe notificaciones del backend con `{cycle_id, enterprise_id, process_type, anonymized_prefix, ...}`.
- Lee los samples anonimizados desde el prefix S3.
- Clasifica (LLM con Bedrock u otro proveedor).
- Persiste resultados en la tabla DDB de analyses (campo `id_grupo` + clasificación final).
- Idempotente por `cycle_id`.

#### ✅ Acceptance Criteria

**Signal Handler:**
- **AC01:** Existe un canal concreto (SNS / SQS / IoT / HTTP) definido y documentado con su ARN o endpoint.
- **AC02:** El backend puede publicar al canal y el payload llega al agente correcto (multiplataforma o cloud) en menos de 60 segundos (objetivo).
- **AC03:** Si el agente está offline, el payload se retiene y se entrega al reconectar, con TTL definido.
- **AC04:** Existe un canal reverso (mismo o alterno) para entregar tags por grupo de vuelta al agente.

**Anonymizer core:**
- **AC05:** Existe un canal concreto definido para que el backend le envíe notificaciones por sample.
- **AC06:** El Anonymizer tiene permisos S3 (cross-account si aplica) sobre `gse-raw/*` (GET) y `gse-anonymized/*` (PUT).
- **AC07:** Por cada notificación, el Anonymizer produce un PUT en `gse-anonymized/{mismo path que gse-raw}` con el sample procesado.
- **AC08:** Es idempotente por `sample_id`: el mismo sample notificado dos veces produce un solo output (o dos outputs idénticos con overwrite).
- **AC09:** Fallos internos van a DLQ propia del Equipo AI (no al DLQ del backend).

**LLM Process Queue + Classifier:**
- **AC10:** Existe un canal concreto (SQS / SNS / EventBridge) definido para que el backend le envíe notificaciones de ciclo cerrado.
- **AC11:** El servicio tiene permisos S3 para leer `gse-anonymized/*`.
- **AC12:** Por cada notificación de ciclo cerrado, el servicio lee los samples, clasifica y persiste en la DDB de analyses con `id_grupo` correcto.
- **AC13:** Es idempotente por `cycle_id`: el mismo ciclo notificado dos veces no duplica la clasificación.

#### 🔗 Dependencias

- **Backend Fase 2:** buckets `gse-raw/` y `gse-anonymized/` creados + bucket policy que permita el acceso del Equipo AI.
- **Backend Fase 2:** Lambdas publicadoras operativas con stubs reemplazables por los ARN/endpoints reales.

#### 📎 Observaciones

- Esta sub-tarea es **acordar + implementar** los 3 contratos. Opcionalmente puede dividirse en 3 sub-tareas separadas si cada pieza la toma una persona distinta del Equipo AI.
- **Bloquea la sub-fase 2.D del backend** (integración real).

---

# 📊 Resumen para la PM

## Épicas

| Épica | Ticket | Acción sugerida |
|---|---|---|
| Fase 1 · Scan & File Discovery | KT-16368 | **Mantener** tal cual. Alinear sub-tareas con las 4 de este documento |
| Fase 2 · Priority Sample Collection (GSE) | KT-16369 | **Actualizar título + descripción + alcance** con el contenido de este documento. Ya no es "Priority Crown Jewel Detection & Prioritization" — es "Priority Sample Collection (GSE)" |

## Sub-tareas (9 en total)

| Épica | Sub-tarea | Área | Owner sugerido |
|---|---|---|---|
| Fase 1 | Backend/Pipeline | backend AWS | Haroldo |
| Fase 1 | Agente Multiplataforma | Win/Mac/Linux/FileServer | Sol |
| Fase 1 | Agente Cloud | OneDrive/SharePoint/Google | Jeff |
| Fase 1 | Keywords Bedrock | AI | Equipo AI (ya existe KAIM-5793) |
| Fase 2 | Backend/Pipeline — Motor GSE | backend AWS | Haroldo |
| Fase 2 | Agente Multiplataforma — Cliente GSE | Win/Mac/Linux/FileServer | Sol |
| Fase 2 | Agente Cloud — Cliente GSE | OneDrive/SharePoint/Google | Jeff |
| Fase 2 | Plataforma Web | frontend | equipo frontend |
| Fase 2 | Signal Handler + Anonymizer + LLM | AI | Equipo AI |

## Bloqueantes críticos para levantar en planning

1. **Fase 1 AC05** (EMR escribe archivo vacío cuando no hay matches) — bloquea Fase 2.
2. **Tensión de anonimización agente vs backend** — bloquea sub-tareas de agente en Fase 2 (ambos agentes).
3. **Contratos de canales** (Signal Handler, Anonymizer, LLM) — bloquean la sub-fase 2.D del backend.
4. **Endpoint KEM de stations activas** — bloquea `gse-cycle-init`.
5. **Runtime del backend** (Python / Node / Go) — no bloquea diseño pero sí estimación precisa.
