# Spec — crown-excel-ingest-confirm (Excel validado → entrada Fase 2)

> Ticket: [KT-17587](https://kriptosteam.atlassian.net/browse/KT-17587)
> Status: draft (2026-06-24)
> Épica: **Discovery / Fase 1** (KT-16369) · Monorepo: `kriptos-io/classifier-v2-backend` (KT-17132)
> Infra: incluida en el entregable (no hay ticket DevOps aparte)

---

## 1. Goal

Procesar el Excel validado que el cliente devuelve, materializar `manifest.json` + `station-{X}.jsonl` como entrada de Fase 2, y transicionar el CYCLE a `confirmed` (o `phase2_skipped`). El depósito del Excel validado en S3 es el **desencadenador de Fase 2 (GSE)**. Versión manual de la lógica de KT-17027 (sin AppSync).

## 2. Non-goals

- UI / plataforma web (variante web = KT-17027, parkeada en BE 07).
- Re-validación / nuevos rounds (requieren nuevo cycle).
- Implementación del LLM downstream (caja negra Equipo IA).
- Generar el Excel (KT-17586).

## 3. User-visible behavior

Trigger: `PutObject` en `s3://kriptos-{env}-crown-reports-validated/{ent}/{cycle}/assessment.xlsx` → EventBridge (`Object Created`, suffix `.xlsx`) → SQS → Lambda.

El cliente marcó, por **categoría**, approve/reject (+ override opcional de área). Resultado:

- `total_files > 0` → `manifest.json` + `station-{X}.jsonl` en `validated_crown_jewels/`, `CYCLE.status = confirmed` → dispara Fase 2.
- `total_files == 0` (rechazó todo) → `manifest.json` con `total_files=0`, `CYCLE.status = phase2_skipped`, Fase 2 NO dispara.

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/excel_decision.py` | Parseo puro del Excel → `{category_id: approve/reject, area_override?}` | Tolerante a filas extra; valida enum decisión. |
| `src/domain/manifest_builder.py` | Construye manifest desde categorías aprobadas | `total_files` = suma de paths expandidos. |
| `src/application/ports/jewel_store.py` | `iter_paths_for_categories(approved)` (stream filtrado de `matches.jsonl`) | Sólo categorías aprobadas; streaming sin OOM. |
| `src/application/ports/state_store.py` | `confirm_cycle` / `skip_phase2` | Conditional sobre `status="awaiting_validation"`. |
| `src/application/usecases/ingest_confirm.py` | Use case orquestador | Idempotente por cycle. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """SQS handler: Excel validado depositado."""
```

**Lógica:**
1. Parsear SQS → S3 event → bucket + key → `enterprise_id, cycle_id`.
2. **Conditional check**: `CYCLE.status = awaiting_validation` (si no → INVALID_STATE).
3. GET + parsear el Excel (decisión por categoría + área override).
4. Por categoría aprobada: stream `matches.jsonl` filtrando esa categoría → paths.
5. PUT `validated_crown_jewels/{ent}/{cycle}/station-{X}.jsonl` (agrupado por station).
6. PUT `validated_crown_jewels/{ent}/{cycle}/manifest.json`.
7. Conditional `SET status = confirmed` (si `total_files>0`) o `phase2_skipped`.
8. El PutObject del manifest dispara Fase 2 (EventBridge → `state-cycle-init` KT-17028).

## 6. Dependencies

- `openpyxl` — NEW (parseo .xlsx).
- `aws-lambda-powertools[tracer]`, `boto3` (S3, DDB), `pydantic`.
- Upstream: Excel de KT-17586 + respuesta del cliente. `matches.jsonl` de EMR (KT-16616).
- Downstream: `state-cycle-init` (KT-17028) dispara GSE.

## 7. Test plan

```
[ ] test_excel_decision::test_parses_approve_reject_per_category
[ ] test_excel_decision::test_parses_area_override
[ ] test_excel_decision::test_tolerates_extra_rows_and_validates_enum
[ ] test_manifest_builder::test_total_files_sums_expanded_paths
[ ] test_jewel_store::test_iter_paths_only_for_approved_categories
[ ] test_jewel_store::test_streams_without_oom
[ ] test_ingest_confirm::test_happy_path_confirms_and_writes_manifest
[ ] test_ingest_confirm::test_reject_all_sets_phase2_skipped
[ ] test_ingest_confirm::test_invalid_state_when_not_awaiting_validation
[ ] test_ingest_confirm::test_idempotent_redeposit_no_double_trigger
[ ] test_e2e::test_validated_excel_triggers_phase2 (moto)
```

## 8. Eval impact

No aplica (sin LLM).

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Excel manipulado con paths fuera del set escaneado | Sólo se expanden paths presentes en `matches.jsonl` (no se confía en paths del Excel); área override validada. |
| Spoofing | Depósito en bucket por actor no autorizado | IAM del bucket `crown-reports-validated`; el canal de subida lo controla CO/Plataforma. |
| Tampering | Doble depósito dispara Fase 2 dos veces | Conditional sobre `awaiting_validation` (AC04). |
| Integrity | S3 PUT parcial → estado inconsistente | Orden: escribir station files + manifest ANTES de transicionar estado; reintentable. |

## 10. Resolved decisions

- **Trigger = depósito de Excel en S3** (no mutation AppSync). Decisión Haroldo 2026-06-24.
- **Dos buckets**: `crown-reports-pending` (salida del consolidador) y `crown-reports-validated` (entrada del cliente).
- **OpenSearch diferido/opcional**: indexar el set confirmado al cluster de Plataforma Web detrás de un flag, fuera del camino crítico. S3 + DDB alcanzan para disparar Fase 2.
- **Granularidad = categoría** (approve/reject por categoría, no por archivo).

## 11. Open questions

| # | Pregunta | Owner | Default temporal |
|---|----------|-------|------------------|
| OQ1 | ¿El parseo del Excel lo hacemos nosotros o CO entrega un dataset estructurado? | Producto + CO | parseamos `.xlsx` con `openpyxl` |
| OQ2 | Layout exacto de la columna de decisión en el Excel respondido | Producto + CO | columna "Decisión" (approve/reject) + "Área (override)" |
| OQ3 | ¿Encendemos el indexado opcional a OpenSearch en MVP? | Producto + Plataforma Web | apagado en MVP |

## 12. Rollout

- Branch: `KT-17587-crown-excel-ingest-confirm`
- Spec + TDD commits; tests verdes; cobertura ≥ 80%.
- PR a `main` con `Implements specs/00X-crown-excel-ingest-confirm.md`.
