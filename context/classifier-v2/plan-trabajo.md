# Plan de trabajo dinámico — Backend Classifier V2

> **Propósito:** vista cruzada por **área × fase**, con entregable esperado y historias de usuario sugeridas por componente.
> **Audiencia:** PMs / leads que están escribiendo HUs · arquitectos validando dependencias.
> **Estado:** vivo — actualizar conforme se cierren TBDs (canales de cajas negras, runtime backend, etc.)

---

## Áreas y owners

| # | Área | Owner | Estado actual | Tecnología |
|---|---|---|---|---|
| A | **Agente Multiplataforma** (PC: Windows/Mac/Linux/FileServer/OneDrive/SharePoint/Google) | Equipo agente | Spec v3 lista · 6 definiciones pendientes · 11 parámetros | TBD |
| B | **Agente Cloud** (corre dentro AWS del cliente) | Equipo agente | Mismo binario que A con flags + IAM role distinto | TBD |
| C | **Backend Phase 1** (Scan & File Discovery) | Equipo backend | POC validado en `poc-harias` | POC en Python; runtime productivo TBD |
| D | **Backend Phase 2** (GSE) | Equipo backend | Spec lista | TBD |
| E | **Plataforma Web** (UI/UX) | Equipo frontend | 9 cambios identificados | Existente (Vue) |
| F | **Cajas negras / dependencias** | Otros equipos | Contratos pendientes | n/a |

---

## Mapa de dependencias entre áreas

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
   Agente (A/B) ───▶│ POST /v2/tree/init    ──▶  Backend Phase 1 │
                    │ PUT presigned URL                           │
                    │                                             │
                    │                       ◀─── Signal Handler ──│ ◀── Backend Phase 2
                    │                            (caja negra F)   │
                    │                                             │
                    │ PUT samples a gse-raw ──▶ Backend Phase 2  │
                    │ POST /v2/gse/request-complete               │
                    └─────────────────────────────────────────────┘
                                        │
                                        ▼
                          Plataforma Web (E) lee:
                            · DDB analyses (campo nuevo id_grupo)
                            · DDB grupos (sensibilidad)
                            · KEM (parametrización)

   Cajas negras (F):
     · Signal Handler   ─── push del payload de cycle al agente
     · Anonymizer       ─── lee gse-raw, escribe gse-anonymized
     · LLM Process      ─── consume cycle cerrado, clasifica
     · KEM API          ─── stations activas + parámetros
     · Bedrock          ─── generación de keywords (Phase 1)
