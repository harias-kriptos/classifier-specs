# Spec — state-enterprise-init (alta de ENTERPRISE + CYCLE al iniciar exploración)

> Ticket: [KT-17370](https://kriptosteam.atlassian.net/browse/KT-17370)
> Status: draft (2026-06-30)
> Épica: **Máquina de Estados** (KT-17270) · Monorepo: `kriptos-io/classifier-state-backend` (KT-17271)
> Infra: incluida en el entregable (no hay ticket DevOps aparte)

---

## 1. Goal

Bootstrap de la máquina de estados: cuando arranca la exploración (Fase 1) de un enterprise, dar de alta el **ENTERPRISE** y su **CYCLE** inicial en `classifier-cycles-state`, junto con las **STATION** esperadas (`stations_expected` según KEM). Sin esto no hay contra qué registrar el recorrido ni el barrier (KT-17371). Es el punto de entrada del lifecycle del CYCLE.

## 2. Non-goals

- Marcar avance de estaciones (`in_progress` / `scan_complete`) ni el barrier → eso es `state-exploration-barrier` (KT-17371).
- Generar el Excel (KT-17586) ni procesar el validado (KT-17587).
- Todo lo posterior a la entrega del EMR: muestreo GSE, validación humana.
- Confirmación del cliente.

## 3. User-visible behavior

Maquinaria interna de estados. Al iniciar exploración, deja el CYCLE en `initialized`:

```
[*] --> initialized   (este ticket)
initialized --> scanning   (primera STATION in_progress · KT-17371)
```

Trigger: notificación de **inicio de exploración** del agente (canal a definir con Equipo Agente — OQ1). Payload mínimo:

```json
{
  "enterprise_id": "ent-uuid",
  "area_id": "area-uuid",        // opcional (KT-17247)
  "cycle_trigger": "exploration_start"
}
```

Comportamiento:

```
1. Validar inputs (enterprise_id requerido; area_id si viene).
2. Consultar KEM → stations_expected (verdad absoluta).
3. Conditional create del CYCLE: PUT con cycle_id=uuid4(), status="initialized",
   ConditionExpression attribute_not_exists → idempotente.
4. PUT ENTERPRISE (PK enterprise_id) si no existe.
5. PUT N STATION (una por estación esperada) en estado inicial requested.
6. Idempotencia: re-arranque del mismo enterprise NO duplica el CYCLE ni
   pisa un CYCLE en estado más avanzado (scanning+).
```

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/cycle_init.py` | Lógica pura: `(payload, stations_expected) -> CycleSeed` | Sin I/O; `cycle_id` determinístico por intento. |
| `src/application/ports/state_store.py` | `create_enterprise_cycle(seed)` | Conditional create (`attribute_not_exists`); no regresa estado avanzado. |
| `src/application/ports/kem_client.py` | `get_stations_expected(enterprise_id)` | Consultado una sola vez al crear el CYCLE. |
| `src/application/usecases/init_enterprise.py` | Use case: KEM → seed → create | Idempotente por `enterprise_id` + cycle activo. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """Procesa la notificación de inicio de exploración (canal OQ1: SQS/EventBridge/API)."""
```

- **In:** evento de inicio de exploración (enterprise_id, area_id?).
- **Side effect:** ENTERPRISE + CYCLE (`initialized`) + N STATION (`requested`) en `classifier-cycles-state`.
- **Out:** ninguno directo; habilita el tracking que consume KT-17371.

## 6. Dependencies

- `aws-lambda-powertools[tracer]`, `boto3` (DDB), `pydantic`.
- DDB `classifier-cycles-state` (KT-17271) — Stream activo.
- **KEM API** (`GET /stations?enterprise_id=`) con API key de Secrets Manager — fuente de `stations_expected`.
- Downstream: `state-exploration-barrier` (KT-17371) consume las STATION creadas.

## 7. Test plan

```
[ ] test_cycle_init::test_seed_uses_stations_expected_from_kem
[ ] test_cycle_init::test_seed_carries_area_id_when_present
[ ] test_state_store::test_create_enterprise_cycle_conditional_succeeds
[ ] test_state_store::test_create_is_idempotent_on_existing_initialized_cycle
[ ] test_state_store::test_does_not_overwrite_advanced_cycle (scanning+)
[ ] test_state_store::test_creates_one_station_per_expected_station
[ ] test_kem_client::test_get_stations_expected
[ ] test_init_enterprise::test_full_happy_path_creates_cycle_and_stations
[ ] test_init_enterprise::test_second_init_same_enterprise_no_duplicate
[ ] test_e2e::test_exploration_start_creates_initialized_cycle (moto)
```

## 8. Eval impact

No aplica (sin LLM).

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Spoofing | Notificación de inicio falsa crea CYCLEs basura | Validación de `enterprise_id` contra KEM (404 → descarta + WARN). |
| Tampering | Doble init pisa un CYCLE avanzado | Conditional create `attribute_not_exists` + AC03 (no regresa estado). |
| Integrity | `stations_expected` incorrecto rompe el barrier | KEM como verdad absoluta, consultado una sola vez. |

## 10. Resolved decisions

- **Estado inicial = `initialized`** (no `scanning`): `scanning` lo setea KT-17371 cuando la primera STATION reporta recorrido. Confirmado con Haroldo 2026-06-29.
- **state-enterprise-init crea las STATION**: una por estación esperada (de KEM), en `requested`. El barrier (KT-17371) sólo transiciona, no crea.
- **`area_id`**: si viene en el payload (KT-17247), se persiste en el ENTERPRISE/CYCLE.

## 11. Open questions

| # | Pregunta | Owner | Default temporal |
|---|----------|-------|------------------|
| OQ1 | Canal exacto de la notificación de inicio de exploración (SQS/EventBridge/API) | Equipo Agente | SQS stub (alineado con OQ1 de KT-17371) |
| OQ2 | ¿Crear STATIONs upfront o lazy (on first recorrido)? | Backend | upfront (este spec); revisar si KEM no es confiable a tiempo |

## 12. Rollout

- Branch: `KT-17370-state-enterprise-init`
- Spec + TDD commits; tests verdes; cobertura ≥ 80%.
- PR a `main` con `Implements specs/00X-state-enterprise-init.md` (renumerar en el monorepo).
