# Spec — crown-validation-confirm

> Ticket: [KT-17027](https://kriptosteam.atlassian.net/browse/KT-17027)
> Status: accepted (Fase 1 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/crown-validation-confirm`

---

## 1. Goal

Cuando el cliente da OK final en la Plataforma Web (un único confirm global por enterprise), leer los candidatos aprobados de OpenSearch, materializarlos como `manifest.json` + N `station-{X}.jsonl` en S3 agrupados por station, y disparar Fase 2 (GSE). Es el bridge entre Fase 1 y Fase 2.

## 2. Non-goals

- UI / UX del botón "Confirmar" — Plataforma Web.
- Implementación del LLM downstream — caja negra Equipo IA.
- Re-validación después de confirm (segundo round con mismo cycle) — fuera de scope; nuevos rounds requieren nuevo cycle.
- Cancelación post-confirm — fuera de scope MVP.
- Confirm parcial por station — la validación es siempre a nivel enterprise (un confirm global).

## 3. User-visible behavior

Trigger: AppSync invoca el Lambda como resolver de la mutation `confirmValidation` (ver `graphql-schema-appsync.md`).

```graphql
mutation confirmValidation(
  enterprise_id: String!, cycle_id: ID!, actor: String!
): ConfirmResult!
```

Side effects:

```
1. Conditional read CYCLE.status; debe ser EXACTAMENTE "stations_complete".
2. Scroll OpenSearch query: cycle_id, validation_status IN [approved, manually_added].
3. Group by station_id.
4. Si total_files > 50k:
   - Split en N chunks de hasta 50k cada uno
   - Escribir N "manifest-chunk-NN.json" + N folders de station files
   - Último chunk lleva flag is_last_chunk=true
5. Si total_files <= 50k:
   - Escribir UN manifest.json single
6. Para cada station con files:
   PUT s3://validated_crown_jewels/{ent}/{cycle_id}/station-{X}.jsonl
7. PUT s3://validated_crown_jewels/{ent}/{cycle_id}/manifest.json (o manifest-chunk-NN.json)
8. Conditional SET CYCLE.status = "confirmed" (o "phase2_skipped" si total_files=0)
9. El PutObject del manifest dispara Fase 2 via EventBridge → SQS FIFO → gse-cycle-init.
```

Response (a AppSync):

```json
{
  "ok": true,
  "cycle_id": "uuid",
  "total_files": 47,
  "stations": ["station-A", "station-B"],
  "manifest_uri": "s3://kriptos-{env}-validated-crown-jewels/ent-001/uuid/manifest.json"
}
```

Errores AppSync:
- `INVALID_STATE` (cycle no está en `stations_complete`, posiblemente ya `confirmed`): error con `current_status` en extension.
- `NOT_FOUND` (cycle_id no existe).
- `BAD_REQUEST` (body inválido).

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/confirm_request.py` | Pydantic con `enterprise_id, cycle_id, actor` (sin `station_id`) | Strict. |
| `src/domain/manifest.py` | `Manifest` builder con stations[], total_files, optional chunks | Inmutable JSON. |
| `src/application/ports/opensearch_scroll.py` | Protocol con `scroll(query) -> Iterator[doc]` | Streaming, no carga todo en mem. |
| `src/application/ports/manifest_writer.py` | Protocol con `write_station_file`, `write_manifest`, `write_manifest_chunks` | S3 PUT directo. |
| `src/application/ports/state_store.py` | Protocol con `confirm_cycle_or_fail`, `mark_phase2_skipped` | Conditional updates. |
| `src/application/usecases/confirm_validation.py` | Use case principal | Idempotente: segundo call retorna 409 si ya confirmado. |
| `src/adapters/opensearch_scroll.py` | Scroll API con batches de 1000 + IAM SigV4 | Cierra scroll context al final. |
| `src/adapters/boto3_s3_writer.py` | Streaming PUT para station files grandes | Usa multipart si > 5MB. |

## 5. Inputs and outputs

AppSync resolver event:

```json
{
  "info": {"fieldName": "confirmValidation"},
  "arguments": {
    "enterprise_id": "ent-001",
    "cycle_id": "uuid",
    "actor": "user-123"
  },
  "identity": {...}
}
```

Output del manifest.json:

```json
{
  "enterprise_id": "ent-001",
  "cycle_id": "uuid",
  "process_type": "crown_validated",
  "stations": ["station-A", "station-B"],
  "stations_expected": 2,
  "total_files": 47,
  "is_chunked": false,
  "is_last_chunk": true,
  "confirmed_at": "2026-05-23T18:00:00Z",
  "confirmed_by": "user-123",
  "normalize_version": "1.0.0"
}
```

Cada `station-{X}.jsonl` contiene una línea por archivo aprobado/agregado.

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — S3 PUT, DDB
- `opensearch-py` + `requests-aws4auth` — scroll con IAM SigV4
- `pydantic` — validación

## 7. Test plan

```
[ ] test_confirm_request::test_no_station_id_field (drop confirmed)
[ ] test_confirm_request::test_rejects_invalid_enterprise_id
[ ] test_manifest::test_builds_with_all_required_fields
[ ] test_manifest::test_zero_files_still_writes_manifest_with_total_zero
[ ] test_manifest::test_split_at_50k_creates_chunks
[ ] test_manifest::test_last_chunk_has_is_last_flag
[ ] test_opensearch_scroll::test_uses_iam_sigv4_auth
[ ] test_opensearch_scroll::test_iterates_all_pages
[ ] test_opensearch_scroll::test_closes_scroll_context_on_exit
[ ] test_manifest_writer::test_writes_one_jsonl_per_station
[ ] test_manifest_writer::test_writes_manifest_after_station_files
[ ] test_state_store::test_confirm_cycle_conditional_succeeds_when_stations_complete
[ ] test_state_store::test_confirm_cycle_fails_when_status_is_scanning
[ ] test_state_store::test_confirm_cycle_fails_when_status_is_already_confirmed
[ ] test_confirm_validation::test_writes_manifest_and_transitions_cycle_to_confirmed
[ ] test_confirm_validation::test_zero_approved_transitions_to_phase2_skipped
[ ] test_confirm_validation::test_double_click_returns_invalid_state_error
[ ] test_confirm_validation::test_50k_files_split_into_chunks
[ ] test_handler::test_appsync_event_shape_parsed
[ ] test_handler::test_logs_include_actor_and_correlation_ids
[ ] test_e2e::test_full_confirm_results_in_eventbridge_trigger_to_phase2
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Spoofing | Actor confirma cycle de otro enterprise | AppSync auth (Cognito) valida tenant upstream. Defensive: este Lambda valida que `enterprise_id` del request matchea con `PK` del CYCLE. Test: `test_cross_enterprise_returns_not_found`. |
| DoS | Confirm con cycle de 500k+ archivos → Lambda timeout | Mem 1024MB + scroll API streaming + split a 50k files. Si total_files excede umbral split en N chunks. |
| Tampering | Race entre 2 confirms del mismo cycle | Conditional `IF status="stations_complete"` gana exactly-once. Segundo → INVALID_STATE. |
| Repudiation | No traza de quién confirmó | `actor` en manifest + DDB + logs. Test: `test_logs_include_actor`. |

## 10. Resolved decisions

- **Drop `station_id` opcional del body**: la validación es siempre a nivel enterprise — un confirm global. El backend produce manifests por station internamente.
- **Estado válido para confirm**: EXACTAMENTE `stations_complete`. Si `scanning` (no todas terminaron) o `confirmed`+ (ya confirmado) → INVALID_STATE.
- **Manifest split umbral**: 50k files por manifest. Más allá → N chunks con `is_last_chunk` flag en el último. `gse-cycle-init` espera al chunk con flag para finalizar el cycle.
- **OS auth**: IAM SigV4 con `requests-aws4auth`.
- **Canal de invocación**: AppSync resolver (no API GW). Event shape de AppSync.
- **Transición de estado**:
  - `total_files > 0` → CYCLE pasa a `confirmed`. El PutObject del manifest.json dispara Fase 2.
  - `total_files == 0` (cliente rechazó todo) → CYCLE pasa a `phase2_skipped`. Manifest se escribe con `total_files=0` pero NO dispara Fase 2 (downstream lo filtra).

## 11. Open questions deferidas

Ninguna específica.

## 12. Rollout

- Branch: `KT-17027-crown-validation-confirm`
- Spec commit + TDD commits (incluyendo perf test de 50k+ files)
- Quality gates verdes
- PR a `main` con `Implements specs/001-crown-validation-confirm.md`
- Deploy via reusable workflow

**Bloqueantes de deploy:** [KT-17015](https://kriptosteam.atlassian.net/browse/KT-17015) (Lambda + bucket validated + SQS FIFO + AppSync resolver) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB) + [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) (OS index) + AppSync schema configurado por Plataforma Web.
