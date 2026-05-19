# SQS Queues — Phase 2

3 colas propias de Phase 2. Todas con DLQ. Las decisiones de FIFO vs Standard están justificadas por el patrón de uso.

---

## 1 · `gse-crown-cycle-queue`

**Tipo:** **SQS FIFO** (`.fifo` suffix)
**Productor:** EventBridge rule sobre PutObject en `suspicious_crown_jewels`
**Consumidor:** `gse-cycle-init` Lambda

### Por qué FIFO

`gse-cycle-init` hace **get-or-create** del CYCLE por enterprise. Si llegan dos eventos del mismo enterprise simultáneamente, dos invocaciones intentan crear el CYCLE → conditional write deduplica pero genera reintentos innecesarios.

Con FIFO + `MessageGroupId = enterprise_id`, los eventos del mismo enterprise se procesan **secuencialmente**, eliminando la race.

### Configuración

| Parámetro | Valor |
|---|---|
| Type | FIFO |
| Content-based deduplication | `false` (lo manejamos manual) |
| MessageDeduplicationId | `sha256(bucket+key)` — set por la EventBridge rule |
| MessageGroupId | `enterprise_id` — set por la EventBridge rule |
| Visibility timeout | 90 s (3× Lambda timeout) |
| Message retention | 4 días |
| Receive wait time (long polling) | 20 s |
| Max receive count | 3 → DLQ |
| KMS encryption | SSE-SQS |

### DLQ

| Parámetro | Valor |
|---|---|
| Name | `gse-crown-cycle-dlq.fifo` |
| Retention | 14 días |
| Alerta | CloudWatch alarm `ApproximateNumberOfMessagesVisible > 0` → SNS |

### Trigger config (Lambda Event Source Mapping)

```yaml
batch_size: 1                         # FIFO + get-or-create → procesar de a 1 facilita debugging
maximum_batching_window: 0            # FIFO recomienda 0
function_response_types: ["ReportBatchItemFailures"]
```

### Cola futura paralela: `gse-classification-cycle-queue`

Misma config, distinto MessageGroupId pattern (TBD). Mismo Lambda destino. La discriminación `process_type` la hace `gse-cycle-init` por `EventSourceArn`.

---

## 2 · `gse-sample-reception-queue`

**Tipo:** **SQS standard**
**Productor:** EventBridge rule sobre PutObject en `gse-raw`
**Consumidor:** `gse-sample-reception-notifier` Lambda

### Por qué standard

El consumer solo hace `ADD samples_received += 1` (atómico) + notify al Anonymizer. **No hay get-or-create ni race condition**. El throughput esperado es alto (cada sample = 1 mensaje), FIFO sería un cuello de botella innecesario.

Idempotencia se aborda con dedup por `sample_id` (TBD) o aceptando sobre-conteo.

### Configuración

| Parámetro | Valor |
|---|---|
| Type | Standard |
| Visibility timeout | 60 s (2× Lambda timeout) |
| Message retention | 4 días |
| Receive wait time (long polling) | 20 s |
| Max receive count | 5 → DLQ |
| KMS encryption | SSE-SQS |

### DLQ

| Parámetro | Valor |
|---|---|
| Name | `gse-sample-reception-dlq` |
| Retention | 14 días |
| Alerta | CloudWatch alarm `ApproximateNumberOfMessagesVisible > 0` → SNS |

### Trigger config

```yaml
batch_size: 10
maximum_batching_window: 5
function_response_types: ["ReportBatchItemFailures"]
```

---

## 3 · `gse-sample-anonymizer-queue`

**Tipo:** **SQS standard**
**Productor:** EventBridge rule sobre PutObject en `gse-anonymized`
**Consumidor:** `gse-sample-anonymizer-notifier` Lambda

### Por qué standard

Mismo razonamiento que `gse-sample-reception-queue`: solo `ADD samples_anonymized += 1`, sin race. Throughput alto.

### Configuración

| Parámetro | Valor |
|---|---|
| Type | Standard |
| Visibility timeout | 60 s |
| Message retention | 4 días |
| Receive wait time | 20 s |
| Max receive count | 5 → DLQ |
| KMS encryption | SSE-SQS |

### DLQ

| Parámetro | Valor |
|---|---|
| Name | `gse-sample-anonymizer-dlq` |
| Retention | 14 días |
| Alerta | CloudWatch alarm `ApproximateNumberOfMessagesVisible > 0` → SNS |

