# Tickets para construir el backend desde cero

> **Contexto:** olvidamos el POC. Lo único que existe es **KEM**. Todo lo demás se construye desde cero.
> **Para:** Haroldo (owner del backend).
> **Cómo usar:** copiar/pegar cada ticket al sistema correspondiente.

---

## Decisión global previa

Antes de abrir cualquier ticket de DevOps, definir:

- **Runtime de las Lambdas:** Python / Node / Go. Los ejemplos de los tickets usan **Python** — ajustar si se decide otro.
- **Cuenta AWS y región:** asumido `us-east-1`. Confirmar si hay separación dev/prod.
- **Naming convention:** asumido `kriptos-{env}-{nombre}`. Ej: `kriptos-dev-compressed-trees`.

---

# 🟦 FASE 1 — Scan & File Discovery

## Ticket 1 · DevOps — `tree-url-generator`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`tree-url-generator`**.

**Función:** la Lambda recibe un POST del agente y devuelve una pre-signed URL para que suba el árbol de archivos al bucket.

**Infraestructura requerida:**
- **Bucket S3 nuevo** `compressed_trees` con encryption AES-256, public-access block, EventBridge notifications habilitado.
- **API Gateway HTTP API nuevo** con ruta `POST /v2/tree/init` integrada con esta Lambda. Auth: API key.
- **CloudWatch Log Group** con retention 30 días.

**Permisos IAM de la Lambda:**
- `s3:PutObject` sobre `compressed_trees/*` (necesario para firmar la presigned URL).

**Configuración Lambda:** memoria 256 MB, timeout 30 s.

---

## Ticket 2 · DevOps — `tree-uncompressor`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`tree-uncompressor`**.

**Función:** se dispara cuando llega un archivo `.jsonl.gz` al bucket `compressed_trees`. Lo descomprime y lo escribe en otro bucket. Propaga los headers de metadata.

**Infraestructura requerida:**
- **Bucket S3 nuevo** `decompressed_trees` con encryption AES-256, public-access block, EventBridge notifications habilitado.
- **EventBridge Rule** que escuche `Object Created` en `compressed_trees` con suffix `.jsonl.gz` → invoca esta Lambda.
- **DLQ SQS** para reintentos fallidos (máx receives = 2 → DLQ).
- **CloudWatch Log Group** con retention 30 días.
- **CloudWatch alarm** sobre depth de la DLQ > 0.

**Permisos IAM de la Lambda:**
- `s3:GetObject`, `s3:HeadObject` sobre `compressed_trees/*`.
- `s3:PutObject` y operaciones multipart sobre `decompressed_trees/*`.

**Configuración Lambda:** memoria 1024 MB, timeout 300 s.

---

## Ticket 3 · DevOps — `emr-job-trigger`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`emr-job-trigger`**.

**Función:** se dispara cuando llega un archivo `.jsonl` al bucket `decompressed_trees`. Arranca un job de EMR Serverless pasándole el bucket y key como argumentos.

**Infraestructura requerida:**
- **EMR Serverless application** (release `emr-7.0.0`, tipo Spark, max capacity 4 vCPU / 8 GB, auto-start, auto-stop después de 5 min idle).
- **EventBridge Rule** que escuche `Object Created` en `decompressed_trees` con suffix `.jsonl` → invoca esta Lambda.
- **DLQ SQS** + alarma.
- **CloudWatch Log Group** con retention 30 días.

**Permisos IAM de la Lambda:**
- `emr-serverless:StartJobRun` sobre la application.
- `iam:PassRole` sobre el rol de ejecución de EMR (ver Ticket 4).

**Configuración Lambda:** memoria 256 MB, timeout 60 s.

---

## Ticket 4 · DevOps — `joyas-priorizer` (EMR Spark)

Crear repo con pipeline para desplegar un job PySpark a EMR Serverless. Repo: **`joyas-priorizer`**.

**Función:** lee el árbol descomprimido + el archivo de keywords del enterprise (que el equipo AI deposita previamente), hace match por nombre de archivo, y escribe el resultado en otro bucket. **Importante: si no hay matches, debe escribir un archivo vacío de todas formas** (necesario para que Fase 2 sepa que esa estación terminó).

