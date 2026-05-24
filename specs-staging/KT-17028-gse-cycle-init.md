# Spec — gse-cycle-init

> Ticket: [KT-17028](https://kriptosteam.atlassian.net/browse/KT-17028)
> Status: accepted (Fase 2 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/gse-cycle-init`

---

## 1. Goal

Cuando aterriza un `manifest.json` validado en `validated_crown_jewels/`, **transicionar el CYCLE existente** a `phase2_collecting` y **agregar los atributos de Fase 2 a las STATION rows existentes** (creadas en Fase 1 por crown-candidates-indexer KT-17024). Crear REQUEST records, y notificar al agente vía Signal Handler. Diseñado multi-trigger desde el inicio via env var.

## 2. Non-goals

- Crear CYCLE nuevo — el CYCLE ya existe de Fase 1, solo se transiciona.
- Crear STATION row nuevo — la STATION ya existe de Fase 1, se UPDATE con atributos de Fase 2.
- Re-consultar KEM — usamos info del manifest (lo que el cliente confirmó).
- Subida de samples (responsabilidad del agente).
- Notification a Anonymizer (KT-17029).
- Implementación del Signal Handler — caja negra Equipo IA.

## 3. User-visible behavior

Trigger: SQS FIFO `gse-validated-cycle-queue.fifo` ← EventBridge sobre PutObject suffix `manifest.json` en `validated_crown_jewels`.

```
Input:  s3://validated_crown_jewels/{ent}/{cycle_id}/manifest.json
        s3://validated_crown_jewels/{ent}/{cycle_id}/station-{X}.jsonl (uno por station)
Side effects:
  1. Lee manifest → stations[], total_files, process_type (crown_validated).
  2. Conditional UPDATE CYCLE → status="phase2_collecting" IF status="confirmed".
  3. Por cada station del manifest:
     - GET s3://...station-{X}.jsonl → list de files con path, size.
     - UPDATE STATION existente (NO PUT condicional con attribute_not_exists):
       SET sampling_status="requested",
           samples_expected=len(files),
           samples_received=0,
           samples_anonymized=0,
           samples_skipped=0,
           files_to_sample=files,
           sample_content_size=10240
  4. PUT REQUEST record (uno por station — Modelo A).
  5. NOTIFY Signal Handler (canal TBD Equipo IA — stub con log mientras tanto).
```

Multi-trigger: env var `EVENT_SOURCE_ARN_TO_PROCESS_TYPE = {"<arn-validated-queue>": "crown_validated", ...}`.

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/manifest.py` | Parser strict del manifest.json | `total_files >= 0`, `stations` list. |
| `src/domain/cycle_transition.py` | Lógica pura de transiciones permitidas: `confirmed → phase2_collecting` | Solo states del enum. |
| `src/domain/request_type.py` | Enum `RequestType = {crown_jewels, classification, ...}` | Extensible. |
| `src/application/ports/state_store.py` | Protocol: `transition_cycle_to_phase2_collecting`, `update_station_with_phase2_attrs`, `put_request_if_absent` | Conditional, idempotent. |
| `src/application/ports/signal_handler_publisher.py` | Protocol `publish(payload)` | Stub con log si canal vacío. |
| `src/application/ports/manifest_reader.py` | Protocol `read_manifest`, `read_station_files` | S3 GET streaming. |
| `src/application/usecases/init_phase2_cycle.py` | Use case principal | Idempotente: re-procesar mismo manifest no duplica. |
| `src/adapters/boto3_state_store.py` | DDB conditional updates | UpdateItem con return values. |
| `src/config.py` | Env: `EVENT_SOURCE_ARN_TO_PROCESS_TYPE` (JSON), `STATE_TABLE_NAME`, `SIGNAL_HANDLER_*` | Fail-fast cold start. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """SQS batch handler. Procesa cada mensaje individualmente."""
```

SQS message body = S3 event con key del manifest.

Process_type derivation: leer `EventSourceArn` del SQS event → mapear via env var.

Signal Handler payload (stub):

```json
{
  "cycle_id": "uuid",
  "enterprise_id": "ent-001",
  "process_type": "crown_validated",
  "requests": [
    {
      "station_id": "station-A",
      "request_type": "crown_jewels",
      "files": [{"path": "...", "size": 245780}],
      "sample_content_size": 10240
    }
  ]
}
```

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — S3, DDB, Secrets Manager (KEM si aplica), SNS/SQS (Signal Handler stub)
- `pydantic` — validación

## 7. Test plan

```
[ ] test_manifest::test_parses_valid_manifest
[ ] test_manifest::test_rejects_missing_required_fields
[ ] test_cycle_transition::test_confirmed_to_phase2_collecting_allowed
[ ] test_cycle_transition::test_phase2_collecting_to_phase2_collecting_idempotent
[ ] test_cycle_transition::test_complete_to_phase2_collecting_rejected
[ ] test_state_store::test_transition_cycle_succeeds_when_confirmed
[ ] test_state_store::test_update_station_phase2_attrs_preserves_phase1_fields
[ ] test_state_store::test_update_station_idempotent_on_reprocess
[ ] test_state_store::test_put_request_if_absent_idempotent
[ ] test_signal_handler::test_stub_logs_when_no_channel
[ ] test_init_phase2_cycle::test_full_happy_path_updates_stations_and_creates_requests
[ ] test_init_phase2_cycle::test_zero_files_in_manifest_skips_creation
[ ] test_init_phase2_cycle::test_station_phase1_fields_preserved_after_update
[ ] test_init_phase2_cycle::test_process_type_derived_from_event_source_arn
[ ] test_init_phase2_cycle::test_unknown_event_source_arn_logs_error_and_skips
[ ] test_handler::test_processes_batch_of_messages
[ ] test_e2e::test_put_manifest_results_in_updated_stations_and_signal (moto)
```

`test_station_phase1_fields_preserved_after_update` es crítico — verifica que `scan_status`, `candidates_count`, etc. de Fase 1 NO se sobrescriben al agregar atributos de Fase 2.

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Spoofing | Atacante PUT manifest falso en `validated_crown_jewels` | Bucket con public-access block + IAM solo permite PUT desde `validation-confirm` Lambda. |
| Tampering | Manifest alterado entre validation-confirm y este Lambda | Manifest contiene `enterprise_id, cycle_id`; conditional UPDATE valida que el cycle existe y está en estado `confirmed`. Si manifest falso → conditional falla. |
| DoS | N manifests del mismo enterprise → N invocaciones | SQS FIFO con `MessageGroupId=enterprise_id` serializa por enterprise. |
| Integrity | UPDATE de STATION sobreescribe Fase 1 fields por error | Test `test_station_phase1_fields_preserved` + UpdateExpression solo SET de campos Fase 2, nunca de campos Fase 1. |

## 10. Resolved decisions

- **STATION model**: UPDATE la misma STATION row (creada en Fase 1), agregar atributos de Fase 2 (`sampling_status`, `samples_expected`, etc.). NO crear nueva row con SK distinto.
- **No re-consulta KEM**: la info de stations viene del manifest (`stations: [...]`). `stations_expected_phase2 = M` (≤ `stations_expected` de Fase 1 si cliente rechazó algunas stations).
- **Transición CYCLE**: solo desde `confirmed` (no desde `phase2_collecting` o más allá). Conditional `IF status="confirmed"`.
- **Multi-trigger**: env var `EVENT_SOURCE_ARN_TO_PROCESS_TYPE`. Agregar nuevo event source sin cambiar código.
- **Signal Handler**: stub con log mientras Equipo IA define canal final.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | Canal Signal Handler final | Equipo IA | Cuando entreguen ARN/endpoint |

## 12. Rollout

- Branch: `KT-17028-gse-cycle-init`
- Spec commit + TDD commits
- Tests verdes; cobertura ≥ 80%
- PR a `main` con `Implements specs/001-gse-cycle-init.md`
- Deploy via reusable workflow

**Bloqueantes de deploy:** [KT-17018](https://kriptosteam.atlassian.net/browse/KT-17018) (Lambda + SQS FIFO + IAM) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB) + Signal Handler canal de Equipo IA (post-MVP — stub funcional mientras tanto).