```

---

# Plan por fase

## Fase 1 · Scan & File Discovery

**Objetivo de la fase:** desde el escaneo del disco del agente hasta tener `suspicious_crown_jewels/{ent}/{sta}/crown_jewels.jsonl` listo para Phase 2.

**Estado:** Phase 1 backend = POC validado. Phase 1 agente = pendiente (cambios v3 al binario).

### Componentes y entregables · Phase 1

#### A1 · Scanner del agente · construcción + envío del árbol

- **Entregable:** binario del agente que recorre el disco y manda al backend `POST /v2/tree/init` + sube el `tree.jsonl.gz` con el payload v3 (incluye tamaño + fecha_creación por archivo).
- **Fase:** F1.A
- **Dependencias:** ninguna externa. Endpoint del backend ya existe en POC.
- **Bloquea a:** Phase 1 backend (no procesa nada sin trees) y Phase 2 (no hay crown_jewels sin trees).
- **HU sugeridas:**
  - **HU-A1.1** — Como **agente**, quiero **construir el árbol del disco respetando `excluded_paths`** para enviar solo lo relevante.
  - **HU-A1.2** — Como **agente**, quiero **incluir `tamaño` y `fecha_modificación` por archivo** en el payload del árbol para que la plataforma muestre tamaño y el backend priorice mejor.
  - **HU-A1.3** — Como **agente**, quiero **escanear primero por fecha de modificación descendente** (parámetro `fecha_modif`) para procesar lo reciente primero.
  - **HU-A1.4** — Como **operador**, quiero **detectar formateo de máquina** para no reclasificar archivos migrados de otra estación.

#### A2 · Subida del árbol · `s3-uploader` (PC Agent)

- **Entregable:** integración con `s3-uploader` existente para PUT del `.jsonl.gz` con los headers `x-amz-meta-*` que firmó el backend.
- **Fase:** F1.A
- **Dependencias:** `s3-uploader` (componente existente · caja negra interna).
- **HU sugeridas:**
  - **HU-A2.1** — Como **PC Agent**, quiero **enviar el tree comprimido vía pre-signed URL** para no depender de auth permanente.
  - **HU-A2.2** — Como **PC Agent**, quiero **reintentar el upload con backoff** si falla, sin pedir nueva URL.

#### B1 · Subida del árbol · PUT directo (Cloud Agent)

- **Entregable:** Cloud Agent que escribe directo en `decompressed_trees` con su IAM role (sin gzip, sin s3-uploader).
- **Fase:** F1.B
- **Dependencias:** IAM role provisioned (ver C1).
- **HU sugeridas:**
  - **HU-B1.1** — Como **Cloud Agent**, quiero **escribir el tree sin compresión, directo a `decompressed_trees`** con mi IAM role para reducir overhead.

#### C1 · Backend Phase 1 · Lambdas + EMR (POC validado)

- **Entregable:** los 3 lambdas (`tree-url-generator`, `tree-uncompressor`, `emr-job-trigger`) + EMR Serverless `joyas-priorizer` ya desplegados.
- **Fase:** F1.C — ya hecho
- **Dependencias:** ninguna nueva.
- **Pendiente crítico para habilitar Phase 2:**
  - **HU-C1.1** — Como **EMR job**, quiero **escribir un `crown_jewels.jsonl` vacío para stations con 0 matches** para que Phase 2 no se atasque esperando un evento que nunca llega.
- **Pendiente cosmético:**
  - **HU-C1.2** — Como **infra**, quiero **renombrar el bucket `crown_jewels` a `suspicious_crown_jewels`** para alinear con el diagrama nuevo y la semántica "candidatos no validados".
- **Pendiente productización:**
  - **HU-C1.3** — Como **operador**, quiero **API key + WAF en `/v2/tree/init`** antes de exponerlo a producción.
  - **HU-C1.4** — Como **operador**, quiero **DLQs y alarmas en los 3 lambdas** para detectar fallas.
  - **HU-C1.5** — Como **operador**, quiero **dedup de trees por `tree_id` o `fingerprint`** para evitar reprocesar.

#### F1 · KEM · contrato de stations activas

- **Entregable:** endpoint `GET /v2/kem/stations?enterprise_id=...` que devuelve la lista de stations activas con `total`.
- **Fase:** F1.D (bloqueante para inicio de Phase 2)
- **Owner:** equipo KEM
- **HU sugeridas:**
  - **HU-F1.1** — Como **backend Phase 2**, necesito **un endpoint KEM que me dé la cantidad de stations activas por enterprise** para fijar `stations_expected`.

#### F2 · Bedrock · generación de keywords (manual)

- **Entregable:** flujo manual de generación + upload de `keywords/{ent}.json` al bucket.
- **Fase:** F1.E (no bloquea, pero sin keywords la EMR produce 0 matches)
- **Owner:** equipo data / IA
- **HU sugeridas:**
  - **HU-F2.1** — Como **analista**, quiero **generar keywords vía Bedrock con contexto de empresa/sector/país** y subirlas a S3 manualmente.

### Entregable agregado de Phase 1

> **Cuando Phase 1 está "lista":**
> Cada estación que el agente escanea produce, en menos de ~5 minutos del PUT del árbol, un `suspicious_crown_jewels/{ent}/{sta}/crown_jewels.jsonl` (eventualmente vacío) con metadata propagada.

---

## Fase 2 · Priority Sample Collection (GSE)

**Objetivo de la fase:** desde que un `crown_jewels.jsonl` aterriza en `suspicious_crown_jewels` hasta que el LLM downstream tiene los samples anonimizados listos para clasificar.

**Estado:** spec lista. Implementación no iniciada.

### Sub-fases sugeridas para Phase 2 backend

| Sub-fase | Contenido | Bloqueado por |
|---|---|---|
| **2.A · Foundation** | DDB + buckets + colas + EB rules + EB pipes (sin Lambdas destino aún) | nada |
| **2.B · Lambdas de cascada** | `gse-station-status` + `gse-enterprise-status` (cierran barriers, no notifican externo) | 2.A |
| **2.C · Lambdas de ingest** | `gse-cycle-init` + `gse-sample-reception-notifier` + `gse-sample-anonymizer-notifier` + `gse-request-complete` (con stubs de notify) | 2.B |
| **2.D · Integración cajas negras** | conectar Signal Handler · Anonymizer · LLM Queue (canales reales) | otros equipos |
| **2.E · Hardening** | Reaper de cycles colgados · dedup formal · monitoring · alarms | 2.D |

### Componentes y entregables · Phase 2

#### D1 · `gse-cycles-samples` (DynamoDB)

- **Entregable:** tabla DDB con stream `NEW_AND_OLD_IMAGES` activado, schema 3-niveles (CYCLE/STATION/REQUEST), TTL configurado.
- **Fase:** 2.A
- **Dependencias:** ninguna.
- **HU sugeridas:**
  - **HU-D1.1** — Como **backend**, quiero **una tabla DDB single-table con CYCLE/STATION/REQUEST** para persistir el estado del ciclo GSE.
  - **HU-D1.2** — Como **backend**, quiero **DDB Streams activos** para que los lambdas de cascada reaccionen a cambios.
  - **HU-D1.3** — Como **operador**, quiero **TTL de 30 días en records cerrados** para auto-cleanup.

#### D2 · Buckets `gse-raw` y `gse-anonymized`

- **Entregable:** 2 buckets nuevos con encryption, public-block, EventBridge notifications, lifecycle rules.
- **Fase:** 2.A
- **Dependencias:** ninguna.
- **HU sugeridas:**
  - **HU-D2.1** — Como **agente**, quiero **un bucket `gse-raw` con permisos de PUT** para subir samples crudos.
  - **HU-D2.2** — Como **infra**, quiero **lifecycle rules en `gse-raw` (7 días) y `gse-anonymized` (30 días)** para no acumular storage indefinido.
  - **HU-D2.3** — Como **Cloud Agent**, necesito **un IAM role que me permita PUT en `gse-raw/{mi enterprise}/...`** sin cross-enterprise access.

#### D3 · Colas SQS (3 + DLQs) y EventBridge rules (3)

- **Entregable:** `gse-crown-cycle-queue` (FIFO) + `gse-sample-reception-queue` + `gse-sample-anonymizer-queue` + 3 DLQs + 3 EB rules S3→SQS.
- **Fase:** 2.A
- **Dependencias:** D2 (buckets como source).
- **HU sugeridas:**
  - **HU-D3.1** — Como **backend**, quiero **3 colas SQS bien diferenciadas** (FIFO para cycle init, standard para samples) para procesar eventos con la semántica adecuada.
  - **HU-D3.2** — Como **operador**, quiero **DLQs con alarmas en cada cola** para detectar fallas sostenidas.
  - **HU-D3.3** — Como **infra**, quiero **EventBridge rules con filter por suffix** para no entregar eventos irrelevantes a las colas.

#### D4 · EventBridge Pipes (DDB Stream → status lambdas)

- **Entregable:** 2 Pipes con filtros por prefijo SK (`STATION#` y `CYCLE#`) apuntando a los 2 lambdas de cascada.
- **Fase:** 2.A (estructura) · target en 2.B
- **HU sugeridas:**
  - **HU-D4.1** — Como **backend**, quiero **un EventBridge Pipe sobre el stream de DDB filtrando STATION items** para alimentar `gse-station-status` sin parsear la tabla entera.

