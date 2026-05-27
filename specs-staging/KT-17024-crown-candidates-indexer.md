# Spec — crown-candidates-indexer

> Ticket: [KT-17024](https://kriptosteam.atlassian.net/browse/KT-17024)
> Status: accepted (Fase 1 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/crown-candidates-indexer`

---

## 1. Goal

Por cada `matches.jsonl` que escribe `joyas-priorizer` en `crown_jewels/{ent}/{sta}/`, indexar cada match en OpenSearch como candidato pre-validación, registrar la STATION en la DDB consolidada (`classifier-cycles-state`), y manejar la lógica de late-arrival STATIONs cuando aparecen tarde.

## 2. Non-goals

- Generar matches (eso es KT-16616).
- Barrier enterprise-level (eso es KT-17025).
- Mutaciones de validación (eso es KT-17026).
- Materialización del set validado (eso es KT-17027).

## 3. User-visible behavior

Trigger: SQS `crown-candidates-indexer-queue` ← EventBridge sobre PutObject en `crown_jewels/` suffix `.jsonl`.

```
Input:  s3://crown_jewels/{ent}/{sta}/matches.jsonl (NDJSON con matches o vacío)
Side effects:
  1. OpenSearch bulk index al índice `crown_jewel_candidates` (N docs, uno por match).
  2. DDB classifier-cycles-state:
     - Get-or-create CYCLE (PK=ent, SK=CYCLE#{cycle_id})
       - Si nuevo: consulta KEM → stations_expected; PUT condicional.
       - Si existe: usa el cycle_id existente.
     - PUT STATION (PK=ent, SK=STATION#{sta}#{cycle_id})
       - Si STATION nueva no contemplada en stations_expected original
         Y CYCLE.status ∈ {scanning, stations_complete}:
         → ADD CYCLE.stations_expected = 1 (late-arrival merge)
       - Si CYCLE.status ∈ {confirmed, phase2_collecting, complete}:
         → Descartar con log WARN (entra en próximo cycle)
       - Setear: scan_status="complete", candidates_count=N, barrier_counted=false.
```

Sin response síncrono.

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/candidate.py` | `Candidate` con `candidate_id = sha256(ent\|sta\|path)` y los 22 campos del doc OS | Inmutable, validado. |
| `src/domain/cycle.py` | `Cycle` con `status` enum (scanning → stations_complete → confirmed → phase2_collecting → complete) | Estados strict. |
| `src/domain/late_arrival.py` | Lógica pura: `(cycle.status, station_already_known) -> Accept \| Merge \| Discard` | Sin I/O. |
| `src/application/ports/kem_client.py` | Protocol `get_stations_expected(ent) -> int` | Sin cache. |
| `src/application/ports/opensearch_indexer.py` | Protocol `bulk_index(docs: list[dict]) -> BulkResult` | Chunks tamañables. |
| `src/application/ports/state_store.py` | Protocol DDB con `get_or_create_cycle`, `put_station_or_merge_late` | Conditional writes. |
| `src/application/usecases/index_candidates.py` | Use case principal | Idempotente por `candidate_id` y `(ent, sta, cycle_id)`. |
| `src/adapters/boto3_kem_http_client.py` | HTTP client con API key de Secrets Manager | Timeout 5s, retries 3. |
| `src/adapters/opensearch_indexer.py` | Cliente OS con `opensearch-py` + IAM SigV4 (`requests-aws4auth`) | Chunk size configurable via env. |
| `src/adapters/boto3_state_store.py` | DDB adapter con conditional writes | `attribute_not_exists` para create. |
| `src/config.py` | Env: `KEM_SECRET_ARN`, `OPENSEARCH_ENDPOINT`, `OPENSEARCH_INDEX`, `STATE_TABLE_NAME`, `BULK_CHUNK_SIZE=1000` | Fail-fast cold start. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> dict:
    """Indexa matches y registra STATION. Retorna {indexed, station_id, cycle_id, action}.
    action ∈ {created, merged_late, discarded_late}."""
```

SQS message body = S3 event:

```json
{"detail": {"bucket": {"name": "kriptos-{env}-crown-jewels"}, "object": {"key": "ent-001/station-A/matches.jsonl"}}}
```

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — S3, DDB, Secrets Manager
- `opensearch-py` — cliente oficial AWS para OpenSearch
- `requests-aws4auth` — NEW. Firma requests OS con SigV4 desde IAM role del Lambda. Sin secrets que rotar.
- `pydantic` — validación
- `moto[s3,dynamodb,secretsmanager]` (dev) + opensearchpy mock — tests

## 7. Test plan

```
[ ] test_candidate::test_candidate_id_deterministic_sha256
[ ] test_candidate::test_validates_required_fields
[ ] test_cycle::test_status_transitions_allowed
[ ] test_late_arrival::test_new_station_in_scanning_merges_and_increments_expected
[ ] test_late_arrival::test_new_station_in_stations_complete_merges_and_increments
[ ] test_late_arrival::test_new_station_in_confirmed_discards
[ ] test_late_arrival::test_known_station_reprocess_idempotent
[ ] test_kem_client::test_returns_stations_expected_from_response
[ ] test_kem_client::test_raises_on_404
[ ] test_opensearch_indexer::test_uses_iam_sigv4_auth
[ ] test_opensearch_indexer::test_bulk_index_uses_configured_chunk_size
[ ] test_opensearch_indexer::test_bulk_index_returns_per_doc_errors
[ ] test_opensearch_indexer::test_retries_failed_docs_up_to_n
[ ] test_state_store::test_get_or_create_cycle_creates_when_absent
[ ] test_state_store::test_get_or_create_cycle_returns_existing
[ ] test_state_store::test_put_station_idempotent_on_reprocess
[ ] test_index_candidates::test_empty_matches_marks_station_complete_with_zero_count
[ ] test_index_candidates::test_n_matches_indexed_and_station_count_n
[ ] test_index_candidates::test_malformed_jsonl_line_skipped_with_warn
[ ] test_handler::test_logs_include_correlation_ids_and_action
[ ] test_e2e::test_put_matches_jsonl_results_in_os_docs_and_ddb_row
[ ] test_e2e::test_reprocess_same_file_idempotent
[ ] test_e2e::test_late_arrival_after_confirmed_discards_with_warn
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Atacante con acceso a OS escribe docs falsos | OS access policy restringe `ESHttpPost` solo a este Lambda role + N3/N4. IAM SigV4 firma cada request. |
| Repudiation | Sin traza de qué Lambda invocation indexó qué docs | Cada doc OS incluye `indexed_at`. Logs Lambda incluyen `request_id, candidates_count, action`. |
| Info disclosure (KEM key) | Si Lambda role lee el secret y loguea por error | Logger filtra patrones `kem-api-key`; secret nunca pasa por log. Test: `test_logs_do_not_contain_kem_key`. |
| DoS | matches.jsonl con millones de líneas → OOM | Lambda mem 512MB + procesamiento en streaming. Si excede timeout 300s → SQS retry. |

## 10. Resolved decisions

- **OS auth**: IAM SigV4 con `requests-aws4auth`. Cada Lambda firma sus requests con su execution role. Sin secrets que rotar, permisos granulares en access policy del dominio.
- **Cache de KEM**: SIN cache. 1 llamada por CYCLE nuevo (cuando aterriza la primera matches.jsonl de la enterprise). Las siguientes N-1 stations reusan el CYCLE existente. Tráfico estimado: ~1-2 calls por enterprise por iteración del pipeline.
- **Bulk chunk size**: 1000 docs default + env var `BULK_CHUNK_SIZE` override para tunear sin redeploy.
- **Late-arrival STATION**:
  - Si CYCLE en `scanning` o `stations_complete` Y la STATION es nueva (no en `stations_expected` original): **mergear** — incrementar `CYCLE.stations_expected += 1`, indexar candidatos, agregar STATION. Barrier re-evalúa en próximo stream event. UX: progress bar puede regresar de "5/5" a "5/6" momentáneamente.
  - Si CYCLE en `confirmed`/`phase2_collecting`/`complete`: **descartar** con log WARN. Station entra al próximo cycle.

## 11. Open questions deferidas

Ninguna específica.

## 12. Rollout

- Branch: `KT-17024-crown-candidates-indexer`
- Spec commit + TDD commits
- Quality gates verdes
- PR a `main` con `Implements specs/001-crown-candidates-indexer.md`
- Deploy via reusable workflow

**Bloqueantes de deploy:** [KT-17012](https://kriptosteam.atlassian.net/browse/KT-17012) (Repo) + [KT-17078](https://kriptosteam.atlassian.net/browse/KT-17078) (Lambda + SQS + EventBridge + IAM) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB con Stream) + [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) (OS índice nuevo en cluster existente).
