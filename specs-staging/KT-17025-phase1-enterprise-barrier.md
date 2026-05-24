# Spec — phase1-enterprise-barrier

> Ticket: [KT-17025](https://kriptosteam.atlassian.net/browse/KT-17025)
> Status: accepted (Fase 1 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/phase1-enterprise-barrier`

---

## 1. Goal

Detectar exactly-once cuándo todas las stations activas de un enterprise terminaron Fase 1 (scan + match + indexación), y marcar el CYCLE como `stations_complete` en DDB para que la Plataforma Web pueda habilitar el botón "Confirmar todo" en su pantalla de progreso.

## 2. Non-goals

- Notificación push a la Plataforma Web — la UI hace polling/subscription a GraphQL.
- Procesar STATIONs de Fase 2 — filter del Pipe descarta; defensive check en código.
- Cerrar CYCLE de Fase 2 (eso es KT-17033).
- Reaper de cycles colgados (Producto, OQ deferred).

## 3. User-visible behavior

Trigger: EventBridge Pipe sobre DDB Stream de `classifier-cycles-state`, filter `eventName ∈ [INSERT, MODIFY] AND NewImage.SK begins_with "STATION#" AND NewImage.scan_status = "complete"`.

```
Input:  DDB Stream record con NewImage de una STATION recién marcada complete.
Side effects:
  1. Conditional ADD STATION.barrier_counted = true (exactly-once guard).
  2. Si pasó: UpdateItem CYCLE → ADD stations_completed = 1.
  3. Si stations_completed >= stations_expected y CYCLE.status = "scanning":
     - Conditional SET CYCLE.status = "stations_complete", ready_at = now.
     (Antes era "ready_for_validation" — renombrado para más claridad UX.)
```

**Sin publish a SNS**. La Plataforma Web consulta el estado via GraphQL subscription `onCycleStatusChange` (ver `graphql-schema-appsync.md`). Sin response síncrono del Lambda.

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/stream_record.py` | Parser de DDB Stream record (NewImage, OldImage) | Strict typing por SK prefix. |
| `src/domain/barrier.py` | Lógica pura: `(samples_state, expected) -> CloseStation \| Skip` | Sin I/O. |
| `src/application/ports/state_store.py` | Protocol con `mark_barrier_counted_or_fail`, `increment_cycle_counter`, `mark_cycle_stations_complete_or_fail` | Conditional ops, devuelve éxito/fallo sin lanzar. |
| `src/application/usecases/process_station_change.py` | Use case que orquesta los 3 pasos conditional | Cada paso es no-op si conditional falla. |
| `src/adapters/boto3_state_store.py` | DDB conditional updates | Usa return values UPDATED_NEW para counters. |

**No hay `notifier.py`** — el Lambda no publica a SNS ni a ningún canal externo. Solo escribe DDB.

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """Procesa batch de DDB Stream records. Sin retorno."""
```

Event (EventBridge Pipe → Lambda):

```json
[
  {
    "eventName": "MODIFY",
    "dynamodb": {
      "NewImage": {
        "PK": {"S": "ent-001"},
        "SK": {"S": "STATION#station-A#cycle-uuid"},
        "scan_status": {"S": "complete"},
        "candidates_count": {"N": "47"},
        "barrier_counted": {"BOOL": false}
      }
    }
  }
]
```

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — DDB
- `pydantic` — Stream record parsing

**Sin SNS, sin libs externas adicionales.**

## 7. Test plan

```
[ ] test_stream_record::test_parses_station_modify_record
[ ] test_stream_record::test_rejects_cycle_prefix (defensive — filter ya descartó)
[ ] test_barrier::test_skip_when_scan_status_not_complete
[ ] test_barrier::test_skip_when_barrier_already_counted
[ ] test_barrier::test_close_station_when_eligible
[ ] test_state_store::test_mark_barrier_counted_succeeds_when_flag_false
[ ] test_state_store::test_mark_barrier_counted_fails_when_flag_true
[ ] test_state_store::test_increment_cycle_counter_returns_new_value
[ ] test_state_store::test_mark_cycle_stations_complete_succeeds_when_scanning
[ ] test_state_store::test_mark_cycle_stations_complete_fails_when_already_marked
[ ] test_process_station_change::test_full_happy_path_marks_cycle_stations_complete
[ ] test_process_station_change::test_duplicate_stream_record_no_double_count
[ ] test_process_station_change::test_late_arrival_with_increased_expected_does_not_close_cycle
[ ] test_handler::test_processes_batch_of_5_records
[ ] test_e2e::test_n_stations_complete_marks_cycle_when_threshold_reached (moto)
[ ] test_e2e::test_late_arrival_after_threshold_keeps_cycle_open (moto)
```

`test_late_arrival_with_increased_expected_does_not_close_cycle` es crítico: si crown-candidates-indexer (KT-17024) detectó una STATION nueva y agregó +1 a `stations_expected` (de 5 → 6), el barrier no debe cerrar prematuramente (5 < 6).

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Race condition: 2 invocaciones del mismo stream record cuentan dos veces | Conditional `barrier_counted = false` previo al ADD; solo una invocación gana. Test: `test_duplicate_stream_record_no_double_count`. |
| Integrity | Late-arrival STATION bumps `stations_expected` y el barrier ya había cerrado | Conditional `IF status = "scanning"` al marcar stations_complete. Si `stations_expected` aumenta después de stations_complete, el cycle no regresa automáticamente — la UX maneja eso visualmente. |

No hay surface externa — Lambda interna que solo escribe DDB.

## 10. Resolved decisions

- **No publish a SNS**: la Plataforma Web hace polling/subscription a GraphQL contra DDB para saber el estado. Sin notificación push.
- **Estados renombrados**: `ready_for_validation` → `stations_complete` (más descriptivo). El cliente puede validar candidatos durante el estado `scanning`; la confirmación final solo se habilita cuando llega a `stations_complete`.
- **Late-arrival STATION**: este Lambda **no detecta** el late-arrival — eso es responsabilidad de `crown-candidates-indexer` (KT-17024). Este Lambda solo procesa Stream records y aplica el barrier check con los counters actuales en cada invocación. Si `stations_expected` incrementó (de 5 a 6 por late-arrival), el barrier no se dispara hasta que `stations_completed` también llegue a 6.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | Reaper para CYCLEs que el cliente nunca confirma (timeout) | Producto | Post-MVP, antes de prod |

## 12. Rollout

- Branch: `KT-17025-phase1-enterprise-barrier`
- Spec commit + TDD commits
- Quality gates verdes
- PR a `main` con `Implements specs/001-phase1-enterprise-barrier.md`
- Deploy via reusable workflow

**Bloqueantes de deploy:** [KT-17013](https://kriptosteam.atlassian.net/browse/KT-17013) (Lambda + EventBridge Pipe + IAM) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB con Stream). Ya NO depende de [KT-17011](https://kriptosteam.atlassian.net/browse/KT-17011) SNS porque se eliminó.