#### D5 · `gse-station-status` (Lambda)

- **Entregable:** Lambda que centraliza el barrier de STATION y escala al CYCLE.
- **Fase:** 2.B
- **Dependencias:** D1, D4.
- **HU sugeridas:**
  - **HU-D5.1** — Como **backend**, quiero **un Lambda que cierre la STATION cuando `(anonymized + skipped) >= expected`** con conditional write para evitar double-counting.
  - **HU-D5.2** — Como **backend**, quiero que **el cierre de STATION incremente atómicamente `CYCLE.stations_completed`**.

#### D6 · `gse-enterprise-status` (Lambda)

- **Entregable:** Lambda que cierra el CYCLE y notifica al downstream LLM.
- **Fase:** 2.B (lógica DDB) + 2.D (notify real)
- **Dependencias:** D1, D4, F4 (LLM contract).
- **HU sugeridas:**
  - **HU-D6.1** — Como **backend**, quiero **un Lambda que cierre el CYCLE cuando todas las stations cerraron** y publique al downstream LLM.
  - **HU-D6.2** — Como **LLM downstream**, quiero **recibir solo cycles completos**, con prefix S3 de los samples anonimizados.

#### D7 · `gse-cycle-init` (Lambda)

- **Entregable:** Lambda que ingiere eventos de las colas de cycle, hace get-or-create del CYCLE y notifica al Signal Handler.
- **Fase:** 2.C (sin notify) + 2.D (notify real)
- **Dependencias:** D1, D3, F1 (KEM), F3 (Signal Handler contract).
- **HU sugeridas:**
  - **HU-D7.1** — Como **backend**, quiero **un Lambda que dispara un cycle GSE cuando aterriza un crown_jewels.jsonl**, consultando KEM para fijar `stations_expected`.
  - **HU-D7.2** — Como **backend**, quiero que **el lambda discrimine `process_type` por EventSourceArn** para soportar múltiples colas de origen sin código distinto.
  - **HU-D7.3** — Como **backend**, quiero **idempotencia vía conditional writes** para que mensajes SQS duplicados no creen 2 cycles.