**Infraestructura requerida:**
- **Bucket S3 nuevo** `keywords` (con permisos para que el equipo AI suba archivos — confirmar con DevOps los principales IAM del equipo AI).
- **Bucket S3 nuevo** `crown_jewels` con encryption, public-access block, EventBridge notifications habilitado.
- El pipeline debe subir `job.py` al bucket `keywords` (o uno separado para scripts).
- **IAM execution role para EMR** con permisos:
  - `s3:GetObject`, `ListBucket` sobre `decompressed_trees/*` y `keywords/*`.
  - `s3:PutObject`, `DeleteObject`, `ListBucket` sobre `crown_jewels/*` (para `mode("overwrite")` de Spark).
  - `logs:*` para los driver/executor.

**Configuración EMR job:** 1 driver + 1 executor, 1 vCPU y 1 GB cada uno, dynamic allocation OFF.

---

## Ticket 5 · DevOps — Monitoring base

Crear infraestructura compartida de monitoring para todo el backend.

**Infraestructura requerida:**
- **SNS topic** `kriptos-backend-alerts`.
- **Subscriptions** del topic: email del equipo backend + canal de Slack (pedir confirmación).
- Alarmas de Fase 1 (de los tickets 1–4) deben publicar a este topic.

---

# 🟪 FASE 2 — Priority Sample Collection (GSE)

## Ticket 6 · DevOps — `gse-cycle-init`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`gse-cycle-init`**.

**Función:** se dispara cuando llega un archivo `crown_jewels.jsonl` al bucket `crown_jewels` (output de Fase 1). Crea o reusa un ciclo en DDB, consulta KEM por las stations activas, crea los registros del ciclo, y notifica al agente vía Signal Handler (canal del equipo AI).

**Infraestructura requerida:**
- **DynamoDB table nueva** `gse-cycles-samples`:
  - PK = String, SK = String.
  - DDB Stream activado con `NEW_AND_OLD_IMAGES`.
  - TTL en atributo `ttl`.
  - Billing PAY_PER_REQUEST.
- **SQS FIFO nueva** `gse-crown-cycle-queue.fifo` con su DLQ.
- **EventBridge Rule** que escuche `Object Created` en `crown_jewels` con suffix `crown_jewels.jsonl` → SQS.
- **Event Source Mapping** del SQS a esta Lambda (batch size 1).
- **CloudWatch Log Group** + alarma sobre DLQ.

**Permisos IAM de la Lambda:**
- `s3:GetObject`, `s3:HeadObject` sobre `crown_jewels/*`.
- `dynamodb:Query`, `PutItem`, `BatchWriteItem`, `UpdateItem` sobre `gse-cycles-samples`.
- `secretsmanager:GetSecretValue` sobre el secret donde vive la API key del KEM.
- (Pendiente) permisos de publicación al canal del Signal Handler — se añade cuando el equipo AI defina el canal.

**Configuración Lambda:** memoria 512 MB, timeout 60 s.

---

## Ticket 7 · DevOps — `gse-sample-reception-notifier`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`gse-sample-reception-notifier`**.

**Función:** se dispara cada vez que el agente sube un sample crudo a `gse-raw`. Incrementa el contador en DDB y notifica al Anonymizer (canal del equipo AI).

**Infraestructura requerida:**
- **Bucket S3 nuevo** `gse-raw` con encryption, public-access block, EventBridge notifications habilitado, lifecycle rule de 7 días.
- **SQS standard nueva** `gse-sample-reception-queue` con su DLQ.
- **EventBridge Rule** que escuche `Object Created` en `gse-raw` con suffix `.json` → SQS.
- **Event Source Mapping** del SQS a esta Lambda (batch size 10, batch window 5 s).
- **CloudWatch Log Group** + alarma sobre DLQ.

**Permisos IAM de la Lambda:**
- `dynamodb:UpdateItem` sobre `gse-cycles-samples`.
- (Pendiente) permisos de publicación al canal del Anonymizer — se añade cuando el equipo AI defina el canal.

**Configuración Lambda:** memoria 256 MB, timeout 30 s.

---

## Ticket 8 · DevOps — `gse-sample-anonymizer-notifier`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`gse-sample-anonymizer-notifier`**.

**Función:** se dispara cuando el Anonymizer escribe un sample anonimizado a `gse-anonymized`. Incrementa el contador en DDB. Esta Lambda no notifica nada externo — el cierre del ciclo lo dispara el DDB Stream.

