# Spec — state-exploration-barrier (notificación de recorrido + barrier enterprise)

> Ticket: [KT-17371](https://kriptosteam.atlassian.net/browse/KT-17371)
> Status: draft (2026-06-24)
> Épica: **Máquina de Estados** (KT-17270) · Monorepo: `kriptos-io/classifier-state-backend` (KT-17271)
> Infra: incluida en el entregable (no hay ticket DevOps aparte)

---

## 1. Goal

Integrar la exploración (Fase 1) con la máquina de estados: cada STATION reporta `in_progress` durante el recorrido y `scan_complete` (con conteo de joyas) cuando EMR (`joyas-priorizer`) entrega su resultado; y un **barrier de enterprise** marca el `CYCLE` como `ready` cuando todas las STATION del cycle están `scan_complete`. Ese `ready` es el gatillo del consolidador del Excel (KT-17586).

## 2. Non-goals

- Generar el Excel consolidado (KT-17586) ni procesar el Excel validado (KT-17587).
- Crear el ENTERPRISE/CYCLE inicial — eso es `state-enterprise-init` (KT-17370).
- Todo lo posterior a la entrega del EMR: muestreo GSE, validación humana.
- Reaper de CYCLEs colgados en `awaiting_validation` (OQ Producto).

## 3. User-visible behavior

Es maquinaria interna de estados (state lambdas sobre DDB Stream + notificaciones). Estados del CYCLE tras este ticket:

```
initialized → scanning → ready → awaiting_validation → confirmed → (Fase 2)
                                          └─→ phase2_skipped
```

- `scanning` → `ready`: **lo setea este ticket** (barrier).
- `ready` → `awaiting_validation`: lo setea KT-17586 (tras escribir el Excel).
- `awaiting_validation` → `confirmed` / `phase2_skipped`: lo setea KT-17587.

Dos entradas:

1. **Notificación de recorrido** (por estación, desde el agente de exploración) → `STATION.scan_status = in_progress`.
2. **Resultado de EMR** (`joyas-priorizer` terminó la estación) → `STATION.scan_status = scan_complete` + `joyas_count = N`. Al cerrar la última STATION pendiente del cycle → barrier dispara `CYCLE.status = ready`.

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/station_status.py` | Lógica pura: transición STATION (`in_progress` / `scan_complete`) | Sin I/O; monotónica (no retrocede de `scan_complete`). |
| `src/domain/enterprise_barrier.py` | Lógica pura: `(stations) -> ReadyToClose \| Pending` | `ready` sólo si `count(scan_complete) >= stations_expected`. |
| `src/application/ports/state_store.py` | `mark_station_scanning`, `mark_station_complete`, `close_cycle_ready` | Conditional writes; barrier con conditional sobre `status="scanning"`. |
| `src/application/usecases/process_exploration_event.py` | Use case: ruteo recorrido vs EMR result | Idempotente por `(station_id, event_type)`. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """Procesa notificaciones de recorrido (SQS) y resultados de EMR (S3/EventBridge o DDB Stream)."""
```

- **Recorrido:** evento del agente (canal a definir con Equipo Agente — OQ1) → `mark_station_scanning`.
- **EMR result:** detección de fin de `joyas-priorizer` por estación (PutObject `rollup.json`/`matches.jsonl` en `crown_jewels/{ent}/{sta}/` vía EventBridge) → `mark_station_complete(joyas_count)`.
- **Barrier:** al cerrar STATION, conditional UPDATE del CYCLE: `SET status="ready"` con `ConditionExpression: status="scanning" AND stations_scan_complete >= stations_expected`.

## 6. Dependencies

- `aws-lambda-powertools[tracer]`, `boto3` (DDB), `pydantic`.
- DDB `classifier-cycles-state` (KT-17271) — Stream activo.
- Upstream: `state-enterprise-init` (KT-17370) crea CYCLE/STATION; `joyas-priorizer` (KT-16616) y su `rollup.json` (KT-17588).
- Downstream: consolidador KT-17586 (escucha `CYCLE.status=ready`).

## 7. Test plan

```
[ ] test_station_status::test_marked_in_progress_on_recorrido
[ ] test_station_status::test_marked_scan_complete_on_emr_result_with_count
[ ] test_station_status::test_status_is_monotonic (no retrocede de scan_complete)
[ ] test_enterprise_barrier::test_pending_when_not_all_complete
[ ] test_enterprise_barrier::test_ready_when_all_complete
[ ] test_state_store::test_close_cycle_ready_conditional_succeeds
[ ] test_state_store::test_close_cycle_ready_fails_if_already_ready (idempotente)
[ ] test_process_exploration_event::test_routes_recorrido_vs_emr_result
[ ] test_process_exploration_event::test_duplicate_notification_no_double_count
[ ] test_e2e::test_all_stations_complete_sets_cycle_ready (moto)
```

## 8. Eval impact

No aplica (sin LLM).

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Notificación duplicada infla `joyas_count` o dispara barrier 2 veces | Conditional writes + AC04 idempotencia por `(station_id, event_type)`. |
| Integrity | Barrier dispara con stations faltantes | Conditional `stations_scan_complete >= stations_expected` (verdad: KEM, ver KT-17370). |

## 10. Resolved decisions

- **Estados nuevos**: `ready` (este ticket), `awaiting_validation` (KT-17586), `confirmed`/`phase2_skipped` (KT-17587). Confirmado con Haroldo 2026-06-24.
- **`awaiting_validation` es estado propio**: el wait del cliente puede durar semanas (Banco de Chile = trimestral, KAIM-6315). No se modela como sub-estado de `ready`.
- **Barrier = ex-KT-17025**; STATION `scan_complete` = ex-KT-17024 (concepto reabsorbido acá).

## 11. Open questions

| # | Pregunta | Owner | Default temporal |
|---|----------|-------|------------------|
| OQ1 | Canal exacto de la notificación de recorrido (SQS/EventBridge/API) | Equipo Agente | SQS stub |
| OQ2 | Reaper de CYCLEs colgados en `awaiting_validation` | Producto | sin reaper en MVP |

## 12. Rollout

- Branch: `KT-17371-state-exploration-barrier`
- Spec + TDD commits; tests verdes; cobertura ≥ 80%.
- PR a `main` con `Implements specs/00X-state-exploration-barrier.md` (renumerar en el monorepo).