#### D8 · `gse-sample-reception-notifier` (Lambda)

- **Entregable:** Lambda que procesa eventos de samples crudos: incrementa `samples_received` y notifica al Anonymizer.
- **Fase:** 2.C (sin notify) + 2.D (notify real)
- **Dependencias:** D1, D3, F2 (Anonymizer contract).
- **HU sugeridas:**
  - **HU-D8.1** — Como **backend**, quiero **incrementar atómicamente `samples_received` por cada sample** que aterrice en `gse-raw`.
  - **HU-D8.2** — Como **backend**, quiero **notificar al Anonymizer con `bucket+key`** del sample para que lo procese.

#### D9 · `gse-sample-anonymizer-notifier` (Lambda)

- **Entregable:** Lambda que procesa eventos de samples anonimizados: solo incrementa `samples_anonymized`.
- **Fase:** 2.C
- **Dependencias:** D1, D3.
- **HU sugeridas:**
  - **HU-D9.1** — Como **backend**, quiero **incrementar atómicamente `samples_anonymized`** por cada sample que aparezca en `gse-anonymized`.

#### D10 · `gse-request-complete` (Lambda + API GW)

- **Entregable:** endpoint HTTP `POST /v2/gse/request-complete` con su Lambda backend.
- **Fase:** 2.C
- **Dependencias:** D1.
- **HU sugeridas:**
  - **HU-D10.1** — Como **agente**, quiero **un endpoint para reportar que terminé de subir samples de una request** (con `total_samples_uploaded` y `samples_skipped`).
  - **HU-D10.2** — Como **backend**, quiero **idempotencia con conditional write** para tolerar reintentos del agente.
  - **HU-D10.3** — Como **operador**, quiero **API key + rate limit** en este endpoint.

#### A3 · Agente · recibir signal y cargar samples (PC y Cloud)