### Trigger config

```yaml
batch_size: 10
maximum_batching_window: 5
function_response_types: ["ReportBatchItemFailures"]
```

---

## EventBridge Rules (S3 → SQS)

Las 3 colas se alimentan vía 3 EventBridge rules, una por bucket origen.

### Rule 1 · `suspicious-crown-jewels-to-cycle-queue`

```yaml
event_pattern:
  source: ["aws.s3"]
  detail-type: ["Object Created"]
  detail:
    bucket:
      name: ["kriptos-{env}-suspicious-crown-jewels"]
    object:
      key: [{ "suffix": "crown_jewels.jsonl" }]
target: arn:aws:sqs:...:gse-crown-cycle-queue.fifo
input_transformer:
  input_paths:
    bucket: "$.detail.bucket.name"
    key:    "$.detail.object.key"
  input_template: |
    {
      "version": "0",
      "detail-type": "Object Created",
      "source": "aws.s3",
      "detail": {
        "bucket": { "name": "<bucket>" },
        "object": { "key": "<key>" }
      }
    }
sqs_target_parameters:
  message_group_id: "$.detail.bucket.name"   # idealmente enterprise_id — extraer del key
  message_deduplication_id: "$.id"           # event id (único por delivery)
```

> **Nota:** `MessageGroupId = enterprise_id` requiere extraer el primer segmento del key. Como EventBridge no permite parseo arbitrario en input transformer, hay 2 opciones:
> - (a) Lambda intermedia que recibe el event y reenvía a SQS con el group id correcto.
> - (b) Aceptar `MessageGroupId = bucket_name` (todos los enterprises serializados — peor para throughput pero más simple).
> - (c) Cambiar a SQS standard y aceptar la race (mitigada por conditional writes).
>
> Recomendación: **(a) Lambda intermedia minimal** o **(c) standard con conditional**.

### Rule 2 · `gse-raw-to-reception-queue`

```yaml
event_pattern:
  source: ["aws.s3"]
  detail-type: ["Object Created"]
  detail:
    bucket:
      name: ["kriptos-{env}-gse-raw"]
    object:
      key: [{ "suffix": ".json" }]
target: arn:aws:sqs:...:gse-sample-reception-queue
```

### Rule 3 · `gse-anonymized-to-anonymizer-notifier-queue`

```yaml
event_pattern:
  source: ["aws.s3"]
  detail-type: ["Object Created"]
  detail:
    bucket:
      name: ["kriptos-{env}-gse-anonymized"]
    object:
      key: [{ "suffix": ".json" }]
target: arn:aws:sqs:...:gse-sample-anonymizer-queue
```

---

## Resumen de configuración

| Cola | Tipo | Visibility | Max receive | Batch | Justificación |
|---|---|---|---|---|---|
| `gse-crown-cycle-queue` | FIFO | 90s | 3 | 1 | Get-or-create CYCLE necesita serialización por enterprise |
| `gse-sample-reception-queue` | Standard | 60s | 5 | 10 | Throughput alto, ADD atómico, no hay race |
| `gse-sample-anonymizer-queue` | Standard | 60s | 5 | 10 | Idem |

---

## Tareas de implementación

| # | Tarea | Estimación |
|---|---|---|
| 1 | Crear las 3 colas + 3 DLQs en Terraform | S |
| 2 | Crear las 3 EventBridge rules + permisos S3 → EB | S |
| 3 | Resolver el dilema MessageGroupId del FIFO (a/b/c) | M |
| 4 | Configurar las 3 alarmas CloudWatch sobre DLQs | S |
| 5 | Conectar Lambdas como Event Source Mappings | S |
| 6 | Test de envío manual y consumo en cada cola | S |

---

## Decisiones por confirmar

- **FIFO vs Standard para `gse-crown-cycle-queue`:** depende de la opción a/b/c del MessageGroupId. Si la complejidad de la Lambda intermedia no compensa, ir a Standard + conditional writes.
- **Backpressure:** si N stations × M samples saturan reception/anonymizer queues, Lambda concurrency debe escalar. Considerar `reserved concurrency` para no afectar otras Lambdas.
- **Dedup formal por sample_id:** ver [gse-cycles-samples.md#idempotencia](gse-cycles-samples.md#idempotencia).
