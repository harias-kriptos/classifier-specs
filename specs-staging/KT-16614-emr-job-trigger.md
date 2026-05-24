# Spec — emr-job-trigger

> Ticket: [KT-16614](https://kriptosteam.atlassian.net/browse/KT-16614)
> Status: accepted (Fase 1 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/emr-job-trigger`

---

## 1. Goal

Cuando aterriza un `.jsonl` en `decompressed_trees/`, lanzar un job EMR Serverless de `joyas-priorizer` pasándole el bucket y key como argumentos, para que el matching de keywords arranque automáticamente.

## 2. Non-goals

- Implementación del job EMR (eso es [KT-16616](https://kriptosteam.atlassian.net/browse/KT-16616)).
- Polling del estado del job — el cycle lo cierra el output S3 del job, no este Lambda.
- Retries del job mismo — EMR no auto-reintenta; falla manual via reprocesamiento del PUT.
- Validación previa de existencia del archivo (decisión: no hacer HeadObject — confiamos en el evento, EMR maneja 404 downstream).

## 3. User-visible behavior

Trigger: EventBridge sobre `PutObject` en `decompressed_trees/`, filter suffix `.jsonl`. Invocación asíncrona.

```
Input  S3 event sobre s3://decompressed_trees/{ent}/{sta}/{tree_id}.jsonl
Side effect: EMR Serverless StartJobRun con:
  entryPoint:            s3://{keywords_bucket}/emr/joyas-priorizer/job.py
  entryPointArguments:   ["{decompressed_bucket}", "{key}"]
  sparkSubmitParameters: --conf spark.dynamicAllocation.enabled=false
                         --conf spark.driver.memory=1g
                         --conf spark.executor.memory=1g
                         --conf spark.driver.cores=1
                         --conf spark.executor.cores=1
                         --conf spark.executor.instances=1
                         --archives s3://{keywords_bucket}/emr/joyas-priorizer/venv.tar.gz#environment
Output: log con jobRunId para tracking en CloudWatch.
```

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/tree_key.py` | `TreeKey` con parsing `{enterprise_id}/{station_id}/{tree_id}.jsonl` | Inválido → log WARN y descartar, no aborta. |
| `src/application/ports/emr_job_starter.py` | Protocol `start_job(entry_point, args, params) -> str (jobRunId)` | Retorna jobRunId o lanza excepción. |
| `src/application/usecases/trigger_emr_job.py` | Use case: validar key, derivar args, llamar starter | No depende de boto3 directo. |
| `src/adapters/boto3_emr_serverless.py` | Implementación de `EMRJobStarter` con boto3 client `emr-serverless` | Retries: 0 (cae al SQS retry del Lambda). |
| `src/config.py` | Env vars: `EMR_APPLICATION_ID`, `EMR_EXECUTION_ROLE_ARN`, `KEYWORDS_BUCKET` | Fail-fast en cold start si falta alguna. |
| `handler.py` | Cablea adapter + usecase | No testeable directo. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> dict:
    """Triggers EMR job. Retorna {'jobRunId': str} para tracing."""
```

Event:

```json
{
  "detail": {
    "bucket": {"name": "kriptos-{env}-decompressed-trees"},
    "object": {"key": "ent-001/station-A/uuid.jsonl"}
  }
}
```

Response (log + return):

```json
{"jobRunId": "00fb5jx2t...", "enterprise_id": "ent-001", "station_id": "station-A", "tree_id": "uuid"}
```

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — cliente `emr-serverless`
- `pydantic` — validación event shape
- `moto[emr-serverless]` (dev) — tests de StartJobRun

Sin libs nuevas.

## 7. Test plan

```
[ ] test_tree_key::test_parses_valid_three_segment_key
[ ] test_tree_key::test_rejects_two_segment_key
[ ] test_tree_key::test_rejects_jsonl_gz_suffix
[ ] test_tree_key::test_rejects_path_traversal
[ ] test_trigger_emr_job::test_calls_starter_with_correct_entry_point
[ ] test_trigger_emr_job::test_calls_starter_with_bucket_and_key_args
[ ] test_trigger_emr_job::test_calls_starter_with_dynamic_allocation_off
[ ] test_trigger_emr_job::test_calls_starter_with_venv_archive_param
[ ] test_trigger_emr_job::test_invalid_key_logs_warn_and_returns_without_calling_starter
[ ] test_trigger_emr_job::test_starter_failure_propagates_exception
[ ] test_boto3_emr_serverless::test_returns_jobrunid_from_response
[ ] test_config::test_fail_fast_if_emr_application_id_missing
[ ] test_handler::test_returns_jobrunid_dict
[ ] test_handler::test_logs_include_jobrunid_enterprise_station_tree
[ ] test_e2e::test_put_decompressed_triggers_emr_with_correct_args (moto)
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Elevation of privilege | Lambda tiene `iam:PassRole` para EMR — atacante con acceso al Lambda podría pasar otros roles | Lambda IAM permite `iam:PassRole` **solo** sobre el ARN específico de `EMR_EXECUTION_ROLE_ARN`, nunca `*`. Validado por DevOps en [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726). |
| Tampering | Event con key arbitrario apunta a bucket de otro enterprise | `TreeKey` parser rechaza paths con `..` o caracteres no whitelisteados (regex `^[a-zA-Z0-9\-_]+$` por segmento). Test: `test_rejects_path_traversal`. |
| DoS | Spam de PUTs causa MaxConcurrentRuns en EMR | EMR Serverless application configurada con max capacity 4 vCPU / 8GB. Si excede, jobs encolados. Aceptable. |

## 10. Resolved decisions

- **HeadObject preventivo**: NO. Confiamos en el evento EventBridge. Si el archivo no existe, EMR falla rápido downstream y se ve en CloudWatch. Ahorra una llamada S3 por cada PUT (potencialmente miles).
- **Empaquetado de `pyahocorasick`**: el `joyas-priorizer` requiere venv archive en S3. Este Lambda lo referencia en `sparkSubmitParameters` con `--archives s3://{keywords_bucket}/emr/joyas-priorizer/venv.tar.gz#environment`.

## 11. Open questions deferidas

Ninguna específica. Retry policy ya cubierta por SQS retry del Lambda (max receives 2 → DLQ).

## 12. Rollout

- Branch: `KT-16614-emr-job-trigger`
- Spec commit: `chore: spec for emr-job-trigger (KT-16614)`
- TDD: failing test commits → impl → refactor
- Quality gates verdes
- PR a `main` con `Implements specs/001-emr-job-trigger.md`
- Deploy via reusable workflow

**Bloqueante de deploy:** [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) (DevOps) está BLOCKED.