- **Entregable:** módulo GSE del agente que recibe el payload del Signal Handler, extrae chunk + metadata por archivo, sube a `gse-raw` (PC vía s3-uploader, Cloud vía PUT directo), y llama `/v2/gse/request-complete` al cerrar.
- **Fase:** F2.agente (paralelo a 2.C/D del backend)
- **Dependencias:** F3 (Signal Handler contract).
- **HU sugeridas:**
  - **HU-A3.1** — Como **agente**, quiero **recibir el payload del cycle (cycle_id, requests, files_to_sample)** del Signal Handler.
  - **HU-A3.2** — Como **agente**, quiero **extraer un chunk de cada `file` de `files_to_sample`** respetando `sample_content_size`.
  - **HU-A3.3** — Como **agente**, quiero **subir cada sample a `gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json`** (vía s3-uploader si PC, IAM si Cloud).
  - **HU-A3.4** — Como **agente**, quiero **reportar `samples_skipped` con motivos** (locked, permission_denied, file_not_found) cuando no puedo procesar un archivo.
  - **HU-A3.5** — Como **agente**, quiero **anonimizar localmente PII básica antes de subir** ⚠️ ver **tensión #1** abajo.

#### F3 · Signal Handler · push al agente

- **Entregable:** servicio que recibe del backend el payload de cycle por station y lo entrega a la station correspondiente.
- **Fase:** F2.equipo-agente
- **Owner:** equipo plataforma agente / IoT
- **Dependencias:** acuerdo de canal (TBD: SNS/SQS/IoT/HTTP).
- **HU sugeridas:**
  - **HU-F3.1** — Como **backend Phase 2**, necesito **un canal para empujar el payload de cycle a una station específica**.
  - **HU-F3.2** — Como **agente**, quiero **recibir el payload sin polling activo** (push real).
  - **HU-F3.3** — Como **operador**, quiero **fallback de entrega cuando la station está offline** (TTL del payload).

#### F4 · Anonymizer core · procesamiento de samples

- **Entregable:** servicio que lee `gse-raw`, anonimiza, y escribe en `gse-anonymized` (mismo path).
- **Fase:** F2.equipo-anonimización
- **Owner:** equipo seguridad / IA
- **Dependencias:** acuerdo de canal de notificación (TBD) + permisos S3 cross-account si están en otra cuenta.
- **HU sugeridas:**
  - **HU-F4.1** — Como **backend Phase 2**, necesito **un servicio que anonimice samples** y los espeje a `gse-anonymized`.
  - **HU-F4.2** — Como **Anonymizer**, quiero **idempotencia por `sample_id`** para tolerar mensajes duplicados.
  - **HU-F4.3** — Como **infra**, quiero **acuerdo de bucket policy cross-account** para que el Anonymizer lea/escriba sin compromiso de IAM general.

#### F5 · LLM Process Queue + Classifier · clasificación final

- **Entregable:** consumidor que arranca con `cycle_id` + prefix S3 y produce las clasificaciones.
- **Fase:** F2.equipo-IA
- **Owner:** equipo IA
- **Dependencias:** acuerdo de canal (TBD).
- **HU sugeridas:**
  - **HU-F5.1** — Como **backend Phase 2**, necesito **un canal para entregar cycles cerrados al LLM**.
  - **HU-F5.2** — Como **LLM**, quiero **idempotencia por `cycle_id`** para tolerar reintentos.
  - **HU-F5.3** — Como **frontend**, quiero **que la clasificación quede persistida en la tabla DDB de analyses** para mostrarla.

### Entregable agregado de Phase 2

> **Cuando Phase 2 está "lista":**
> Para cada `crown_jewels.jsonl` que aterriza, dentro de un tiempo razonable (TBD según volumen) el LLM downstream recibe una notificación con `cycle_id` cerrado y la ubicación de los samples anonimizados listos para clasificar.

---

# Plan por área (vista perpendicular)

## A · Agente Multiplataforma (PC)

**7 módulos del binario** según [v2/new-agent/](new-agent/) — el plan agrupa por módulo, no por fase backend (porque el agente integra ambas fases).

### A.Scanner

