# Spec — tree-uncompressor

> Ticket: [KT-16613](https://kriptosteam.atlassian.net/browse/KT-16613)
> Status: accepted (Fase 1 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/tree-uncompressor`

---

## 1. Goal

Cuando el agente sube un `.jsonl.gz` al bucket `compressed_trees/`, descomprimir en streaming y depositar el `.jsonl` en `decompressed_trees/`, propagando intactos los 7 headers `x-amz-meta-*` para que la cadena downstream (`emr-job-trigger` → `joyas-priorizer`) preserve la identidad del enterprise/station/tree.

## 2. Non-goals

- Validación del contenido del NDJSON (lo hace `joyas-priorizer`).
- Manejo del Cloud Agent (que sube directo a `decompressed_trees` vía IAM) — flujo distinto.
- Reintentos de archivos corruptos — falla rápido, mensaje a DLQ.
- Cifrado en tránsito custom — usa el default S3 (TLS) + AES-256 server-side.

## 3. User-visible behavior

Trigger: EventBridge sobre `PutObject` en `compressed_trees/`, filter suffix `.jsonl.gz`. Invocación asíncrona (sin response síncrono).

```
Input  S3 object: s3://compressed_trees/{ent}/{sta}/{tree_id}.jsonl.gz
       Headers:   x-amz-meta-enterprise-id, -station-id, -total-lines,
                  -fingerprint, -uploaded-at, -agent-version, -tree-id
                  + server-side encryption

Output S3 object: s3://decompressed_trees/{ent}/{sta}/{tree_id}.jsonl
       Headers:   los 7 anteriores propagados intactos.
```

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/object_key.py` | Tipo `ObjectKey` con regex `^[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-]+\.jsonl\.gz$` | Solo paths whitelisteados (anti path-traversal). |
| `src/domain/object_metadata.py` | Tipo `ObjectMetadata` con los 7 headers como atributos tipados | Inmutable; clone exacto para PUT destino. |
| `src/application/ports/s3_stream.py` | Protocol con `head`, `stream_get`, `multipart_put` | Adapter `boto3` lo implementa. |
| `src/application/usecases/decompress_tree.py` | Use case que orquesta head → stream gunzip → multipart upload | No depende de boto3 directo. |
| `src/adapters/boto3_s3_stream.py` | Implementación con streaming GET + multipart PUT 8MB chunks | Aborta multipart si excepción. |
| `handler.py` | Lambda entrypoint, cablea adapter + usecase | No testeable directo. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """Descomprime .jsonl.gz → .jsonl propagando metadata. No retorna."""
```

Event shape (EventBridge → Lambda direct invoke):

```json
{
  "detail": {
    "bucket": {"name": "kriptos-{env}-compressed-trees"},
    "object": {"key": "ent-001/station-A/0ce84cb1-....jsonl.gz", "size": 12345678}
  }
}
```

## 6. Dependencies

- `aws-lambda-powertools[tracer]` — logs JSON + X-Ray
- `boto3` — S3 streaming (`get_object` con `Body.iter_chunks`) + multipart upload
- `pydantic` — validación del event shape
- Standard lib `gzip` — streaming gunzip
- `moto[s3]` (dev) — tests

Sin libs nuevas.

## 7. Test plan

```
[ ] test_object_key::test_rejects_path_traversal
[ ] test_object_key::test_accepts_valid_three_segment_key
[ ] test_object_key::test_rejects_missing_jsonl_gz_suffix
[ ] test_object_metadata::test_parses_all_seven_headers_from_head_response
[ ] test_object_metadata::test_raises_if_required_header_missing
[ ] test_decompress_tree::test_happy_path_propagates_all_headers
[ ] test_decompress_tree::test_aborts_multipart_on_gzip_corrupted
[ ] test_decompress_tree::test_skips_when_source_404
[ ] test_decompress_tree::test_utf8_invalid_line_logs_warn_and_continues
[ ] test_decompress_tree::test_streams_5gb_decompressed_without_oom
[ ] test_handler::test_invalid_event_shape_logs_error_and_returns
[ ] test_handler::test_passes_event_to_usecase
[ ] test_e2e::test_put_compressed_lands_decompressed_with_metadata (moto)
[ ] test_e2e::test_corrupted_gzip_no_destination_object_created (moto)
[ ] test_e2e::test_jsonl_with_invalid_utf8_line_still_lands_in_destination (moto)
```

## 8. Eval impact

No aplica — sin componente LLM.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Metadata alterada entre source y destino | El usecase **clona** los headers del HEAD response al multipart PUT. Test: `test_happy_path_propagates_all_headers`. |
| DoS | Archivo `.jsonl.gz` "zip bomb" inflado a TB | Memoria limitada a 1024 MB + streaming (no carga full en mem). Si excede timeout 300s → falla, mensaje a DLQ. Test: `test_streams_5gb_decompressed_without_oom`. |
| Info disclosure | Logs contienen contenido del NDJSON | Logger **NUNCA** loguea el body, solo metadata. Test: `test_logs_do_not_contain_jsonl_lines`. |
| Repudiation | No hay traza de qué tree se descomprimió | Logs estructurados con `tree_id, enterprise_id, station_id, request_id`. |

No hay surface nueva crítica — Lambda interna sin endpoint público.

## 10. Resolved decisions

- **UTF-8 inválido a media descompresión**: log WARN y continuar. Una línea malformed no aborta el archivo completo (millones de líneas posibles). `joyas-priorizer` downstream salta JSON inválido también.
- **Política con destino corrupto**: si el GET source falla a mitad → abortar multipart, log ERROR, mensaje a DLQ. No reintentar localmente.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | Lifecycle del bucket destino (retención días) | DevOps | Al provisionar bucket (KT-16726) |

## 12. Rollout

- Branch: `KT-16613-tree-uncompressor`
- Spec commit: `chore: spec for tree-uncompressor (KT-16613)`
- TDD: failing test commits → impl commits → refactor
- Quality gates: `pytest --cov-fail-under=80`, `ruff check + format`, `mypy --strict src`, Snyk + SonarCloud verdes
- PR a `main` con `Implements specs/001-tree-uncompressor.md`
- Deploy via reusable workflow `kriptos-io/unlockstack`

**Bloqueante de deploy:** [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) (DevOps) está BLOCKED. Skill 04 (TDD impl) puede avanzar en local con `moto`; deploy queda en espera.
