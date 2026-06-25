# Specs staging — Classifier backend

> **Última actualización:** 2026-06-02 (reorganización en 3 épicas + modelo infra-en-entregable).
>
> Especificaciones técnicas (output de Skill 02) de los tickets de código del backend. **Staging area** — cada spec se migra al monorepo del módulo: `kriptos-io/classifier-v2-backend` (Discovery), `classifier-state-backend` (Máquina de Estados) o `classifier-gse-backend` (GSE), en `<monorepo>/specs/001-<slug>.md`.
>
> **Estado actual del backend:** ver [`context/classifier-v2/STATUS.md`](../context/classifier-v2/STATUS.md) (verdad viva: 3 épicas, monorepos, tickets). La infra de cada lambda va **dentro de su entregable** — no hay specs/tickets de infra suelta.
>
> Las specs siguen [`templates/SPEC_TEMPLATE.md`](../templates/SPEC_TEMPLATE.md) — 11 secciones, ninguna skipeable. Threat model embedido en sección 9.

---

## Cómo usar este directorio

1. **Para arrancar implementación** de cualquier ticket: leer la spec correspondiente. Cualquiera de las 13 está lista para Skill 03 (Plan) → Skill 04 (TDD).
2. **Cuando DevOps cree el repo del producto** (por ej. para `crown-candidates-indexer`):
   - Copiar `specs-staging/KT-17024-crown-candidates-indexer.md` → `<repo>/specs/001-crown-candidates-indexer.md`.
   - Renumerar a `001` (cada repo arranca su propia numeración).
   - Cambiar el header `Status: draft` → `Status: accepted`.
   - Commitear: `chore: spec for crown-candidates-indexer (KT-17024)`.
3. **Mantener sincronía**: si una spec cambia después de migrar, actualizar AMBAS copias o dejar la de staging marcada como `Status: superseded` apuntando al repo del producto.

---

## Índice de specs (reorganizado en 3 épicas · 2026-06-02)

### 🔍 Discovery / Fase 1 — KT-16369 · monorepo `classifier-v2-backend`

