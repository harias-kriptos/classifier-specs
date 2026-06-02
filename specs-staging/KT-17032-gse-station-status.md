# Spec — gse-station-status

> Ticket: [KT-17032](https://kriptosteam.atlassian.net/browse/KT-17032)
> Status: accepted (Fase 2 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/gse-station-status`

---

## 1. Goal

State lambda exactly-once que detecta cuándo una STATION de Fase 2 tiene **contadores cuadrados** (`samples_anonymized + samples_skipped >= samples_expected`), transiciona `sampling_status="sample_anonymized"`, y escala el contador `stations_sample_anonymized` del CYCLE padre.

## 2. Non-goals

- Cierre del CYCLE (eso es KT-17033).
- Procesar STATIONs de Fase 1 (filter del Pipe descarta porque solo dispara si `sampling_status exists`).
- Notificaciones externas.

## 3. User-visible behavior

Trigger: EventBridge Pipe sobre DDB Stream de `classifier-cycles-state`, **filter por atributo**:

```json
{
  "eventName": ["INSERT", "MODIFY"],
  "dynamodb": {
    "NewImage": {
      "SK": {"S": [{"prefix": "STATION#"}]},
      "sampling_status": {"S": ["uploading", "sample_recolected", "sample_anonymized"]}
    }
  }
}
```

Solo dispara cuando `sampling_status` existe — automáticamente excluye STATIONs en estado Fase 1 (donde el campo no existe).

```
Para cada record:
  1. Skip rápido si sampling_status == "sample_anonymized" (ya cerrada — idempotency).
  2. Si (samples_anonymized + samples_skipped) < samples_expected: log DEBUG, no cerrar.
  3. Conditional UPDATE STATION:
     - SET sampling_status="sample_anonymized", sampling_complete_at=now.
     - ConditionExpression: sampling_status <> "sample_anonymized".
  4. Si conditional pasó (exactly-once gate):
     - ADD CYCLE.stations_sample_anonymized = 1.
```

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/stream_record.py` | Compartible con KT-17025 (lib externa) | — |
| `src/domain/sampling_close.py` | Lógica pura: `(state) -> ShouldClose \| Skip` | Sin I/O. |
| `src/application/ports/state_store.py` | Protocol con `close_sampling_or_fail`, `increment_cycle_stations_sample_anonymized` | Conditional. |
| `src/application/usecases/process_station_change.py` | Use case que orquesta los 3 pasos conditional | Cada paso no-op si conditional falla. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """Pipe batch handler. Sin retorno."""
```

Sin notifications externas — el cierre del CYCLE se dispara por DDB Stream consumido por KT-17033.

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — DDB
- `pydantic`

## 7. Test plan

```
[ ] test_stream_record::test_parses_station_record (shared lib)
[ ] test_sampling_close::test_skip_when_counters_under_threshold
[ ] test_sampling_close::test_skip_when_already_sample_anonymized
[ ] test_sampling_close::test_close_when_threshold_reached
[ ] test_sampling_close::test_zero_expected_closes_at_first_event
[ ] test_state_store::test_close_sampling_succeeds_when_not_complete
[ ] test_state_store::test_close_sampling_fails_when_already_complete
[ ] test_state_store::test_increment_cycle_counter_returns_new_value
[ ] test_process_station_change::test_phase1_station_filtered_out_by_pipe (test del filter)
[ ] test_process_station_change::test_full_happy_path_increments_cycle_once
[ ] test_process_station_change::test_duplicate_stream_record_no_double_count
[ ] test_handler::test_processes_batch
[ ] test_e2e::test_station_counters_satisfied_transitions_to_sample_anonymized_and_bumps_cycle (moto)
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Stream duplicate cierra STATION 2 veces | Conditional `sampling_status<>sample_anonymized` exactly-once. Test: `test_duplicate_stream_record_no_double_count`. |
| Integrity | Race con KT-17025 (crown-enterprise-barrier) | **Filter del Pipe es por atributo**: KT-17025 filtra `scan_status=complete`, KT-17032 filtra `sampling_status exists`. Cada uno solo ve sus eventos. Sin overlap. |

No hay surface externa.

## 10. Resolved decisions

- **Filter del Pipe por atributo `sampling_status exists`**: solo dispara para eventos de Fase 2. Lo de Fase 1 lo maneja KT-17025.
- **Sub-estado de transición**: `sampling_status: uploading → sample_anonymized` (cuando counters cuadran). El sub-estado intermedio `sample_recolected` (si lo usáramos) sería transitorio entre `uploading` y `sample_anonymized`.
- **Contador en CYCLE**: `stations_sample_anonymized` (NEW, separado de `stations_completed` de Fase 1). Cuando llega a `stations_expected` → KT-17033 cierra CYCLE.
- **Sin notify externo**: lo dispara DDB Stream del CYCLE para KT-17033.

## 11. Open questions deferidas

Ninguna específica.

## 12. Rollout

- Branch: `KT-17032-gse-station-status`
- Spec + TDD commits
- Tests verdes; cobertura ≥ 80%
- PR a `main` con `Implements specs/001-gse-station-status.md`

**Bloqueantes de deploy:** [KT-17022](https://kriptosteam.atlassian.net/browse/KT-17022) (Lambda + Pipe + IAM) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB con Stream).