- **Entregable:** árbol completo del disco enviado al backend con `tamaño + fecha_creación` por archivo. Scan por fecha descendente (feature flag).
- **HU clave:** HU-A1.1 a HU-A1.4 (ver Phase 1)
- **Decisiones pendientes:** Honey pods (TBD), fingerprint de formateo (TBD).

### A.Processing

- **Entregable:** extracción por chunks fijos, colas big/small, tokenización + embedding + fuzzy hash por chunk.
- **HU sugeridas:**
  - **HU-A.P1** — Como **agente**, quiero **separar archivos en colas big/small** según `big_file_threshold` para que los grandes no bloqueen.
  - **HU-A.P2** — Como **agente**, quiero **tokenizar con input extendido** (chunk + metadata) para alimentar al classifier.
  - **HU-A.P3** — Como **agente**, quiero **un mecanismo SWAP en colas** para no perder trabajos en alta carga (TBD diseño).

### A.Classifier

- **Entregable:** 4 ramas (Regex, Grupos `heads`, PII `Siege`, Joyas) + Scoring que produce `analysis_classification_status`.
- **HU sugeridas:**
  - **HU-A.C1** — Como **agente**, quiero **4 sub-clasificadores en paralelo** y un Scoring final.
  - **HU-A.C2** — Como **agente**, quiero la **rama Joyas detrás de feature flag** para activarla solo cuando el cliente la configura.
- **Decisiones pendientes (críticas):** algoritmo `heads`, algoritmo `Siege`, lógica de Scoring cuando 3 ramas escriben el mismo campo.

### A.GSE (Group Sample Engine — lado agente)

- **Entregable:** 6 pasos del GSE local (recibir señal → colectar/enviar sample anonimizado → recibir tags → actualizar BDD grupos → sincronizar pending → llamar Tagging).
- **HU clave:** HU-A3.1 a HU-A3.5 (ver Phase 2)
- **Tensión crítica:** ver **Tensión #1** abajo (anonimización agente vs backend).

### A.Tagging

- **Entregable:** escritura de tags en metadatos del archivo **sin alterar fecha de modificación** + actualización de hashset dedup + señal al backend.
- **HU sugeridas:**
  - **HU-A.T1** — Como **agente**, quiero **escribir tags sin alterar `fecha_modif`** del archivo (Win: SetFileTime preserve, macOS/Linux: utime pre/post).
  - **HU-A.T2** — Como **agente**, quiero **un filtro de self-writes** para que mis propios cambios de metadata no disparen el filewatcher.

### A.Real-time / Filewatcher

- **Entregable:** filewatcher con debounce que enruta a la cola high de Processing.
- **HU sugeridas:**
  - **HU-A.R1** — Como **agente**, quiero **filewatcher con debounce** para no encolar el mismo evento múltiples veces.
  - **HU-A.R2** — Como **agente**, quiero **monitorear solo formatos permitidos** y poder limitar a paths prioritarios (POC primero).

### A.Sistema / KEM

- **Entregable:** integración con KEM para parametrización + System Tray notification + validación de firma del binario.
- **HU sugeridas:**
  - **HU-A.S1** — Como **operador**, quiero **ver en System Tray cuando el agente está desactivado**.
  - **HU-A.S2** — Como **agente**, quiero **leer parámetros desde KEM** (todos los 11) sin hardcoding.
  - **HU-A.S3** — Como **operador**, quiero **validación de firma del binario** para detectar tampering.

## B · Agente Cloud

> Mismo binario que A con flags y wiring distinto. Los entregables son las mismas HU de A excepto:

- **Excluir:** s3-uploader (no aplica — usa IAM directo).
- **Excluir:** System Tray (no hay UI en cloud).
- **Añadir:** provisioning del IAM role para PUT en `gse-raw` y `decompressed_trees`.

**HU específicas Cloud:**
- **HU-B.1** — Como **operador**, quiero **un IAM role pre-provisioned para Cloud Agent** con permisos mínimos para PUT en los 2 buckets.
- **HU-B.2** — Como **Cloud Agent**, quiero **detectar mi modo (cloud vs PC) al arrancar** para usar la ruta de upload correcta.

