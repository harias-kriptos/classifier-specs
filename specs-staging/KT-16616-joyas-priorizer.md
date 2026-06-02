# Spec — joyas-priorizer (PySpark)

> Ticket: [KT-16616](https://kriptosteam.atlassian.net/browse/KT-16616)
> Status: accepted (Fase 1 cerrada 2026-05-23, MOD aplicado)
> Repo destino futuro: `kriptos-io/joyas-priorizer`

---

## 1. Goal

Para cada árbol descomprimido en `decompressed_trees/{ent}/{sta}/{tree}.jsonl`, encontrar todos los archivos cuyo **nombre normalizado** matchea alguna keyword multi-token del enterprise (algoritmo Aho-Corasick), y escribir el subconjunto en `crown_jewels/{ent}/{sta}/matches.jsonl` con la metadata de qué patrón matcheó cada archivo — incluso si el resultado es vacío.

## 2. Non-goals

- Generación de keywords — responsabilidad del Equipo IA (LLM Bedrock + post-process).
- Validación humana de matches — `crown-validation-handler` (KT-17026).
- Búsqueda en contenido de archivos (opera solo sobre `name`, no abre archivos).
- Filtrar patrones de un solo token o muy genéricos — responsabilidad del generador, no del matcher.

## 3. User-visible behavior

Invocación: `emr-job-trigger` (KT-16614) llama `EMR StartJobRun` con args `[decompressed_bucket, tree_key]`.

```
Input:  s3://decompressed_trees/{ent}/{sta}/{tree_id}.jsonl   (NDJSON con 5 campos por línea)
        s3://keywords/{ent}.jsonl                              (JSONL con N patrones)
Output: s3://crown_jewels/{ent}/{sta}/matches.jsonl            (NDJSON con N matches o vacío)
```

Match line ejemplo de output:

```jsonl
{"name":"Plan-Estrategico-Q1","path":"/Users/foo/Estratégico/","size":245780,"extension":"pdf","modified_date":"2026-04-14T09:15:22Z","name_normalized":"plan estrategico q","path_normalized":"users foo estrategico","matched_patterns":["plan estrategico quinquenal grupo bancario"],"matched_business_areas":["estrategia planeacion"],"original_category":["Plan Estratégico Quinquenal Grupo Bancario"],"original_business_area":["Estrategia & Planeación"],"normalize_version":"1.0.0"}
```

**Matching strategy**: el matcher Aho-Corasick busca patrones **únicamente sobre `name_normalized`** (no incluye `path_normalized`). El `path_normalized` se calcula y persiste para uso downstream (filtros por carpeta en UI) pero NO contribuye al match. Esta decisión privilegia precision sobre recall.

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/normalize.py` | Función `normalize(raw: str) -> str` — copia exacta de `classifier-specs/.../normalize_category.py` | Determinística, `NORMALIZE_VERSION = "1.0.0"`. |
| `src/domain/pattern.py` | Tipo `Pattern` con `category, original_category, business_area, original_business_area` | Inmutable. |
| `src/domain/file_record.py` | Tipo `FileRecord` con 5 campos + computed `name_normalized`, `path_normalized` | Validado por `pydantic`. |
| `src/application/ports/keyword_loader.py` | Protocol `load(enterprise_id) -> list[Pattern]` | Lee JSONL de S3; archivo faltante → lista vacía + log WARN. |
| `src/application/usecases/match_patterns.py` | Use case que recibe DataFrame + broadcast Aho-Corasick automaton y produce filtered DataFrame con `matched_patterns` | No depende de SparkSession directo. |
| `src/adapters/s3_keyword_loader.py` | Implementación con boto3 | Skipea líneas JSONL malformed, sigue. |
| `src/adapters/spark_pipeline.py` | Orquestación Spark: read NDJSON → normalize via `pandas_udf` → match via broadcast Aho-Corasick sobre name_normalized → write JSONL | `coalesce(1)` final; `mode("overwrite")`. |
| `job.py` (entrypoint EMR) | Arg parsing, SparkSession init, cablea adapters + usecase | No testeable directo en unit. |

## 5. Inputs and outputs

```python
def main(decompressed_bucket: str, tree_key: str) -> None:
    """Ejecuta el matching y escribe matches.jsonl. Exit code 0 siempre que no haya excepción no controlada."""
```

Formato keywords JSONL:

```jsonl
{"category":"plan estrategico quinquenal grupo bancario","original_category":"Plan Estratégico Quinquenal Grupo Bancario","business_area":"estrategia planeacion","original_business_area":"Estrategia & Planeación"}
```

Formato tree NDJSON (input):

```jsonl
{"name": "backup-old-491", "path": "/Users/carla.vega/Documentos/RRHH-General/", "size": 6915320, "extension": "bak", "modified_date": "2024-08-20T12:00:00Z"}
```

## 6. Dependencies

- **`pyspark`** (provisto por EMR Serverless runtime emr-7.0.0) — no se empaqueta
- **`pyahocorasick`** — NEW. Empaquetado en **virtual environment archive `.tar.gz`** subido a `s3://{keywords_bucket}/emr/joyas-priorizer/venv.tar.gz`, referenciado con `--archives` en `sparkSubmitParameters`. Versión pineada en el archive.
- **`pandas`** (provisto por EMR runtime) — `pandas_udf` vectorizado para normalización
- **`boto3`** — leer keywords desde S3
- Standard lib `unicodedata`, `re` — usados por `normalize()`

## 7. Test plan

```
[ ] test_normalize::test_strips_accents_and_lowercases
[ ] test_normalize::test_removes_digits
[ ] test_normalize::test_removes_roman_only_tokens
[ ] test_normalize::test_collapses_whitespace
[ ] test_normalize::test_corpus_100_filenames_bit_identical_to_reference_python
[ ] test_pattern::test_validates_required_fields
[ ] test_file_record::test_parses_5_field_ndjson_line
[ ] test_s3_keyword_loader::test_loads_jsonl_skipping_malformed_lines
[ ] test_s3_keyword_loader::test_missing_file_returns_empty_list_with_warn
[ ] test_match_patterns::test_aho_corasick_match_uses_only_name_normalized_not_path
[ ] test_match_patterns::test_no_match_returns_empty_dataframe
[ ] test_match_patterns::test_match_preserves_original_category_and_business_area
[ ] test_spark_pipeline::test_writes_empty_matches_jsonl_when_no_match (CRITICAL)
[ ] test_spark_pipeline::test_overwrite_mode_replaces_previous_output
[ ] test_spark_pipeline::test_performance_1M_files_2K_patterns_under_5min (benchmark)
[ ] test_e2e::test_full_job_locally_on_sample_tree (PySpark local mode)
```

**Test crítico**: `test_corpus_100_filenames_bit_identical_to_reference_python` verifica que `normalize()` da output bit-idéntico al de `classifier-specs/.../normalize_category.py`. Si falla, drift entre IA generator y backend matcher.

## 8. Eval impact

**Sí — el matching afecta calidad downstream.**

### Eval corpus

```jsonl
{"id":"match-001","fixture":"evals/corpus/banking-tree.jsonl","keywords_fixture":"evals/corpus/banking-keywords.jsonl","expected":{"matches_count":47,"sample_matches":[{"name":"Plan-Estrategico-Q1-2026","matched_patterns":["plan estrategico quinquenal grupo bancario"]}]}}
{"id":"match-002-no-results","fixture":"evals/corpus/empty-match-tree.jsonl","expected":{"matches_count":0,"output_file_exists":true}}
```

### Expected delta

| Metric | Baseline (POC v1 substring) | After Aho-Corasick (name only) |
|---|---|---|
| Recall on banking corpus | ~60% (perdía con tildes/dígitos) | ≥90% |
| Precision on banking corpus | ~85% | ≥95% (mejor por usar solo name) |
| Job duration (1M files × 2K patterns) | TBD | < 5 min |

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | Keywords contienen patrones sensibles del cliente (nombres reales de iniciativas) | Bucket `keywords/` con IAM restricto solo al EMR exec role + principal del Equipo IA. KMS server-side encryption. |
| Info disclosure | Output `matches.jsonl` contiene paths reales del filesystem | Bucket `crown_jewels/` con public-access block + EventBridge restringido. Acceso de lectura solo a `crown-candidates-indexer` (KT-17024 IAM). |
| Tampering (silent) | Cambio de `normalize_category.py` sin bumpear `NORMALIZE_VERSION` → drift vs IA generator | Test `test_corpus_100_filenames_bit_identical_to_reference_python` falla si hay drift. Bump policy en Global Question GQ4. |

## 10. Resolved decisions

- **Match target**: solo `name_normalized` (no incluir `path_normalized`). Mayor precision, menor recall. `path_normalized` se persiste en OS para UX (filtros por folder en UI) pero NO contribuye al match Aho-Corasick.
- **Algoritmo**: Aho-Corasick sobre patrones broadcast (`pyahocorasick`). NO substring naïve, NO UDF Python row-by-row. Aplicado vía `pandas_udf` vectorizado.
- **Empaquetado de `pyahocorasick`**: venv archive `.tar.gz` en S3, referenciado con `--archives`. Versión pineada. Más reproducible que pip install en bootstrap.
- **Formato keywords**: JSONL (no JSON), una línea por patrón.
- **Bucket destino**: `crown_jewels` (NO `crown_jewel_candidates` — el bucket ya existe por [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728), semánticamente contiene candidatos pre-validación).
- **Archivo vacío obligatorio**: si 0 matches, igual escribir `matches.jsonl` vacío. Señal para que `crown-candidates-indexer` (KT-17024) sepa que la station terminó.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | Política con patrones de 1 token después de normalizar | Equipo IA (generador) | Si surge problema de recall/precision |

## 12. Rollout

- Branch: `KT-16616-joyas-priorizer`
- Spec commit: `chore: spec for joyas-priorizer (KT-16616)`
- TDD commits + venv archive build pipeline
- Quality gates verdes
- Eval run: `evals/run.py --corpus banking` con corpus fixture; comparar contra baseline; commitear en `evals/results/`
- PR a `main` con `Implements specs/001-joyas-priorizer.md`
- Deploy del `job.py` a `s3://{keywords_bucket}/emr/joyas-priorizer/` via reusable workflow

**Bloqueante de deploy:** Ninguno — infra ya está ([KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) DONE).