**Infraestructura requerida:**
- **Bucket S3 nuevo** `gse-anonymized` con encryption, public-access block, EventBridge notifications habilitado, lifecycle rule de 30 días. El equipo AI debe tener permisos de PUT sobre este bucket (confirmar con DevOps los principales IAM del equipo AI).
- **SQS standard nueva** `gse-sample-anonymizer-queue` con su DLQ.
- **EventBridge Rule** que escuche `Object Created` en `gse-anonymized` con suffix `.json` → SQS.
- **Event Source Mapping** del SQS a esta Lambda (batch size 10, batch window 5 s).
- **CloudWatch Log Group** + alarma sobre DLQ.

**Permisos IAM de la Lambda:**
- `dynamodb:UpdateItem` sobre `gse-cycles-samples`.

**Configuración Lambda:** memoria 256 MB, timeout 30 s.

---

## Ticket 9 · DevOps — `gse-request-complete`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`gse-request-complete`**.

**Función:** endpoint HTTP que el agente llama cuando termina de subir todos los samples de una request. Marca la request como completada y suma los archivos saltados.

**Infraestructura requerida:**
- **Nueva ruta en el API Gateway de Fase 1** (Ticket 1): `POST /v2/gse/request-complete` integrada con esta Lambda. Auth: API key.
- **CloudWatch Log Group**.

**Permisos IAM de la Lambda:**
- `dynamodb:UpdateItem`, `TransactWriteItems`, `GetItem` sobre `gse-cycles-samples`.

**Configuración Lambda:** memoria 256 MB, timeout 30 s.

---

## Ticket 10 · DevOps — `gse-station-status`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`gse-station-status`**.

**Función:** se dispara cuando cualquier registro de tipo STATION cambia en DDB. Si los contadores cuadran, cierra la station y suma 1 al contador del ciclo padre.

**Infraestructura requerida:**
- **EventBridge Pipe** con:
  - Source = DDB Stream de `gse-cycles-samples`.
  - Filter = `eventName IN ["MODIFY","INSERT"]` AND `NewImage.SK begins_with "STATION#"`.
  - Target = esta Lambda.
  - Batch size 10, batching window 5 s.
  - DLQ propio + alarma.
- **CloudWatch Log Group**.

**Permisos IAM de la Lambda:**
- `dynamodb:UpdateItem` sobre `gse-cycles-samples`.

**Permisos IAM del Pipe (rol del Pipe):**
- `dynamodb:DescribeStream`, `GetShardIterator`, `GetRecords`, `ListStreams` sobre el stream de la tabla.
- `lambda:InvokeFunction` sobre esta Lambda.

**Configuración Lambda:** memoria 256 MB, timeout 30 s.

---

## Ticket 11 · DevOps — `gse-enterprise-status`

Crear repo con pipeline para desplegar una Lambda en **Python**. Repo: **`gse-enterprise-status`**.

**Función:** se dispara cuando cualquier registro de tipo CYCLE cambia en DDB. Si todas las stations cerraron, cierra el ciclo y notifica al downstream LLM (canal del equipo AI).

**Infraestructura requerida:**
- **EventBridge Pipe** con:
  - Source = DDB Stream de `gse-cycles-samples`.
  - Filter = `eventName = "MODIFY"` AND `NewImage.SK begins_with "CYCLE#"`.
  - Target = esta Lambda.
  - Batch size 10, batching window 5 s.
  - DLQ propio + alarma.
- **CloudWatch Log Group**.

**Permisos IAM de la Lambda:**
- `dynamodb:UpdateItem` sobre `gse-cycles-samples`.
- (Pendiente) permisos de publicación al canal del LLM Process Queue — se añade cuando el equipo AI defina el canal.

**Permisos IAM del Pipe:** mismo patrón que Ticket 10.

**Configuración Lambda:** memoria 256 MB, timeout 30 s.

---

# Resumen

| # | Componente | Bloquea a |
|---|---|---|
| 1 | tree-url-generator | nada |
| 2 | tree-uncompressor | nada (paralelo a 1) |
| 3 | emr-job-trigger | 4 |
| 4 | joyas-priorizer (EMR) | 6 (output es input de Fase 2) |
| 5 | Monitoring base | nada (paralelo) |
| 6 | gse-cycle-init | 7, 8, 9, 10, 11 |
| 7 | gse-sample-reception-notifier | 10 (necesita data en DDB) |
| 8 | gse-sample-anonymizer-notifier | 10 |
| 9 | gse-request-complete | 10 |
| 10 | gse-station-status | 11 |
| 11 | gse-enterprise-status | nada (último de la cadena) |
