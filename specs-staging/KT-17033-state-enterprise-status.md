# Spec — state-enterprise-status

> Ticket: [KT-17033](https://kriptosteam.atlassian.net/browse/KT-17033)
> Status: accepted (2026-05-23) · renombrado `gse-enterprise-status` → `state-enterprise-status` (2026-06-02)
> Épica: **Máquina de Estados** (KT-17270) · Monorepo: `kriptos-io/classifier-state-backend` (KT-17271)
> Infra: incluida en el entregable (no hay ticket DevOps aparte)

---

## 1. Goal

State lambda exactly-once que detecta cuándo un CYCLE tiene todas las stations cerradas en Fase 2 (`stations_sample_anonymized >= stations_expected`), cierra el CYCLE como `complete`, setea TTL para cleanup, y notifica al downstream LLM Process Queue. Es el último eslabón del pipeline.

## 2. Non-goals

- Implementación del LLM downstream — caja negra Equipo IA.
- Procesar CYCLEs en otros estados que no sean `phase2_collecting` (filter del Pipe descarta).
- Reaper de CYCLEs colgados (OQ deferred Producto).

## 3. User-visible behavior

Trigger: EventBridge Pipe sobre DDB Stream de `classifier-cycles-state`, **filter por atributo**:

```json
{
  "eventName": ["MODIFY"],
  "dynamodb": {
    "NewImage": {
      "SK": {"S": [{"prefix": "CYCLE#"}]},
      "status": {"S": ["phase2_collecting"]}
    }
  }
}
```

Solo dispara cuando CYCLE está en `phase2_collecting` — automáticamente excluye transitions de Fase 1.

```
Para cada record:
  1. Skip rápido si stations_sample_anonymized < stations_expected.
  2. Estrategia publish-first:
     a. Publicar al LLM con payload incluyendo anonymized_prefix (S3 URI completo).
     b. Si publish OK → conditional UPDATE CYCLE:
        SET status="complete", completed_at=now, ttl=now+90d.
        CASCADE: setear ttl=now+90d en STATIONs y REQUESTs del cycle (separate update).
        ConditionExpression: status="phase2_collecting" AND stations_sample_anonymized >= stations_expected.
     c. Si publish falla → SQS retry del Pipe; eventual DLQ + alarma.
```

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/stream_record.py` | Shared lib | — |
| `src/domain/cycle_close.py` | Lógica pura: `(state) -> ShouldClose \| Skip` | Sin I/O. |
| `src/application/ports/state_store.py` | Protocol con `close_cycle_with_ttl_cascade` | Doble conditional + cascade TTL. |
| `src/application/ports/llm_publisher.py` | Protocol `publish(payload)` | Stub con log si canal vacío. |
| `src/application/usecases/process_cycle_change.py` | Use case con publish-first | Idempotente. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """Pipe batch handler."""
```

LLM payload (stub):

```json
{
  "cycle_id": "uuid",
  "enterprise_id": "ent-001",
  "process_type": "crown_validated",
  "stations_completed": 5,
  "samples_anonymized_total": 312,
  "anonymized_prefix": "s3://kriptos-{env}-gse-anonymized/ent-001/cycle-uuid/",
  "completed_at": "2026-05-23T20:00:00Z"
}
```

`anonymized_prefix` es **S3 URI completo** — el LLM hace GET directo sin componer nada.

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — DDB, SNS/SQS (LLM publisher stub)
- `pydantic`

## 7. Test plan

```
[ ] test_stream_record::test_parses_cycle_record (shared lib)
[ ] test_cycle_close::test_skip_when_stations_under_threshold
[ ] test_cycle_close::test_skip_when_already_complete (filter ya descarta, defensive check)
[ ] test_cycle_close::test_close_when_threshold_reached
[ ] test_state_store::test_close_cycle_succeeds_with_double_conditional
[ ] test_state_store::test_close_cycle_fails_if_status_already_complete
[ ] test_state_store::test_close_cycle_fails_if_counter_drifted_back
[ ] test_state_store::test_ttl_set_to_90_days_on_close
[ ] test_state_store::test_cascade_ttl_to_stations_and_requests
[ ] test_llm_publisher::test_stub_logs_when_no_channel
[ ] test_llm_publisher::test_payload_includes_s3_uri_anonymized_prefix
[ ] test_process_cycle_change::test_publish_first_then_set_status
[ ] test_process_cycle_change::test_publish_failure_does_not_close_cycle
[ ] test_process_cycle_change::test_full_happy_path_publishes_once_and_closes
[ ] test_process_cycle_change::test_duplicate_stream_record_no_double_publish
[ ] test_handler::test_processes_batch
[ ] test_e2e::test_cycle_phase2_complete_closes_cycle_with_ttl_and_publishes (moto)
```

## 8. Eval impact

No aplica (sin LLM acá — solo dispara al LLM downstream).

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Stream duplicate publish 2 veces al LLM | Conditional doble + publish-first strategy. **Contrato con Equipo IA**: el LLM debe ser idempotente por `cycle_id`. La gestión de duplicados es responsabilidad de ellos. |
| Repudiation | No traza de qué cycle se notificó | Logs + DDB `completed_at`. |
| Integrity | Publish a LLM falla post-conditional → CYCLE marcado pero LLM no notificado | **Estrategia publish-first**: publish ANTES de SET status. Si publish falla → SQS retry del Pipe → eventual DLQ + alarma. CYCLE no se cierra hasta que publish acknowledged. |

## 10. Resolved decisions

- **Filter del Pipe**: `CYCLE.status = "phase2_collecting"`. Solo dispara para CYCLEs en Fase 2 — automáticamente excluye otras transiciones.
- **Estrategia publish-first**: publica al LLM primero. Si OK → SET status=complete + TTL. Si falla → SQS retry. **Contrato Equipo IA: LLM idempotente por cycle_id**.
- **TTL = 90 días**: al cerrar CYCLE, setear `ttl = now + 90d`. CASCADE: actualizar STATIONs y REQUESTs del cycle con el mismo TTL para que se borren en sincronía.
- **`anonymized_prefix` = S3 URI completo**: `s3://kriptos-{env}-gse-anonymized/{ent}/{cycle_id}/`. Self-contained, sin acoplamiento de naming convention.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | Canal LLM Process Queue final (SNS/SQS/HTTP) | Equipo IA | Cuando entreguen ARN/endpoint |

## 12. Rollout

- Branch: `KT-17033-gse-enterprise-status`
- Spec + TDD commits
- Tests verdes; cobertura ≥ 80%
- PR a `main` con `Implements specs/001-gse-enterprise-status.md`

**Bloqueantes de deploy:** [KT-17023](https://kriptosteam.atlassian.net/browse/KT-17023) (Lambda + Pipe + IAM) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB) + canal LLM Process Queue de Equipo IA (post-MVP — stub funcional).