## C · Backend Phase 1

Ya cubierto en sección por fase. Resumen de entregables:
- 4 lambdas + EMR — ya hechos.
- Fix de `crown_jewels.jsonl` vacío — pendiente.
- API auth + monitoring — pendiente.

## D · Backend Phase 2

Ya cubierto en sección por fase (D1-D10).

## E · Plataforma Web

9 cambios identificados en [v2/new-agent/plataforma-web.md](new-agent/plataforma-web.md). Resumen por componente:

#### E1 · Vistas de pending y grupos

- **Entregable:** vista en plataforma con documentos en `pending` + grupos detectados localmente; permite asignación manual a `sin grupo asignado`.
- **HU sugeridas:**
  - **HU-E1.1** — Como **operador**, quiero **ver documentos en estado `pending`** para validar manualmente los que el agente no clasificó.
  - **HU-E1.2** — Como **operador**, quiero **asignar manualmente un grupo** a documentos `sin grupo asignado`.

#### E2 · Visualización de clusters

- **HU sugeridas:**
  - **HU-E2.1** — Como **operador**, quiero **ver los clusters generados, sus criterios, y los docs asignados**.

#### E3 · Tamaño de doc visible

- **HU sugeridas:**
  - **HU-E3.1** — Como **operador**, quiero **ver el tamaño en las vistas de análisis y explorador**.

#### E4 · Observabilidad solo big files

- **HU sugeridas:**
  - **HU-E4.1** — Como **operador**, quiero **una vista de observabilidad limitada a `big_file`**, con separación visual por agente.

#### E5 · Contadores ajustados

- **HU sugeridas:**
  - **HU-E5.1** — Como **operador**, quiero **contadores por grupo y por estado** (`pending`, `classified`, `big_file`), separados por agente.

#### E6 · Última conexión

- **HU sugeridas:**
  - **HU-E6.1** — Como **operador**, quiero **ver la fecha de última conexión** de cada agente, usando el sistema de auth existente.

#### E7 · Configuración de parametrizaciones

- **HU sugeridas:**
  - **HU-E7.1** — Como **operador**, quiero **configurar los 9 parámetros del agente desde la UI** (chunk_size, max_chunks, sample_content_size, paths, etc.) — todos persistidos en KEM.

#### E8 · Movimiento entre máquinas

- **HU sugeridas:**
  - **HU-E8.1** — Como **operador**, quiero **una UX para validar archivos clasificados que migran de una máquina a otra**.

#### E9 · Sensibilidad por tabla de grupos

- **HU sugeridas:**
  - **HU-E9.1** — Como **frontend**, quiero **leer la sensibilidad desde la tabla de grupos vía `id_grupo`** (no desde el análisis individual).
  - **HU-E9.2** — Como **frontend**, quiero **distinguir visualmente documentos sin grupo asignado** para empujar la validación manual.

## F · Cajas negras / dependencias externas

Ya cubiertas en sección por fase (F1-F5). Resumen:

| Caja negra | Owner | Bloqueante | Lo que esperamos |
|---|---|---|---|
| KEM API | Equipo backend (KEM) | Sí — bloquea `gse-cycle-init` | Endpoint stations activas |
| Bedrock keywords | Equipo data | No — Phase 1 funciona sin él (0 matches) | Generación + upload de keywords/{ent}.json |
| Signal Handler | Equipo plataforma agente | Sí — bloquea integración Phase 2 | Push payload a station |
| Anonymizer | Equipo seguridad/IA | Sí — bloquea cierre de cycle | Lee gse-raw, escribe gse-anonymized |
| LLM Process Queue + Classifier | Equipo IA | Sí — bloquea entregable final | Clasifica el cycle |

---

# Tensiones identificadas (decisiones que afectan a varios equipos)

## Tensión #1 · Anonimización: ¿agente o backend?

- **Spec del agente** ([v2/new-agent/gse.md](new-agent/gse.md)) dice: "El sample debe ir ANONIMIZADO antes de enviarse al back".
- **Spec del backend** (este plan + [phase2/external-contracts.md](new-backend/phase2/external-contracts.md)) define un **Anonymizer cloud** que procesa `gse-raw → gse-anonymized`.

