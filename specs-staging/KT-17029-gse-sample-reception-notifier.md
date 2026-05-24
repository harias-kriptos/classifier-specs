# Spec — gse-sample-reception-notifier

> Ticket: [KT-17029](https://kriptosteam.atlassian.net/browse/KT-17029)
> Status: accepted (Fase 2 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/gse-sample-reception-notifier`

---

## 1. Goal

Por cada sample crudo (`.json`) que el agente sube a `gse-raw/`, incrementar `samples_received` en la STATION row del DDB y notificar al Anonymizer (caja negra Equipo IA). Si es el primer sample, transicionar `sampling_status` de `requested` a `uploading`.

## 2. Non-goals

- Anonimización (caja negra Equipo IA).
- Validación del contenido del sample.
- Cierre de la STATION (eso es KT-17032).
- Manejar samples batch — cada sample es un archivo `.json` singular (NO `.jsonl`).

## 3. User-visible behavior

Trigger: SQS `gse-sample-reception-queue` ← EventBridge sobre PutObject suffix `.json` en `gse-raw`.

```
Input:  s3://gse-raw/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json
        (un sample = un archivo JSON con chunk + metadata de UN file)
Side effects:
  1. Parsear path → enterprise_id, station_id, cycle_id, request_type, sample_id (=NNN).
  2. UpdateItem STATION (la row ya existe, no PUT):
     - ADD samples_received :one
     - SET sampling_status = if_not_exists(sampling_status, :requested) → transiciona a "uploading" si era requested.
     Actually mejor: conditional SET sampling_status="uploading" IF sampling_status="requested".
  3. NOTIFY Anonymizer con payload {bucket, key, ent, sta, cycle, request_type, sample_id}.
```

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/sample_key.py` | Parser regex `{ent}/{sta}/{cycle}/{req_type}/sample_NNN.json` (con extensión `.json` exactamente) | Rechaza `.jsonl`, otros suffixes. |
| `src/domain/sample_id.py` | `sample_id = NNN` del filename. Validador: integer. | |
| `src/application/ports/state_store.py` | Protocol con `increment_samples_received_and_transition_status` | Atomic update: counter ADD + conditional SET status. |
| `src/application/ports/anonymizer_notifier.py` | Protocol `notify(payload)` | Stub con log si canal vacío. |
| `src/application/usecases/notify_reception.py` | Use case mínimo | Idempotente a nivel sobre-conteo aceptable. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """SQS batch handler."""
```

Anonymizer payload (stub):

```json
{
  "bucket": "kriptos-{env}-gse-raw",
  "key": "ent-001/station-A/cycle-uuid/crown_jewels/sample_001.json",
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "cycle-uuid",
  "request_type": "crown_jewels",
  "sample_id": "001"
}
```

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — DDB, Anonymizer notify (canal TBD)
- `pydantic`

## 7. Test plan

```
[ ] test_sample_key::test_parses_5_segment_key
[ ] test_sample_key::test_rejects_jsonl_extension (debe ser .json)
[ ] test_sample_key::test_rejects_path_traversal
[ ] test_sample_id::test_extracts_NNN_from_filename
[ ] test_state_store::test_increment_returns_new_value
[ ] test_state_store::test_first_increment_transitions_status_to_uploading
[ ] test_state_store::test_subsequent_increments_dont_re_transition
[ ] test_state_store::test_station_in_status_uploading_remains_uploading
[ ] test_anonymizer_notifier::test_stub_logs_when_no_channel
[ ] test_notify_reception::test_full_happy_path
[ ] test_notify_reception::test_station_not_found_logs_warn (race con cycle-init)
[ ] test_notify_reception::test_duplicate_sqs_message_over_counts (aceptable)
[ ] test_handler::test_processes_batch_of_10
[ ] test_e2e::test_put_sample_increments_ddb_counter_and_transitions_status (moto)
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | PUT directo en `gse-raw` por atacante | Bucket IAM restricted: PC Agent via presigned URL (1h, scoped), Cloud Agent via IAM con scope enterprise. |
| DoS | Flood de samples spurios | SQS retry + DLQ. Sobre-conteo aceptable (el barrier final usa `>=`). |
| Info disclosure | Payload Anonymizer expone path real | Topic/cola encriptada KMS; sub solo el Anonymizer Lambda. |

## 10. Resolved decisions

- **sample_id = filename NNN** del archivo (`sample_001.json` → `sample_id="001"`). El path S3 completo es la fuente de verdad para dedupe (mismo path = mismo sample).
- **Samples como `.json` singular**, NO `.jsonl`. Un sample = un archivo S3 = un objeto JSON con chunk + metadata de UN file. Cada PUT dispara EventBridge → counter ++ granular.
- **Transición de status**: conditional SET `sampling_status="uploading" IF sampling_status="requested"`. Solo la primera invocación gana la transición; las siguientes son no-op para el status.
- **Anonymizer notify**: stub con log mientras Equipo IA define canal.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | Canal Anonymizer final | Equipo IA | Cuando entreguen ARN/endpoint |

## 12. Rollout

- Branch: `KT-17029-gse-sample-reception-notifier`
- Spec + TDD commits
- Tests verdes; cobertura ≥ 80%
- PR a `main` con `Implements specs/001-gse-sample-reception-notifier.md`

**Bloqueantes de deploy:** [KT-17019](https://kriptosteam.atlassian.net/browse/KT-17019) (Lambda + SQS) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB) + [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) (bucket gse-raw + SQS) + canal Anonymizer Equipo IA (post-MVP — stub funcional).
