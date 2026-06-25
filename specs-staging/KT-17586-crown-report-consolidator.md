# Spec — crown-report-consolidator (Excel JDC por enterprise)

> Ticket: [KT-17586](https://kriptosteam.atlassian.net/browse/KT-17586)
> Status: draft (2026-06-24)
> Épica: **Discovery / Fase 1** (KT-16369) · Monorepo: `kriptos-io/classifier-v2-backend` (KT-17132)
> Infra: incluida en el entregable (no hay ticket DevOps aparte)

---

## 1. Goal

Generar **un único Excel consolidado por enterprise** (formato KAIM-6316 / tipo CESEM) cuando el CYCLE entra en `ready`, depositarlo en `crown-reports-pending`, y transicionar el CYCLE a `awaiting_validation`. Cierra Fase 1 a nivel enterprise.

## 2. Non-goals

- Forma/estilo final del Excel (colores, plantilla) — Producto + CO (KAIM-6316). Emitimos las **columnas de fondo**.
- Generar categorías/keywords (KT-16859) ni hacer el match (EMR).
- Procesar el Excel validado del cliente (KT-17587).
- Front / plataforma web.

## 3. User-visible behavior

Trigger: `CYCLE.status = ready` (EventBridge Pipe sobre DDB Stream con filter por atributo, o invocación directa desde KT-17371).

Salida: `s3://kriptos-{env}-crown-reports-pending/{ent}/{cycle}/assessment.xlsx`. Pestaña principal "Joyas de la Corona" con columnas (KAIM-6316):

| Categoría del documento | Cantidad de documentos | Área de negocio | Nivel de riesgo | Tipo de información | Regulación aplicable |
|---|---|---|---|---|---|
| Plan Estratégico Quinquenal | 7106 | Dirección General / Planeación | Alto | … | … |

Las **3 indispensables** (KAIM-6316): categoría, cantidad de documentos, área de negocio. Riesgo/tipo/regulación vienen del LLM (KT-16859).

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/category_rollup.py` | Merge puro de N `rollup.json` → agregado por `category_id` | `count` total = suma de counts por estación; área = argmax del histograma. |
| `src/application/ports/report_store.py` | `read_rollups(ent, cycle)`, `put_assessment_xlsx(...)` | — |
| `src/application/ports/state_store.py` | `set_cycle_awaiting_validation` | Conditional sobre `status="ready"`. |
| `src/application/usecases/consolidate_report.py` | Use case: leer rollups → merge → join metadata LLM → xlsx → transición | Idempotente por cycle. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """Pipe/EventBridge handler: CYCLE entró en `ready`."""
```

**Lógica:**
1. Validar trigger (`CYCLE.status = ready`).
2. Listar y leer `crown_jewels/{ent}/{cycle}/**/rollup.json` (decenas de archivos KB).
3. **Merge por `category_id`:** `count += count`, `area_histogram` merge → área mayoritaria.
4. **Join metadata LLM** por categoría (riesgo, tipo, regulación) — fuente KT-16859.
5. Generar `.xlsx` con `openpyxl`.
6. `PUT crown-reports-pending/{ent}/{cycle}/assessment.xlsx`.
7. Conditional `SET CYCLE.status = awaiting_validation`.

## 6. Dependencies

- `openpyxl` — NEW (generación .xlsx). Justificación: formato client-facing KAIM-6316.
- `aws-lambda-powertools[tracer]`, `boto3` (S3, DDB), `pydantic`.
- Upstream: `rollup.json` (KT-17588), metadata LLM (KT-16859), barrier (KT-17371).
- Downstream: el cliente recibe el Excel; el confirm es KT-17587.

## 7. Test plan

```
[ ] test_category_rollup::test_merge_sums_counts_across_stations
[ ] test_category_rollup::test_area_is_argmax_of_merged_histogram
[ ] test_category_rollup::test_merge_empty_rollups_yields_empty_report
[ ] test_report_store::test_reads_all_rollups_for_cycle
[ ] test_report_store::test_writes_xlsx_with_kaim6316_columns
[ ] test_consolidate_report::test_joins_llm_metadata_by_category
[ ] test_consolidate_report::test_transitions_cycle_to_awaiting_validation
[ ] test_consolidate_report::test_idempotent_rewrite_same_object
[ ] test_consolidate_report::test_skips_if_cycle_not_ready
[ ] test_e2e::test_ready_cycle_produces_xlsx_and_transitions (moto)
```

## 8. Eval impact

No aplica directamente (consume metadata del LLM; no la genera). La calidad de categoría/riesgo se evalúa en KT-16859.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Information disclosure | El Excel contiene conteos sensibles por área | Bucket privado `crown-reports-pending`, IAM mínimo; entrega al cliente fuera de scope (canal CO). |
| Integrity | Doble disparo reescribe Excel inconsistente | Idempotente por cycle (AC06) + conditional de transición. |

## 10. Resolved decisions

- **Generamos el Excel nosotros** y lo depositamos en `crown-reports-pending` (decisión Haroldo 2026-06-24). La forma/estilo la define CO/Producto.
- **Performance**: el consolidador lee `rollup.json` (O(#estaciones)), nunca `matches.jsonl` (O(#archivos)). La agregación pesada vive en EMR (KT-17588).
- **Granularidad = categoría**, no archivo (KAIM-6316).

## 11. Open questions

| # | Pregunta | Owner | Default temporal |
|---|----------|-------|------------------|
| OQ1 | ¿Emitimos `.xlsx` ya estilado o un dataset que CO estiliza? | Producto + CO | `.xlsx` con columnas de fondo, sin estilo final |
| OQ2 | Pestañas complementarias del LLM (KAIM-6316 menciona 2 extra) — ¿se incluyen? | Alfonso / Producto | sólo pestaña "Joyas de la Corona" en MVP |

## 12. Rollout

- Branch: `KT-17586-crown-report-consolidator`
- Spec + TDD commits; tests verdes; cobertura ≥ 80%.
- PR a `main` con `Implements specs/00X-crown-report-consolidator.md`.