**Posibles interpretaciones:**
- (a) **Defensa en profundidad**: agente hace pase básico (PII obvia), backend hace pase profundo (prompt injection, etc.).
- (b) **El agente NO anonimiza**: el spec es histórico, ahora todo es backend.
- (c) **El agente anonimiza, el backend solo valida**: backend rechaza si detecta PII no anonimizada.

**Bloquea:** HU-A3.5 + HU-F4.1 + el contrato del Anonymizer.
**Decisión pendiente — owner: producto + seguridad.**

## Tensión #2 · Canales de las 3 cajas negras

Signal Handler · Anonymizer · LLM Queue — los 3 sin canal definido. Cada equipo dueño elige: SNS, SQS, EventBridge, Lambda invoke, HTTP, IoT.

**Bloquea:** integración Phase 2.D para el backend.
**Decisión pendiente — owner: cada equipo dueño + arquitectura.**

## Tensión #3 · Runtime del backend

POC Phase 1 está en Python. Phase 2 sin definir. ¿Continuar Python? ¿Pasar a Node/TypeScript? ¿Go por performance?

**Bloquea:** estimación real de tareas técnicas (S/M/L), pero NO bloquea diseño.
**Decisión pendiente — owner: equipo backend.**

## Tensión #4 · Semántica del barrier de Phase 2

Hoy: STATION cierra con `(anonymized + skipped) >= expected`. Si el agente sub-reporta `samples_skipped` y el Anonymizer falla, el cycle queda colgado.

**Decisiones derivadas:**
- ¿Necesitamos un Reaper que cierre cycles tras N horas? (HU-D-Reaper futura)
- ¿Necesitamos timeout en la API request-complete?

**Owner:** equipo backend + producto.

## Tensión #5 · Cycles concurrentes por enterprise

Si llega un trigger `crown` mientras hay un `crown` collecting, ¿se reusa el cycle o se crea otro? Hoy: get-or-create busca por `(enterprise + status=collecting + process_type)` → reusa.

**Caso borde:** Phase 1 produce trees a destiempo (una station termina hoy, otra mañana). El cycle "abierto" abarcaría ambas → el LLM espera más de lo razonable.

**Decisión pendiente:** ¿windowing por tiempo? ¿forzar cierre tras N horas?

---

# Métricas para la planificación (estimación gruesa)

| Área | # entregables backend | # HU candidatas | Bloqueo principal |
|---|---|---|---|
| Backend Phase 1 (mejoras) | 5 | ~5 | EMR fix |
| Backend Phase 2 | 10 | ~25 | 3 cajas negras |
| Agente PC (todos los módulos) | 7 módulos × ~3 HU | ~25 | 6 definiciones del agente |
| Agente Cloud | overlap con PC + 2 propias | ~2 propias | IAM provisioning |
| Plataforma Web | 9 cambios | ~12 | DDB schema (id_grupo) |
| Cajas negras | 5 contratos | ~15 (HU del lado dueño) | acuerdos cross-equipo |

**Total HU candidatas:** ~85–100 según granularidad final.

---

# Referencias

- Spec backend: [new-backend/README.md](new-backend/README.md), [new-backend/phase1/](new-backend/phase1/), [new-backend/phase2/](new-backend/phase2/)
- Spec agente: [new-agent/README.md](new-agent/README.md), [new-agent/definiciones.md](new-agent/definiciones.md), [new-agent/parametrizaciones.md](new-agent/parametrizaciones.md), [new-agent/plataforma-web.md](new-agent/plataforma-web.md)
- Diagramas: [new-backend/arquitectura-completa.html](new-backend/arquitectura-completa.html), [new-backend/phase1-scan-file-discovery.html](new-backend/phase1-scan-file-discovery.html), [new-backend/phase2-priority-sample-collection.html](new-backend/phase2-priority-sample-collection.html), [plan-trabajo.html](plan-trabajo.html)