| Ticket | Slug | Estado | Notas |
|---|---|---|---|
| [KT-16613](https://kriptosteam.atlassian.net/browse/KT-16613) | [`KT-16613-tree-uncompressor.md`](KT-16613-tree-uncompressor.md) | ✅ Done | — |
| [KT-16614](https://kriptosteam.atlassian.net/browse/KT-16614) | [`KT-16614-emr-job-trigger.md`](KT-16614-emr-job-trigger.md) | ✅ Done | — |
| [KT-16616](https://kriptosteam.atlassian.net/browse/KT-16616) | [`KT-16616-joyas-priorizer.md`](KT-16616-joyas-priorizer.md) | ✅ Done | Aho-Corasick + normalize compartido |
| [KT-17588](https://kriptosteam.atlassian.net/browse/KT-17588) | [`KT-17588-emr-rollup.md`](KT-17588-emr-rollup.md) | 🆕 draft | add-on EMR: `rollup.json` por categoría/estación |
| [KT-17586](https://kriptosteam.atlassian.net/browse/KT-17586) | [`KT-17586-crown-report-consolidator.md`](KT-17586-crown-report-consolidator.md) | 🆕 draft | Excel consolidado por enterprise (KAIM-6316) |
| [KT-17587](https://kriptosteam.atlassian.net/browse/KT-17587) | [`KT-17587-crown-excel-ingest-confirm.md`](KT-17587-crown-excel-ingest-confirm.md) | 🆕 draft | Excel validado → manifest → dispara Fase 2 |
| [KT-16859](https://kriptosteam.atlassian.net/browse/KT-16859) | _(spec en IA)_ | In Progress | harness agentic: sugiere categorías + keywords (re-scope Fase 1) |
| [KT-17024](https://kriptosteam.atlassian.net/browse/KT-17024) | [`KT-17024-crown-candidates-indexer.md`](KT-17024-crown-candidates-indexer.md) | ⛔ descopeado | superseded: STATION→KT-17371, rollup→KT-17588, OS→BE 07. **Recomendado cancelar** |

> **Cierre de Fase 1 (manual por Excel, sin front — confirmado KAIM-6315/6316):** EMR escribe `rollup.json` por estación → barrier (KT-17371) marca CYCLE `ready` → `crown-report-consolidator` (KT-17586) genera el Excel por enterprise → cliente responde Excel → `crown-excel-ingest-confirm` (KT-17587) lo procesa y dispara Fase 2. **Sin OpenSearch en el camino crítico.**

### ⚙️ Máquina de Estados — KT-17270 · monorepo `classifier-state-backend`

| Ticket | Slug | Estado | Notas |
|---|---|---|---|
| [KT-17028](https://kriptosteam.atlassian.net/browse/KT-17028) | [`KT-17028-state-cycle-init.md`](KT-17028-state-cycle-init.md) | ✅ Done | crea CYCLE/STATION/REQUEST · multi-trigger |
| [KT-17032](https://kriptosteam.atlassian.net/browse/KT-17032) | [`KT-17032-state-station-status.md`](KT-17032-state-station-status.md) | ✅ Done | cierre STATION (state lambda) |
| [KT-17033](https://kriptosteam.atlassian.net/browse/KT-17033) | [`KT-17033-state-enterprise-status.md`](KT-17033-state-enterprise-status.md) | ✅ Done | cierre CYCLE + notify LLM |
| [KT-17370](https://kriptosteam.atlassian.net/browse/KT-17370) | _(pendiente)_ | RFC | state-enterprise-init: alta ENTERPRISE+CYCLE al iniciar exploración |
| [KT-17371](https://kriptosteam.atlassian.net/browse/KT-17371) | [`KT-17371-state-exploration-barrier.md`](KT-17371-state-exploration-barrier.md) | 🆕 draft | notificación recorrido + barrier → CYCLE `ready` |

> La DDB `classifier-cycles-state` (ex-KT-17009) vive en este monorepo. La infra de cada lambda va dentro de su entregable.
> **Estados del CYCLE:** `initialized → scanning → ready → awaiting_validation → confirmed → (Fase 2)` · `phase2_skipped` si el cliente rechaza todo.

### 📦 GSE — KT-16370 · monorepo `classifier-gse-backend`

| Ticket | Slug | Estado | Notas |
|---|---|---|---|
| [KT-17029](https://kriptosteam.atlassian.net/browse/KT-17029) | [`KT-17029-gse-sample-reception-notifier.md`](KT-17029-gse-sample-reception-notifier.md) | RFC | counter + notify Anonymizer |
| [KT-17030](https://kriptosteam.atlassian.net/browse/KT-17030) | [`KT-17030-gse-sample-anonymizer-notifier.md`](KT-17030-gse-sample-anonymizer-notifier.md) | RFC | counter |
| [KT-17031](https://kriptosteam.atlassian.net/browse/KT-17031) | [`KT-17031-gse-request-complete.md`](KT-17031-gse-request-complete.md) | RFC | API GW + TransactWriteItems |

### 🧩 Validación — futura (BE 07, sin crear)

| Ticket | Slug | Estado | Notas |
|---|---|---|---|
| [KT-17025](https://kriptosteam.atlassian.net/browse/KT-17025) | [`KT-17025-crown-enterprise-barrier.md`](KT-17025-crown-enterprise-barrier.md) | ⛔ cancelado · diferido | recrear en la épica de Validación; contexto preservado en este spec |
| [KT-17026](https://kriptosteam.atlassian.net/browse/KT-17026) | [`KT-17026-crown-validation-handler.md`](KT-17026-crown-validation-handler.md) | RFC (parkeado · → BE 07) | GraphQL approve/reject/add. Equivalente manual hoy: parte de KT-17587 |
| [KT-17027](https://kriptosteam.atlassian.net/browse/KT-17027) | [`KT-17027-crown-validation-confirm.md`](KT-17027-crown-validation-confirm.md) | RFC (parkeado · → BE 07) | scroll OS + manifest. **Equivalente manual vigente: KT-17587** |

> **Nota (2026-06-24):** el cierre de Fase 1 pasó a ser **manual por Excel** (KT-17586 + KT-17587). KT-17026/17027 (validación web vía AppSync) se conservan para cuando exista el front y se moverán a la épica BE 07.

---

## Convenciones aplicadas a TODAS las specs

- **Stack** (heredado de `s3-tree-uploader` patrón validado): Python 3.11 Container Lambda + ECR, `aws-lambda-powertools[tracer]`, `boto3`, `pydantic`, `uv` lock, arquitectura clean/hexagonal (`domain` / `application` / `adapters`), tests con `pytest` + `moto`, `ruff` + `mypy --strict`, cobertura ≥ 80%.
- **DDB compartida** ([KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009)): `classifier-cycles-state`, PK `enterprise_id`, SK multi-prefix (`CYCLE#`, `STATION#`, `REQUEST#`). Stream `NEW_AND_OLD_IMAGES` activo.
- **Naming** repo: `{nombre-componente}`. ECR + Lambda: `lambda-{nombre}`.
- **Idempotencia**: conditional writes en DDB para todos los counters y barriers. Idempotent upserts en OpenSearch por `candidate_id`. Idempotent puts en S3.
- **Logs**: structured JSON con `enterprise_id, station_id, cycle_id, request_id`.
- **Errores**: log ERROR + DLQ tras N reintentos. Alarmas SNS sobre DLQ > 0.

---

## Decisiones cerradas (no son open questions en las specs)

1. **Algoritmo matching de joyas-priorizer**: Aho-Corasick sobre patrones broadcast + `pandas_udf` vectorizado en Spark. Sin substring naïve, sin UDF Python row-by-row.
2. **Función `normalize()`**: el archivo `classifier-specs/context/classifier-v2/components/phase-1/normalize_category.py` es la única fuente de verdad. Versionada con `normalize_version` en outputs.
3. **Formato keywords**: JSONL (no JSON). Una línea por patrón con `category`, `original_category`, `business_area`, `original_business_area`.
4. **Bucket de candidatos**: `crown_jewels` (no `crown_jewel_candidates` — KT-16728 ya lo creó). Semánticamente contiene candidatos pre-validación.
5. **Storage validación**: híbrido DDB (state) + OpenSearch (corpus). Reusa cluster de Plataforma Web.
6. **Validation mode** ∈ {`enterprise`, `station`}: el cliente decide por cycle. Soportado por todas las Lambdas relevantes.
7. **Multi-trigger gse-cycle-init**: desde el inicio. `EVENT_SOURCE_ARN_TO_PROCESS_TYPE` env var mapea ARN → `process_type`.
8. **KEM**: verdad absoluta para `stations_expected`. Consultado al crear CYCLE, no reconsultado.

---

## Open questions globales (no específicas a un ticket)

| # | Pregunta | Owner | Default temporal |
|---|----------|-------|------------------|
| GQ1 | Canal de notificación final de Plataforma Web (SNS, GraphQL subscription, webhook) | Producto + Plataforma Web | SNS topic stub |
| GQ2 | Reaper para CYCLEs colgados | Producto | sin reaper en MVP |
| GQ3 | Late-arrival de STATIONs después del barrier | Producto | descartar con log WARN |
| GQ4 | Threat surface completo (tenant isolation, path traversal, DoS) | Haroldo + Tech Lead | mitigaciones específicas embebidas en cada spec; análisis cross-cutting deferido |
| GQ5 | Versionado de `normalize_category.py` (bump policy) | Equipo IA + Tech Lead | versión inicial `1.0.0`, sin migration plan |
