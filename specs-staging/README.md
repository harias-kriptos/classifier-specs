# Specs staging — Classifier backend

> **Última actualización:** 2026-05-23.
>
> Especificaciones técnicas (output de Skill 02) para los 13 tickets de código del backend. **Staging area** — cuando DevOps provisione el repo del producto correspondiente, cada spec se migra a `kriptos-io/<componente>/specs/001-<slug>.md`.
>
> Las specs siguen [`templates/SPEC_TEMPLATE.md`](../templates/SPEC_TEMPLATE.md) — 11 secciones, ninguna skipeable. Threat model embedido en sección 9 (sin archivo separado en staging).

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

## Índice de specs

### Fase 1 — Scan + Match (sprint vivo)

| Ticket | Slug | Status spec | Notas |
|---|---|---|---|
| [KT-16613](https://kriptosteam.atlassian.net/browse/KT-16613) | [`KT-16613-tree-uncompressor.md`](KT-16613-tree-uncompressor.md) | draft | DevOps blocker: KT-16726 |
| [KT-16614](https://kriptosteam.atlassian.net/browse/KT-16614) | [`KT-16614-emr-job-trigger.md`](KT-16614-emr-job-trigger.md) | draft | DevOps blocker: KT-16726 |
| [KT-16616](https://kriptosteam.atlassian.net/browse/KT-16616) | [`KT-16616-joyas-priorizer.md`](KT-16616-joyas-priorizer.md) | draft | MOD aplicado: Aho-Corasick + normalize compartido |

### Fase 1 — Validación humana

| Ticket | Slug | Status spec | Notas |
|---|---|---|---|
| [KT-17024](https://kriptosteam.atlassian.net/browse/KT-17024) | [`KT-17024-crown-candidates-indexer.md`](KT-17024-crown-candidates-indexer.md) | draft | Bulk index OS + STATION en DDB |
| [KT-17025](https://kriptosteam.atlassian.net/browse/KT-17025) | [`KT-17025-phase1-enterprise-barrier.md`](KT-17025-phase1-enterprise-barrier.md) | draft | State lambda — exactly-once barrier |
| [KT-17026](https://kriptosteam.atlassian.net/browse/KT-17026) | [`KT-17026-validation-mutation-handler.md`](KT-17026-validation-mutation-handler.md) | draft | GraphQL mutations — approve/reject/add |
| [KT-17027](https://kriptosteam.atlassian.net/browse/KT-17027) | [`KT-17027-validation-confirm.md`](KT-17027-validation-confirm.md) | draft | Scroll OS + manifest + bridge a Fase 2 |

### Fase 2 — GSE

| Ticket | Slug | Status spec | Notas |
|---|---|---|---|
| [KT-17028](https://kriptosteam.atlassian.net/browse/KT-17028) | [`KT-17028-gse-cycle-init.md`](KT-17028-gse-cycle-init.md) | draft | Multi-trigger por process_type |
| [KT-17029](https://kriptosteam.atlassian.net/browse/KT-17029) | [`KT-17029-gse-sample-reception-notifier.md`](KT-17029-gse-sample-reception-notifier.md) | draft | SQS consumer + counter + notify Anonymizer |
| [KT-17030](https://kriptosteam.atlassian.net/browse/KT-17030) | [`KT-17030-gse-sample-anonymizer-notifier.md`](KT-17030-gse-sample-anonymizer-notifier.md) | draft | SQS consumer + counter |
| [KT-17031](https://kriptosteam.atlassian.net/browse/KT-17031) | [`KT-17031-gse-request-complete.md`](KT-17031-gse-request-complete.md) | draft | API GW + TransactWriteItems |
| [KT-17032](https://kriptosteam.atlassian.net/browse/KT-17032) | [`KT-17032-gse-station-status.md`](KT-17032-gse-station-status.md) | draft | State lambda STATION Fase 2 |
| [KT-17033](https://kriptosteam.atlassian.net/browse/KT-17033) | [`KT-17033-gse-enterprise-status.md`](KT-17033-gse-enterprise-status.md) | draft | State lambda CYCLE + notify LLM |

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
